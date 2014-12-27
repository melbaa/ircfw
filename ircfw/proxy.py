import traceback
import logging
import socket

import zmq
import zmq.eventloop

import ircfw.constants as const
import ircfw.globals
import ircfw.irc_connection


class proxy:

    def __init__(self, proxyname, should_see_nicks, host, port, use_ssl, nicks, irc_password, channels, zmq_ioloop_instance, zmq_ctx
                 ):
        """
        proxyname - string - for debugging
        should_see_nicks - list of strings - nicks that should be visible via this proxy
        rest: see irc_connection.py

        """
        self.proxyname = proxyname.encode('utf8')

        self.logger = logging.getLogger(__name__)

        self.ioloop = zmq_ioloop_instance

        #self.dealer = ircfw.globals.CONTEXT.socket(zmq.DEALER)
        self.dealer = zmq_ctx.socket(zmq.DEALER)
        self.dealer.connect(const.BROKER_FRONTEND)
        self.ioloop.add_handler(
            self.dealer, self.on_reply_from_bot, self.ioloop.READ)

        if len(should_see_nicks) > 0:
            """
            advertise nicks on this proxy that SHOULD be available.
            some plugins depend on those nicks. such a timeout is a temporary
            solution; it will probabyl become a bug at some point when
            a slow joiner happens. TODO FIXME

            we don't pass the proxy directly to the plugin, because we want
            the zmq address of the proxy to reach the plugin

            a possible fix is to spam this message until the plugin acks it.
            requires bidirectional communication and complexity.
            """
            nicksbytes = [nick.encode('utf8') for nick in should_see_nicks]
            nicksbytes = b' '.join(nicksbytes)
            delayedcb = zmq.eventloop.ioloop.DelayedCallback(
                lambda: self.dealer.send_multipart([const.CONTROL_MSG, self.proxyname, const.PROXY_NICKS, nicksbytes]), 5000, self.ioloop)
            delayedcb.start()

        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.nicks = nicks
        self.irc_password = irc_password
        self.channels = channels
        self.irc_connection = None
        self.reconnect()

    def reconnect(self):

        if self.irc_connection:
            self.ioloop.remove_handler(self.irc_connection.irc_socket.fileno())
            self.irc_connection = None

        try:
            self.irc_connection = ircfw.irc_connection.irc_connection(
                self.host, self.port, self.use_ssl, self.nicks, self.irc_password, self.channels
            )

            self.ioloop.add_handler(self.irc_connection.irc_socket.fileno(), self.irc_connection_ready, self.ioloop.READ | self.ioloop.WRITE
                                    #, self.ioloop.WRITE
                                    )
        except RuntimeError as e:
            self.logger.debug("wtf happens", exc_info=True)
            delayedcb = zmq.eventloop.ioloop.DelayedCallback(
                self.reconnect  # loop; try again
                , 10000  # 10 sec
                , self.ioloop)
            delayedcb.start()
        except Exception as err:
            self.logger.error(traceback.format_exc())

    def irc_connection_ready(self, fd, evts):

        def on_read(self):
            """
            read from irc_connection and write to zmq dealer.
            the message sent is multipart and has the following frames:
            """
            raw_messages = self.irc_connection.read()

            """
      FIXME currently this is a race with irc_connection.read(), nick might
      change between a .read() and current_nick..() call
      fix would be read() to attach a current nick to each msg
      """
            current_irc_nick = self.irc_connection.current_nick_pass()[0]
            for rawmsg in raw_messages:
                self.logger.info(rawmsg)

                """
        self.proxyname for debugging
        msgtype is irc_raw
          or control, so we can notify plugin dispatch
          there should be a geordi here
        current_irc_nick so plugin dispatch know if it's a trigger,
          only if msgtype is irc_raw
        """
                to_send = [const.IRC_MSG, self.proxyname                           # lame, have to fix in irc_connection
                           , current_irc_nick.encode('utf8'), str(self.irc_connection.BUFSIZE).encode('utf8'), rawmsg
                           ]
                self.logger.info('about to send %s', to_send)

                if self.irc_connection.pending_write():
                    # in case irc_connection itself wanted to write something
                    self.install_handler(self.ioloop.READ | self.ioloop.WRITE)
                try:
                    self.dealer.send_multipart(to_send, zmq.NOBLOCK)
                    self.logger.info('sent!')
                except Exception as e:
                    self.logger.error(e.args, e.errno, e.strerror)

        def on_write(self):
            more = self.irc_connection.write()
            self.logger.info('wrote reply to irc_connection.irc_socket')
            if more == 0:
                """
                reinstall READ only handler if there is nothing else to write
                when someone queues something to write, he has to install a
                READ|WRITE handler
                """
                self.install_handler(self.ioloop.READ)

        try:
            if evts & self.ioloop.READ:
                on_read(self)
            if evts & self.ioloop.WRITE:
                on_write(self)
            if evts & self.ioloop.ERROR:
                raise RuntimeError("oops. socket returned error")
        except socket.error as err:
            self.logger.error(traceback.format_exc())
            self.ioloop.add_callback(self.reconnect)
        except Exception as err:
            self.logger.error(traceback.format_exc())

    def on_reply_from_bot(self, sock, evts):
        """
        read a reply from the irc bot and pass it to irc
        incoming messages on dealer socket are like this:
        frame 1: type. one of
          irc_raw:
          control:
        frame 2: msg
        """
        rep = self.dealer.recv_multipart()
        self.logger.info('received reply from backend %s', rep)
        proxy_name, plugin_name, msg = rep

        self.irc_connection.queue_binary_reply(msg)
        self.install_handler(self.ioloop.READ | self.ioloop.WRITE)
        """
    if msgtype == b'irc_raw':
      self.irc_connection.queue_binary_reply(msg)
    else:
      raise RuntimeError('unknown message type')
    """

    def install_handler(self, what):
        # self.ioloop.remove_handler(self.irc_connection.irc_socket.fileno())
        self.ioloop.add_handler(
            self.irc_connection.irc_socket.fileno(), self.irc_connection_ready, what)
        logmsg = 'installed irc_socket handler for '
        if what & self.ioloop.READ:
            logmsg += 'READ '
        if what & self.ioloop.WRITE:
            logmsg += 'WRITE '
        if what & self.ioloop.ERROR:
            logmsg += 'ERROR '
        self.logger.info(logmsg)
