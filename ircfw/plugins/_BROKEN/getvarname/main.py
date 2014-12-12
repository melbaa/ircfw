import string
import random

import ircfw.parse as parse


class plugin():

    def __init__(self, bot):
        self.langs = {'ahk': ahk_alphabet, 'autohotkey': ahk_alphabet}
        self.bot = bot

        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return self.bot.command \
            +  " <language>; get a variable name for a language." \
            + "it can be one of " + str(self.langs.keys())

    def name_and_aliases(self):
        return ["getvarname", "gvn", "genvarname"]

    def use(self, rawcommand):
        try:
            if not rawcommand:
                return "tell me a language"
            lang, rawcommand = parse.get_word(rawcommand)
            lang = str.lower(lang)
            if lang not in self.langs:
                return "unknown language"

            return self.langs[lang]()

        except ValueError as err:
            return str(err)


def pick_from_alphabet(alphabet, maxlen):
    var = ''
    for i in range(maxlen):
        var += random.choice(alphabet)
    return var


def ahk_alphabet():
    ahk_var_maxsz = 253
    alphabet = string.ascii_letters + string.digits + '#_@$[]?'
    return pick_from_alphabet(alphabet, random.randint(1, ahk_var_maxsz))
