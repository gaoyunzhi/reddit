import os
import yaml

class DB(object):
	def __init__(self):
		with open('db/config') as f:
			self.config = yaml.load(f, Loader=yaml.FullLoader)
		with open('db/cookie') as f:
			self.cookie = yaml.load(f, Loader=yaml.FullLoader)
		self.existing = {}
		for name in self.getChannels():
			fn = 'db/%s_existing' % name
			os.system('touch %s' % fn)
			with open(fn) as f:
				self.existing[name] = set(x.strip() for x in f.readlines())

	def blacklistAdd(self, channel, word):
		self._initBlacklist(channel)
		if word in self.config[channel]['blacklist']:
			return 'fail'
		self.config[channel]['blacklist'].append(word)
		self._sortBlacklist(channel)
		self._save()
		return 'success'

	def blacklistRemove(self, channel, word):
		self._initBlacklist(channel)
		if word in self.config[channel]['blacklist']:
			self.config[channel]['blacklist'].remove(word)
		else:
			return 'fail'
		self._sortBlacklist(channel)
		self._save()
		return 'success'

	def getBlacklist(self, channel):
		self._initBlacklist(channel)
		return self.config[channel]['blacklist']

	def getChannels(self):
		return [x for x in self.cookie.keys() if self.cookie[x]]

	def getCookie(self, name):
		return self.cookie.get(name)

	def setCookie(self, name, cookie):
		self.cookie[name] = cookie
		with open('db/cookie', 'w') as f:
			f.write(yaml.dump(self.cookie, sort_keys=True, indent=2))
		return 'success'

	def getBlacklist(self, name):
		self._initBlacklist(name)
		return self.config[name]['blacklist']

	def exist(self, name, x):
		return x.strip() in self.existing[name]

	def addToExisting(self, name, x):
		x = x.strip()
		if x in self.existing[name]:
			return
		self.existing[name].add(x)
		with open('db/%s_existing' % name, 'a') as f:
			f.write('\n' + x)

	def _initBlacklist(self, channel):
		self.config[channel] = self.config.get(channel, {})
		self.config[channel]['blacklist'] = self.config[channel].get('blacklist', [])

	def _sortBlacklist(self, channel):
		self.config[channel]['blacklist'] = \
			sorted(list(set(self.config[channel]['blacklist'])))

	def _save(self):
		with open('db/config', 'w') as f:
			f.write(yaml.dump(self.config, sort_keys=True, indent=2, allow_unicode=True))
