import urllib.request
import lxml.etree
import io
import lxml.html
import re


class plugin():

    def __init__(self, bot):
        self.bot = bot
        self.fml_cache = []
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "get a life story"

    def name_and_aliases(self):
        return ["fml"]

    def use(self, rawcommand):
        reply = self.fml()
        self.bot.privmsg(self.bot.sender[0], reply, 'multiline')
        return None

    def fml(self):

        if len(self.fml_cache):
            reply = self.fml_cache[0]
            self.fml_cache = self.fml_cache[1:]
            return reply

        f = urllib.request.urlopen("http://www.fmylife.com/random")
        c = f.readall()
        c = c.decode('utf-8', 'ignore')
        #fh = codecs.open('fmldbg', 'w', 'utf-8')
        # fh.write(c)

        tree = lxml.html.document_fromstring(c)
        candidates = tree.find_class('post')
        self.fml_cache = []
        for i in candidates[1:-1]:  # first and last are bs
            i = i.text_content()
            i = i[i.find("Today"):i.rfind("FML") + len("FML")]
            i = re.sub('\n', ' ', i)
            i = re.sub('\s+', ' ', i)
            self.fml_cache.append(i)
        # print(candidates)
        reply = self.fml_cache[0]
        self.fml_cache = self.fml_cache[1:]
        # fh.write(reply)
        return reply
