#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import yaml
import praw
from telegram_util import log_on_fail
from telegram.ext import Updater

with open('credential') as f:
	credential = yaml.load(f, Loader=yaml.FullLoader)

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
	print(reddit.user.me())

if __name__ == '__main__':
	run()