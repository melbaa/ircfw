import logging

import zmq

import ircfw.constants as const
import ircfw.parse

class plugin:
  def __init__(self, zmq_ioloop, zmq_ctx):

    self.logger = logging.getLogger(__name__)
    self.plugin_name = b'irc_ping' #this is the topic we sub to

    self.request = zmq_ctx.socket(zmq.SUB)
    self.request.connect(const.PLUGIN_DISPATCH)
    self.request.setsockopt(zmq.SUBSCRIBE, const.IRC_PING_PLUGIN)

    self.push_reply = zmq_ctx.socket(zmq.PUSH)
    self.push_reply.connect(const.BROKER_BACKEND_REPLIES)

    self.ioloop = zmq_ioloop
    self.ioloop.add_handler(self.request, self.on_request, self.ioloop.READ)

  def on_request(self, sock, evts):
    req = self.request.recv_multipart()
    self.logger.info('received request %s', req)
    topic, zmq_addr, proxy_name, rawmsg = req
    msg = rawmsg.decode('utf8', 'ignore')
    sender, command, params, trailing = ircfw.parse.irc_message(msg)
    pong = const.PONG + b' :' + trailing.encode('utf8')
    reply = [zmq_addr, proxy_name, topic, pong]
    self.logger.info('about to send reply %s', reply)
    self.push_reply.send_multipart(reply)
    self.logger.info('sent!')
