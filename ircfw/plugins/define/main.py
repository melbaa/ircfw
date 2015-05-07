import urllib.parse
import urllib.request

import lxml.etree as ET

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse

"""
could use wikionary, supports phrases
"""


"""
http://www.dictionaryapi.com/api/v1/references/thesaurus/xml/microscopic?key=???
http://www.dictionaryapi.com/content/products/documentation/thesaurus-tag-description.txt



"""


REQUEST_URL = 'http://www.dictionaryapi.com/api/v1/references/thesaurus/xml/{}?key={}'
XML_PARSER = ET.XMLParser(encoding='utf8')


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
            self.on_request,
            plugin_dispatch,
            command_dispatch_backend_replies,
            zmq_ioloop,
            zmq_ctx)
        self.logger = self.generic_plugin.logger
        self.MERRIAM_THESAURUS_KEY = api_key

    def on_request(self, sock, evts):
        msg = sock.recv_multipart()
        self.logger.info('got msg %s', msg)
        topic, zmq_addr, proxy_name, bufsize, \
            senderbytes, paramsbytes, argsbytes = msg

        args = argsbytes.decode('utf8')
        args.strip()
        result = None
        if not args:
            result = 'give me a word or phrase'
        else:
            result = self.use(args)
        replies = ircfw.unparse.make_privmsgs(
            senderbytes,
            paramsbytes,
            result.encode('utf8'),
            int(bufsize.decode('utf8')),
            'multiline')

        self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def use(self, rawcommand):
        quoted_words = urllib.parse.quote_plus(rawcommand)
        req_url = REQUEST_URL.format(quoted_words, self.MERRIAM_THESAURUS_KEY)

        xml_rep = urllib.request.urlopen(req_url).read()
        root = ET.fromstring(xml_rep)

        suggestions = root.xpath('suggestion/text()')
        if len(suggestions):
            return 'suggestions - {}'.format(make_string(suggestions))

        description = '{word} ({speech_part}) --- {meanings}; synonyms - {synonyms}; \
  related words - {related_words}; near antonyms - {near}; antonyms - {antonyms}.'

        entries = []
        for entry in root.getchildren():
            data_dict = {
                # , 'meaning_core' : entry.xpath('sens/mc/text()')
                'word': entry.xpath('term/hw/text()'),
                'speech_part': entry.xpath('fl/text()'),
                'meanings': entry.xpath('sens/*[self::mc or self::vi]//text()'),
                'synonyms': entry.xpath('sens/syn//text()'),
                'related_words': entry.xpath('sens/rel//text()'),
                'near': entry.xpath('sens/near//text()'),
                'antonyms': entry.xpath('sens/ant//text()')
            }

            for key in data_dict:
                data = make_string(data_dict[key])
                data_dict[key] = data

            entries.append(description.format(**data_dict))

        result = ' '.join(entries)
        if not len(result):
            result = 'no idea'
        return result
