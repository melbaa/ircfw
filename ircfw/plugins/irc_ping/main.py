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
    get this functionality from a plugin. unfortunately the ad-hoc protocol
    currently used between components has no clean way to support carrying a
    control messages from plugins to other components.

    to stay connected, we have to interact with the network. the way
    (excluding optimizations) is via ping/pong messages.

    network can send us ping, we have to reply with pong. this passive stance
    fails, because we might lose an incoming ping, so we never know when to pong.

    we can send ping, network has to reply with pong. active approach is best,
    because we know for sure that for some reason, we aren't receiving pongs from
    the network. either our ping didn't reach network, or pong didn't reach us.
    assuming a network error, we have to reconnect.

    we have to know (keep state) if we had a recent interaction, if we sent a
    ping and wait for a pong, if a pong hasn't arrived recently and reconnect needed.

    we (this plugin) can't reconnect on its own, it has to tell a proxy to do it.

    this plugin maintains connections with multiple irc networks, via respective
    proxy.

stories:
    network sends us ping, send pong. start timer that on timeout, has to do an
    active ping

    bot just started, start timer that on timeout does an active ping

    timer timeout. send ping. start a timer waiting for pong. on timeout
    ask proxy to reconnect. on pong, stop timer. start timer for active ping.
"""

class plugin:

    def __init__(self, zmq_ioloop, zmq_ctx):

        self.logger = logging.getLogger(__name__)
        self.plugin_name = const.IRC_PING_PLUGIN  # this is the topic we sub to

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
