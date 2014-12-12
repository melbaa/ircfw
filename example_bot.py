#!/usr/bin/env python3

import json
import logging
import sys
import types

# third party
import zmq
import zmq.eventloop

# local
import ircfw.irc_command_dispatch
import ircfw.irc_connection
import ircfw.plugin_dispatch
import ircfw.plugins
import ircfw.plugins.artistinfo.main
import ircfw.plugins.codepointinfo.main
import ircfw.plugins.cplusplus.main
import ircfw.plugins.define.main
import ircfw.plugins.googlism.main
import ircfw.plugins.hostinfo.main
import ircfw.plugins.irc_ping.main
import ircfw.plugins.length.main
import ircfw.plugins.phobia.main
import ircfw.plugins.pick.main
import ircfw.plugins.privmsg_ping.main
import ircfw.plugins.quakelive.main
import ircfw.plugins.re.main
import ircfw.plugins.reverse.main
import ircfw.plugins.sadict.main
import ircfw.plugins.substitute.main
import ircfw.proxy

logging.basicConfig(level=logging.DEBUG)


class bot:
    def __init__(self):

        with open('secrets.json') as f:
            secrets = json.loads(f.read())

        ctx = zmq.Context()
        self.ioloop = zmq.eventloop.ioloop.IOLoop.instance()

        # loop should throw instead of swallowing exceptions
        # see  http://zeromq.github.com/pyzmq/api/generated/zmq.eventloop.ioloop.html#zmq.eventloop.ioloop.IOLoop.handle_callback_exception # NOQA
        old_handle_callback_exception = self.ioloop.handle_callback_exception

        def handle_callback_exception(self, callback):
            old_handle_callback_exception(callback)
            raise sys.exc_info()[1]

        # this replaces a method of the ioloop instance. why not derive?
        # FIXME when different instances (probably in separate processes)
        #  will need a decent derived class for ioloop
        # FIXME this doesn't even touch exceptions in add_handler callbacks
        #  which the loop still swallows
        method = types.MethodType(handle_callback_exception, self.ioloop)
        self.ioloop.handle_callback_exception = method

        main_broker = ircfw.irc_command_dispatch \
            .irc_command_dispatch(self.ioloop, ctx)

        proxies = []
        for servername in secrets['servers']:
            data = secrets['servers'][servername]
            proxy = ircfw.proxy.proxy(
                proxyname=servername,
                should_see_nicks=data['should_see_nicks'],
                host=data['host'],
                port=data['port'],
                use_ssl=data['use_ssl'],
                nicks=data['nicks'],
                irc_password=data['irc_password'],
                channels=data['channels'],
                zmq_ioloop_instance=self.ioloop,
                zmq_ctx=ctx)
            proxies.append(proxy)

        plugin_dispatch = ircfw.plugin_dispatch \
            .plugin_dispatch(self.ioloop, ctx)

        artistinfo = ircfw.plugins.artistinfo.main.plugin(
            self.ioloop,
            ctx,
            secrets['plugins']['artistinfo']['api_key'],
            secrets['plugins']['artistinfo']['api_secret'])
        define = ircfw.plugins.define.main.plugin(
            self.ioloop,
            ctx,
            secrets['plugins']['define']['api_key'])

        irc_ping = ircfw.plugins.irc_ping.main.plugin(self.ioloop, ctx)
        cplusplus = ircfw.plugins.cplusplus.main.plugin(self.ioloop, ctx)
        hostinfo = ircfw.plugins.hostinfo.main.plugin(self.ioloop, ctx)
        phobias = ircfw.plugins.phobia.main.plugin(self.ioloop, ctx)
        sadict = ircfw.plugins.sadict.main.plugin(self.ioloop, ctx)
        re = ircfw.plugins.re.main.plugin(self.ioloop, ctx)
        codepointinfo = ircfw.plugins.codepointinfo.main.plugin(
            self.ioloop, ctx)
        length = ircfw.plugins.length.main.plugin(self.ioloop, ctx)
        privmsg_ping = ircfw.plugins.privmsg_ping.main.plugin(self.ioloop, ctx)
        reverse = ircfw.plugins.reverse.main.plugin(self.ioloop, ctx)
        pick = ircfw.plugins.pick.main.plugin(self.ioloop, ctx)
        substitute = ircfw.plugins.substitute.main.plugin(self.ioloop, ctx)
        googlism = ircfw.plugins.googlism.main.plugin(self.ioloop, ctx)
        quakelive = ircfw.plugins.quakelive.main.plugin(self.ioloop, ctx)

    def run(self):
        self.ioloop.start()

    def run_once(self):
        pass


def main():

    bot().run()


if __name__ == '__main__':
    main()


