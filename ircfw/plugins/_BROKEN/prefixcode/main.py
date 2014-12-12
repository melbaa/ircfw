import ircfw.parse as parse


class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')
        self.bot = bot

    def test(self):
        return True

    def help(self):
        return "isprefixcode <q> <lenghts>; checks the kraft inequality. <q> is the size/arity of the alphabet (q-ary alphabet, usually 2). <lengths> is a list of codeword lengths. for example an alphabet of size 2 (binary) will have 2 prefix codewords of length 1 - 0 and 1. "

    def name_and_aliases(self):
        return ["isprefixcode"]

    def use(self, rawcommand):
        def impl(qary, alist):
            s = 0
            for i in alist:
                s += qary ** -i
            return s <= 1, s

        try:
            if not len(rawcommand):
                raise ValueError("expecting q")

            q, rawcommand = parse.get_word(rawcommand)
            q = int(q)
            if not len(rawcommand):
                raise ValueError("expecting a list of lengths")
            L = []
            while len(rawcommand):
                i, rawcommand = parse.get_word(rawcommand)
                i = int(i)
                L.append(i)
            itdoes, s = impl(q, L)
            return str(itdoes) + ' ' + str(s) + ' <= 1'
        except ValueError as e:
            return str(e)
