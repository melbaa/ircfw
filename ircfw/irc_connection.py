import logging
import socket
import ssl
import traceback
import random

import asyncio

import ircfw.constants as const
import ircfw.parse
import ircfw.unparse


def utf8(txt):
    return txt.encode('utf8', errors='strict')

def decodeutf8(rawbytes):
    return rawbytes.decode('utf8')


class irc_protocol_handlers:
    def __init__(self, nicks, irc_password, channels):
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__)
        self.nicks = []  # list of (nick, pass) tuples for nickserv
        for nick, passwd in nicks:
            self.nicks.append((utf8(nick), utf8(passwd)))  # note tuple
        """
        the index for enumerate(self.nicks)
        don't use directly, use the current_nick() function
        """
        self._current_nick = 0
        self.irc_password = utf8(irc_password)  # for irc PASS msg
        self.channels = channels
        """
        the max num of bytes for a command is 512, including
        the \r\n at the end, thus 510 for command and params only.
        It is lowered on rpl_whoreply (actually possible with rpl_welcome
        too and should be simpler, but we might not have our cloak yet)
        to compensate for user/mask/host size.
        """
        self.BUFSIZE = 510

    def register(self):
        """
        server registration is a mess. see irc_registration.graphml
        """
        if len(self.irc_password):
            yield b"PASS " + self.irc_password
        yield from self.try_nick()

    def feed(self, rawline):
        """
            tuka da  ima handleri za rpl_welcome i tn. zaradi bufsize????
            i ostanalite neshta ot command.py, zaeti nikove, ghosts
        """
        line = rawline.decode('utf8', 'ignore')
        sender, command, params, trailing = ircfw.parse.irc_message(line)

        # verbose log
        # logmsg = 'parsed <sender> {} <command> {} <params> {} <trailing> {}'
        # self.logger.debug(logmsg.format(sender, command, params, trailing))

        command_bin = command.encode('utf8')
        if command_bin == const.RPL_WELCOME:
            yield from self.on_rpl_welcome()
        elif command_bin == const.RPL_WHOREPLY:
            yield from self.on_rpl_whoreply(params)
        elif command_bin == const.NOTICE:
            yield from self.on_notice(sender, params, trailing)
        elif command_bin == const.ERR_NOSUCHNICK:
            yield from self.on_err_nosuchnick(params)
        elif command_bin == const.ERR_UNAVAILRESOURCE:
            yield from self.on_err_unavailresource(params, sender, trailing)
        elif command_bin == const.ERR_NICKNAMEINUSE:
            yield from self.on_err_nicknameinuse()
        elif command_bin == const.PING:
            yield from self.on_PING(trailing)
        elif command_bin == const.PONG:
            # don't have to do anything here
            self.logger.info('got ' + line)
            pass

    def try_nick(self):
        nick, passwd = self.current_nick_pass()
        yield b"NICK " + nick
        yield b"USER melba 8 * :surprise!"

    def current_nick_pass(self):
        idx = self._current_nick
        try:
            return self.nicks[idx]
        except IndexError:
            alnums = b"abcdefghijklmnopqrstuvwxyz1234567890"
            suffix = bytearray()
            suffix.append(random.choice(alnums))
            suffix.append(random.choice(alnums))
            suffix.append(random.choice(alnums))
            firstnick = self.nicks[0][0]
            randnick = firstnick + b'_' + suffix
            return randnick, b''
        raise RuntimeError("why are you here?")

    def nick_rotate(self):
        self._current_nick += 1

    def on_PING(self, trailing):
        yield const.PONG + b' :' + utf8(trailing)

    def on_rpl_welcome(self):
        # if we supplied passwords we have to wait for a reply from nickserv
        # and join channels later else we can join right away
        nick, passwd = self.current_nick_pass()
        if len(passwd):
            yield b'PRIVMSG NickServ :' + b'IDENTIFY ' + passwd
        else:
            for chan in self.channels:
                yield from self.join_chan(chan)
        yield b"WHO " + nick

    def on_rpl_whoreply(self, cmd_params):
        self.logger.info(
            "352 rpl_whoreply nick_pass={} cmd_params={}".format(
                str(self.current_nick_pass()), str(cmd_params)))

        fw_nick = decodeutf8(self.current_nick_pass()[0])
        cmd_nick = cmd_params[0]
        if fw_nick == cmd_nick:
            sub = 0
            sub += 1  # :
            sub += len(cmd_params[0])  # nick
            sub += 1  # !
            sub += len(cmd_params[2])  # userid
            sub += 1  # @
            sub += len(cmd_params[3])  # host
            sub += 1  # <space>
            self.BUFSIZE -= sub
            self.logger.info("on_rpl_whoreply BUFSIZE is now %s", self.BUFSIZE)
        return
        yield  # magic

    def on_notice(self, sender, params, trailing):
        if len(sender) >= 2 \
                and sender[0] == "NickServ" \
                and params[0] == decodeutf8(self.current_nick_pass()[0]) \
                and (trailing.find('You are now identified for') != -1
                    or trailing.find('you are now recognized') != -1):
                # join channels
            for chan in self.channels:
                yield from self.join_chan(chan)
            yield b"WHO " + self.current_nick_pass()[0]

    def on_err_nosuchnick(self, params):
        if params[1] == 'NickServ':
            # join channels
            for chan in self.channels:
                yield from self.join_chan(chan)

    def on_err_unavailresource(self, params, sender, trailing):
        nick, passwd = self.current_nick_pass()
        self.logger.debug(str(params) + ' ' + str(nick) + ' ' + str(passwd))
        """
            TODO FIXME this doesn't execute, i think it should be params[0]
            find how to recerate the situation (ghosted nick), inspect what
            the server sends

            hard to trace because the situation fixes itself
            (ghosted nick released after a few hours by server)
        """
        if params[1] == nick \
                and sender[0] == 'NickServ' \
                and trailing.find('temporarily unavailable') != -1:
            msg = b"release" + b' ' + nick + b' ' + passwd
            yield b'PRIVMSG NickServ :' + msg
            self.logger.warn(
                'nick %s is being protected, tried to release it', nick)
            self.nick_rotate()
            yield from self.try_nick()

    def on_err_nicknameinuse(self):
        nick, passwd = self.current_nick_pass()
        self.logger.warn('nick %s is already used, rotating', nick)
        self.nick_rotate()
        yield from self.try_nick()

    def join_chan(self, channel):
        if isinstance(channel, list):
            channel, pwd = channel
            yield b"JOIN" + b" " + utf8(channel) + b" " + utf8(pwd)
        else:
            yield b"JOIN" + b" " + utf8(channel)


