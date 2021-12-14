"""
there's a c++ bot on libera (geordi, clang), quakenet (geordi)

user makes a request to bot
bot makes a request to geordi
if timeout secs pass with no reply from geordi, notify user
if reply from geordi before timeout expires, cancel timeout, reply to user
if reply from geordi after timeout has expired, ignore geordi
"""

import logging
import asyncio

import zmq

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.parse
import ircfw.util

class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        # this will be the address of a proxy with a geordi
        # it gets updated on PROXY_NICKS control msg
        self.geordi_location = None
        self.geordi_location_proxy_name = None
        self.busy = False  # true if waiting reply from geordi or timeout
        self.pending_request_data = None  # state while geordi answers

        self.logger = logging.getLogger(__name__)
        self.plugin_name = const.CPLUSPLUS_PLUGIN


        self.generic_plugin = generic_plugin(
            __name__,
            const.CPLUSPLUS_PLUGIN,
            [
                const.CPLUSPLUS_PLUGIN_NEW_REQUEST,
                const.CPLUSPLUS_PLUGIN_PROXY_NICKS,
                const.CPLUSPLUS_PLUGIN_GEORDI_REPLY,
            ],
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger

        self.ioloop = zmq_ioloop

    async def main(self):
        while True:
            req = await self.generic_plugin.read_request()
            self.logger.info('received request %s', req)
            #plugin_name, zmq_addr, proxy_name, bufsize, rawmsg = req
            topic, zmq_addr, proxy_name, *rest = req
            if topic == const.CPLUSPLUS_PLUGIN_PROXY_NICKS:
                rawtopic, rawcmd, rawcmdargs = rest
                cmdargs = rawcmdargs.decode('utf8').split(' ')
                self.logger.info('got a PROXY_NICKS in msg %s', req)
                if const.CPLUSPLUS_PLUGIN_GEORDI_NICK in cmdargs:
                    """TODO FIXME
                    someday this should contain all the addresses of proxies
                    that have geordies, not just the latest one received
                    """
                    self.geordi_location = zmq_addr
                    self.geordi_location_proxy_name = proxy_name
                    # bufsized used to talk to geordi on his server
                    self.geordi_location_bufsize = 450  # will get updated later
                    self.logger.info('geordi_location update from msg %s', req)
            elif topic == const.CPLUSPLUS_PLUGIN_NEW_REQUEST:
                bufsize, rawmsg = rest
                msg = rawmsg.decode('utf8', 'ignore')
                sender, command, params, trailing = ircfw.parse.irc_message(msg)
                senderbytes = sender[0].encode('utf8')
                paramsbytes = params[0].encode('utf8')
                if self.geordi_location is None or self.busy:
                    # reply with "can't answer right now"
                    replies = ircfw.unparse.make_privmsgs(senderbytes, paramsbytes, b"can't answer right now. try later", int(bufsize.decode('utf8')), 'multiline'
                                                        )
                    replies = list(replies)
                    await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)
                else:
                    nick, trailing = ircfw.parse.get_word(trailing)
                    trigger, cppcode = ircfw.parse.get_word(trailing)

                    try:
                        # send msg to geordi
                        replies = ircfw.unparse.make_privmsgs(
                            const.CPLUSPLUS_PLUGIN_GEORDI_NICK.encode('utf8'), const.CPLUSPLUS_PLUGIN_GEORDI_NICK.encode(
                                'utf8'), cppcode.encode('utf8'), self.geordi_location_bufsize, 'raise'
                        )
                        replies = list(replies)
                        await self.generic_plugin.send_replies(
                            replies, self.geordi_location, self.geordi_location_proxy_name)

                        # set a timeout for no reply from geordi
                        def cb():
                            ircfw.util.create_task(self._on_timeout(), logger=self.logger, message='geordi timeout')
                        timeout_cb = self.ioloop.call_later(10, cb)

                        self.busy = True
                        self.pending_request_data = senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb

                    except RuntimeError as e:
                        self.logger.info('request too big: %s', cppcode)
                        replies = ircfw.unparse.make_privmsgs(
                            senderbytes, paramsbytes, b"code too big. try to make it shorter", int(
                                bufsize.decode('utf8')), 'multiline'
                        )
                        await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)
            elif topic == const.CPLUSPLUS_PLUGIN_GEORDI_REPLY:
                if self.busy:
                    senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb = self.pending_request_data
                    bufsize = int(bufsize.decode('utf8'))
                    # cancel timeout
                    timeout_cb.cancel()

                    # reply to original requester
                    bufsize_geordi, rawmsg = rest
                    bufsize_geordi = int(bufsize_geordi.decode('utf8'))
                    self.geordi_location_bufsize = bufsize_geordi

                    msg = rawmsg.decode('utf8', 'ignore')
                    sender, command, params, trailing = ircfw.parse.irc_message(
                        msg)
                    replies = ircfw.unparse.make_privmsgs(
                        senderbytes, paramsbytes, trailing.encode(
                            'utf8', 'ignore'), bufsize, 'multiline'
                    )
                    await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)
                    self.busy = False
                    self.pending_request_data = None
                else:
                    self.logger.info('ignoring geordi msg')


    async def _on_timeout(self):
        if self.busy:
            senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb = self.pending_request_data
            replies = ircfw.unparse.make_privmsgs(
                senderbytes, paramsbytes, b'your request timed out. try later', int(
                    bufsize.decode('utf8')), 'multiline'
            )
            await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

        self.busy = False
        self.logger.info('timed out for: %s', self.pending_request_data)
        self.pending_request_data = None
