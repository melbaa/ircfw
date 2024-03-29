
import logging
import urllib.parse
import urllib.request
import urllib.error

import lxml.etree
import zmq

import ircfw.constants as const
import ircfw.parse
import ircfw.unparse


class plugin():

    def __init__(
            self,
            api_key,
            api_secret,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.logger = logging.getLogger(__name__)
        self.plugin_name = const.ARTISTINFO_PLUGIN

        self.request = zmq_ctx.socket(zmq.SUB)
        self.request.connect(plugin_dispatch)
        self.request.setsockopt(
            zmq.SUBSCRIBE, const.ARTISTINFO_PLUGIN_NEW_REQUEST)

        self.push_reply = zmq_ctx.socket(zmq.PUSH)
        self.push_reply.connect(command_dispatch_backend_replies)

        self.ioloop = zmq_ioloop

        self.api_key = api_key
        self.secret = api_secret

        self.reqstr = "http://ws.audioscrobbler.com/2.0/?method=artist.getinfo" \
            + "&artist={artist}" \
            + "&api_key=" + self.api_key \
            + "&autocorrect=1"

    async def main(self):
        while True:
            req = await self.request.recv_multipart()
            topic, zmq_addr, proxy_name, bufsize, rawmsg = req
            msg = rawmsg.decode('utf8')
            if topic == const.ARTISTINFO_PLUGIN_NEW_REQUEST:
                sender, command, params, trailing = ircfw.parse.irc_message(msg)
                nick, trailing = ircfw.parse.get_word(trailing)
                cmd, artist = ircfw.parse.get_word(trailing)
                artist = artist.strip()
                result = None
                if not len(artist):
                    result = 'tell me an artist first'
                else:
                    try:
                        artist_quoted = urllib.parse.quote_plus(artist)
                        request = self.reqstr.format(artist=artist_quoted)
                        print(request)
                        data = urllib.request.urlopen(request).read()
                        root = lxml.etree.fromstring(data)
                        tags = str(
                            [elem.text for elem in root.xpath('artist/tags/tag/name')])
                        result = artist + " - " + tags
                    except urllib.error.HTTPError as err:
                        result = str(err)

                replies = ircfw.unparse.make_privmsgs(
                    sender[0].encode('utf8'),
                    params[0].encode('utf8'),
                    result.encode('utf8'),
                    int(bufsize.decode('utf8')),
                    'multiline')
                await self._send_replies(replies, zmq_addr, proxy_name)

    async def _send_replies(self, replies, zmq_addr, proxy_name):
        self.logger.info('about to send replies %s', replies)
        for reply in replies:
            reply = [zmq_addr, proxy_name, self.plugin_name, reply]
            await self.push_reply.send_multipart(reply)
        self.logger.info('sent!')
