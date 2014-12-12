import random
import lxml.etree


class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')
        import os
        print(os.getcwd())
        self.bot = bot
        self.namedb = self.load_namedb(
            os.path.dirname(__file__) + '/' + 'names.xml')

    def test(self):
        return True

    def help(self):
        return "getname [<type> OR <types> OR <list>]. both <types> and <list> returns possible types. <type> gives a name from the specific type. no arguments returns a name from any type"

    def name_and_aliases(self):
        return ["getname"]

    def use(self, rawcommand):
        if rawcommand in {'types', 'list'}:
            self.bot.privmsg(
                self.bot.sender[0], str(list(self.namedb.keys())), 'multiline')
            return
        k = rawcommand
        result = ''
        if k not in self.namedb:
            k = random.choice(list(self.namedb.keys()))
            result += 'random '
        v = random.choice(list(self.namedb[k])).strip()
        result += 'type: "' + k + '" name: "' + v + '"'
        return result

    def load_namedb(self, filename):
        tree = lxml.etree.parse(filename)
        root = tree.getroot()
        d = dict()
        for i in root.getchildren():
            k = i.attrib['type']
            v = i.text.split(',')
            d[k] = v
        return d
