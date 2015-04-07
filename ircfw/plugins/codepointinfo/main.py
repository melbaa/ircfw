import re
import unicodedata


import socket
import urllib.request

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.CODEPOINTINFO_PLUGIN,
            [const.CODEPOINTINFO_PLUGIN_NEW_REQUEST],
            self.on_request,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger

    def on_request(self, sock, evts):
        msg = sock.recv_multipart()
        self.logger.info('got msg %s', msg)
        topic, zmq_addr, proxy_name, bufsize \
            , senderbytes, paramsbytes, triggerbytes, argsbytes = msg

        trigger = triggerbytes.decode('utf8')
        args = argsbytes.decode('utf8')
        args.strip()

        result = self.use(trigger, args)
        replies = ircfw.unparse.make_privmsgs(
            senderbytes, paramsbytes, result.encode(
                'utf8'), int(bufsize.decode('utf8')), 'multiline'
        )

        self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def help(self):
        return "chr <unicode_codepoint> prints the corresponding character; nchr is the reverse"

    def use(self, trigger, args):
        if len(args) == 0:
            return self.help()
        if trigger == "chr":
            return mychr(args)
        else:
            return nchr(args)

def nchr(rawcommand):
    result = ''
    cmd = rawcommand[:10] # prevent accidental wall of text
    for c in cmd:
        result += pretty_codepoint(ord(c)) + ' '
    
    result += '  -  ' +  describe_codepoint(cmd)
    return result

def mychr(rawcommand):  
    if len(rawcommand):
        rawcommand = re.sub(' ', '', rawcommand)
        rawcommand = re.sub('(?i)u\+', '', rawcommand)
        try:
            number = int(rawcommand, 16)
            codepoint = chr(number)
            
            result = pretty_codepoint(number)
            
            result += '  -  ' + describe_codepoint(codepoint)
            return result
        except (ValueError, OverflowError) as err:
            return str(err)

def pretty_codepoint(codepoint_num_val):
    codepoint = chr(codepoint_num_val)
    result = ''
    if codepoint_num_val < 0x1f:  # see ascii/unicode table
        # control codes have no names anyway.
        # only comments not accessible from unicodedata
        result = "unprintable character"
    else:
        result = codepoint
    result += ' ' + unicodedata.name(codepoint)
    result += ' ' + pretty_codepoint_num(codepoint_num_val)
    return result
    
def pretty_codepoint_num(codepoint_num_val):
    return 'U+' + str.upper(hex(codepoint_num_val)[2:])
            
def describe_codepoint(rawcommand): 
    if len(rawcommand):
        try:
            # try to combine diacritics like rings and accents
            txt = unicodedata.normalize('NFC', rawcommand)
            result = 'NFC normalized: '
            decomposition = ''
            for c in txt:
                result += c
                result += ' '+ unicodedata.name(c)
                result += ' ' + pretty_codepoint_num(ord(c))
                result += ' '
                
                decomp = unicodedata.decomposition(c)
                if len(decomp):
                    decomposition += decomp + ' '
            if len(decomposition):
                result += 'decomposition: ' + decomposition
            return result
        except ValueError as err:
            return str(err)
