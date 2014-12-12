import urllib.parse
import lxml.html
import urllib.request
import re


class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "ebonics <txt>; speak like an african"

    def name_and_aliases(self):
        return ["ebonics"]

    def use(self, rawcommand):
        if len(rawcommand) == 0:
            return self.help()
        match = re.search("[^ ]", rawcommand)
        if match is None:
            return self.help()
        try:
            timeout = 10  # sec
            params = urllib.parse.urlencode(
                {"English": rawcommand, "submit": " Talk Like a Pimp "})
            params = params.encode('utf-8')
            f = urllib.request.urlopen(
                "http://joel.net/EBONICS/Translator", params, timeout)
            html = f.read().decode("utf8")
            html = lxml.html.fromstring(html)
            txt = html.xpath(
                "//*[@class='bubblemid']")[1].text_content().strip()
            return txt
        except Exception as err:
            return str(err)
