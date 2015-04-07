import re

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


"""
TODO broken - does not iterate graphemes, so returns wrong output
for eg. Devanagari or other languages with composite characters.

ICU has a grapheme iterator, but i don't want to pull deps
"""


class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.REVERSE_PLUGIN,
            [const.REVERSE_PLUGIN_NEW_REQUEST],
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
        return "reverse <txt>"

    def use(self, rawcommand):
        return rawcommand[::-1]
