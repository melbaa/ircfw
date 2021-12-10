from quakelive import Player


def use(self, trigger, args):
    # self.logger.info(args)
    p = Player(args, weapons=True)

    p.scrape_matches()  # last week matches

    res = ''
    for i in range(5):
        p.matches[i].get_json()
        data = p.matches[i].data
        print(data)
        for player in data['SCOREBOARD']:
            if player['PLAYER_NICK'].lower() == args.lower():
                print(player['RANK'])
                print(str(player['RANK']))
                res += data['GAME_TIMESTAMP_NICE'] \
                    + ' ago. rank ' \
                    + str(player['RANK']) \
                    + ' of ' \
                    + str(len(data['SCOREBOARD'])) \
                    + '. railgun accuracy: ' \
                    + str(player['RAILGUN_ACCURACY']) \
                    + ', railgun hits: ' \
                    + str(player['RAILGUN_HITS']) \
                    + '; '

    if res == '':
        res = "nfi sry"
        # self.logger.info(data) #log last match
    return res

print(use(object(), '', 'baksteen'))
