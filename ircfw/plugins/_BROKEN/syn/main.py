import random

class plugin():
  def __init__(self, bot):
    

    self.choices = ['syn-ack', 'syn-ack', 'rst']
    print('plugin' ,self.name_and_aliases(), 'started')
    

  def test(self):
    return True
  
  def help(self):
    return "act like establishing a tcp 3 way handshake"
    
  def name_and_aliases(self):
    return ["syn"]
  
  def use(self,rawcommand):
    return random.choice(self.choices)
  