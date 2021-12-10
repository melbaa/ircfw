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
            const.PRIVMSG_PING_PLUGIN,
            [const.PRIVMSG_PING_PLUGIN_NEW_REQUEST],
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
        return "ping <url>; check if a host is live"

    def use(self, rawcommand):
        return impl(rawcommand)


def impl(rawcommand):
    if not rawcommand:
        return "pong"
    rawcommand = rawcommand.strip()
    if not rawcommand.startswith('http'):
        rawcommand = 'https://' + rawcommand
    try:
        r = urllib.request.urlopen(rawcommand, timeout=6)
        return "got HTTP status " + str(r.status)
    except urllib.error.URLError as err:
        return str(err)

def impl1(rawcommand):
    if not rawcommand:
        return "pong"
    else:
        try:
            q = urllib.parse.quote(rawcommand)
            r = urllib.request.urlopen(
                'http://downforeveryoneorjustme.com/' + q, timeout=6)
            r = r.read()
            reply = ''
            if r.find(b"It's just you.") != -1:
                reply = rawcommand + " looks up from here."
            elif r.find(b"It's not just you!") != -1:
                reply = rawcommand + " looks down from here."
            elif r.find(b"doesn't look like a site."):
                reply = "is " + rawcommand + " even a website?"
            else:
                reply = "unexpected"
            return reply
        except urllib.error.URLError as err:
            return str(err)
