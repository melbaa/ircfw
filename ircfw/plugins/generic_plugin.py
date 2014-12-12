
import logging

import zmq

import ircfw.constants as const
import ircfw.parse
import ircfw.unparse


class generic_plugin:

    """
    create instance by passing desired topics and callback function.
    the same callback is called for each topic so it's responsibility
    of the caller to differentiate between them on his own.

    use send_replies() to pass messages to different proxies with
    the zmq_addr field.
    """

    def __init__(self, zmq_ioloop, zmq_ctx, logger_name, plugin_name  # eg const.ARTISTINFO_PLUGIN
                 , subscribe_topics  # list
                 , on_msg_callback):
        self.logger = logging.getLogger(logger_name)
        self.plugin_name = plugin_name

        self.request = zmq_ctx.socket(zmq.SUB)
        self.request.connect(const.PLUGIN_DISPATCH)

        for topic in subscribe_topics:
            self.request.setsockopt(zmq.SUBSCRIBE, topic)

        self.push_reply = zmq_ctx.socket(zmq.PUSH)
        self.push_reply.connect(const.BROKER_BACKEND_REPLIES)

        self.ioloop = zmq_ioloop
        self.ioloop.add_handler(
            self.request, on_msg_callback, self.ioloop.READ)

    def send_replies(self, replies, zmq_addr, proxy_name):
        self.logger.info('about to send replies %s', replies)
        for reply in replies:
            reply = [zmq_addr, proxy_name, self.plugin_name, reply]
            self.push_reply.send_multipart(reply)
        self.logger.info('sent!')
