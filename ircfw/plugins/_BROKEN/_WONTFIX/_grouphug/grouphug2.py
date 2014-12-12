import collections
import re
import urllib.request

import lxml.html

Confession = collections.namedtuple('Confession', 'text uri')


def grouphug(self):
    if not hasattr(self, '__confessions'):
        self.__confessions = []
    if len(self.__confessions):
        result = self.__confessions[0]
        self.__confessions = self.__confessions[1:]
        return result
    try:
        src = urllib.request.urlopen(
            "http://confessions.grouphug.us/random", timeout=5).read().decode('utf8')
        tree = lxml.html.fromstring(src)
    except (IOError, urllib.error.URLError) as err:
        return Confession(text=str(err), uri='wtf')
    for i in tree.find_class('node-confession'):
        children = i.getchildren()
        if len(children) != 2:
            print('ERROR: wtf fix gh')
            return Confession(text='Something went wrong with your request.', uri='wtf')
        uri = children[0].text_content().strip()  # this is the h2
        txt = children[1].text_content()
        txt = re.sub('\s+', ' ', txt)
        self.__confessions.append(Confession(text=txt, uri=uri))

    return grouphug(self)


if __name__ == '__main__':
    print("TESTING grouphug2")

    class o:
        pass
    obj = o()
    print(grouphug(obj))
