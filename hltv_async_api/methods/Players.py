import re


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
            player['team'] = '?'
            player['team_id'] = 0

        name_div = r.find('div', class_='playerRealname')
        player['name'] = name_div.get_text().strip()
        flag = name_div.find('img')
        for parent in name_div.parents:
            if flag:
                break
            flag = parent.find('img', class_='flag')
        player['nationality'] = flag.get('title', '') if flag else ''

        age_div = r.find('div', class_='playerInfoRow playerAge')
        age = re.search(r'\d+', age_div.find('span', class_='listRight').get_text()) if age_div else None
        player['age'] = int(age.group()) if age else 0

        # HLTV reworked this block: only rating and headshot ratio are still published as plain numbers.
        player['rating'] = ''
        for stat in r.select('div.player-stat'):
            label = stat.find('b')
            value = stat.find('span', class_='statsVal')
            if label and value and label.get_text(strip=True).lower().startswith('rating'):
                player['rating'] = value.get_text(strip=True)
                break
        player['hs'] = ''
        for stat in r.select('div.all-time-stat'):
            if 'headshots' in stat.get_text().lower():
                player['hs'] = stat.find('div', class_='stat').get_text(strip=True)
                break

        img = r.find('img', class_='player-summary-stat-box-left-bodyshot') or r.find('img', class_='bodyshot-img')
        player['img'] = img['src'] if img else ''

        trophies_div = r.select('div.trophyRow .trophy')
        player['total_trophies'] = len(trophies_div)
        player['last_trophy'] = ''
        for trophy in trophies_div:
            description = trophy.find('span', class_='trophyDescription')
            if '/events/' in (trophy.get('href') or '') and description:
                player['last_trophy'] = description.get('title', '')
                break
        try:
            player['total_mvp'] = int(r.find('div', class_='mvp-count').get_text())
        except (AttributeError, ValueError):
            player['total_mvp'] = 0

        matches = []
        for col in r.find_all('div', class_='col-6 text-ellipsis'):
            if 'matches' in col.get_text().lower()[:40]:
                for match in col.find_all('a', class_='playerpage-matchbox'):
                    matches.append(next(p for p in match['href'].split('/') if p.isdigit()))
                break
        player['last_matches'] = matches

        return player
