import logging

import zmq

import ircfw.constants as const
import ircfw.parse

"""
todo active ping

components:
    this plugin
    the proxies talking to various irc networks and this bot
    irc networks


facts:
    implementing the functionality here is inefficient. it makes much more
sense to do it closer to the network (in proxy, as it's responsible for
reconnections). the point was to see what needed to be touched in order to
get this functionality from a plugin. turns out not much, but enough to require
knowledge of the rest of the framework.
    to stay connected, we have to interact with the network. the way
(excluding optimizations) is via ping/pong messages.
    network can send us ping, we have to reply with pong. this passive stance
fails, because we might lose an incoming ping, so we never know when to pong.
    we can send ping, network has to reply with pong. active approach is best,
because we know for sure that for some reason, we aren't receiving pongs from
the network. either our ping didn't reach network, or pong didn't reach us.
assuming a network error, we have to reconnect.
    we have to know (keep state) if we had a recent interaction, if we sent a
ping and wait for a pong, if a pong hasn't arrived recently.
    we (this plugin) can't reconnect on its own, it has to tell a proxy to do it.
    this plugin maintains connections with multiple irc networks, via respective
proxy.


states:
    CLEAN (60 sec) - had server interaction recently, all should be fine
        start a timeout
        on timeout expires: send a ping, move to PING_SENT
        on receive ping/pong: restart timeout
    PING_SENT (60 sec) - no interaction recently, so we send a PING
        on timeout, tell the proxy, talking to that server to reconnect
    RECONNECTING (60 sec)


"""

class plugin:

    def __init__(self, zmq_ioloop, zmq_ctx):

        self.logger = logging.getLogger(__name__)
        self.plugin_name = b'irc_ping'  # this is the topic we sub to

        self.request = zmq_ctx.socket(zmq.SUB)
        self.request.connect(const.PLUGIN_DISPATCH)
        self.request.setsockopt(zmq.SUBSCRIBE, const.IRC_PING_PLUGIN)

        self.push_reply = zmq_ctx.socket(zmq.PUSH)
        self.push_reply.connect(const.BROKER_BACKEND_REPLIES)

        self.ioloop = zmq_ioloop
        self.ioloop.add_handler(
            self.request, self.on_request, self.ioloop.READ)

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
