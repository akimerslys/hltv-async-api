import re
from datetime import datetime

from hltv_async_api.Utils.numbers import to_float, to_int


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
                id_ = to_int(name_div['href'].split('/')[3])
                name = name_div.text
                team = player.find('td', {'class', 'teamCol'})['data-sort']

                maps = to_int(player.find('td', {'class', 'statsDetail'}).text)

                ratings = {'ratingCol ratingPositive', 'ratingCol ratingNeutral', 'ratingCol ratingNegative'}
                rating = 0.0
                for rat in ratings:
                    try:
                        rating = to_float(player.find('td', {'class', rat}).text)

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
        player = {'id': to_int(id), 'nickname': nickname}

        try:
            team_div = r.find('div', class_='playerInfoRow playerTeam').find('a')
            player['team'] = team_div.get_text().strip()
            player['team_id'] = int(team_div['href'].split('/', 3)[2])
        except (AttributeError, TypeError):
            player['team'] = '?'
            player['team_id'] = 0

        # players without a published real name have no (or an empty) playerRealname block
        name_div = r.find('div', class_='playerRealname')
        player['name'] = name_div.get_text().strip() if name_div else ''
        flag = name_div.find('img') if name_div else None
        for parent in (name_div.parents if name_div else ()):
            if flag:
                break
            flag = parent.find('img', class_='flag')
        player['nationality'] = flag.get('title', '') if flag else ''

        age_div = r.find('div', class_='playerInfoRow playerAge')
        age_span = age_div.find('span', class_='listRight') if age_div else None
        age = re.search(r'\d+', age_span.get_text()) if age_span else None
        player['age'] = int(age.group()) if age else 0

        # HLTV reworked this block: only rating and headshot ratio are still published as plain numbers.
        player['rating'] = 0.0
        for stat in r.select('div.player-stat'):
            label = stat.find('b')
            value = stat.find('span', class_='statsVal')
            if label and value and label.get_text(strip=True).lower().startswith('rating'):
                player['rating'] = to_float(value.get_text(strip=True))
                break
        player['hs'] = 0.0
        for stat in r.select('div.all-time-stat'):
            if 'headshots' in stat.get_text().lower():
                value = stat.find('div', class_='stat')
                player['hs'] = to_float(value.get_text(strip=True)) if value else 0.0
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

        # ---- new profile layout: facts, role scores, socials, schedule
        born = r.select_one('.dob-popup-row span:last-child')
        try:
            player['born'] = datetime.strptime(born.get_text(strip=True), '%d %B %Y').strftime('%d-%m-%Y') if born else ''
        except ValueError:
            player['born'] = born.get_text(strip=True) if born else ''
        prize = r.select_one('.playerPrizeMoney .listRight')
        player['prize_money'] = to_int(prize.get_text().replace(',', '')) if prize else 0
        player['top20'] = []
        for link in r.select('.top20ListRight a'):
            year = link.find_next_sibling('span', class_='top-20-year')
            digits = re.search(r"(\d{2})", year.get_text()) if year else None
            player['top20'].append({'rank': to_int(link.get_text()), 'year': 2000 + int(digits.group(1)) if digits else 0,
                                    'article_id': to_int((re.search(r'/news/(\d+)', link.get('href', '')) or [0, 0])[1])})

        window = r.select_one('.stats-window')
        window_text = re.sub(r'[^\w\s]', ' ', window.get_text()) if window else ''
        maps_in_window = re.search(r'(\d+)\s+maps', window_text)
        player['stats_period'] = re.sub(r'\s*\d+\s+maps\s*$', '', window_text).strip() if window else ''
        player['stats_maps'] = to_int(maps_in_window.group(1)) if maps_in_window else 0

        player['rating_top_percent'], player['rating_percentile'] = 0, 0
        roles = {}
        for stat in r.select('div.player-stat'):
            label = stat.find('b')
            if label is None:
                continue
            name = label.get_text(strip=True).lower()
            if name.startswith('rating'):
                image = stat.find('img', class_='statsImg')
                percent = re.findall(r'\d+', image.get('title', '')) if image else []
                if len(percent) >= 2:
                    player['rating_top_percent'], player['rating_percentile'] = int(percent[0]), int(percent[1])
            elif stat.select_one('.row-stats-section-score-100'):
                value = stat.select_one('.statsVal b')
                roles[name] = to_int(value.get_text()) if value else 0
        player['roles'] = roles

        socials = {}
        domains = {'twitter.com': 'twitter', 'x.com': 'twitter', 'twitch.tv': 'twitch', 'instagram.com': 'instagram',
                   'faceit.com': 'faceit', 'youtube.com': 'youtube', 'facebook.com': 'facebook',
                   'steamcommunity.com': 'steam', 'vk.com': 'vk', 'tiktok.com': 'tiktok'}
        for link in r.select('.socialMediaButtons a[href]'):
            host = re.sub(r'^www\.', '', re.sub(r'^\w+://', '', link['href']).split('/')[0])
            if host in domains:
                socials[domains[host]] = link['href']
        player['socials'] = socials

        upcoming, recent = [], []
        for box in r.select('a.playerpage-matchbox'):
            href = box.get('href') or ''
            team = box.select_one('.playerpage-matchbox-team img')
            entry = {'opponent': team.get('title', '') if team else '',
                     'opponent_name': (box.select_one('.playerpage-matchbox-team .text-ellipsis') or box).get_text(strip=True),
                     'event': (box.select_one('.playerpage-matchbox-bottom') or box).get_text(strip=True)}
            when = box.select_one('.playerpage-match-time[data-unix]')
            result = box.select_one('.playerpage-match-result')
            if result is not None:
                scores = [int(n) for n in re.findall(r'\d+', result.get_text())][:2]
                entry.update({'stats_id': to_int((re.search(r'/stats/matches/(?:\w+/)?(\d+)', href) or [0, 0])[1]),
                              'score1': scores[0] if scores else 0, 'score2': scores[1] if len(scores) > 1 else 0,
                              'won': 'won-matchbox' in (box.get('class') or [])})
                recent.append(entry)
            elif when is not None:
                entry.update({'id': to_int((re.search(r'/matches/(\d+)', href) or [0, 0])[1]),
                              'timestamp': to_int(when.get('data-unix')) // 1000})
                upcoming.append(entry)
        player['upcoming_matches'] = upcoming
        player['recent_matches'] = recent
        # ids taken from the links of the profile's match list, in page order: match ids of upcoming and live
        # matches, statistics ids (get_match_stats) of finished ones. recent_matches / upcoming_matches say which is which.
        matches = []
        for col in r.find_all('div', class_='col-6 text-ellipsis'):
            if 'matches' in col.get_text().lower()[:40]:
                for match in col.find_all('a', class_='playerpage-matchbox'):
                    match_id = next((p for p in (match.get('href') or '').split('/') if p.isdigit()), None)
                    if match_id:
                        matches.append(int(match_id))
                break
        player['last_matches'] = matches

        return player
