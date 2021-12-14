
import urllib.request
from urllib.parse import quote
import json

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

"""
http://www.hamweather.com/support/documentation/aeris/endpoints/
"""

API_URL = 'http://api.aerisapi.com/observations/{city},{state}?client_id={client_id}&client_secret={client_secret}'
ERROR_MSG = 'something went wrong'

class AerisLookup:
    def __init__(self, client_id, client_secret, logger):
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logger

    def lookup(self, city, state):

        city = quote(city)
        state = quote(state)
        url = API_URL.format(city=city, state=state, client_id=self.client_id,
            client_secret=self.client_secret)

        try:
            with urllib.request.urlopen(url) as request:
                response = request.read().decode('utf8')
                json_resp = json.loads(response)
                return self._format_reply(json_resp)
        except Exception as err:
            self.logger.error(str(err))
            return ERROR_MSG

    def _format_reply(self, json_resp):

        success = '{temp}C {weather} Timezone: {tz} ICAO: {icao}'
        try:
            if json_resp['success']:
                icao = json_resp['response']['id']
                tz = json_resp['response']['profile']['tz']
                temp = json_resp['response']['ob']['tempC']
                weather = json_resp['response']['ob']['weather']
                return success.format(temp=temp, weather=weather, tz=tz,
                    icao=icao)
            else:
                return json_resp['error']['description']
        except Exception as err:
            self.logger.error(str(err))
            return ERROR_MSG

class plugin:
    def __init__(
            self,
            client_id,
            client_secret,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.WEATHER_PLUGIN,
            [const.WEATHER_PLUGIN_NEW_REQUEST],
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)

        self.logger = self.generic_plugin.logger
        self.api = AerisLookup(client_id, client_secret, self.logger)

    async def main(self):
        while True:
            msg = await self.generic_plugin.read_request
            self.logger.info('got msg %s', msg)
            topic, zmq_addr, proxy_name, bufsize \
                , senderbytes, paramsbytes, argsbytes = msg

            args = argsbytes.decode('utf8')
            args.strip()

            try:
                city, state = args.split(', ')
                result = self.api.lookup(city, state)

            except ValueError as err:
                result = 'the correct command is weather <city>, <state>'

            replies = ircfw.unparse.make_privmsgs(
                senderbytes, paramsbytes, result.encode(
                    'utf8'), int(bufsize.decode('utf8')), 'truncate'
            )

            await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)


