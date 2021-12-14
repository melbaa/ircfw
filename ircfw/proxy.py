import datetime
import logging
import socket
import traceback
import weakref
import ssl

import asyncio

import zmq
import zmq.asyncio

import ircfw.constants as const
import ircfw.globals
import ircfw.irc_connection
import ircfw.util


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
        self.TTL = 2 * 60  # sec. time before timeout
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
        self.timer = self.ioloop.call_later(self.TTL, self.on_timeout)

    def stop_timeout(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def on_anymsg(self):
        self.init_timeout()

    def on_timeout(self):
        self.timeout_count += 1
        if self.timeout_count == 1:
            # send a ping somehow
            self.logger.info('trying to ping via heartbeat')
            self._proxy.queue_binary_reply(b'PING :heartbeat %d' % self.timeout_count)
        elif self.timeout_count == 2:
            # reconnect somehow
            self.logger.info('trying to reconnect via heartbeat')
            # TODO probably make the heartbeat a separate coro and maybe crash main() from it?
            import pdb;pdb.set_trace()
            self._proxy.reconnect()

        # self.timer = None
        self.reset_timeout()

    def on_reconnect_start(self):
        """
        don't need this timer while there's no open connection
        """
        self.stop_timeout()

    def on_reconnect_success(self):
        self.init_timeout()





class proxy:
    """
    relays between the public irc network and the private zmq-based bot network
    """

    def __init__(
            self,
            proxyname,
            command_dispatch_frontend,
            should_see_nicks,
            host,
            port,
            use_ssl,
            nicks,
            irc_password,
            channels,
            ioloop,
            zmq_ctx):
        """
        proxyname - string - for debugging
        should_see_nicks - list of strings - nicks that should be visible via
        this proxy
        rest: see irc_connection.py

        """
        self.proxyname = proxyname.encode('utf8')
        self.ioloop = ioloop

        self.logger = logging.getLogger(__name__)

        self.dealer = zmq_ctx.socket(zmq.DEALER)
        self.dealer.connect(command_dispatch_frontend)

        self.should_see_nicks = should_see_nicks


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


    async def reconnect(self):

        self.logger.info('trying to reconnect')

        if self.irc_connection:
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
            await self.irc_connection.connect()


            """
            advertise nicks on this proxy that SHOULD be available.
            some plugins depend on those nicks. such a timeout is a temporary
            solution; it will probably become a bug at some point when
            a slow joiner happens. TODO FIXME

            we don't pass the proxy directly to the plugin, because we want
            the zmq address of the proxy to reach the plugin

            a possible fix is to spam this message until the plugin acks it.
            requires bidirectional communication and complexity.
            """
            def cb():
                ircfw.util.create_task(self.broadcast_nicks(), logger=self.logger, message='delayed broadcast nicks')
            self.delayedcb = self.ioloop.call_later(5, cb)

            self.irc_heartbeat.on_reconnect_success()

        except RuntimeError:
            self.logger.debug("wtf", exc_info=True)
            """
            delayedcb = zmq.eventloop.ioloop.DelayedCallback(
                self.reconnect,  # loop; try again
                10000,  # 10 sec
                self.ioloop)
            delayedcb.start()
            """
        except Exception:
            self.logger.error(traceback.format_exc())

    def irc_connection_ready(self, fd, evts):

        try:
            pass

        except ssl.SSLWantReadError:
            self.logger.info('SSLWantReadError')
        except socket.error:
            self.logger.error(traceback.format_exc())
            self.ioloop.add_callback(self.reconnect)
        except Exception:
            self.logger.error(traceback.format_exc())


    def queue_binary_reply(self, msg):
        self.irc_connection.queue_binary_reply(msg)


    async def broadcast_nicks(self):
        if not len(self.should_see_nicks):
            # nothing to broadcast
            return

        nicksbytes = [nick.encode('utf8') for nick in self.should_see_nicks]
        nicksbytes = b' '.join(nicksbytes)

        await self.dealer.send_multipart(
            [const.CONTROL_MSG,
            self.proxyname, const.PROXY_NICKS, nicksbytes])

            # msgtype, proxy_name,      rawcmd,      rawcmdargs = rest
            # CONTROL_MSG, proxyname,   PROXY_NICKS, nicks


    async def irc2bot(self):
        """
        read from irc_connection and write to zmq dealer.
        the message sent is multipart and has the following frames:
        """

        while True:
            self.logger.info('irc2bot start iter')
            raw_messages = self.irc_connection.read()


            """
            FIXME currently this is a race with irc_connection.read(),
            nick might change between a .read() and current_nick..() call
            fix would be read() to attach a current nick to each msg
            """
            nick = self.irc_connection.current_nick()

            async for rawmsg in raw_messages:
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
                    await self.dealer.send_multipart(to_send, zmq.NOBLOCK)
                    self.logger.info('sent!')
                except Exception as e:
                    self.logger.error(e.args, e.errno, e.strerror)


    async def bot2irc(self):
        """
        send prepared data to irc

        """
        while True:
            self.logger.info('bot2irc start iter')
            await self.irc_connection.wait_pending_write()

            self.irc_heartbeat.on_anymsg()

            while self.irc_connection.pending_write():
                await self.irc_connection.write()
                # TODO maybe sleep a bit here for basic ratelimiting

    async def drain_backend(self):
        """
        read a reply from the backend and prepare it for sending
        """
        while True:
            self.logger.info('drain_backend start iter')
            rep = await self.dealer.recv_multipart()
            self.logger.info('received reply from backend %s', rep)
            proxy_name, plugin_name, msg = rep

            self.queue_binary_reply(msg)





    async def main(self):
        while True:
            try:
                await self.reconnect()
                irc2bot = ircfw.util.create_task(self.irc2bot(), logger=self.logger, message='irc2bot')
                bot2irc = ircfw.util.create_task(self.bot2irc(), logger=self.logger, message='bot2irc')
                drain_backend = ircfw.util.create_task(self.drain_backend(), logger=self.logger, message='drain_backend')
                aws = [irc2bot, bot2irc, drain_backend]
                done, pending = await asyncio.wait(aws, return_when=asyncio.FIRST_EXCEPTION)
                for task in done:
                    task.result()
            except (ConnectionResetError, OSError) as e:
                self.logger.exception(e)
                await asyncio.sleep(20)  # don't get banned for reconnecting too often
            except Exception as e:
                self.logger.error('you messed up')
                import pdb;pdb.set_trace()
                pass



