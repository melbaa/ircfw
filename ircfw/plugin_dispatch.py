import logging

import zmq

import ircfw.constants as const
import ircfw.parse


class plugin_dispatch:

    def __init__(self, zmq_ioloop, zmq_ctx):
        self.irc_commands = zmq_ctx.socket(zmq.SUB)
        self.irc_commands.connect(const.BROKER_BACKEND_TOPICS)
        self.irc_commands.setsockopt(zmq.SUBSCRIBE, const.PING_TOPIC)
        self.irc_commands.setsockopt(zmq.SUBSCRIBE, const.PRIVMSG_TOPIC)
        self.irc_commands.setsockopt(zmq.SUBSCRIBE, const.PROXY_NICKS_TOPIC)

        self.plugin_dispatch = zmq_ctx.socket(zmq.PUB)
        self.plugin_dispatch.bind(const.PLUGIN_DISPATCH)

        self.ioloop = zmq_ioloop
        self.ioloop.add_handler(
            self.irc_commands, self.read_and_dispatch, self.ioloop.READ)
        self.logger = logging.getLogger(__name__)

    def read_and_dispatch(self, sock, evts):
        msg = self.irc_commands.recv_multipart()
        self.logger.info("received %s", msg)
        #topic, zmq_addr, proxy_name, curr_nick, rawmsg = msg
        topic, zmq_addr, proxy_name, *rest = msg

        # pub to irc ping plugin: (plugin_name, reply_addr, from_proxy, msg)
        if topic == const.PING_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            to_pub = [const.IRC_PING_PLUGIN, zmq_addr, proxy_name, rawmsg]
            self.plugin_dispatch.send_multipart(to_pub)
            self.logger.info('sent message %s', to_pub)
        # end of irc ping plugin

        #C++ PLUGIN
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            # is not a plugin trigger in the form 'botnick, blablabla'
            if not len(trigger_with_args):
                # it might be a continuation of a longer conversation with some plugin
                # have to check if geordi sent us a message
                if sender[0] == const.CPLUSPLUS_PLUGIN_GEORDI_NICK:
                    # received message from geordi. that is not a plugin trigger
                    # it must be a reply then
                    self.logger.info(
                        'forwarding message from geordi %s', rawmsg)
                    to_pub = [const.CPLUSPLUS_PLUGIN_GEORDI_REPLY, zmq_addr, proxy_name, bufsize, rawmsg
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message to c++, %s', to_pub)

                # nothing else to do
            else:  # plugin trigger with new request
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.CPLUSPLUS_PLUGIN_TRIGGERS:
                    to_pub = [const.CPLUSPLUS_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize                              # send unparsed msg because we need to know who to reply to
                              #(nick) and where (nick/chan) and the request (args)
                              , rawmsg
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message to c++, %s', to_pub)

        elif topic == const.PROXY_NICKS_TOPIC:
            rawcmd, rawcmdargs = rest
            to_pub = [const.CPLUSPLUS_PLUGIN_PROXY_NICKS, zmq_addr, proxy_name, topic, rawcmd, rawcmdargs
                      ]
            self.plugin_dispatch.send_multipart(to_pub)
            self.logger.info('sent message to c++, %s', to_pub)
        # end of C++ PLUGIN

        # start of ARTISTINFO
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.ARTISTINFO_PLUGIN_TRIGGERS:
                    to_pub = [const.ARTISTINFO_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize                              # send unparsed msg because we need to know who to reply to
                              #(nick) and where (nick/chan) and the request (args)
                              , rawmsg
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message to artistinfo, %s', to_pub)
        # end of artistinfo

        # start of hostinfo
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.HOSTINFO_PLUGIN_TRIGGERS:
                    to_pub = [const.HOSTINFO_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message to hostinfo, %s', to_pub)
        # end of hostinfo

        # start of phobias
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.PHOBIAS_PLUGIN_TRIGGERS:
                    to_pub = [const.PHOBIAS_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of phobias

        # start of sadict
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.SADICT_PLUGIN_TRIGGERS:
                    to_pub = [const.SADICT_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of sadict

        # start of re
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.RE_PLUGIN_TRIGGERS:
                    to_pub = [const.RE_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of re

        # start of codepointinfo
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.CODEPOINTINFO_PLUGIN_TRIGGERS:
                    to_pub = [const.CODEPOINTINFO_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), trigger.encode('utf8')  # notice trigger sent
                              , args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of codepointinfo

        # start of length
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.LENGTH_PLUGIN_TRIGGERS:
                    to_pub = [const.LENGTH_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of length

        # start of privmsg ping
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.PRIVMSG_PING_PLUGIN_TRIGGERS:
                    to_pub = [const.PRIVMSG_PING_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of privmsg ping

        # start of reverse
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.REVERSE_PLUGIN_TRIGGERS:
                    to_pub = [const.REVERSE_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of reverse

        # start of pick
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.PICK_PLUGIN_TRIGGERS:
                    to_pub = [const.PICK_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of pick

        # start of pick
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.SUBSTITUTE_PLUGIN_TRIGGERS:
                    to_pub = [const.SUBSTITUTE_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of pick

        # start of define
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.DEFINE_PLUGIN_TRIGGERS:
                    to_pub = [const.DEFINE_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of define

        # start of googlism
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.GOOGLISM_PLUGIN_TRIGGERS:
                    to_pub = [const.GOOGLISM_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), trigger.encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of googlism

        # start of quakelive
        if topic == const.PRIVMSG_TOPIC:
            curr_nick, bufsize, rawmsg = rest
            msg = rawmsg.decode('utf8')
            sender, command, params, trailing = ircfw.parse.irc_message(msg)
            trigger_with_args = ircfw.parse \
                .potential_request(trailing, curr_nick.decode('utf8'))
            if len(trigger_with_args):
                trigger, args = ircfw.parse.get_word(trigger_with_args)
                if trigger in const.QUAKELIVE_PLUGIN_TRIGGERS:
                    to_pub = [const.QUAKELIVE_PLUGIN_NEW_REQUEST, zmq_addr, proxy_name, bufsize, sender[0].encode('utf8'), params[0].encode('utf8'), trigger.encode('utf8'), args.encode('utf8')
                              ]
                    self.plugin_dispatch.send_multipart(to_pub)
                    self.logger.info('sent message, %s', to_pub)
        # end of quakelive