class irc_connection:

    """
    the class is meant to be used as follows:
    - caller creates an instance, which tries to register with server
    immediately. nothing is sent over the wire yet, just enqueued
    - caller calls
    irc_connection.queue_binary_reply(bytes) when it wants to send something
    to irc server. nothing is sent over the wire yet
    - caller polls irc_connection.irc_socket or
    irc_connection.fileno() for readiness. caller calls irc_connection.read()
    for read readiness; irc_connection.write() for write readiness and this
    sends bytes over the wire
    """

    def __init__(
            self,
            host='irc.d-t-net.de',
            port=6667,
            use_ssl=False,
            nicks=[("nick1", 'pass1'), ('nick2', 'pass2')],
            irc_password='',
            channels=('#testschan',)):

        self.logger = logging.getLogger(__name__)

        """
        recv takes a bufsize argument, but nobody bothers to actually research
        what bufsize makes sense on their platform. and it's even less obvious
        for crossplatform python. so we use an arbitrary power of 2 as
        recommended in the docs.

        update: docs probably recommend 4096, because kernel pages are often 4k

        update: 262144 is mentioned in Lib/asyncio/selector_events.py as
        max_size = 256 * 1024

        update: MaxRecvDataSegmentLength - Sets the maximum data segment
        length that can be received. This value should be set to multiples
        of PAGE_SIZE. Currently the maximum supported value is 64 * PAGE_SIZE,
        e.g. 262144 if PAGE_SIZE is 4kB.
        """
        self.RECVSIZE = 4096

        self.irc_host = host
        self.irc_port = port
        self.use_ssl = use_ssl

        self.reader, self.writer = None, None

        """
        the irc_socket gives us incomplete irc messages so we queue them
        here until we can pull out a complete one
        """
        self._recv_queue = bytearray()
        """
        the irc_socket might not be able to receive a complete message so
        we queue the pending bytes here
        """
        self._send_queue = bytearray()
        self._send_queue_flag = asyncio.Event()

        self.irc_handlers = irc_protocol_handlers(
            nicks, irc_password, channels)

        """
        register to irc netw, send PASS and NICK
        """
        irc_msgs = self.irc_handlers.register()
        for msg in irc_msgs:
            self.queue_binary_reply(msg)

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(
            host=self.irc_host,
            port=self.irc_port,
            ssl=self.use_ssl,
        )


    async def read(self):
        """
        read some data from irc_connection._recv_queue or
        irc_connection.irc_socket and
        return a list of complete but unparsed messages to caller.
        the messages are byte arrays. caller will decide what to
        do next
        """
        def find_end_line(bytebuf):
            newlinesz = 2
            foundpos = bytebuf.find(b'\r\n')  # strict ircd impl
            if foundpos == -1:
                foundpos = bytebuf.find(b'\n')  # lame impl
                newlinesz -= 1
            return newlinesz, foundpos

        more = await self.reader.read(self.RECVSIZE)

        if len(more):
            self._recv_queue += more
        else:
            raise socket.error("socket connection broken")  # socket closed??

        newlinesz, foundpos = find_end_line(self._recv_queue)
        while foundpos != -1:
            newline = self._recv_queue[:foundpos]
            self._recv_queue = self._recv_queue[foundpos + newlinesz:]

            # self.logger.info("getline: " + str(newline))

            irc_msgs = self.irc_handlers.feed(newline)
            for msg in irc_msgs:
                self.queue_binary_reply(msg)

            yield newline
            newlinesz, foundpos = find_end_line(self._recv_queue)

    async def write(self):
        """
        return
        0 - nothing more to write
        number > 0 - num bytes remaining to write
        """
        if len(self._send_queue) == 0:
            self.logger.info('nothing to write')
            return

        self.logger.info('trying to send: ' + str(self._send_queue))

        self.writer.write(self._send_queue)
        await self.writer.drain()

        self.logger.info('sent: ' + str(self._send_queue))
        self._send_queue = bytearray()


    def bufsize(self):
        return self.irc_handlers.BUFSIZE

    def current_nick(self):
        nick, passwd = self.irc_handlers.current_nick_pass()
        return nick

    def queue_binary_reply(self, binmsg, option='raise'):
        """queue a binary message, utf8 encoded, at most BUFSIZE long
        for sending.
        binmsg does NOT have \r\n at the end, we add it here
        """

        BUFSIZE = self.bufsize()

        if option == 'raise':
            if len(binmsg) > BUFSIZE:
                raise RuntimeError("message too long")
        elif option == 'truncate':
            binmsg = binmsg[:BUFSIZE]
        else:
            raise RuntimeError('unknown option')

        if binmsg[-2] == b'\r\n':
            raise RuntimeError(r"don't add \r\n yourself, i'll do it")
        self._send_queue += binmsg
        self._send_queue += b'\r\n'

        self.logger.info('setting send_queue_flag')
        self._send_queue_flag.set()  # notify waiter there's data

    async def wait_pending_write(self):
        self.logger.info('waiting on send_queue_flag')
        await self._send_queue_flag.wait()

        self.logger.info('clearing send_queue_flag')
        self._send_queue_flag.clear()  # waiter knows there's data

    def pending_write(self):
        return len(self._send_queue) != 0
