import re

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
            const.RE_PLUGIN,
            [const.RE_PLUGIN_NEW_REQUEST],
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
        return "re <pattern> <text>. search the regular expression pattern in the text. No spaces allowed in the pattern, use \\s instead"

    def use(self, rawcommand):
        pos = 0
        pat = ''
        while pos < len(rawcommand) and rawcommand[pos] != ' ':
            pat += rawcommand[pos]
            pos += 1

        if pos < len(rawcommand) and rawcommand[pos] == ' ':
            pos += 1
        rawcommand = rawcommand[pos:]

        #pat = re.escape(pat)

        try:
            res = re.search(pat, rawcommand)
            reply = ''
            if res is None:
                return 'you fail hard.'
            else:
                beforematch = res.string[:res.start()]
                if len(beforematch):
                    reply += 'pre=' + beforematch + ' '
                reply += 'exact=' + res.group(0)
                aftermatch = res.string[res.end():]
                if len(aftermatch):
                    reply += ' post=' + res.string[res.end():]
                groups = res.groups()
                for i in range(len(groups)):
                    if groups[i] is None:
                        reply += ' $' + str(i + 1) + ' did not match'
                    else:
                        reply += ' $' + str(i + 1) + '=' + groups[i]
                return reply
        except re.error as err:
            return str(err)
