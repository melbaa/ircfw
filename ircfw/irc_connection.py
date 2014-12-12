import logging
import socket
import ssl
import traceback

import ircfw.constants as const
import ircfw.parse
import ircfw.unparse


class irc_connection:
    """
    the class is meant to be used as follows:
    - caller creates an instance, which tries to register with server
    immediately. nothing is sent over the wire yet, just enqueued
    - caller calls irc_connection.queue_reply(string) or
    irc_connection.queue_binary_reply(bytes) when it wants to send something
    to irc server. nothing is sent over the wire yet
    - caller polls irc_connection.irc_socket or
    irc_connection.fileno() for readiness. caller calls irc_connection.read()
    for read readiness; irc_connection.write() for write readiness and this
    sends bytes over the wire
    """

    def __init__(self
    , host = 'irc.d-t-net.de'
    , port = 6667
    , use_ssl = False
    , nicks = [("nick1", 'pass1'),('nick2', 'pass2')] #list of (nick, pass) tuples
    , irc_password = ''
    , channels = ('#testschan',)
    ):

        """the max num of bytes for a command is 512, including
              the \r\n at the end, thus 510 for command and params only.
              It is lowered on rpl_whoreply (actually possible with rpl_welcome
              too and should be simpler, but we might not have our cloak yet)
              to compensate for user/mask/host size. see command.py
        """
        self.logger = logging.getLogger(__name__)

        self.BUFSIZE = 510
        self.nicks = nicks
        """
        the index for enumerate(self.nicks)
        don't use directly, use the current_nick() function
        """
        self._current_nick = 0
        self.channels = channels

        self.irc_password = irc_password
        self.irc_host = host
        self.irc_port = port
        self.use_ssl = use_ssl

        self.irc_socket = self.create_socket(self.irc_host
            , self.irc_port
            , self.use_ssl
        )
        self.irc_socket.setblocking(0)

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



        """
        server registration is a mess. see irc_registration.graphml
        """
        if len(self.irc_password):
            self.queue_reply("PASS " + self.irc_password)
        self.try_nick()


    def read(self):
        """
        read some data from irc_connection._recv_queue or
        irc_connection.irc_socket and
        return a list of complete but unparsed messages to caller.
        the messages are byte arrays. caller will decide what to
        do next
        """
        def find_end_line(bytebuf):
            newlinesz = 2
            foundpos = bytebuf.find(b'\r\n') #strict ircd impl
            if foundpos == -1:
                foundpos = bytebuf.find(b'\n') #lame impl
                newlinesz -= 1
            return newlinesz, foundpos

        more = None
        if isinstance(self.irc_socket, ssl.SSLSocket):
            more = self.irc_socket.read(self.BUFSIZE)
        else:
            more = self.irc_socket.recv(self.BUFSIZE)

        if len(more):
            self._recv_queue += more
        else:
            raise socket.error("socket connection broken") #socket closed??

        newlinesz, foundpos = find_end_line(self._recv_queue)
        while foundpos != -1:
            newline = self._recv_queue[:foundpos]
            self._recv_queue = self._recv_queue[foundpos+newlinesz:]
            #self.logger.info("getline: " + str(newline))
            #yield newline.decode('utf-8', 'ignore') #note the yield

            self._local_handlers(newline)
            yield newline
            newlinesz, foundpos = find_end_line(self._recv_queue)



    def write(self):
        """
        return
        0 - nothing more to write
        number > 0 - num bytes remaining to write
        """
        if len(self._send_queue) == 0:
            self.logger.info('had nothing to write')
            return 0

        #self.mysendall(self._send_queue)
        self.logger.info('trying to send: ' + str(self._send_queue))
        c = 0
        if isinstance(self.irc_socket, ssl.SSLSocket):
            c = self.irc_socket.write(self._send_queue)
        else:
            c = self.irc_socket.send(self._send_queue)

        self.logger.info('sent: ' + str(self._send_queue[:c]))
        self._send_queue = self._send_queue[c:]
        self.logger.info('remaining: ' + str(self._send_queue))
        #time.sleep(3)
        remaining = len(self._send_queue)
        return remaining



    def create_socket(self, host, port, ssl_conn, timeout = None):
        msg = "getaddrinfo returns an empty list"
        try:
                for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
                        af, socktype, proto, canonname, sa = res
                        sock = None
                        try:
                                sock = socket.socket(af, socktype, proto)
                                if ssl_conn:
                                        sock = ssl.wrap_socket(sock, suppress_ragged_eofs=True, do_handshake_on_connect=True)
                                if timeout is not None:
                                        sock.settimeout(timeout) #raises SSLError with ssl sockets :(
                                sock.connect(sa)
                                return sock
                        except (socket.error, ssl.SSLError):
                                self.logger.info(traceback.format_exc())
                                if sock is not None:
                                        sock.close()
                                """
                                sometimes we get unexpected eof (8)
                                #http://tools.ietf.org/html/rfc2246#section-7.2.1
                                it's because of unproper shutdown
                                """
        except socket.gaierror:
                self.logger.info(traceback.format_exc())
        raise RuntimeError("couldn't connect :(")


    def fileno(self):
        return self.irc_socket.fileno()

    def current_nick_pass(self):
        idx = self._current_nick
        try:
            return self.nicks[idx]
        except IndexError as e:
            alnums = "abcdefghijklmnopqrstuvwxyz1234567890"
            suffix = ''
            suffix += random.choice(alnums)
            suffix += random.choice(alnums)
            suffix += random.choice(alnums)
            firstnick = self.nicks[0][0]
            randnick = firstnick + '_' + suffix
            return randnick, ''
        raise RuntimeError("why are you here?")

    def try_nick(self):
        nick,passwd = self.current_nick_pass()
        self.queue_reply("NICK " + nick)
        self.queue_reply("USER melba 8 * :surprise! meh.")

    def nick_rotate(self):
        self._current_nick += 1

    def queue_reply(self, msg, option = 'truncate'):
        """
        queue a raw message (in unicode) for sending to the server.
        here we utf8 encode the message
        msg has no \r\n, we add it here

        option can be one of:
        truncate - the default behavior - msg will be truncated to BUFSIZE
        raise - raise an exception if len(msg) > BUFSIZE
        """

        #reply to server
        msgbytes = msg.encode('utf-8')

        if option == 'raise' and len(msgbytes) > self.BUFSIZE:
            raise OverflowError

        elif option == 'truncate':
            msgbytes = msgbytes[:self.BUFSIZE]
        else:
            raise RuntimeError("Unknown option " + option)

        self.queue_binary_reply(msgbytes)

    def queue_binary_reply(self, binmsg):
        """queue a binary message, utf8 encoded, at most BUFSIZE long
        for sending.
        binmsg does NOT have \r\n at the end, we add it here
        """

        if len(binmsg) > self.BUFSIZE:
            raise RuntimeError("message too long")
        if binmsg[-2] == b'\r\n':
            raise RuntimeError(r"don't add \r\n yourself, i'll do it")
        self._send_queue += binmsg
        self._send_queue += b'\r\n'



    def _local_handlers(self, rawline):

        """
            tuka da  ima handleri za rpl_welcome i tn. zaradi bufsize????
            i ostanalite neshta ot command.py, zaeti nikove, ghosts
        """
        line = rawline.decode('utf8', 'ignore')
        sender, command, params, trailing = ircfw.parse.irc_message(line)
        command_bin = command.encode('utf8')
        if command_bin == const.RPL_WELCOME:
            self.on_rpl_welcome()
        elif command_bin == const.RPL_WHOREPLY:
            self.on_rpl_whoreply(params)
        elif command_bin == const.NOTICE:
            self.on_notice(sender,params,trailing)
        elif command_bin == const.ERR_NOSUCHNICK:
            self.on_err_nosuchnick(params)
        elif command_bin == const.ERR_UNAVAILRESOURCE:
            self.on_err_unavailresource(params, sender, trailing)
        elif command_bin == const.ERR_NICKNAMEINUSE:
            self.on_err_nicknameinuse()

    def on_rpl_welcome(self):
        #if we supplied passwords we will have to wait for a reply from nickserv
        #and join channels later else we can join right away
        nick, passwd = self.current_nick_pass()
        if len(passwd):
            #self.privmsg("NickServ", "IDENTIFY " + passwd)
            msg = 'IDENTIFY ' + passwd
            self.queue_binary_reply(b'PRIVMSG NickServ :' + msg.encode('utf8'))
        else:
            for chan in self.channels:
                self.join_chan(chan)
        self.queue_reply("WHO " + nick)

    def on_rpl_whoreply(self, cmd_params):
        if self.current_nick_pass()[0] == cmd_params[0]:
            sub = 0
            sub += 1 #:
            sub += len(cmd_params[0]) #nick
            sub += 1 #!
            sub += len(cmd_params[2]) #userid
            sub += 1 #@
            sub += len(cmd_params[3]) #host
            sub += 1 #<space>
            self.BUFSIZE -= sub
            self.logger.info("on_rpl_whoreply BUFSIZE is now %s", self.BUFSIZE)


    def on_notice(self, sender, params, trailing):
        if len(sender) >= 2 \
            and sender[0] == "NickServ" \
            and params[0] == self.current_nick_pass()[0] \
            and trailing.find('You are now identified for') != -1:
                #join channels
                for chan in self.channels:
                        self.join_chan(chan)
                self.queue_reply("WHO " + self.current_nick_pass()[0])

    def on_err_nosuchnick(self, params):
            if params[1] == 'NickServ':
                    #join channels
                    for chan in self.channels:
                            self.join_chan(chan)

    def on_err_unavailresource(self, params, sender, trailing):
        nick, passwd = self.current_nick_pass()
        self.logger.debug(str(params) + ' ' + nick + ' ' + passwd)
        """
            TODO FIXME this doesn't execute, i think it should be params[0]
            find how to recerate the situation (ghosted nick), inspect what
            the server sends

            hard to trace because the situation fixes itself (ghosted nick released
            after a few hours by server)
        """
        if params[1] == nick \
            and sender[0] == 'NickServ' \
            and trailing.find('temporarily unavailable') != -1:
                msg = "release" + ' ' + nick + ' ' + passwd
                self.queue_binary_reply(b'PRIVMSG NickServ :' + msg.encode('utf8'))
                self.logger.warn('nick %s is being protected, tried to release it', nick)
                self.nick_rotate()
                self.try_nick()

    def on_err_nicknameinuse(self):
        nick, passwd = self.current_nick_pass()
        self.logger.warn('nick %s is already used, rotating', nick)
        self.nick_rotate()
        self.try_nick()

    def join_chan(self, channel):
        self.queue_reply("JOIN" + " " + channel)

    def pending_write(self):
        return len(self._send_queue) != 0

