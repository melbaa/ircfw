import pytest

from ircfw.unparse import make_privmsgs, MessageTooBig


txt = """
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



def test_truncate():

    txtbytes = txt.encode('utf8')
    assert len(txtbytes) > 512

    MAXSZ = 380
    gen = make_privmsgs(b'melba', b'#melba', txtbytes, MAXSZ, 'truncate')
    msg = list(gen)[0]
    print(msg)

    assert len(msg) <= MAXSZ

def test_raise():
    txtbytes = txt.encode('utf8')
    assert len(txtbytes) > 512

    MAXSZ = 380
    with pytest.raises(MessageTooBig):
        gen = make_privmsgs(b'melba', b'#melba', txtbytes, MAXSZ, 'raise')
        msg = list(gen)[0]
        print(msg)

        assert len(msg) <= MAXSZ

def test_raise2():
    txtbytes = b'haha'
    MAXSZ = 380
    gen = make_privmsgs(b'melba', b'#melba', txtbytes, MAXSZ, 'raise')
    msg = list(gen)[0]
    print(msg)

if __name__ == '__main__':
    unittest.main()
