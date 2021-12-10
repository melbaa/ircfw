import socket
import urllib.request

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.HOSTINFO_PLUGIN,
            [const.HOSTINFO_PLUGIN_NEW_REQUEST],
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger

    async def main(self):
        while True:
            msg = await self.generic_plugin.read_request()
            self.logger.info('got msg %s', msg)
            topic, zmq_addr, proxy_name, bufsize \
                , senderbytes, paramsbytes, argsbytes = msg

            args = argsbytes.decode('utf8')
            args.strip()
            result = None
            if not args:
                result = 'which host?'
            else:
                result = impl(self.logger, args)
            replies = ircfw.unparse.make_privmsgs(
                senderbytes, paramsbytes, result.encode('utf8'),
                int(bufsize.decode('utf8')),
                'multiline',
            )

            await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)




def impl(logger, host_arg):
    try:
        addr_list = socket.getaddrinfo(host_arg, None)
    except socket.gaierror as e:
        return str(e)

    logger.info('addr_list %s', addr_list)
    unique = set()
    for family, socktype, proto, canonname, sockaddr in addr_list:
        host = sockaddr[0]  # because ipv6 is a 4-tuple
        unique.add(host)

    for host in unique:
        b = urllib.request.urlopen(
            'http://ip-api.com/json/{}'.format(host))
        txt = b.read().decode('utf-8')
        return txt

def impl_old(logger, host_arg):
    try:
        addr_list = socket.getaddrinfo(host_arg, None)
    except socket.gaierror as e:
        return str(e)

    logger.info('addr_list %s', addr_list)
    unique = set()
    for family, socktype, proto, canonname, sockaddr in addr_list:
        host = sockaddr[0]  # because ipv6 is a 4-tuple
        unique.add(host)

    for host in unique:
        b = urllib.request.urlopen(
            'http://api.hostip.info/get_html.php?ip={0}&position=true'.format(host))
        txt = b.read().decode('utf-8')
        txt = txt.replace('\n', ' ')
        return txt
