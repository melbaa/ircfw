import datetime
import logging
import socket
import traceback
import weakref
import ssl

import zmq
import zmq.eventloop

import ircfw.constants as const
import ircfw.globals
import ircfw.irc_connection


class irc_heartbeat:
    """
    reset timeout each time a handler is installed, means we got something to
    read. also zero counter

    on timeout, send a PING, reset timeout, incr counter
    on second timeout, reconnect, reset_timeout, zero counter
    """
    def __init__(self, ioloop, proxy):
        self.ioloop = ioloop
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__)
        self.timer = None
        self.TTL = datetime.timedelta(minutes=4)  # time before timeout
        """
        pointer to parent? is it bad? how to break the circular ref. here
        need it for reconnect, sending a reply
        use a weak reference just in case

        an alternative would be to return "commands" or "advice" to the caller.
        caller then tells proxy what to do and this class is reduced to just a
        state machine. caller will have to map commands to functionality.

        an alternative is to return closures with the required data and
        functions captured. caller can then use the closures whenever it
        wants
        """
        self._proxy = weakref.proxy(proxy)

        self.init_timeout()

    def init_timeout(self):
        self.timeout_count = 0
        self.reset_timeout()

    def reset_timeout(self):
        self.stop_timeout()
        self.timer = self.ioloop.add_timeout(self.TTL, self.on_timeout)

    def stop_timeout(self):
        if self.timer:
            self.ioloop.remove_timeout(self.timer)
            self.timer = None

    def on_anymsg(self):
        self.init_timeout()

    def on_timeout(self):
        self.timeout_count += 1
        if self.timeout_count == 1:
            # send a ping somehow
            self.logger.info('trying to ping')
            self._proxy.queue_binary_reply(b'PING :helloworld')
        elif self.timeout_count == 2:
            # reconnect somehow
            self.logger.info('trying to reconnect')
            self._proxy.reconnect()
        """
        what happens if we cancel an exired timeout?
        from the tornado and minitornado ioloops source, it seems like we
        shouldn't
        """
        self.timer = None
        self.reset_timeout()

    def on_reconnect_start(self):
        """
        don't need this timer while there's no open connection
        """
        self.stop_timeout()

    def on_reconnect_success(self):
        self.init_timeout()


class proxy:
    def __init__(
            self,
            proxyname,
            should_see_nicks,
            host,
            port,
            use_ssl,
            nicks,
            irc_password,
            channels,
            zmq_ioloop_instance,
            zmq_ctx):
        """
        proxyname - string - for debugging
        should_see_nicks - list of strings - nicks that should be visible via
        this proxy
        rest: see irc_connection.py

        """
        self.proxyname = proxyname.encode('utf8')

        self.logger = logging.getLogger(__name__)

        self.ioloop = zmq_ioloop_instance

        self.dealer = zmq_ctx.socket(zmq.DEALER)
        self.dealer.connect(const.BROKER_FRONTEND)
        self.ioloop.add_handler(
            self.dealer, self.on_reply_from_bot, self.ioloop.READ)

        if len(should_see_nicks):
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
                lambda: self.dealer.send_multipart(
                    [const.CONTROL_MSG,
                        self.proxyname, const.PROXY_NICKS, nicksbytes]),
                5000,
                self.ioloop)
            delayedcb.start()

        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.nicks = nicks
        self.irc_password = irc_password
        self.channels = channels
        self.irc_heartbeat = irc_heartbeat(
            self.ioloop,
            self)
        self.irc_connection = None
        self.reconnect()

    def reconnect(self):

        if self.irc_connection:
            self.ioloop.remove_handler(self.irc_connection.irc_socket.fileno())
            self.irc_connection = None

        self.irc_heartbeat.on_reconnect_start()

        try:
            self.irc_connection = ircfw.irc_connection.irc_connection(
                self.host,
                self.port,
                self.use_ssl,
                self.nicks,
                self.irc_password,
                self.channels)

            self.install_handler()
            self.irc_heartbeat.on_reconnect_success()

        except RuntimeError:
            self.logger.debug("wtf happens", exc_info=True)
            delayedcb = zmq.eventloop.ioloop.DelayedCallback(
                self.reconnect,  # loop; try again
                10000,  # 10 sec
                self.ioloop)
            delayedcb.start()
        except Exception:
            self.logger.error(traceback.format_exc())

    def irc_connection_ready(self, fd, evts):

        def on_read(self):
            """
            read from irc_connection and write to zmq dealer.
            the message sent is multipart and has the following frames:
            """
            raw_messages = self.irc_connection.read()

            """
            FIXME currently this is a race with irc_connection.read(),
            nick might change between a .read() and current_nick..() call
            fix would be read() to attach a current nick to each msg
            """
            nick = self.irc_connection.current_nick()
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

                BUFSIZE = self.irc_connection.bufsize()
                to_send = [
                    const.IRC_MSG,
                    self.proxyname,
                    nick,
                    str(BUFSIZE).encode('utf8'),
                    rawmsg]
                self.logger.info('about to send %s', to_send)

                try:
                    self.dealer.send_multipart(to_send, zmq.NOBLOCK)
                    self.logger.info('sent!')
                except Exception as e:
                    self.logger.error(e.args, e.errno, e.strerror)

        def on_write(self):
            more = self.irc_connection.write()
            self.logger.info('wrote reply to irc_connection.irc_socket')

        try:

            self.irc_heartbeat.on_anymsg()

            if evts & self.ioloop.READ:
                on_read(self)
            if evts & self.ioloop.WRITE:
                on_write(self)
            if evts & self.ioloop.ERROR:
                raise RuntimeError("oops. socket returned error")

            self.install_handler()

        except ssl.SSLWantReadError:
            self.logger.info('SSLWantReadError')
            self.install_handler()
        except socket.error:
            self.logger.error(traceback.format_exc())
            self.ioloop.add_callback(self.reconnect)
        except Exception:
            self.logger.error(traceback.format_exc())

    def on_reply_from_bot(self, sock, evts):
        """
        read a reply from the irc bot and pass it to irc
        """
        rep = self.dealer.recv_multipart()
        self.logger.info('received reply from backend %s', rep)
        proxy_name, plugin_name, msg = rep

        self.queue_binary_reply(msg)

    def queue_binary_reply(self, msg):
        self.irc_connection.queue_binary_reply(msg)
        self.install_handler()

    def install_handler(self):
        # self.ioloop.remove_handler(self.irc_connection.irc_socket.fileno())
        what = self.ioloop.READ
        if self.irc_connection.pending_write():
            what = what | self.ioloop.WRITE

        self.ioloop.add_handler(
            self.irc_connection.irc_socket.fileno(),
            self.irc_connection_ready,
            what)
        logmsg = 'installed irc_socket handler for '
        if what & self.ioloop.READ:
            logmsg += 'READ '
        if what & self.ioloop.WRITE:
            logmsg += 'WRITE '
        if what & self.ioloop.ERROR:
            logmsg += 'ERROR '
        self.logger.info(logmsg)
