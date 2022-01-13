import logging

from unittest.mock import MagicMock

def test_googlism():
    from ircfw.plugins.googlism.main import impl
    searchterm = "entertainment"
    searchtype = "what"
    impl(searchterm, searchtype)

def test_hostinfo():
    from ircfw.plugins.hostinfo.main import impl
    result = impl(MagicMock(), 'tetris')
    assert result == '[Errno 11001] getaddrinfo failed'
    result = impl(MagicMock(), 'google.com')
    assert result

def test_ping():
    from ircfw.plugins.privmsg_ping.main import impl
    assert impl('abv.bg') == 'got HTTP status 200'

def test_youtubesearch():
    from ircfw.plugins.youtube.main import impl
    impl("eminem the way i am")

def test_define(secrets, logger):
    api_key = secrets['plugins']['define']['api_key']
    from ircfw.plugins.define.main import impl
    # impl('randy', api_key)
    # output = impl('aoeuaoeu', api_key)
    # output = impl('aoeuaoeuaeouaeuaeuo', api_key)
    # output = impl('aoeuaoeuaoeuaoeu', api_key)
    output = impl('aa', api_key, logger)
    import pdb;pdb.set_trace()

