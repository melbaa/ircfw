import random

import ircfw.parse as parse


class plugin():

    def __init__(self, bot):
        self.bot = bot
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "wrong [<nick>]; optionally tell nick he's wrong"

    def name_and_aliases(self):
        return ["wrong"]

    def use(self, rawcommand):
        http:
            //adrinael.net / randomwrong
        nick = ''
        if len(rawcommand):
            nick, rawcommand = parse.get_word(rawcommand)
        num = random.randint(0, 21)  # he has that many pictures
        reply = 'http://adrinael.net/wrong'
        if num != 0:
            reply += str(num)
        if not len(nick):
            return reply
        else:
            self.bot.privmsg(nick, reply)
            return None
