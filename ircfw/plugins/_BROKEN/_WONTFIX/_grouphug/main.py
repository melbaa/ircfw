import collections
import re
import urllib.request

import lxml.html

Confession = collections.namedtuple('Confession', 'text uri')

class plugin():
  def __init__(self, bot):
    print('plugin' ,self.name_and_aliases(), 'started')
    self.confessions = []
    self.bot = bot

  def test(self):
    return True
  
  def help(self):
    return "get a confession"
    
  def name_and_aliases(self):
    return ["gh", "grouphug"]
  
  def use(self,rawcommand):
    return self.grouphug()
  
  
  def grouphug_impl(self):
    print(self.confessions)
    if len(self.confessions):
      result = self.confessions[0]
      self.confessions = self.confessions[1:]
      return result
    try:
      src = urllib.request.urlopen("http://confessions.grouphug.us/random", timeout = 5).read().decode('utf8')
      tree = lxml.html.fromstring(src)
    except (IOError, urllib.error.URLError) as err:
      return Confession(text = str(err), uri = 'wtf')
    confession_nodes = tree.find_class('node-confession')
    assert len(confession_nodes), 'they changed ze website again'
    for i in tree.find_class('node-confession'):
      children = i.getchildren()
      if len(children) != 2: 
        print('ERROR: wtf fix gh')
        return Confession(text = 'Something went wrong with your request.', uri = 'wtf')
      uri = children[0].text_content().strip() #this is the h2 
      txt = children[1].text_content()
      txt = re.sub('\s+', ' ', txt)
      self.confessions.append(Confession(text = txt, uri = uri))
      
    #now we will have a confession so on the next call we return it
    return self.grouphug_impl() 
    



  def grouphug(self, mode = 'multiline'):
    conf = self.grouphug_impl()
    if mode == 'multiline':
        self.bot.privmsg(self.bot.sender[0], conf.text, 'multiline')
    else:
        try:
            self.bot.privmsg(self.bot.sender[0], conf.text, 'raise')
        except OverflowError as err:
            self.bot.privmsg(self.bot.sender[0], conf.uri + conf.text)