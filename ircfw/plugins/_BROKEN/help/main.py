"""
DONE da podrejda po azbuchen red keys?

TODO helpa mai ne pokazva vsiki komandi
TODO da pokazva aliases za suotvetnata komanda
"""

class plugin():
  def __init__(self, bot):
    print('plugin' ,self.name_and_aliases(), 'started')
    self.bot = bot

  def test(self):
    return True
  
  def help(self):
    return "help <command>. Available commands are " \
      + str(sorted(self.bot._plugin_dispatch.keys()))
    
  def name_and_aliases(self):
    return ["help", 'hi']
  
  def use(self,rawcommand):
    command = rawcommand.strip()
    if command == '':
      self.bot.privmsg(self.bot.sender[0], self.help(), 'multiline')
      return
    if command not in self.bot._plugin_dispatch:
      return "no such command exists: " + command
    return self.bot._plugin_dispatch[command].help()
  