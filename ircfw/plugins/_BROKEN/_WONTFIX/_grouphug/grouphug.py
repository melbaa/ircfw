import re
import urllib.request
import html.parser
import html.entities

class GHparser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        #status can be:
        #out - outside confession
        #in - inside confession
        self.status = 'out'

        #a confession starts after the third </h2>
        self.counter = 0
        self.confession = ''
        self.confessions = []
        self.confessionlinks = []
        
    def handle_entityref(self, name):
        if self.status == 'in':
            self.confession += html.entities.entitydefs[name]
            
    def handle_charref(self, name):
            if self.status == 'in':
                self.confession += html.entities.entitydefs[html.entities.codepoint2name[int(name)]]
            
    def handle_starttag(self, tag, attrs):
        if tag == 'div' and self.counter > 3:
            for i,j in attrs:
                if i == 'class' and 'content' in j:
                    self.status = 'in'
        elif tag == 'a':
            for i,j in attrs:
                #print(i,j)
                if i == 'href' and '/confessions/' in j:
                    self.confessionlinks.append('http://grouphug.us' + j)
                    
    def handle_data(self, data):
        if self.status == 'in':
            self.confession += data
            
    def handle_endtag(self, tag):
        if tag == 'h2':
            self.counter += 1
        elif tag == 'div' and self.status == 'in':
            self.status = 'out'
            self.confessions.append(self.confession)
            self.confession = ''
    
    
def grouphug(self, multiline = False):
    if not hasattr(self,'__gh_confessions'):
        self.__gh_confessions = []
    if not hasattr(self, '__gh_confessionlinks'):
        self.__gh_confessionlinks = []
        
    if len(self.__gh_confessions) != 0:
        conf = self.__gh_confessions[0]
        conflink = self.__gh_confessionlinks[0]
        self.__gh_confessions = self.__gh_confessions[1:]
        self.__gh_confessionlinks = self.__gh_confessionlinks[1:]
        self.privmsg(self.sender[0], conf, 'multiline')
        # try:
            # self.privmsg(self.sender[0], confession, 'raise')
        # except OverflowError as err:
            # self.privmsg(self.sender[0], conflink + ' ' + confession)
        return
    
    try:
        b = urllib.request.urlopen("http://confessions.grouphug.us/random", timeout = 5)
    except urllib.error.URLError as err:
        self.privmsg(self.sender[0], str(err))
        return
    charset = None
    header = b.getheader('Content-Type')
    charsetbegin = header.find('charset=')
    if charsetbegin == -1:
        charset = 'utf-8' #SWAG
    else:
        charsetbegin += len('charset=')
        i = charsetbegin + 1
        while i < len(header) and  header[i] != ' ':
            i += 1
        charsetend = i
        charset = header[charsetbegin:charsetend]
    b = b.readall()
    html = b.decode(charset)
    parser = GHparser()
    parser.feed(html)
    for i in range(len(parser.confessions)):
        parser.confessions[i] = re.sub('\n', ' ', parser.confessions[i])
        parser.confessions[i] = re.sub(' +', ' ', parser.confessions[i])
    self.debugprint(parser.confessionlinks)
    self.debugprint(parser.confessions)
    conf = parser.confessions[0]
    conflink = parser.confessionlinks[0]
    self.__gh_confessions = parser.confessions[1:]
    self.__gh_confessionlinks = parser.confessionlinks[1:]
    self.privmsg(self.sender[0], conf, 'multiline')
    # try:
        # self.privmsg(self.sender[0], conf, 'raise')
    # except OverflowError as err:
        # self.privmsg(self.sender[0], conflink + ' ' + conf)