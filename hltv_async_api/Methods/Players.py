class Players:
    def __init__(self, tz):
        self.TZ = tz

    @staticmethod
    def get_top_players(r, top):
        players = []
        rank = 1
        try:
            for player in r.find('tbody').find_all('tr'):
                name_div = player.find('td', {'class', 'playerCol'}).find('a')
                id_ = name_div['href'].split('/')[3]
                name = name_div.text
                team = player.find('td', {'class', 'teamCol'})['data-sort']

                maps = player.find('td', {'class', 'statsDetail'}).text

                ratings = {'ratingCol ratingPositive', 'ratingCol ratingNeutral', 'ratingCol ratingNegative'}
                rating = 'ERROR'
                for rat in ratings:
                    try:
                        rating = player.find('td', {'class', rat}).text

                        break
                    except AttributeError:
                        pass

                players.append({
                    'id': id_,
                    'rank': rank,
                    'nickname': name,
                    'team': team,
                    'maps': maps,
                    'rating': rating,
                })
                rank += 1
                if rank > top:
                    break
        except AttributeError:
            raise AttributeError("Top players parsing error, probably page not fully loaded")

        return players

    @staticmethod
    def get_player_info(r, id, nickname):
        player = {'id': id, 'nickname': nickname}

        try:
            team_div = r.find('div', class_='playerInfoRow playerTeam').find('a')
            player['team'] = team_div.get_text().strip()
            player['team_id'] = int(team_div['href'].split('/', 3)[2])
        except (AttributeError, TypeError):
            team_str = '?'
            team_id = 0

        name_div = r.find('div', class_='playerRealname')
        player['name'] = name_div.get_text().strip()
        player['nationality'] = name_div.find('img')['title']

        player['age'] = int(
            r.find('div', class_='playerInfoRow playerAge').find('span', class_='listRight').get_text().strip().split()[
                0])

        rating_div = r.find('div', class_='playerpage-container').find_all('span', class_='statsVal')
        player['rating'] = rating_div[0].get_text().strip()
        player['kpr'] = rating_div[1].get_text().strip()
        player['hs'] = rating_div[2].get_text().strip()

        player['img'] = r.find('img', class_='bodyshot-img')['src']
        try:
            trophies_div = r.find('div', class_='trophyRow').find_all(class_='trophy')
            player['total_trophies'] = len(trophies_div)

            # Find last trophy
            last_trophy = ''
            for trophy in trophies_div:
                try:
                    if trophy['href'] and 'events' in trophy['href']:
                        player['last_trophy'] = trophy.find('span', class_='trophyDescription')['title']
                        break
                except (KeyError, TypeError):
                    player['last_trophy'] = ''

            # Find MVPs
            try:
                player['total_mvp'] = int(trophies_div[0].find('div', class_='mvp-count').text)
            except (IndexError, AttributeError, ValueError):
                player['total_mvp'] = 0

        except Exception:
            player['total_trophies'] = 0
        try:
            matches = []
            matches_div = r.find_all('div', class_='col-6 text-ellipsis')[1]
            for match in matches_div.find_all('a'):
                matches.append(match['href'].split('/', 4)[3])
            player['last_matches'] = matches
        except (AttributeError, ValueError):
            player['last_matches'] = []

        return player