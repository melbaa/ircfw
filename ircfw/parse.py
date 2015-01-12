# TODO this really needs to work on binary, not unicode data
def irc_message(msg):
    """
    The extracted message is parsed into the components <prefix>,
    <command> and list of parameters (<params>).

    The Augmented BNF representation for this is:

    message  =  [ ":" prefix SPACE ] command [ params ] crlf
    prefix   =  servername / ( nickname [ [ "!" user ] "@" host ] )
    command  =  1*letter / 3digit
    params   =  *14( SPACE middle ) [ SPACE ":" trailing ]
           =/ 14( SPACE middle ) [ SPACE [ ":" ] trailing ]

    nospcrlfcl =  %x01-09 / %x0B-0C / %x0E-1F / %x21-39 / %x3B-FF
            ; any octet except NUL, CR, LF, " " and ":"
    middle   =  nospcrlfcl *( ":" / nospcrlfcl )
    trailing   =  *( ":" / " " / nospcrlfcl )

    SPACE    =  %x20    ; space character
    crlf     =  %x0D %x0A   ; "carriage return" "linefeed"
    """

    sender = []  # servername or nickname, user, host
    command = ''
    params = []
    trailing = ''
    pos = 0
    if msg[pos] == ':':  # prefix sender
        pos += 1
        sth = ''
        while pos < len(msg) and not str.isspace(msg[pos]) and msg[pos] != '!':
            sth += msg[pos]
            pos += 1
        sender.append(sth)
        if pos < len(msg) and msg[pos] == '!':
            pos += 1
            user = ''
            while pos < len(msg) and msg[pos] != '@':
                user += msg[pos]
                pos += 1
            sender.append(user)
            pos += 1  # skip @
            host = ''
            while pos < len(msg) and msg[pos] != ' ':
                host += msg[pos]
                pos += 1
            sender.append(host)
        if msg[pos] == ' ':
            pos += 1
        else:
            raise "WTF"
    while pos < len(msg) and str.isalnum(msg[pos]):
        command += msg[pos]
        pos += 1
    # fill params
    while pos < len(msg) and msg[pos] != ':':
        if msg[pos] == ' ':
            pos += 1
        else:
            param = ''
            while pos < len(msg) and msg[pos] != ' ':
                param += msg[pos]
                pos += 1
            params.append(param)
    # fill trailing
    if pos < len(msg) and msg[pos] == ':':
        pos += 1
        while pos < len(msg):
            trailing += msg[pos]
            pos += 1
    return sender, command, params, trailing


def get_word(msg):
    """
    msg is a string of words separated by spaces
    return a tuple of the first word and the remaining of the string without
    the preceding spaces

    get_word("word word2 word3") == ("word", "word2 word3")
    """

    pos = 0
    word = ''
    while pos < len(msg) and msg[pos] != ' ':
        word += msg[pos]
        pos += 1

    while pos < len(msg) and msg[pos] == ' ':
        pos += 1
    trailing = msg[pos:]
    return word, trailing


def potential_request(privmsg_trailing, bot_nick):
    """check if trailing starts with our nick, then it might be a valid
    plugin trigger
    """
    botnicklen = len(bot_nick)
    if privmsg_trailing[:botnicklen] == bot_nick \
            and privmsg_trailing[botnicklen] in {' ', ',', ':'}:
        skip_nick, remaining = get_word(privmsg_trailing)
        return remaining
    return ''
