import re
from datetime import datetime, timedelta

import pytz
from bs4 import BeautifulSoup
from hltv_async_api.Utils import datetools as dt


class Matches:
    def __init__(self, tz):
        self.TIMEZONE = tz

    @staticmethod
    def _get_match_status(status):
        status_ = {'Match over': 0, 'LIVE': 1}
        return status_[status] if status in status_ else 2

    def get_matches(self, r: BeautifulSoup, days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True):
        """returns a list of all upcoming matches on HLTV"""

        matches = []

        try:
            if live:
                for live_div in r.find_all('div', class_='liveMatch-container'):
                    rating = int(live_div['stars'])
                    if rating >= min_rating:
                        id = live_div['data-scorebot-id']
                        t1_id = live_div['team1']
                        t2_id = live_div['team2']
                        teams = live_div.find_all('div', {'class': 'matchTeamName text-ellipsis'})
                        team1 = teams[0].text
                        team2 = teams[1].text
                        maps = live_div.find('div', {'class': 'matchMeta'}).text[-1:]
                        try:
                            event = live_div.find('div', {'class', 'matchEventName gtSmartphone-only'}).text
                        except AttributeError:
                            try:
                                event = live_div.find('span', {'class': 'line-clamp-3'}).text
                            except AttributeError:
                                event = ''

                        matches.append({
                            'id': id,
                            'date': 'LIVE',
                            'time': 'LIVE',
                            'team1': team1,
                            'team2': team2,
                            't1_id': t1_id,
                            't2_id': t2_id,
                            'maps': maps,
                            'rating': rating,
                            'event': event
                        })

            if future:
                for i, date_div in enumerate(r.find_all('div', {'class': 'upcomingMatchesSection'}), start=1):
                    if i > days:
                        break
                    date_ = date_div.find('span', {'class': 'matchDayHeadline'}).text.split()[-1]

                    for match in date_div.find_all('div', {'class': 'upcomingMatch'}):
                        time_ = match.find('div', {'class': 'matchTime'}).text
                        dtime_ = datetime.strptime(date_ + '/' + time_, "%Y-%m-%d/%H:%M")
                        dtime = dt.localize_datetime_to_timezone(self.TIMEZONE, date_=dtime_)
                        rating = int(match['stars'])
                        if rating >= min_rating:
                            id_ = 0
                            t1_id = 0
                            t2_id = 0
                            team1 = 'TBD'
                            team2 = 'TBD'

                            try:
                                id_ = match.find('a')['href'].split('/')[2]
                                t1_id = match['team1']
                                t2_id = match['team2']
                            except (IndexError, AttributeError, KeyError):
                                pass
                            maps = match.find('div', {'class': 'matchMeta'}).text[-1:]
                            try:
                                teams = match.find_all('div', {'class': 'matchTeamName text-ellipsis'})

                                team1 = teams[0].text
                                team2 = teams[1].text
                            except (IndexError, AttributeError):
                                pass

                            try:
                                event = match.find('div', {'class', 'matchEventName gtSmartphone-only'}).text
                            except AttributeError:

                                try:
                                    event = match.find('span', {'class': 'line-clamp-3'}).text
                                except AttributeError:
                                    event = ''

                            matches.append({
                                'id': id_,
                                'date': dtime.strftime('%d-%m-%Y'),
                                'time': dtime.strftime('%H:%M'),
                                'team1': team1,
                                'team2': team2,
                                't1_id': t1_id,
                                't2_id': t2_id,
                                'maps': maps,
                                'rating': rating,
                                'event': event
                            })

        except AttributeError:
            return None

        return matches

    def get_match_info(self, r: BeautifulSoup, id_, team1, team2, event, stats: bool = True, predicts: bool = True):

        status = r.find('div', {'class': 'countdown'})

        status_int = self._get_match_status(status).text

        match_info = {'id': id_}

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
            score1 = scores[0].get_text().replace('\n', '')[-1]
            score2 = scores[1].get_text().replace('\n', '')[-1]

        maps = []
        for map_div in r.find_all('div', {'class': 'mapholder'}):
            mapname = map_div.find('div', {'class': 'mapname'}).text
            pick = ''
            r_team1 = '0'
            r_team2 = '0'
            if mapname != 'TBA':
                try:
                    r_teams = map_div.find_all('div', {'class': 'results-team-score'})
                    r_team1 = r_teams[0].text
                    r_team2 = r_teams[1].text
                except (AttributeError, IndexError, TypeError):
                    r_team1 = '0'
                    r_team2 = '0'
                try:
                    if 'pick' in map_div.find('div', class_='results-left')['class']:
                        pick = team1
                    elif 'pick' in map_div.find('span', class_='results-right')['class']:
                        pick = team2
                except TypeError:
                    pick = ''

            maps.append({'mapname': mapname, 'r_team1': r_team1, 'r_team2': r_team2, 'pick': pick})

        match_info['maps'] = maps

        if stats and status_int == 0:
            stats_ = []
            for table_div in r.find_all('table', {'class': 'table totalstats'})[:2]:
                for player in table_div.find_all('tr')[1:]:
                    player_id = player.find('a', class_='flagAlign')['href'].split('/')[2]
                    player_name = player.find('div', class_='statsPlayerName').text.strip()
                    nickname = re.findall(r"'(.*?)'", player_name)[0]

                    kd = player.find('td', class_='kd').text.strip()
                    adr = player.find('td', class_='adr').text.strip()
                    rating = player.find('td', class_='rating').text.strip()
                    stats_.append({
                        'id': player_id,
                        'nickname': nickname,
                        'kd': kd,
                        'adr': adr,
                        'rating': rating
                    })
            match_info['stats'] = stats_

        if status_int == 1:
            for map in maps:
                try:
                    if map["r_team1"].isdigit() and map["r_team2"].isdigit():
                        len_ = len(map)
                        s1, s2 = int(map["r_team1"]), int(map["r_team2"])
                        if s1 > 12 and s1 > s2:
                            if len_ != 1:
                                score1 += 1
                            else:
                                score1 = s1
                                score2 = s2

                        elif s2 > 12 and s2 > s1:
                            if len_ != 1:
                                score2 += 1
                            else:
                                score2 = s2
                                score1 = s1
                except ValueError:
                    pass

        if predicts and status != 0:
            try:
                predict_div = r.find('div', class_='standard-box pick-a-winner').find_all('div', class_='percentage')
                match_info['predict1'] = predict_div[0].text
                match_info['predict2'] = predict_div[1].text
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
                        rating = len(big_res.find_all('i', {'class': 'fa fa-star star'}))
                    except AttributeError:
                        rating = 0

                    match_id = res['href'].split('/', 3)[2]
                    teams = res.find_all('td', class_='team-cell')
                    team1 = teams[0].get_text().strip()
                    team2 = teams[1].get_text().strip()

                    event = res.find('span', class_='event-name').text

                    scores = res.find("td", class_="result-score").text.strip().split('-')
                    s_t1 = scores[0].strip()
                    s_t2 = scores[1].strip()

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
                    date = dt.localize_datetime_to_timezone(date_str=date__).strftime('%d-%m-%Y')
                except Exception:
                    date = None

                for res in date_div.find_all("a", {"class": "a-reset"}):
                    if res['href'] == '/forums' or n > max:
                        break
                    result_ = {}
                    rating = len(res.find_all('i', {'class': 'fa fa-star star'}))

                    if rating >= min_rating:
                        match_id = 0
                        team1 = 'TBD'
                        team2 = 'TBD'
                        try:
                            match_id = res['href'].split('/', 3)[2]
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

                        scores = res.find("td", class_="result-score").text.strip().split('-')
                        result_['score1'] = scores[0].strip()
                        result_['score2'] = scores[1].strip()
                        result_['rating'] = rating
                        result_['event'] = res.find('span', class_='event-name').text

                        results.append(result_)
                        n += 1

        return results