import urllib.parse
import urllib.request
import re


import socket
import urllib.request

from ircfw.plugins.generic_plugin import generic_plugin
import ircfw.constants as const
import ircfw.unparse


class plugin:

    def __init__(self, zmq_ioloop, zmq_ctx):
        self.generic_plugin = generic_plugin(
            zmq_ioloop, zmq_ctx, __name__, const.SADICT_PLUGIN, [
                const.SADICT_PLUGIN_NEW_REQUEST], self.on_request
        )
        self.logger = self.generic_plugin.logger

    def on_request(self, sock, evts):
        msg = sock.recv_multipart()
        self.logger.info('got msg %s', msg)
        topic, zmq_addr, proxy_name, bufsize \
            , senderbytes, paramsbytes, argsbytes = msg

        args = argsbytes.decode('utf8')
        args.strip()
        result = None
        if not args:
            result = 'give me something in english or bulgarian to translate'
        else:
            result = self.use(args)
        replies = ircfw.unparse.make_privmsgs(
            senderbytes, paramsbytes, result.encode(
                'utf8'), int(bufsize.decode('utf8')), 'truncate'
        )

        self.generic_plugin.send_replies(replies, zmq_addr, proxy_name)

    def use(self, rawcommand):
        try:
            to_translate = rawcommand
            while len(to_translate) and to_translate[0] == ' ':
                to_translate = to_translate[1:]
            if len(to_translate):
                # posledniq put kat ne raboteshe tva url, dirbg se beshe
                # sduhalo
                url = 'http://www.diri.bg/search.php?word='
                url += urllib.parse.quote(
                    to_translate.encode('cp1251', 'ignore'))
                reply = urllib.request.urlopen(url)
                reply = reply.readall()
                #self.logger.info('sadict raw reply %s', reply)
                src = reply.decode('cp1251')
                #self.logger.info('sadict decoded reply %s', src)
                src = src[src.find('<TABLE'):src.rfind('TABLE>')]
                src = src[src.rfind('<TD'):src.rfind('</TD>')]
                src = re.sub(r'<BR>', ' ', src)  # notice: puts a blank
                src = re.sub(r'</BR>', ' ', src)
                src = re.sub(r'<B>', '', src)
                src = re.sub(r'</B>', '', src)
                src = re.sub(r'<TD.*?>', '', src)
                src = re.sub(r'<font.*?>', '', src)
                src = re.sub(r'</font>', '', src)
                src = re.sub(r'\n', '', src)
                return src
        except urllib.error.URLError as err:
            return str(err)
