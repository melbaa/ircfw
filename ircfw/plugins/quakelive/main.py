import io
import urllib.parse
import urllib.request
import re
import random

import lxml.html

import ircfw.parse as parse
from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

from ircfw.plugins.quakelive.quakelive import Player


class plugin:

    def __init__(
            self,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.QUAKELIVE_PLUGIN,
            [const.QUAKELIVE_PLUGIN_NEW_REQUEST],
            self.on_request,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger

    def on_request(self, sock, evts):
        msg = sock.recv_multipart()
        self.logger.info('got msg %s', msg)
        topic, zmq_addr, proxy_name, bufsize \
            , senderbytes, paramsbytes, triggerbytes, argsbytes = msg

        args = argsbytes.decode('utf8')
        trigger = triggerbytes.decode('utf8')
        args.strip()
        result = None

        # args validation will be re.match('^(\w)+$', args)

        self.logger.info(args)
        if not args:
            args = 'melba'
        self.logger.info(args)

        if re.match('^(\w)+$', args):
            result = self.use(trigger, args)
        else:
            result = self.help()

        replies = ircfw.unparse.make_privmsgs(
            senderbytes, paramsbytes, result.encode(
                'utf8'), int(bufsize.decode('utf8')), 'truncate'
        )

        self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def help(self):
        return "qlstats <nick>. stats on last few games by <nick>. default 'melba'"

    def use(self, trigger, args):
        self.logger.info(args)
        p = Player(args, weapons=True)

        p.scrape_matches()  # last week matches

        res = ''
        for i in range(5):
            p.matches[i].get_json()
            data = p.matches[i].data
            try:
                for player in data['SCOREBOARD']:
                    if player['PLAYER_NICK'].lower() == args.lower():

                        # rank -1 in duel is the player that lost, so we fix it
                        # to 2
                        if data['GAME_TYPE'] == 'duel' \
                                and str(player['RANK']) == '-1':
                            player['RANK'] = '2'

                        res += data['GAME_TIMESTAMP_NICE'] \
                            + ' ago. rank ' \
                            + str(player['RANK']) \
                            + ' of ' \
                            + str(len(data['SCOREBOARD'])) \
                            + '. railgun accuracy: ' \
                            + str(player['RAILGUN_ACCURACY']) \
                            + ', railgun hits: ' \
                            + str(player['RAILGUN_HITS']) \
                            + '; '
            except KeyError as e:
                self.logger.info(str(e))
                self.logger.info(data)

        if res == '':
            res = "nfi sry. probably unknown game type or no such player"
            self.logger.info(data)  # log last match
        return res
