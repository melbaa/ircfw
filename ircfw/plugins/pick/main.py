import re
import random

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


class plugin:

    def __init__(self, zmq_ioloop, zmq_ctx):
        self.generic_plugin = generic_plugin(
            zmq_ioloop, zmq_ctx, __name__, const.PICK_PLUGIN, [
                const.PICK_PLUGIN_NEW_REQUEST], self.on_request
        )
        self.logger = self.generic_plugin.logger

    def on_request(self, sock, evts):
        msg = sock.recv_multipart()
        self.logger.info('got msg %s', msg)
        topic, zmq_addr, proxy_name, bufsize \
            , senderbytes, paramsbytes, argsbytes = msg

        args = argsbytes.decode('utf8')
        args.strip()
        result = None
        if not args:
            result = self.help()
        else:
            result = self.use(args)
        replies = ircfw.unparse.make_privmsgs(
            senderbytes, paramsbytes, result.encode(
                'utf8'), int(bufsize.decode('utf8')), 'multiline'
        )

        self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def help(self):
        return "usage: pick <a> or <b> or ...; return one of <a>, <b> ..."

    def use(self, rawcommand):
        list_to_choose_from = self.make_choices_list(rawcommand)
        if len(list_to_choose_from) >= 1:
            return "I pick '" + random.choice(list_to_choose_from) + "'"
        return self.help()

    def make_choices_list(self, string):
        """i barely know how this works anymore
        """
        string = string.strip()
        string = re.sub(r'\s+', ' ', string)
        L = string.split(' ')
        i = 0
        choices = []
        choice = ''
        or_was_last = 1
        while i < len(L):
            if L[i].lower() != 'or':
                choice += L[i] + ' '
                or_was_last = 0
            else:
                if choice != '':
                    choices.append(choice[:-1])
                choice = ''
                or_was_last = 1
            i += 1
        if not or_was_last and choice != ' ':
            choices.append(choice[:-1])
        return choices
