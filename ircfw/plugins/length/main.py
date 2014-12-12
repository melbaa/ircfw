import re

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


class plugin:

    def __init__(self, zmq_ioloop, zmq_ctx):
        self.generic_plugin = generic_plugin(
            zmq_ioloop, zmq_ctx, __name__, const.LENGTH_PLUGIN, [
                const.LENGTH_PLUGIN_NEW_REQUEST], self.on_request
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
        return "length <txt>"

    def use(self, rawcommand):
        return str(len(rawcommand))
