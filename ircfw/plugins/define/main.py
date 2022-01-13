import urllib.parse
import urllib.request
import json

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

"""
could use wikionary, supports phrases
"""


"""
https://dictionaryapi.com/products/api-collegiate-thesaurus
https://dictionaryapi.com/products/json#sec-2.hwi

"""


REQUEST_URL = 'https://www.dictionaryapi.com/api/v3/references/thesaurus/json/{}?key={}'



def make_string(arg):
    return ' '.join(arg)


class plugin:

    def __init__(
            self,
            api_key,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx):
        self.generic_plugin = generic_plugin(
            __name__,
            const.DEFINE_PLUGIN,
            [const.DEFINE_PLUGIN_NEW_REQUEST],
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger
        self.MERRIAM_THESAURUS_KEY = api_key

    async def main(self):
        while True:
            msg = await self.generic_plugin.read_request()
            self.logger.info('got msg %s', msg)
            topic, zmq_addr, proxy_name, bufsize, \
                senderbytes, paramsbytes, argsbytes = msg

            args = argsbytes.decode('utf8')
            args.strip()
            result = None
            if not args:
                result = 'give me a word or phrase'
            else:
                result = impl(args, self.MERRIAM_THESAURUS_KEY, self.logger)
            replies = ircfw.unparse.make_privmsgs(
                senderbytes,
                paramsbytes,
                result.encode('utf8'),
                int(bufsize.decode('utf8')),
                'multiline')

            # limit output lines for excess flood
            replies = list(replies)[:4]

            await self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

def get_word_list(dt, list_name, pretty_name):
    # the dt structure might not have the list_name list
    output = ''

    if not list_name in dt:
        return output

    words = []
    for ls in dt[list_name]:
        for word in ls:
            words.append(word['wd'])

    if words:
        output = '; {pretty_name} - {txt}'.format(pretty_name=pretty_name, txt=make_string(words))
    return output

def parse_definition(words):
    output = ''
    for word in words:
        speech_part = word['fl']
        output += ' {id} ({speech_part})'.format(speech_part=speech_part, id=word['meta']['id'])
        for definition in word['def']:
            for sense in definition['sseq']:
                for subsense in sense:
                    dt = subsense[1]
                    definition_text = dt['dt'][0][1]
                    output += '; def - ' + definition_text

                    output += get_word_list(dt, 'syn_list', 'synonyms')
                    output += get_word_list(dt, 'ant_list', 'antonyms')
                    output += get_word_list(dt, 'near_list', 'near antonyms')
                    output += get_word_list(dt, 'rel_list', 'related words')
    return output




def impl(rawcommand, api_key, logger):
    quoted_words = urllib.parse.quote_plus(rawcommand)
    req_url = REQUEST_URL.format(quoted_words, api_key)

    resp = urllib.request.urlopen(req_url)
    words = json.loads(resp.read().decode('utf8'))

    if not words:
        return 'no idea'


    try:
        output = parse_definition(words)
        return output
    except Exception as e:
        logger.exception(e)

    try:
        output = make_string(words) or 'no idea'
        return output
    except Exception as e:
        logger.exception(e)
        import pdb;pdb.set_trace()
        pass



