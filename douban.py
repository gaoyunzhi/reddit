#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram_util import matchKey, cutCaption, clearUrl, splitCommand, autoDestroy, log_on_fail, compactText
import sys
import os
from telegram.ext import Updater, MessageHandler, Filters
import export_to_telegraph
import time
import yaml
import web_2_album
import album_sender
from soup_get import SoupGet, Timer
from db import DB
import threading

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)
export_to_telegraph.token = credential['telegraph_token']

tele = Updater(credential['bot_token'], use_context=True)
debug_group = tele.bot.get_chat(-1001198682178)

last_loop_time = {}

sg = SoupGet()
db = DB()

def dataCount(item):
	for x in item.find_all('span', class_='count'):
		r = int(x.get('data-count'))
		if r:
			yield r

def wantSee(item, page, channel_name):
	if matchKey(str(item.parent), ['people/gyz', '4898454']):
		return True
	if matchKey(str(item), db.getBlacklist(channel_name)):
		return False
	require = 120 + page
	if 'people/renjiananhuo' in str(item.parent):
		require *= 4 # 这人太火，发什么都有人点赞。。。
	if sum(dataCount(item)) > require:
		return True
	return False

def getSource(item):
	new_status = item
	while 'new-status' not in new_status.get('class'):
		new_status = new_status.parent
	if new_status.get('data-sid'):
		return 'https://www.douban.com/people/%s/status/%s/' % \
			(new_status['data-uid'], new_status['data-sid'])

def getCap(quote, url):
	if '_' in url:
		url = '[%s](%s)' % (url, url)
	return cutCaption(quote, url, 4000)

def getResult(post_link, item):
	raw_quote = item.find('blockquote') or ''
	topic = item.find('p', class_='topic-say')
	topic = topic and topic.text
	if topic and raw_quote:
		raw_quote.insert(0, '【%s】' % topic)
		
	quote = export_to_telegraph.exportAllInText(raw_quote)
	quote = quote.replace('\n', '\n\n')
	for _ in range(5):
		quote = quote.replace('\n\n\n', '\n\n')
	quote = compactText(quote).strip('更多转发...').strip()

	r = web_2_album.Result()

	note = item.find('div', class_='note-block')
	if (note and note.get('data-url')) or matchKey(post_link, 
			['https://book.douban.com/review/', 'https://www.douban.com/note/']):
		note = (note and note.get('data-url')) or post_link
		url = export_to_telegraph.export(note, force=True) or note
		r.cap = getCap(quote, url)
		return r

	if item.find('div', class_='url-block'):
		url = item.find('div', class_='url-block')
		url = url.find('a')['href']
		url = clearUrl(export_to_telegraph.export(url) or url)
		r.cap = getCap(quote, url)
		return r

	if '/status/' in post_link:
		r = web_2_album.get(post_link, force_cache=True)
		r.cap = quote
		if r.imgs or r.video:
			return r

	if quote and raw_quote.find('a', title=True, href=True):
		r.cap = quote
		return r

def findCreatedAt(item):
	if not 'item':
		return None
	create_block = item.find('span', class_='created_at')
	if not create_block:
		return None
	return create_block.get('title')

def postTele(douban_channel, item, timer):
	if not item or not item.find('span', class_='created_at'):
		if '仅自己可见' in str(item):
			return # 被审核掉的广播
		print('no created at')
		print(item)
		# see how often this happen...
		return
	post_link = item.find('span', class_='created_at').find('a')['href']
	source = getSource(item) or post_link
	source = source.strip()
	post_link = post_link.strip()

	if db.exist(douban_channel.username, source):
		return 'existing'
	if db.exist(douban_channel.username, post_link):
		return 'repeated_share'

	result = getResult(post_link, item)
	if result:
		timer.wait(len(result.imgs or [1]) * 25)
		try:
			r = album_sender.send(douban_channel, source, result)
		except Exception as e:
			print('send_failure', e, source)
			return
		db.addToExisting(douban_channel.username, post_link)
		db.addToExisting(douban_channel.username, source)
		return 'sent'

