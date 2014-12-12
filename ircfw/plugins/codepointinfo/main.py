import unicodedata
import re


import socket
import urllib.request

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

class plugin:
  def __init__(self, zmq_ioloop, zmq_ctx):
    self.generic_plugin = generic_plugin(
      zmq_ioloop
      , zmq_ctx
      , __name__
      , const.CODEPOINTINFO_PLUGIN
      , [const.CODEPOINTINFO_PLUGIN_NEW_REQUEST]
      , self.on_request
    )
    self.logger = self.generic_plugin.logger

  def on_request(self, sock, evts):
    msg = sock.recv_multipart()
    self.logger.info('got msg %s', msg)
    topic, zmq_addr, proxy_name, bufsize \
      ,senderbytes,paramsbytes, triggerbytes, argsbytes = msg

    trigger = triggerbytes.decode('utf8')
    args = argsbytes.decode('utf8')
    args.strip()

    result = self.use(trigger, args)
    replies = ircfw.unparse.make_privmsgs(
      senderbytes
      , paramsbytes
      , result.encode('utf8')
      , int(bufsize.decode('utf8'))
      , 'multiline'
    )

    self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)


  def help(self):
    return "chr <unicode_codepoint> prints the corresponding character; nchr is the reverse"

  def use(self, trigger, args):
    if len(args) == 0: return self.help()
    if trigger == "chr":
      return codepoint2utf8(args)
    else:
      return describe_codepoint(args)

def codepoint2utf8(rawcommand): #chr
    if len(rawcommand):
        rawcommand = re.sub(' ', '', rawcommand)
        rawcommand = re.sub('(?i)u\+', '', rawcommand)
        try:
            number = int(rawcommand, 16)
            the_char = chr(number)
            result = ''
            if number < 0x1f: #see ascii/unicode table
              #control codes have no names anyway.
              # only comments not accessible from unicodedata
              result = "unprintable character"
            else:
              result = the_char
            result += '  -  ' + describe_codepoint(the_char)
            return result
        except (ValueError, OverflowError) as err:
            return str(err)

def describe_codepoint(rawcommand): #nchr
    if len(rawcommand):
        try:
            result = unicodedata.name(rawcommand[0])
            result += '   -   U+' + str.upper(hex(ord(rawcommand[0]))[2:])
            return result
        except ValueError as err:
            return str(err)
