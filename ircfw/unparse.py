import unittest

def make_privmsgs(to_nick, nick_or_channel, txtbytes, bufsize, option='truncate'):
    """
    generates privmsgs. they will look like this:
    PRIVMSG nick_or_channel :to_nick, txtbytes
    
    option is one of 'truncate' (default), 'raise', 'multiline'
    multiline splits the message into multiple lines and prepends
      sender to all parts
    truncate will cut the message to bufsize bytes
    raise will throw an exc when msg > bufsize
    """

    def prepend_sender_dead_code():
        """this will return something like
           "PRIVMSG #channel :nick, " or
           "PRIVMSG nick : "
        """
        msg = "PRIVMSG" + ' '
        if self.params[0] == self.my_nick_and_pass()[0]:
            msg += to
        else:
            msg += self.params[0]
        msg += ' ' + ':'
        if self.params[0] == self.my_nick_and_pass()[0]:
            pass
        else:
            msg += to + ', '
        return msg

    def make_line_generator(txtbytes, bufsize, header):
        """
        returns correct utf8 encoded lines that fit in bufsize
        """
        # http://en.wikipedia.org/wiki/UTF-8#Description
        msg = bytearray()
        for i, byte in enumerate(txtbytes):
            leader, codesize = codeleader(byte)
            if leader and len(msg) + len(header) + codesize <= bufsize:
                # message so far + next codepoint will fit in BUFSIZE
                msg += txtbytes[i:i + codesize]
            elif leader and len(msg) + len(header) + codesize > bufsize:
                yield header + msg
                msg = bytearray()
                msg += txtbytes[i:i + codesize]
            elif byte >> 6 == 0b10:  # continuation byte
                pass
            else:
                raise RuntimeError("unexpected byte")
        if len(msg):
            yield header + msg

    def codeleader(byte):
        """returns (bool, int), where bool is true if the byte is
           a code leader, int is the size of the code in utf-8
        """
        if byte >> 7 == 0b0:
            return True, 1
        if byte >> 5 == 0b110:
            return True, 2
        if byte >> 4 == 0b1110:
            return True, 3
        if byte >> 3 == 0b11110:
            return True, 4
        return False, 1

    header = b'PRIVMSG '
    if nick_or_channel.startswith(b'#'):  # reply in channel
        header += nick_or_channel
    else:
        header += to_nick  # reply privately
    header += b' :' + to_nick + b', '
    msg = header + txtbytes
    if option == 'raise':
        if len(msg) > bufsize:
            raise RuntimeError(
                'msg={} is larger than bufsize={}'.format(msg, bufsize))
        yield msg
    elif option == 'truncate':
        gen = make_line_generator(txtbytes, bufsize, header)
        yield next(gen)
    elif option == 'multiline':
        gen = make_line_generator(txtbytes, bufsize, header)
        for line in gen:
            yield line
    else:  # unknown option
        raise RuntimeError("unknown option")

        
        
        
        
class PrivmsgTest(unittest.TestCase):
    def setUp(self):
        self.txt = """
HOUSE
I. 1. къща, дом, жилище

at their HOUSE у тях

to keep HOUSE водя/гледам/грижа се за домакинство

to keep a good HOUSE живея/храня се добре

to make someone free of one's HOUSE приемаме някого много радушно, карам го да се чувствува като у дома си

to turn someone out of HOUSE and home изпъждам някого от дома му

to set/put one's HOUSE in order уреждам си работите, въвеждам преобразования

like a HOUSE on fire енергично. бързо, отлично

2. сграда, помещение, постройка

3. бърлога (на животно), черупка

4. семейство, потекло, династия, род

the HOUSE of Stuart (династия на) Стюартите

5. камара, палата (в парламента)

to enter the HOUSE ставам депутат

the HOUSE s of Parliament (сградата на) парламента

to make/keep a HOUSE осигурявам кворум в парламента

to be in possession of the HOUSE вземам думата/изказвам се в парламента

6. фирма, търговска къща

7. пансион, всички ученици и пр. от един пансион, манастир, монашеско братство

8. хан, хотел, кръчма

to have a drink on the HOUSE почерпвам се/пия за сметка на заведението

9. театр, театър, салон, публика, представление

a good HOUSE пълен салон

10. астрол. 1/2 част от небето, зодия дом на планета

11. вид хазартна игра, лото, бинго

12. публичен дом

HOUSE of ill-fame/disrepute ост. воен. sl. публичен дом

13. attr домашен, къщен, домакински, който живее в болница (за лекар)

the HOUSE парламентът, разг. борсата, ист. разг. работнически приют

колежът Christ Church в Оксфорд

HOUSE of God църква, храм божи

to bow down in the HOUSE of Rinunon жертвувам/действувам против принципите/убежденията си

II. 1. давам/намирам жилище на, подслонявам (се), давам подслои на, живея

this building HOUSEs an art gallery в това здание се помещава художествена галерия

2. складирам, затварям, помествам (в нещо), прибирам (на гараж, в хангар)
"""
    
    def test_truncate(self):
        txtbytes = self.txt.encode('utf8')
        self.assertGreater(len(txtbytes), 512)
        
        MAXSZ = 380
        gen = make_privmsgs(b'melba', b'#melba', txtbytes, MAXSZ, 'truncate')
        msg = list(gen)[0]
        print(msg)
        
        self.assertLessEqual(len(msg), MAXSZ)
    

if __name__ == '__main__':
    unittest.main()