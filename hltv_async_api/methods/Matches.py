import re
from datetime import datetime, timedelta

import pytz
from bs4 import BeautifulSoup
from hltv_async_api.Utils import datetools as dt
from hltv_async_api.Utils.numbers import to_float, to_int


class Matches:
    def __init__(self, tz):
        self.TIMEZONE = tz

    @staticmethod
    def _get_match_status(status):
        status_ = {'Match over': 0, 'LIVE': 1}
        if status in status_:
            return status_[status]
        # 2 = upcoming (countdown such as '1d : 2h : 3m : 4s'), 3 = anything else, e.g. 'Match postponed'
        return 2 if re.search(r'\d+\s*[dhms](?![a-z])', status) else 3

    @staticmethod
    def _match_base(div) -> dict:
        """Fields shared by live and upcoming entries of the matches page."""
        id_ = to_int(div.get('data-match-id'))
        t1_id = to_int(div.get('team1'))
        t2_id = to_int(div.get('team2'))
        names = []
        for team_div in div.select('.match-teams .match-team')[:2]:
            name = team_div.find(class_='match-teamname')
            names.append(name.get_text(strip=True) if name else 'TBD')
        team1, team2 = (names + ['TBD', 'TBD'])[:2]

        maps = 0  # best-of; 0 when the page does not say
        for meta in div.select('.match-meta'):
            text = meta.get_text(strip=True)
            if text.startswith('bo'):
                maps = to_int(text)
                break

        logo = div.select_one('img.match-event-logo')
        if logo and logo.get('title'):
            event = logo['title']
        else:
            event_div = div.select_one('.match-event')
            event = event_div.get_text(strip=True) if event_div else ''

        return {'id': id_, 'team1': team1, 'team2': team2, 't1_id': t1_id, 't2_id': t2_id,
                'maps': maps, 'rating': int(div.get('data-stars') or 0), 'event': event}

    def get_matches(self, r: BeautifulSoup, days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True):
        """returns a list of all upcoming matches on HLTV"""

        matches = []
        fields = ('team1', 'team2', 't1_id', 't2_id', 'maps', 'rating', 'event')

        try:
            if live:
                for live_div in r.select('div.liveMatchesSection div.match-wrapper'):
                    base = self._match_base(live_div)
                    if base['rating'] >= min_rating:
                        matches.append({'id': base['id'], 'date': 'LIVE', 'time': 'LIVE',
                                        **{k: base[k] for k in fields}})

            if future:
                for i, date_div in enumerate(r.select('div.matches-list-section'), start=1):
                    if i > days:
                        break
                    date_ = date_div.find(class_='matches-list-headline').get_text().split()[-1]

                    for match in date_div.select('div.match-wrapper'):
                        base = self._match_base(match)
                        if base['rating'] < min_rating:
                            continue
                        time_ = match.find(class_='match-time').get_text(strip=True)
                        dtime_ = datetime.strptime(date_ + '/' + time_, "%Y-%m-%d/%H:%M")
                        dtime = dt.localize_datetime_to_timezone(self.TIMEZONE, date_=dtime_)

                        matches.append({'id': base['id'], 'date': dtime.strftime('%d-%m-%Y'),
                                        'time': dtime.strftime('%H:%M'), **{k: base[k] for k in fields}})

        except AttributeError:
            return None

        return matches

    def get_match_info(self, r: BeautifulSoup, id_, team1, team2, event, stats: bool = True, predicts: bool = True):

        status = r.find('div', {'class': 'countdown'}).text.strip()

        status_int = self._get_match_status(status)

        match_info = {'id': to_int(id_)}

        if status_int == 2:
            components = status.split(" : ")

            days, hours, minutes, seconds = 0, 0, 0, 0

            for component in components:
                if 'd' in component:
                    days = int(component.replace("d", ""))
                elif 'h' in component:
                    hours = int(component.replace("h", ""))
                elif 'm' in component:
                    minutes = int(component.replace("m", ""))
                elif 's' in component:
                    seconds = int(component.replace("s", ""))

            date_ = datetime.now(tz=pytz.timezone('Europe/Copenhagen')).replace(second=0, microsecond=0) + timedelta(
                days=days,
                hours=hours,
                minutes=minutes,
                seconds=seconds)

            status = dt.localize_datetime_to_timezone(self.TIMEZONE, date_=date_).strftime('%d-%m-%Y-%H-%M')

        match_info['status'] = status

        score1, score2 = 0, 0

        if status_int == 0:
            scores = r.find_all('div', class_='team')
            score1 = to_int((re.findall(r'\d+', scores[0].get_text()) or [0])[-1])
            score2 = to_int((re.findall(r'\d+', scores[1].get_text()) or [0])[-1])

        maps = []
        for map_div in r.find_all('div', {'class': 'mapholder'}):
            mapname = map_div.find('div', {'class': 'mapname'}).text
            pick = ''
            r_team1 = 0  # rounds won; 0 while the map is not played
            r_team2 = 0
            if mapname != 'TBA':
                try:
                    r_teams = map_div.find_all('div', {'class': 'results-team-score'})
                    r_team1 = to_int(r_teams[0].text)
                    r_team2 = to_int(r_teams[1].text)
                except (AttributeError, IndexError, TypeError):
                    r_team1 = 0
                    r_team2 = 0
                try:
                    if 'pick' in map_div.find('div', class_='results-left')['class']:
                        pick = team1
                    elif 'pick' in map_div.find('span', class_='results-right')['class']:
                        pick = team2
                except TypeError:
                    pick = ''

            stats_link = map_div.select_one('a.results-stats')
            maps.append({'mapname': mapname, 'r_team1': r_team1, 'r_team2': r_team2, 'pick': pick,
                         'stats_id': to_int((re.search(r'mapstatsid/(\d+)', stats_link.get('href', '')) or [0, 0])[1])
                         if stats_link else 0})

        match_info['maps'] = maps
        detailed = r.select_one('.stats-detailed-stats a[href*="/stats/matches/"]')
        match_info['stats_id'] = (to_int(re.search(r'/stats/matches/(?:\w+/)?(\d+)', detailed.get('href', '')).group(1))
                                  if detailed and re.search(r'/stats/matches/(?:\w+/)?(\d+)', detailed.get('href', '')) else 0)

        if stats and status_int == 0:
            stats_ = []
            for table_div in r.find_all('table', {'class': 'table totalstats'})[:2]:
                for player in table_div.find_all('tr')[1:]:
                    player_id = to_int(player.find('a', href=re.compile(r'^/player/\d+'))['href'].split('/')[2])
                    player_name = player.find('div', class_='statsPlayerName').text.strip()
                    nickname = re.findall(r"'(.*?)'", player_name)[0]

                    kd = player.find('td', class_='kd').text.strip()
                    adr = player.find('td', class_='adr').text.strip()
                    rating = player.find('td', class_='rating').text.strip()
                    stats_.append({
                        'id': player_id,
                        'nickname': nickname,
                        'kd': kd,
                        'adr': to_float(adr),
                        'rating': to_float(rating)
                    })
            match_info['stats'] = stats_

        if status_int == 1:
            for map in maps:
                s1, s2 = map["r_team1"], map["r_team2"]
                if s1 > 12 and s1 > s2:
                    score1 += 1
                elif s2 > 12 and s2 > s1:
                    score2 += 1

        if predicts and status_int != 0:
            try:
                predict_div = r.find('div', class_='standard-box pick-a-winner').find_all('div', class_='percentage')
                match_info['predict1'] = to_int(predict_div[0].text)
                match_info['predict2'] = to_int(predict_div[1].text)
            except (AttributeError, IndexError):
                pass

        match_info['score1'], match_info['score2'] = score1, score2
        return match_info

    def get_results(self, r: BeautifulSoup, days: int = 1,
                    min_rating: int = 1,
                    max: int = 30,
                    featured: bool = True,
                    regular: bool = True) -> list:

        results = []

        if featured:
            try:
                big_res = r.find("div", {'class', "big-results"}).find_all("a", {"class": "a-reset"})

                for res in big_res:

                    try:
                        rating = len(res.find_all('i', {'class': 'fa fa-star star'}))
                    except AttributeError:
                        rating = 0

                    match_id = to_int(res['href'].split('/', 3)[2])
                    teams = res.find_all('td', class_='team-cell')
                    team1 = teams[0].get_text().strip()
                    team2 = teams[1].get_text().strip()

                    event = res.find('span', class_='event-name').text

                    scores = res.find("td", class_="result-score").text.strip().split('-')
                    s_t1 = to_int(scores[0])
                    s_t2 = to_int(scores[1])

                    results.append({
                        'id': match_id,
                        'team1': team1,
                        'team2': team2,
                        'score1': s_t1,
                        'score2': s_t2,
                        'rating': rating,
                        'event': event,
                    })
            except AttributeError:
                pass

        if regular:

            n = 0

            for i, date_div in enumerate(r.find_all('div', class_='results-sublist')[1:], start=1):
                if i > days: break
                try:
                    date__ = dt.normalize_date_(date_div.find('span', class_='standard-headline').text)
                    date = dt.localize_datetime_to_timezone(self.TIMEZONE, date_str=date__).strftime('%d-%m-%Y')
                except Exception:
                    date = None

                for res in date_div.find_all("a", {"class": "a-reset"}):
                    if res['href'] == '/forums' or n >= max:
                        break
                    result_ = {}
                    rating = len(res.find_all('i', {'class': 'fa fa-star star'}))

                    if rating >= min_rating:
                        match_id = 0
                        team1 = 'TBD'
                        team2 = 'TBD'
                        try:
                            match_id = to_int(res['href'].split('/', 3)[2])
                        except IndexError:
                            pass
                        finally:
                            result_['id'] = match_id
                            if date: result_['date'] = date
                        try:
                            teams = res.find_all('td', class_='team-cell')
                            team1 = teams[0].get_text().strip()
                            team2 = teams[1].get_text().strip()
                        except (AttributeError, IndexError):
                            pass
                        finally:
                            result_['team1'] = team1
                            result_['team2'] = team2

                        score_td = res.find("td", class_="result-score")
                        event_span = res.find('span', class_='event-name')
                        if score_td is None or event_span is None:
                            continue  # not a result row
                        scores = (score_td.text.strip().split('-') + ['', ''])[:2]
                        result_['score1'] = to_int(scores[0])
                        result_['score2'] = to_int(scores[1])
                        result_['rating'] = rating
                        result_['event'] = event_span.text

                        results.append(result_)
                        n += 1

        return results