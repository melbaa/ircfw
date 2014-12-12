import re
import urllib.request
import random
import html.parser
import html.entities

class NoChuckNorris(Exception): pass



class myparser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.txt = ''

    def handle_charref(self, name):
        self.txt += html.entities.entitydefs[html.entities.codepoint2name[int(name)]]
    def handle_data(self, name):
        self.txt += name
    def handle_entityref(self, name):
        self.txt += html.entities.entitydefs[name]


def chucknorris(name):
    bytez = urllib.request.urlopen('http://www.chucknorrisfacts.com/')
    bytez = bytez.readall()
    html = bytez.decode('ISO-8859-1') #aka latin_1
    #check if there is at least one page
    i = 1 #page num
    m = re.search(r'<a href="page1.html">', html)
    if m is None:
        raise NoChuckNorris('no page 1')
    pages = []
    while m is not None:
        m = re.search(r'<a href="page'+str(i)+'.html">', html)
        if m:
            pages.append(i)
        i += 1
    if len(pages) == 0:
        raise NoChuckNorris('idk dead/useless code?')
    rd = random.choice(pages)
    bytez = urllib.request.urlopen('http://www.chucknorrisfacts.com/page'+str(rd)+'.html')
    bytez = bytez.readall()
    txt = bytez.decode('ISO-8859-1') #aka latin_1
    m = True
    quotes = []
    while m is not None:
        m = re.search(r'<li>(?:\w|\d|\s|&|;|.)+?</li>',txt)
        if m:
            quotes.append(m.group(0))
            txt = txt[m.end():]
    if len(quotes) == 0:
        raise NoChuckNorris('no quotes')
    rd = random.choice(quotes)
    rd = re.sub("Chuck\s+Norris'",name + "'s", rd, flags = re.IGNORECASE)
    rd = re.sub('Chuck\s+Norris',name, rd, flags = re.IGNORECASE)
    rd = re.sub('\s|\n|\t',' ', rd, flags = re.IGNORECASE)     
    p = myparser()
    p.feed(rd)
    rd = p.txt
    rd = re.sub("Norris'", name + "'s", rd, flags = re.IGNORECASE)
    rd = re.sub("Norris", name, rd, flags = re.IGNORECASE)
    rd = re.sub("Chuck", name, rd, flags = re.IGNORECASE)
    rd = re.sub('\s+', ' ', rd)    
    return rd

    
