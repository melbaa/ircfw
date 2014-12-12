

def make_privmsgs(to_nick, nick_or_channel, txtbytes, bufsize, option='truncate'):
    """generates privmsgs. it will look like this:
      PRIVMSG nick_or_channel :to_nick, txtbytes
    option is one of 'truncate' (default), 'raise', 'multiline'
    multiline splits the message into multiple lines and prepends
      sender to all parts
    truncate is only the first line
    see queue_reply() for decriptions of trucate and raise
    """

    def prepend_sender_dead_code():
        """this will return something like 
           "PRIVMSG #channel :nick, " or
           "PRIVMSG nick : "
        """
        msg = "PRIVMSG" + ' '
        if self.params[0] == self.my_nick_and_pass()[0]:
            msg += to
        else:
            msg += self.params[0]
        msg += ' ' + ':'
        if self.params[0] == self.my_nick_and_pass()[0]:
            pass
        else:
            msg += to + ', '
        return msg

    def make_line_generator(txtbytes, bufsize, header):
        """
        returns correct utf8 encoded lines that fit in bufsize
        """
        # http://en.wikipedia.org/wiki/UTF-8#Description
        msg = bytearray()
        for i, byte in enumerate(txtbytes):
            leader, codesize = codeleader(byte)
            if leader \
                    and len(msg) + len(header) + codesize < bufsize:
                # message so far + next codepoint will fit in BUFSIZE
                msg += txtbytes[i:i + codesize]
            elif leader \
                    and len(msg) + len(header) + codesize >= bufsize:
                yield header + msg
                msg = bytearray()
                msg += txtbytes[i:i + codesize]
            elif byte >> 6 == 0b10:  # continuation byte
                pass
            else:
                raise RuntimeError("unexpected byte")
        if len(msg):
            yield header + msg

    def codeleader(byte):
        """returns (bool, int), where bool is true if the byte is 
           a code leader, int is the size of teh code in utf-8
        """
        if byte >> 7 == 0b0:
            return True, 1
        if byte >> 5 == 0b110:
            return True, 2
        if byte >> 4 == 0b1110:
            return True, 3
        if byte >> 3 == 0b11110:
            return True, 4
        return False, 1

    header = b'PRIVMSG '
    if nick_or_channel.startswith(b'#'):  # reply in channel
        header += nick_or_channel
    else:
        header += to_nick  # reply privately
    header += b' :' + to_nick + b', '
    msg = header + txtbytes
    if option == 'raise':
        if len(msg) > bufsize:
            raise RuntimeError(
                'msg={} is larger than bufsize={}'.format(msg, bufsize))
        yield msg
    elif option == 'truncate':
        gen = make_line_generator(txtbytes, bufsize, header)
        yield next(gen)
    elif option == 'multiline':
        gen = make_line_generator(txtbytes, bufsize, header)
        for line in gen:
            yield line
    else:  # unknown option
        raise RuntimeError("unknown option")
