import socket
import urllib.request

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

from youtube_search import YoutubeSearch as yts

# [20:56] <rbrcs> yt-dlp --get-title --get-id ytsearch10:"$@" | awk '!(NR%2){print "https://www.youtube.com/watch?v="$0}; NR%2{print $0}'


class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.YOUTUBE_PLUGIN,
            [const.YOUTUBE_PLUGIN_NEW_REQUEST],
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
            results = None
            if not args:
                results = [self.help()]
            else:
                results = self.use(args)

            for result in results:
                replies = ircfw.unparse.make_privmsgs(
                    senderbytes, paramsbytes, result.encode(
                        'utf8'), int(bufsize.decode('utf8')), 'multiline'
                )
                await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def help(self):
        return "no search term"

    def use(self, rawcommand):
        return impl(rawcommand)


def impl(rawcommand):
    rawcommand = rawcommand.strip()
    results = yts(rawcommand, max_results=5).to_dict()
    txt = ''
    for result in results:
        yield result['title'] + ' ' + result['duration'] + " " + 'https://youtube.com' + result['url_suffix']
