import random
import urllib.request
import urllib.parse
import re

import lxml.html

import ircfw.parse as parse


class plugin():

    def __init__(self, bot):
        self.bot = bot
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "what|who|when|where is|are <something>; interface to googlism"

    def name_and_aliases(self):
        return ["what", "who", "when", "where"]

    def use(self, rawcommand):
        mustbe_is, rawcommand = parse.get_word(rawcommand)
        if mustbe_is_are == 'is' or mustbe_is_are == 'are':
            searchterm = rawcommand
            temp = ""
            # remove special chars
            for char in searchterm:
                if str.isalnum(char) or str.isspace(char):
                    temp += char
            searchterm = temp
            searchterm = searchterm.strip()
            searchterm = re.sub(r'\s+', ' ', searchterm)
            if not len(searchterm):
                return self.help()
            return googlism_impl(searchterm, self.bot.usercmd)
        else:
            return self.help()


def googlism_impl(searchterm, searchtype):
    opts = dict()
    for i, word in enumerate(["who", "what", "where", "when"]):
        opts[word] = i + 1  # api takes types from 1 to 4
    if not searchtype in opts:
        raise ValueError("Unknown argument given: " + option)
    data = urllib.parse.urlencode(
        {"ism": searchterm, "type": opts[searchtype]})
    req = urllib.request.urlopen("http://www.googlism.com/search/",
                                 data=data.encode('utf-8'),
                                 timeout=5)
    reply = req.readall().decode('utf-8', 'ignore')
    root = lxml.html.fromstring(reply)
    defs = root.xpath('/html/body/div/div[4]/br')
    defs = defs[1:-1]  # ignore first and last elems
    if len(defs):
        return random.choice(defs).tail.strip()
    return 'no ideaaaa'


def googlism_impl_old(self, searchterm, option):
    """
    requires:
    urllib.request
    io
    random


    searchterm is the word to search for
    option is one of who(1),what(2), where(3), when(4)
    """
    typeval = 0
    if option == "who":
        typeval = 1
    elif option == "what":
        typeval = 2
    elif option == "where":
        typeval = 3
    elif option == "when":
        typeval = 4
    else:
        raise ValueError("Unknown argument given: " + option)

    if searchterm == '0':
        searchterm = '0 '  # lame
    searchterm_for_urlopen = urllib.parse.quote_plus(searchterm)
    if searchterm == '0 ':
        searchterm = '0'  # so lame
    try:
        data = urllib.request.urlopen("http://www.googlism.com/index.htm?ism="
                                      + searchterm_for_urlopen
                                      + "&type=" + str(typeval), timeout=7)  # 7, not 8 rofl
    except urllib.error.URLError as err:
        reply = 'my request timed out'
        return reply

    searchterm = searchterm.lower()
    html = data.readall().decode('utf-8', 'ignore')

    failresponse = '<span class="suffix">Googlism for:</span> ' \
        + searchterm + '</h1><br>Sorry,'
    start = html.find(failresponse)

    result = ""
    if start != -1:
        result = "no idea"
    else:
        winresponse = '<br><h1><span class="suffix">Googlism for:</span> ' \
            + searchterm + '</h1><br>'
        start = html.find(winresponse)
        if start == -1:
            raise Exception("wtf fix googlism")
        start += len(winresponse)
        end = html.rfind(searchterm + " is ")
        if end == -1:
            raise Exception("wth fix googlissm")
        while html[end] != '\n':
            end += 1
        whatmatters = html[start:end]
        whatmatters = whatmatters.replace("<br>", "")
        whatmatters = io.StringIO(whatmatters)
        linelist = []
        for line in whatmatters:
            linelist.append(line[:-1])
        result = random.choice(linelist)
    return result
