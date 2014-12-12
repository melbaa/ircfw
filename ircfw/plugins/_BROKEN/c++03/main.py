import urllib.request
import urllib.parse
import re
import lxml.html

class plugin():
  def __init__(self, bot):
    print('plugin' ,self.name_and_aliases(), 'started')
    self.bot = bot

  def test(self):
    return True
  
  def help(self):
    return "c++03 <code>. compile and run <code>"
    
  def name_and_aliases(self):
    return ["c++03"]
  
  def use(self,rawcommand):
    params = urllib.parse.urlencode({'lang': 'C++', 'code': rawcommand, 'run': 'True', 'submit':'Submit'})
    params = params.encode('utf8')
    timeout = 20 #seconds
    replysize = int(self.bot.BUFSIZE*1.7) #truncate output
    
    reply = urllib.request.urlopen("http://codepad.org", params, timeout)
    html = lxml.html.parse(reply)
    output = html.xpath('//pre')[3].text_content()
    output = re.subn('(\n|\r)+', ' ', output) #returns a tuple
    output = output[0] #get rid of tuple
    output = output[:replysize]
    self.bot.privmsg(self.bot.sender[0], output, 'multiline')
    return
    
    
  