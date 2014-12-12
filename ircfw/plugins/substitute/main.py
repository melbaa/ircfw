import re

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
      , const.SUBSTITUTE_PLUGIN
      , [const.SUBSTITUTE_PLUGIN_NEW_REQUEST]
      , self.on_request
    )
    self.logger = self.generic_plugin.logger

  def on_request(self, sock, evts):
    msg = sock.recv_multipart()
    self.logger.info('got msg %s', msg)
    topic, zmq_addr, proxy_name, bufsize \
      ,senderbytes,paramsbytes, argsbytes = msg

    args = argsbytes.decode('utf8')
    args.strip()
    result = None
    if not args:
      result = self.help()
    else:
      result = self.use(args)
    replies = ircfw.unparse.make_privmsgs(
      senderbytes
      , paramsbytes
      , result.encode('utf8')
      , int(bufsize.decode('utf8'))
      , 'multiline'
    )

    self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)


  def help(self):
    return "sub <pattern> <replacement> <text>. replace the regular expression <pattern> with the string <replacement> in the <text>"

  def use(self,rawcommand):
    if not len(rawcommand):
        return "incorrect input: pattern expected"
    pattern, rawcommand = parse.get_word(rawcommand)
    if not len(rawcommand):
        return "incorrect input: replacement string expected"
    repl, rawcommand = parse.get_word(rawcommand)
    if not len(rawcommand):
        return "incorrect input: expected text to substitute in"
    txt = rawcommand
    newstr, numsubs = re.subn(pattern, repl, txt)
    if numsubs == 0:
        return "nothing to substitute"
    reply = str(numsubs)
    if numsubs == 1:
        reply += " substitution"
    else:
        reply += " substitutions"
    reply += ": " + newstr
    return reply



