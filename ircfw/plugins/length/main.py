import re
import unicodedata

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
            const.LENGTH_PLUGIN,
            [const.LENGTH_PLUGIN_NEW_REQUEST],
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger

    async def main(self):
        while True:
            msg = await self.generic_plugin.read_request()
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

            await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def help(self):
        return "length <txt>"

    def use(self, rawcommand):
        plain = len(rawcommand)
        nfc_normalized = len(unicodedata.normalize('NFC', rawcommand))
        return 'plain: {} NFC normalized: {}'.format(plain, nfc_normalized)
