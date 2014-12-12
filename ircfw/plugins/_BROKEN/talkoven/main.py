import urllib.parse
import urllib.request
import re
import lxml.html


class plugin():

    def __init__(self, bot):
        self.bot = bot
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "trechnik <word_in_bulgarian>; see the meaning of a bulgarian word"

    def name_and_aliases(self):
        return ["talkoven", "trechnik"]

    def use(self, rawcommand):
        if not len(rawcommand):
            return
        cooked = urllib.parse.urlencode({"search": rawcommand})
        html = urllib.request.urlopen(
            "http://t-rechnik.info/search.php?" + cooked)
        html = html.read().decode("utf8")
        root = lxml.html.fromstring(html)
        tbl = root.get_element_by_id("table")
        if len(tbl) == 3:
            txt = tbl[2].text_content()
            txt = re.sub(r"\r|\n", " ", txt)
            txt = re.sub(r"\s+", " ", txt)
            self.bot.privmsg(self.bot.sender[0], txt, option="multiline")
            return
        return "nothing found"
