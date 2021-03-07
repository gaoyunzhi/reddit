#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import praw
from telegram_util import log_on_fail
from telegram.ext import Updater
import plain_db
# import reddit_2_album

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)

with open('db/setting') as f:
	setting = yaml.load(f, Loader=yaml.FullLoader)

existing = plain_db.loadKeyOnlyDB('existing')

# reddit = reddit_2_album.reddit

reddit = praw.Reddit(
	client_id=credential['reddit_client_id'],
	client_secret=credential['reddit_client_secret'],
	password=credential['reddit_password'],
	user_agent="testscript",
	username=credential['reddit_username'],
)

tele = Updater(credential['bot_token'], use_context=True)
debug_group = tele.bot.get_chat(credential['debug_group'])
channel = tele.bot.get_chat(credential['channel'])

@log_on_fail(debug_group)
def run():
	for subname in setting['subreddits']:
		subreddit = reddit.subreddit(subname)
		for submission in subreddit.hot(limit=10):
			if submission.score < 500:
				continue
			if not existing.add(submission.url):
				continue
			if submission.permalink != submission.url and not existing.add(submission.permalink):
				continue
			url = 'https://www.reddit.com' + submission.permalink
			print("test('%s')" % url)
			# album = reddit_2_album.get(url)
			# album_sender.send_v2(channel, album)

if __name__ == '__main__':
	run()