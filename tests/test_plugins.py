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

