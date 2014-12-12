import ircfw.parse as parse


class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')
        self.bot = bot

    def test(self):
        return True

    def help(self):
        return "ftb <number> [<from base> [<to base>]]; converts <number> from base <from base> to <to base>, skip <from base> and 10 is assumed, skip <to base> and 16 is assumed, you can skip both. min base = 2, max base = 36"

    def name_and_aliases(self):
        return ["ftb"]

    def use(self, rawcommand):
        if not len(rawcommand):
            return
        result = []
        number, rawcommand = parse.get_word(rawcommand)
        if len(rawcommand):
            from_base, rawcommand = parse.get_word(rawcommand)
            if len(rawcommand):
                to_base, rawcommand = parse.get_word(rawcommand)
                result = ftb_impl(number, from_base, to_base)
            else:
                """
                a number and a base given, assume number is 
                decimal and convert to base
                """
                to_base = from_base
                result = ftb_impl(numstr=number, to_base=to_base)

        else:  # only number given, convert it to hex
            result = ftb_impl(number)

        result = ''.join(result)  # convert the list to a string
        return result


def ftb_impl(numstr, from_base='10', to_base='16'):
    """
    bases are from 2 to 36
    """
    ENONALNUM = list(numstr + ' has a non alpha-numeric character')
    EFBDEC = list(from_base + ' is not decimal')
    ETBDEC = list(to_base + ' is not decimal')
    ENOTINFB = list(numstr + ' is not in base ' + from_base)
    E2TO36 = list('supported bases are >= 2 and <= 36')
    MAXBASE = 36
    MINBASE = 2
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
               'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    try:
            # handle numstr sign
        numstrsign = 0
        if numstr[0] == '+':
            numstrsign = 1
        elif numstr[0] == '-':
            numstrsign = -1

        if numstrsign in (1, -1):
            numstr = numstr[1:]
        # end of handle numstr sign

        if from_base[0] == '+':
            from_base = from_base[1:]
        elif from_base[0] == '-':
            return E2TO36
        for char in from_base:
            if not str.isdigit(char):
                return EFBDEC
        from_base = int(from_base)

        for char in numstr:
            if not (str.isalnum(char) and char != '.'):
                return ENONALNUM
            if int(char, MAXBASE) >= from_base:
                return ENOTINFB

        if to_base[0] == '+':
            to_base = to_base[1:]
        elif to_base[0] == '-':
            return E2TO36
        for char in to_base:
            if not str.isdigit(char):
                return ETBDEC
        to_base = int(to_base)

        if from_base < MINBASE or from_base > MAXBASE \
           or to_base < MINBASE or to_base > MAXBASE:
            return E2TO36

        numdec = int(numstr, from_base)

        result = []
        while numdec:
            result = [numdec % to_base] + result
            numdec = numdec // to_base

        for i in range(len(result)):
            char_idx = result[i]
            result[i] = numbers[result[i]]

        if numstrsign != 0:
            result = [str(numstrsign)] + result
        return result
    except UnicodeEncodeError as err:
        return list(str(err))
