import logging
import asyncio

import zmq

import ircfw.globals
import ircfw.constants as const
import ircfw.parse


class irc_command_dispatch:

    """
    the class will
    1) receive potential requests on the router socket.
    2) publish each request by topic the irc command type on the
      publisher socket
    3) collect replies on the pull socket
    4) dispatch replies to the clients on the router socket from 1)
    """

    def __init__(
            self,
            command_dispatch_frontend,
            command_dispatch_backend_topics,
            command_dispatch_backend_replies,
            ioloop,
            zmq_ctx):

        self.ioloop = ioloop
        self.router = zmq_ctx.socket(zmq.ROUTER)
        self.router.bind(command_dispatch_frontend)
        """
        going to publish parsed incoming msgs by topic
        """
        self.publisher = zmq_ctx.socket(zmq.PUB)
        self.publisher.bind(command_dispatch_backend_topics)

        """
        for replies
        """
        self.pull_replies = zmq_ctx.socket(zmq.PULL)
        self.pull_replies.bind(command_dispatch_backend_replies)
        self.logger = logging.getLogger(__name__)

    async def read_request(self):
        while True:
            logmsg = await self.router.recv_multipart()
            self.logger.info("received message %s", logmsg)

            # zmq_addr, msgtype, proxy_name, curr_nick, rawmsg = logmsg
            # http://www.python.org/dev/peps/pep-3132/
            zmq_addr, msgtype, proxy_name, *rest = logmsg
            if msgtype == const.IRC_MSG:
                curr_nick, bufsize, rawmsg = rest
                msg = rawmsg.decode('utf8', 'ignore')
                sender, command, params, trailing = ircfw.parse.irc_message(msg)
                msg_to_pub = [
                    const.IRC_MSG + const.SUBTOPIC_SEP + command.encode('utf8'),
                    zmq_addr,
                    proxy_name,
                    curr_nick,
                    bufsize,
                    rawmsg]
                await self.publisher.send_multipart(msg_to_pub)
                self.logger.info("sent %s", msg_to_pub)
            elif msgtype == const.CONTROL_MSG:
                rawcmd, rawcmdargs = rest
                to_send = [
                    const.CONTROL_MSG + const.SUBTOPIC_SEP + rawcmd,
                    zmq_addr,
                    proxy_name,
                    rawcmd,
                    rawcmdargs]
                await self.publisher.send_multipart(to_send)
                self.logger.info("sent %s", to_send)
            else:
                self.logger.warn(
                    'unknown message type %s for msg %s', msgtype, logmsg)
                raise RuntimeError('unknown message type bro')

    async def read_reply(self):
        while True:
            rep = await self.pull_replies.recv_multipart()
            self.logger.info('received reply %s', rep)
            addr, proxy_name, from_plugin, msg = rep
            to_send = [addr, proxy_name, from_plugin, msg]
            self.logger.info('sending to proxy %s', to_send)
            await self.router.send_multipart(to_send)

    async def main(self):
        await asyncio.wait([self.read_reply(), self.read_request()])




