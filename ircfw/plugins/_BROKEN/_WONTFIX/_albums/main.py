"""
does not work because now they want a unique user agent. also they have
  an official python lib now. more info 
  http://www.discogs.com/developers/accessing.html
  https://github.com/discogs/discogs_client
  
probably wont fix
"""

import collections
import io
import urllib.parse

import lxml.etree

class plugin():
  def __init__(self, bot):
    print('plugin' ,self.name_and_aliases(), 'started')
    self.bot = bot

  def test(self):
    return True
  
  def help(self):
    return "get discography about artist. big discograhy will flood the channel"
    
  def name_and_aliases(self):
    return ["albums"]
  
  def use(self,rawcommand):
    #pass the url with the key directly later
    #pages 69, 84, 99 from lxml manual
   
    api_key='????'
    artist = urllib.parse.quote_plus(rawcommand)
    request_url = 'http://www.discogs.com/artist/{0}?f=xml&api_key={1}'.format(artist,api_key)
    tree = lxml.etree.parse(request_url)
    root = tree.getroot()
    
    name = tree.xpath('/resp/artist/name')
    realname = tree.xpath('//realname')
    namevariations = tree.xpath('/resp/artist/namevariations/name')
    aliases = tree.xpath('/resp/artist/aliases/name')
    members = tree.xpath('/resp/artist/members/name')
    releases = tree.xpath('//release')
    
    result = collections.OrderedDict()
    
    result['names'] = [n.text for n in name]
    result['realname'] = [n.text for n in realname]
    result['namevariations'] = [n.text for n in namevariations]
    result['aliases'] = [n.text for n in aliases]
    result['members'] = [n.text for n in members]
    
    result['releases'] = []
    rls_set = set()
  
    for rls in releases:
      rls_info = []
      #a good release has unique title and passes exclude filters
      unique = False
      pass_filters = True
      if rls.attrib['type'] == 'Main':
        #rls_info.append('id: ' + rls.attrib['id'] + ' ')
        for child in rls:
          if child.tag == 'title':
            if child.text not in rls_set:
              rls_set.add(child.text)
              unique = True
          if child.tag == 'format':
            formats = child.text.split(', ')
            exclude_list = 'Vinyl, 7", 10", 12", Cass, Maxi, Single, VHS, Mini'.split(', ')
            for excl in exclude_list:
              for format in formats:
                if excl in format:
                  pass_filters = False
          rls_info.append(child.tag + ': ' + child.text + ' ')
        if unique and pass_filters:
          result['releases'].append( ''.join(rls_info))
    
    for key, value_list in result.items():
      print(key, value_list)
      if len(value_list):
        if key == 'releases':
          for value in sorted(value_list):
            self.bot.privmsg(self.sender[0], value, 'multiline')
        else:
          result_string = io.StringIO()
          result_string.write(key + ': ')
          for value in value_list:
            result_string.write(value + '; ')
          self.bot.privmsg(self.sender[0], result_string.getvalue(), 'multiline')
    emotes = ":) :P :D ;))".split(" ")
    self.privmsg(self.sender[0], "THE END " + random.choice(emotes))
