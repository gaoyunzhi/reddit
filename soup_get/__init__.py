from bs4 import BeautifulSoup
import cached_url
import time
import random

class Timer(object):
	def __init__(self):
		self.reset()

	def reset(self):
		self.last_request = 0

	def wait(self, wait):
		if time.time() - self.last_request < wait:
			time.sleep(wait + self.last_request - time.time())
		self.last_request = time.time()

class SoupGet(object):
	def __init__(self):
		self.timer = Timer()
		self.reset()

	def reset(self):
		self.num_requests = 0
		self.timer.reset()

	def getSoup(self, url, cookie):
		self.num_requests += 1
		wait = min(random.random() * 20, self.num_requests * random.random())
		self.timer.wait(wait)
		return BeautifulSoup(cached_url.get(url, {'cookie': cookie}), 'html.parser')