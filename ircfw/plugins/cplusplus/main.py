"""
there's a c++ bot on freenode (geordi, clang), quakenet (geordi)
"""

import logging

import zmq
import zmq.eventloop

import ircfw.constants as const
import ircfw.parse


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
        self.busy = False  # true if waiting reply from geordi or timeout
        self.pending_request_data = None  # state while geordi answers

        self.logger = logging.getLogger(__name__)
        self.plugin_name = const.CPLUSPLUS_PLUGIN

        self.request = zmq_ctx.socket(zmq.SUB)
        self.request.connect(plugin_dispatch)
        self.request.setsockopt(
            zmq.SUBSCRIBE, const.CPLUSPLUS_PLUGIN_NEW_REQUEST)
        self.request.setsockopt(
            zmq.SUBSCRIBE, const.CPLUSPLUS_PLUGIN_PROXY_NICKS)
        self.request.setsockopt(
            zmq.SUBSCRIBE, const.CPLUSPLUS_PLUGIN_GEORDI_REPLY)

        self.push_reply = zmq_ctx.socket(zmq.PUSH)
        self.push_reply.connect(command_dispatch_backend_replies)

        self.ioloop = zmq_ioloop
        self.ioloop.add_handler(
            self.request, self.on_request, self.ioloop.READ)

    def on_request(self, sock, evts):
        req = self.request.recv_multipart()
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
                self.logger.info('geordi_location update from msg %s', req)
        elif topic == const.CPLUSPLUS_PLUGIN_NEW_REQUEST:
            bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8', 'ignore')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            senderbytes = sender[0].encode('utf8')
            paramsbytes = params[0].encode('utf8')
            if (self.geordi_location is None) or (self.busy):
                # reply with "can't answer right now"
                replies = ircfw.unparse.make_privmsgs(senderbytes, paramsbytes, b"can't answer right now. try later", int(bufsize.decode('utf8')), 'multiline'
                                                      )
                self._send_replies(replies, zmq_addr, proxy_name)
            else:
                nick, trailing = ircfw.parse.get_word(trailing)
                trigger, cppcode = ircfw.parse.get_word(trailing)

                try:
                    # send msg to geordi
                    replies = ircfw.unparse.make_privmsgs(
                        const.CPLUSPLUS_PLUGIN_GEORDI_NICK.encode('utf8'), const.CPLUSPLUS_PLUGIN_GEORDI_NICK.encode(
                            'utf8'), cppcode.encode('utf8'), int(bufsize.decode('utf8')), 'raise'
                    )
                    self._send_replies(
                        replies, self.geordi_location, proxy_name)

                    # set a timeout for no reply from geordi
                    timeout_cb = zmq.eventloop.ioloop.DelayedCallback(
                        self._on_timeout, 10000, self.ioloop
                    )
                    timeout_cb.start()

                    self.busy = True
                    self.pending_request_data = senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb

                except RuntimeError as e:
                    self.logger.info('request too big: %s', cppcode)
                    replies = ircfw.unparse.make_privmsgs(
                        senderbytes, paramsbytes, b"code too big. try to make it shorter", int(
                            bufsize.decode('utf8')), 'multiline'
                    )
                    self._send_replies(replies, zmq_addr, proxy_name)

        elif topic == const.CPLUSPLUS_PLUGIN_GEORDI_REPLY:
            if self.busy:
                senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb = self.pending_request_data
                # cancel timeout
                timeout_cb.stop()

                # reply to original requester
                bufsize_meh, rawmsg = rest
                msg = rawmsg.decode('utf8', 'ignore')
                sender, command, params, trailing = ircfw.parse.irc_message(
                    msg)
                replies = ircfw.unparse.make_privmsgs(
                    senderbytes, paramsbytes, trailing.encode(
                        'utf8', 'ignore'), int(bufsize.decode('utf8')), 'multiline'
                )
                self._send_replies(replies, zmq_addr, proxy_name)
                self.busy = False
                self.pending_request_data = None

            # else ignore the geordi

    def _send_replies(self, replies, zmq_addr, proxy_name):
        self.logger.info('about to send replies %s', replies)
        for reply in replies:
            reply = [zmq_addr, proxy_name, self.plugin_name, reply]
            self.push_reply.send_multipart(reply)
        self.logger.info('sent!')

    def _on_timeout(self):
        if self.busy:
            senderbytes, paramsbytes, bufsize, zmq_addr, proxy_name, timeout_cb = self.pending_request_data
            replies = ircfw.unparse.make_privmsgs(
                senderbytes, paramsbytes, b'your request timed out. try later', int(
                    bufsize.decode('utf8')), 'multiline'
            )
            self._send_replies(replies, zmq_addr, proxy_name)

        self.busy = False
        self.logger.info('timed out for: %s', self.pending_request_data)
        self.pending_request_data = None
