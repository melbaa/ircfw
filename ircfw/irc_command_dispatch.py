import logging

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
  def __init__(self, zmq_ioloop_instance, zmq_ctx):

    self.ioloop = zmq_ioloop_instance

    self.router = zmq_ctx.socket(zmq.ROUTER)
    self.router.bind(const.BROKER_FRONTEND)
    self.ioloop.add_handler(self.router, self.read_request, self.ioloop.READ)
    """
    going to publish parsed incoming msgs by topic
    """
    self.publisher = zmq_ctx.socket(zmq.PUB)
    self.publisher.bind(const.BROKER_BACKEND_TOPICS)

    """
    for replies
    """
    self.pull_replies = zmq_ctx.socket(zmq.PULL)
    self.pull_replies.bind(const.BROKER_BACKEND_REPLIES)
    self.ioloop.add_handler(self.pull_replies, self.read_reply, self.ioloop.READ)

    self.logger = logging.getLogger(__name__)



  def read_request(self, socket, evts):
    logmsg = self.router.recv_multipart()
    self.logger.info("received message %s", logmsg)

    #zmq_addr, msgtype, proxy_name, curr_nick, rawmsg = logmsg
    zmq_addr, msgtype, proxy_name, *rest = logmsg #http://www.python.org/dev/peps/pep-3132/
    if msgtype == const.IRC_MSG:
      curr_nick, bufsize, rawmsg = rest
      msg = rawmsg.decode('utf8', 'ignore')
      sender, command, params, trailing = ircfw.parse.irc_message(msg)
      msg_to_pub = [const.IRC_MSG + const.SUBTOPIC_SEP + command.encode('utf8')
                    , zmq_addr, proxy_name, curr_nick, bufsize, rawmsg]
      self.publisher.send_multipart(msg_to_pub)
      self.logger.info("sent %s", msg_to_pub)
    elif msgtype == const.CONTROL_MSG:
      rawcmd, rawcmdargs = rest
      to_send = [const.CONTROL_MSG + const.SUBTOPIC_SEP + rawcmd
                 , zmq_addr, proxy_name, rawcmd, rawcmdargs]
      self.publisher.send_multipart(to_send)
      self.logger.info("sent %s", to_send)
    else:
      self.logger.warn('unknown message type %s for msg %s', msgtype, logmsg)
      raise RuntimeError('unknown message type bro')

  def read_reply(self, sock, evts):
    rep = self.pull_replies.recv_multipart()
    self.logger.info('received reply %s', rep)
    addr, proxy_name, from_plugin, msg = rep
    to_send = [addr, proxy_name, from_plugin, msg]
    self.logger.info('sending to proxy %s', to_send)
    self.router.send_multipart(to_send)

