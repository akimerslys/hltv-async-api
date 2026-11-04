import re
from typing import Any


class Teams:
    def __init__(self, tz):
        self.TZ = tz

    @staticmethod
    def get_top_teams(r, max_teams):
        teams = []
        try:
            for i, team in enumerate(r.find_all("div", {'class': "ranked-team standard-box"}), start=1):
                if i > max_teams:
                    break

                rank = team.find('span', {'class': 'position'}).text[1:]
                title_div: Any
                if rank != '1':
                    title_div = team.find('div', {'class': 'teamLine sectionTeamPlayers'})
                else:
                    title_div = team.find('div', {'class': 'teamLine sectionTeamPlayers teamLineExpanded'})

                title = title_div.find('span', {'class': 'name'}).text
                points = title_div.find('span', {'class': 'points'}).text.split(' ', 1)[0][1:]

                id_ = team.find('a', {'class': 'details moreLink'})['href'].split('/')[-1]

                changes = {'change positive', 'change neutral', 'change negative'}
                change = ''
                for change_ in changes:
                    try:
                        change = team.find('div', {'class', change_}).text
                        break
                    except AttributeError:
                        pass

                teams.append({
                    'id': id_,
                    'rank': rank,
                    'title': title,
                    'points': points,
                    'change': change,
                })
        except AttributeError:
            raise AttributeError("Parsing error, probably page not fully loaded")

        return teams

    @staticmethod
    def get_team_info(r, team_id, title):
        team = {'id': int(team_id), 'title': title, 'rank': 0, 'players': {}, 'coach': '?', 'age': 0, 'weekstop30': 0}
        try:
            known_players = r.find('div', class_='bodyshot-team g-grid').find_all('a')
            team['players'] = {
                player.find('span', {'class': 'text-ellipsis bold'}).text: int(player['href'].split('/')[2]) for
                player in known_players}

            # unknown_players = {'unknown' + str(i): 0 for i in range(len(players) + 1, 6)}
            # players.update(unknown_players)

            for stat in r.find_all('div', {'class': 'profile-team-stat'}):
                label = (stat.find('b').get_text(strip=True) if stat.find('b') else '').lower()
                value = stat.find('span', {'class': 'right'})
                try:
                    if label == 'world ranking':
                        team['rank'] = re.search(r'#(\d+)', value.get_text()).group(1)
                    elif label.startswith('weeks in top'):
                        team['weekstop30'] = value.get_text(strip=True)
                    elif label == 'average player age':
                        team['age'] = value.get_text(strip=True)
                    elif label == 'coach':
                        team['coach'] = stat.find('span', {'class': 'bold a-default'}).get_text().strip("' ")
                except AttributeError:
                    pass
            try:
                team['logo'] = r.find('div', class_='profile-team-logo-container').find_all('img')[-1]['src']
                team['last_trophy'] = r.find('div', {'class': 'trophyHolder'}).find('span')['title']
                team['total_trophies'] = len(r.find_all('div', {'class': 'trophyHolder'}))
            except AttributeError:
                pass

            return team
        except AttributeError:
            raise AttributeError("Parsing error, probably page not fully loaded")