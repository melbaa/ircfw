
import logging

import zmq

class generic_plugin:

    """
    create instance by passing desired topics and callback function.
    the same callback is called for each topic so it's responsibility
    of the caller to differentiate between them on his own.

    use send_replies() to pass messages to different proxies with
    the zmq_addr field.
    """

    def __init__(
            self,
            logger_name,
            plugin_name,  # eg const.ARTISTINFO_PLUGIN
            subscribe_topics,  # list
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.logger = logging.getLogger(logger_name)
        self.plugin_name = plugin_name

        self.request = zmq_ctx.socket(zmq.SUB)
        self.request.connect(plugin_dispatch)

        for topic in subscribe_topics:
            self.request.setsockopt(zmq.SUBSCRIBE, topic)
            self.logger.info('subscribed to topic ' + str(topic))

        self.push_reply = zmq_ctx.socket(zmq.PUSH)
        self.push_reply.connect(command_dispatch_backend_replies)

        self.ioloop = zmq_ioloop

    async def send_replies(self, replies, zmq_addr, proxy_name):
        self.logger.info('about to send replies %s', replies)
        for reply in replies:
            reply = [zmq_addr, proxy_name, self.plugin_name, reply]
            await self.push_reply.send_multipart(reply)
        self.logger.info('sent!')

    async def read_request(self):
        return await self.request.recv_multipart()
