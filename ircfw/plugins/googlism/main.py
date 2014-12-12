import io
import urllib.parse
import urllib.request
import re
import random

import lxml.html

import ircfw.parse as parse
from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

class plugin:
  def __init__(self, zmq_ioloop, zmq_ctx):
    self.generic_plugin = generic_plugin(
      zmq_ioloop
      , zmq_ctx
      , __name__
      , const.GOOGLISM_PLUGIN
      , [const.GOOGLISM_PLUGIN_NEW_REQUEST]
      , self.on_request
    )
    self.logger = self.generic_plugin.logger

  def on_request(self, sock, evts):
    msg = sock.recv_multipart()
    self.logger.info('got msg %s', msg)
    topic, zmq_addr, proxy_name, bufsize \
      ,senderbytes,paramsbytes, triggerbytes,argsbytes = msg

    args = argsbytes.decode('utf8')
    trigger = triggerbytes.decode('utf8')
    args.strip()
    result = None
    if not args:
      result = self.help()
    else:
      result = self.use(trigger, args)
    replies = ircfw.unparse.make_privmsgs(
      senderbytes
      , paramsbytes
      , result.encode('utf8')
      , int(bufsize.decode('utf8'))
      , 'truncate'
    )

    self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)


  def help(self):
    return "what|who|when|where is|are <something>"

  def use(self,trigger,rawcommand):
    mustbe_is_are, rawcommand = parse.get_word(rawcommand)
    if mustbe_is_are == 'is' or mustbe_is_are == 'are':
        searchterm = rawcommand
        temp = ""
        #remove special chars
        for char in searchterm:
            if str.isalnum(char) or str.isspace(char):
                temp += char
        searchterm = temp
        searchterm = searchterm.strip()
        searchterm = re.sub(r'\s+', ' ', searchterm)
        if not len(searchterm):
            return self.help()
        return googlism_impl(searchterm, trigger)
    else:
      return self.help()

def googlism_impl(searchterm, searchtype):
  opts = dict()
  for i,word in enumerate(["who", "what", "where", "when"]):
    opts[word] = i+1 #api takes types from 1 to 4
  if not searchtype in opts:
    raise ValueError("Unknown argument given: " + option)
  data = urllib.parse.urlencode({"ism": searchterm, "type": opts[searchtype]})
  req = urllib.request.urlopen("http://www.googlism.com/search/",
                        data=data.encode('utf-8'),
			                  timeout = 5)
  reply = req.readall().decode('utf-8', 'ignore')
  root = lxml.html.fromstring(reply)
  defs = root.xpath('/html/body/div/div[4]/br')
  defs = defs[1:-1] #ignore first and last elems
  if len(defs):
    return random.choice(defs).tail.strip()
  return 'no ideaaaa'


def googlism_impl_old(self,searchterm, option):
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

    if searchterm == '0': searchterm = '0 ' #lame bastards
    searchterm_for_urlopen = urllib.parse.quote_plus(searchterm)
    if searchterm == '0 ': searchterm = '0' #fuckin noobs
    try:
        data = urllib.request.urlopen("http://www.googlism.com/index.htm?ism="
                                      + searchterm_for_urlopen
                                      + "&type=" + str(typeval)
                                      , timeout = 7) #7, not 8 rofl
    except urllib.error.URLError as err:
        reply = 'my request timed out'
        return reply

    searchterm = searchterm.lower()
    html = data.readall().decode('utf-8', 'ignore')

    failresponse = '<span class="suffix">Googlism for:</span> ' \
                 + searchterm +'</h1><br>Sorry,'
    start = html.find(failresponse)

    result = ""
    if start != -1:
        result = "no idea"
    else:
        winresponse = '<br><h1><span class="suffix">Googlism for:</span> ' \
                    +searchterm+'</h1><br>'
        start = html.find(winresponse)
        if start == -1: raise Exception("wtf fix googlism")
        start += len(winresponse)
        end = html.rfind(searchterm + " is ")
        if end == -1: raise Exception("wth fix googlissm")
        while html[end] != '\n':
            end += 1
        whatmatters = html[start:end]
        whatmatters = whatmatters.replace("<br>","")
        whatmatters = io.StringIO(whatmatters)
        linelist = []
        for line in whatmatters:
            linelist.append(line[:-1])
        result = random.choice(linelist)
    return result
