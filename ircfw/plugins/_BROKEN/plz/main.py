# DEAD CODE :)
# TODO thinking how to write it as plugins or something else


class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "this plugin does nothing"

    def name_and_aliases(self):
        return ["null", "nullalias"]

    def use(self, rawcommand):
        return "nothing to do '" + rawcommand + "' received"



import urllib.parse
import urllib.request
import urllib.error
import re
import unicodedata
import io
import random
import os
import string
import collections
import socket

import lxml.etree
import lxml.html

import ircfw.constants as constants
import ircfw.parse as parse

def plzprivmsg(self):
    to, self.trailing = parse.get_word(self.trailing)
    self.queue_reply("PRIVMSG "+ to + ' ' + ':' + self.trailing)

def plzjoin(self):
    chan, self.trailing = parse.get_word(self.trailing)
    self.join_chan(chan)


def plzflush(self):
    self._file.flush()
    self.privmsg(self.sender[0], "log is the file "
                 + self._file.name + ' in ' + os.getcwd())


"""
this thing works but looks baaaaaad so i removed the command
it'll stay here for reference
"""
def topic(self):
    if self.nick != self.params[0]: #not a private message
        self.queue_reply("TOPIC " + self.params[0])
        reply = "The channel topic is:"
        if len(self.trailing):
            tell_nick, self.trailing = parse.get_word(self.trailing)
            reply = tell_nick + ", the channel topic is:"
        line_list = []
        while 1:
            line = self.getline()
            sender, command, params, trailing = self.parse_message(line)
            self.debugprint("in topic: " + line)
            if command == constants.RPL_NOTOPIC \
               and params[1] == self.params[0]:
                self.privmsg(self.sender[0], "what topic?")
                break
            elif command == constants.RPL_TOPIC \
                 and params[1] == self.params[0]:
                reply += " " + trailing
                self.queue_reply("PRIVMSG" + ' ' + self.params[0]
                           + ' ' + ':' + reply)
                break
            else:
                line_list.append(line)
        for line in line_list:
            self.process(line)