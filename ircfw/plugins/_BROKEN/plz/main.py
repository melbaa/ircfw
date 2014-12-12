class plugin():

    def __init__(self, bot):
        print('plugin', self.name_and_aliases(), 'started')

    def test(self):
        return True

    def help(self):
        return "this plugin does nothing"

    def name_and_aliases(self):
        return ["null", "nullalias"]

    def use(self, rawcommand):
        return "nothing to do '" + rawcommand + "' received"
