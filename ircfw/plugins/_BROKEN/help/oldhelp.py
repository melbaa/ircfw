# DEAD CODE :)


def help(self):
    self.trailing = self.trailing.strip()
    self.trailing = re.sub(r'\s+', ' ', self.trailing)
    topic = ""
    while len(self.trailing):
        tmp, self.trailing = self.get_word(self.trailing)
        if len(topic):
            topic += ' ' + tmp
        else:
            topic = tmp

    print(topic)
    if len(topic) == 0:

        reply = 'help topics are:'
        for topic in self.help_topics:
            reply += ' ' + "'" + topic + "'"

        msglen = self.BUFSIZE - 2
        beg = 0
        end = beg + msglen
        while beg < len(reply):
            self.privmsg(self.sender[0], reply[beg:end])
            beg = end
            end += msglen
    elif topic in self.help_topics:
        self.privmsg(self.sender[0], self.help_topics[topic])


  def load_helpfile(self, path, adict):
    """load a file in adict where a key is separated by
    a value by two newlines
    
    throws if a key is about to be redefined or undefined
    """
    if os.path.isfile(path):
      with open(path) as f:
        # what we can expect
        KEY, VAL, LF = 1, 2, 3
        n = KEY
        key = None
        for line in f:
          line = line.rstrip()
          if line != '':
            if n == KEY:
              key = line
              value = adict.get(key)
              if value is None:
                adict[key] = value
                n = VAL
              else:
                raise Exception('redefinition for key "' + key + '"')
            elif n == VAL:
              adict[key] = line
              n = KEY
              key = None
            else:
              raise Exception('u should never reach this')
        # the file has ended but we are still expecting a value
        if n != KEY:
          raise Exception(key + ' is undefined in ' + path)
    else:
      raise RuntimeError(path + " not found, you need to setup your helpfile")
    return adict