@log_on_fail(debug_group)
def processChannel(name, url_prefix):
	existing = 0
	print('start processing %s' % name)
	timer = Timer()

	douban_channel = tele.bot.get_chat('@' + name)
	if 'status' in url_prefix:
		page_range = range(50, 0, -1)
	else:
		page_range = range(1, 100)
	global_max_created_at = ''
	for page in page_range:
		if 'test' in sys.argv:
			print('page: %d' % page)
		url = url_prefix + '?p=' + str(page)
		items = list(sg.getSoup(url, db.getCookie(name))
			.find_all('div', class_='status-item'))
		if not items and 'status' not in url_prefix:
			debug_group.send_message('Cookie expired for channel: %s' % name)
			return
		max_created_at = ''
		for item in items:
			created_at = findCreatedAt(item)
			if created_at:
				max_created_at = max(max_created_at, created_at)
			if not wantSee(item, page, name):
				continue
			r = postTele(douban_channel, item, timer)
			if r == 'sent' and 'skip' in sys.argv:
				return # testing mode, only send one message
			if r == 'existing':
				existing += 1
			elif r == 'sent':
				existing = 0
		global_max_created_at = max(global_max_created_at, max_created_at)
		if existing > 10 or page * existing > 200:
			break
		if max_created_at < last_loop_time.get(name, ''):
			break
	last_loop_time[name] = global_max_created_at
	print('channel %s finished by visiting %d page' % (name, page))

def removeOldFiles(d):
	try:
		for x in os.listdir(d):
			if os.path.getmtime(d + '/' + x) < time.time() - 60 * 60 * 72 or \
				os.stat(d + '/' + x).st_size < 400:
				os.system('rm ' + d + '/' + x)
	except:
		pass

@log_on_fail(debug_group)
def loopImp():
	removeOldFiles('tmp')
	sg.reset()
	for name in db.getChannels():
		if name == 'today_read':
			url_prefix = 'https://www.douban.com/people/gyz/statuses'
		elif name == 'douban_one':
			url_prefix = 'https://www.douban.com/people/139444387/statuses'
		else:
			url_prefix = 'https://www.douban.com/'
		processChannel(name, url_prefix)

def loop():
	loopImp()
	threading.Timer(60 * 60 * 2, loop).start() 

@log_on_fail(debug_group)
def private(update, context):
	update.message.reply_text('Add me to public channel, then use /d_sc to set your douban cookie')

def commandInternal(msg):
	command, text = splitCommand(msg.text)
	if matchKey(command, ['/d_sc', 'set_cookie']):
		return db.setCookie(msg.chat.username, text)
	if matchKey(command, ['/d_ba', 'blacklist_ba']):
		return db.blacklistAdd(msg.chat.username, text)
	if matchKey(command, ['/d_br', 'blacklist_br']):
		return db.blacklistRemove(msg.chat.username, text)
	if matchKey(command, ['/d_bl', 'blacklist_list']):
		return 'blacklist:\n' + '\n'.join(db.getBlacklist(msg.chat.username))

@log_on_fail(debug_group)
def command(update, context):
	msg= update.channel_post
	if not msg.text.startswith('/d'):
		return
	r = commandInternal(msg)
	if not r:
		return
	autoDestroy(msg.reply_text(r), 0.1)
	msg.delete()

if __name__ == '__main__':
	if 'debug' in sys.argv or 'now' in sys.argv:
		threading.Timer(1, loop).start()
	else:
		threading.Timer(60 * 60, loop).start()
	tele.dispatcher.add_handler(MessageHandler(
		Filters.text & Filters.private, private))
	tele.dispatcher.add_handler(MessageHandler(
		Filters.update.channel_post & Filters.command, command))
	tele.start_polling()
	tele.idle()