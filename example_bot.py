#!/usr/bin/env python3

import argparse
import json
import logging
import sys
import types

# https://hynek.me/articles/waiting-in-asyncio/
# https://www.roguelynn.com/words/asyncio-we-did-it-wrong/
# https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
import asyncio

# third party
import zmq
import zmq.asyncio
# import zmq.eventloop
# import tornado.ioloop



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
import ircfw.plugins.help.main
import ircfw.plugins.hostinfo.main
import ircfw.plugins.length.main
import ircfw.plugins.phobia.main
import ircfw.plugins.pick.main
import ircfw.plugins.privmsg_ping.main
import ircfw.plugins.youtube.main
import ircfw.plugins.re.main
import ircfw.plugins.reverse.main
import ircfw.plugins.substitute.main
import ircfw.plugins.weather.main
import ircfw.proxy

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("asyncio").setLevel(logging.DEBUG)

"""
inproc:// transports are not disconnected and also seem to be
messsed up on windows
update: should be fixed in newer zmq versions
TODO see what happens when tcp:// is replaced by inproc

those ports should really be randomly assigned, but then we'd need
  an address book on the network
"""
# proxies connect, command dispatch binds
COMMAND_DISPATCH_FRONTEND = "tcp://127.0.0.1:70005"

# plugin dispatch connects, command dispatch binds
COMMAND_DISPATCH_BACKEND_TOPICS = "tcp://127.0.0.1:70006"

# plugins connect, command dispatch binds
COMMAND_DISPATCH_BACKEND_REPLIES = "tcp://127.0.0.1:70007"

# plugins connect, plugin dispatch binds
PLUGIN_DISPATCH = 'tcp://127.0.0.1:70008'


class bot:

    def __init__(self, conf_file):

        with open(conf_file) as f:
            secrets = json.loads(f.read())

        # zmq uses add_reader and add_writer low level methods, which proactor loop doesn't have
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()  # pylint: disable=no-member
        )
        ctx = zmq.asyncio.Context()

        # loop should throw instead of swallowing exceptions
        # see  http://zeromq.github.com/pyzmq/api/generated/zmq.eventloop.ioloop.html#zmq.eventloop.ioloop.IOLoop.handle_callback_exception # NOQA


        # in the modern world, no such callback anymore
        """

        old_handle_callback_exception = self.ioloop.handle_callback_exception

        def handle_callback_exception(self, callback):
            old_handle_callback_exception(callback)
            raise sys.exc_info()[1]

        # this replaces a method of the ioloop instance. why not derive?
        # TODO FIXME when different instances (probably in separate processes)
        #  will need a decent derived class for ioloop
        # TODO FIXME this doesn't even touch exceptions in add_handler
        #  callbacks which the loop still swallows
        method = types.MethodType(handle_callback_exception, self.ioloop)
        self.ioloop.handle_callback_exception = method


        """

        def handle_exception(loop, context):
            # context["message"] will always be there; but context["exception"] may not
            msg = context.get("exception", context["message"])
            logging.error(f"Caught exception: {msg}")
            raise RuntimeError('crash and burn')

        # but asyncio has a global exception handler
        self.ioloop = asyncio.new_event_loop()
        self.ioloop.set_exception_handler(handle_exception)

        # also enable debug mode
        self.ioloop.set_debug(True)

        # gather all independently runnable components
        self.components = []

        main_broker = ircfw.irc_command_dispatch.irc_command_dispatch(
            COMMAND_DISPATCH_FRONTEND,
            COMMAND_DISPATCH_BACKEND_TOPICS,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(main_broker)

        for servername in secrets['servers']:
            data = secrets['servers'][servername]
            if data.get('disabled'):
                logging.info('skipping disabled server %s', servername)
                continue

            proxy = ircfw.proxy.proxy(
                proxyname=servername,
                command_dispatch_frontend=COMMAND_DISPATCH_FRONTEND,
                should_see_nicks=data['should_see_nicks'],
                host=data['host'],
                port=data['port'],
                use_ssl=data['use_ssl'],
                nicks=data['nicks'],
                irc_password=data['irc_password'],
                channels=data['channels'],
                ioloop=self.ioloop,
                zmq_ctx=ctx)
            self.components.append(proxy)

        plugin_dispatch = ircfw.plugin_dispatch.plugin_dispatch(
            COMMAND_DISPATCH_BACKEND_TOPICS,
            PLUGIN_DISPATCH,
            self.ioloop,
            ctx)
        self.components.append(plugin_dispatch)

        artistinfo = ircfw.plugins.artistinfo.main.plugin(
            secrets['plugins']['artistinfo']['api_key'],
            secrets['plugins']['artistinfo']['api_secret'],
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(artistinfo)
        define = ircfw.plugins.define.main.plugin(
            secrets['plugins']['define']['api_key'],
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(define)
        hlp = ircfw.plugins.help.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(hlp)
        hostinfo = ircfw.plugins.hostinfo.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(hostinfo)
        phobias = ircfw.plugins.phobia.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(phobias)
        re = ircfw.plugins.re.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(re)
        codepointinfo = ircfw.plugins.codepointinfo.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(codepointinfo)
        length = ircfw.plugins.length.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(length)
        privmsg_ping = ircfw.plugins.privmsg_ping.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(privmsg_ping)
        reverse = ircfw.plugins.reverse.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(reverse)
        pick = ircfw.plugins.pick.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(pick)
        substitute = ircfw.plugins.substitute.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(substitute)
        googlism = ircfw.plugins.googlism.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(googlism)
        youtube = ircfw.plugins.youtube.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        self.components.append(youtube)
        """
        cplusplus = ircfw.plugins.cplusplus.main.plugin(
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        weather = ircfw.plugins.weather.main.plugin(
            secrets['plugins']['weather']['client_id'],
            secrets['plugins']['weather']['client_secret'],
            PLUGIN_DISPATCH,
            COMMAND_DISPATCH_BACKEND_REPLIES,
            self.ioloop,
            ctx)
        """

    async def run(self):
        tasks = []
        for component in self.components:
            task = asyncio.create_task(component.main())
            tasks.append(task)
        await asyncio.wait(tasks)

    def run_once(self):
        raise NotImplementedError


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('CONFIGPATH', type=str, help='path to secrets.json')
    args = parser.parse_args()
    asyncio.run(bot(args.CONFIGPATH).run())

    #self.ioloop.run_forever()

    # asyncio.run(asyncio.gather(*proxies))


if __name__ == '__main__':
    main()
