from ircfw.irc_connection import *

def test_recognized():
    rawline = b':NickServ!service@rizon.net NOTICE if :Password accepted - you are now recognized.'
    nicks = [ ['if','ifpass'] ]
    irc_password = ""
    channels = [ ["#chan", "pass"] ]
    iph = irc_protocol_handlers(nicks, irc_password, channels)
    result = list(iph.feed(rawline))
    assert result == [b'JOIN #chan pass', b'WHO if']

