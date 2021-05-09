#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import praw
from telegram_util import log_on_fail
from telegram.ext import Updater
import plain_db
import reddit_2_album
import album_sender
import time

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)

with open('db/setting') as f:
	setting = yaml.load(f, Loader=yaml.FullLoader)

existing = plain_db.loadKeyOnlyDB('existing')

reddit = reddit_2_album.reddit

tele = Updater(credential['bot_token'], use_context=True)
debug_group = tele.bot.get_chat(credential['debug_group'])

@log_on_fail(debug_group)
def run():
	for channel_id, detail in setting.items():
		channel = tele.bot.get_chat(channel_id)
		for subname, subsetting in detail.items():
			subreddit = reddit.subreddit(subname)
			send = False
			for submission in subreddit.hot(
					limit=subsetting.get('only_recent', 100)):
				if submission.score < subsetting.get('upvote', 500):
					continue
				if not existing.add(submission.url):
					continue
				if submission.permalink != submission.url and not existing.add(submission.permalink):
					continue
				url = 'http://www.reddit.com' + submission.permalink
				album = reddit_2_album.get(url)
				if not album.imgs and submission.score < subsetting.get('upvote', 500) * 10:
					continue
				result = album_sender.send_v2(channel, album)
				result_len = len(result)
				time.sleep(result_len * 10 + (result_len ** 2) / 2)
				send = True
				break
			time.sleep(10)

if __name__ == '__main__':
	run()