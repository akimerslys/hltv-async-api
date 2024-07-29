from datetime import datetime
from typing import Any, List
from hltv_async_api.Utils import datetools as dt


class Events:
    def __init__(self, tz):
        self.TIMEZONE = tz

    @staticmethod
    def get_event_results(r, event_id: int | str, days: int = 1, max_: int = 10) -> list[dict[str, Any]] | None:

        match_results = []

        n = 0
        for i, result in enumerate(
                r.find("div", {'class', 'results-holder'}).find_all("div", {'class', 'results-sublist'}), start=1):
            if i > days or n > max_:
                break
            try:
                date_ = dt.normalize_date(result.find("span", class_="standard-headline").text.strip())
                date = dt.localize_datetime_to_timezone(date_str=date_).strftime("%d-%m-%Y")
            except Exception:
                date = None

            for match in result.find_all("a", class_="a-reset"):
                if n > max_:
                    break

                id_ = match['href'].split('/')[2]
                teams = match.find_all("div", class_="team")
                team1 = teams[0].text.strip()
                team2 = teams[1].text.strip()

                scores = match.find("td", class_="result-score").text.strip().split('-')
                score_t1 = scores[0].strip()
                score_t2 = scores[1].strip()

                match_results.append({
                    'id': id_,
                    'date': date,
                    'team1': team1,
                    'team2': team2,
                    'score1': score_t1,
                    'score2': score_t2,
                })
                n += 1
        return match_results

    @staticmethod
    def get_event_matches(r, event_id, days, max_) -> list[dict[str, Any]] | None:
        live_matches: List | Any
        matches = []
        try:
            live_matches = r.find("div", {'class', 'liveMatchesSection'}).find_all("div",
                                                                                   {'class', 'liveMatch-container'})
        except AttributeError:
            live_matches = []
        for live in live_matches:
            id_ = live.find('a', {'class': 'match a-reset'})['href'].split('/')[2]
            teams = live.find_all("div", class_="matchTeamName text-ellipsis")
            team1 = teams[0].text.strip()
            team2 = teams[1].text.strip()
            t1_id = live['team1']
            t2_id = live['team2']

            # scores will be implemented in the socket extension of this library.
            """try:
                scores = live.find("td", class_="matchTeamScore").text.strip().split('-')
                score_team1 = scores[0].strip()
                score_team2 = scores[1].strip()
            except AttributeError:
                score_team1 = 0
                score_team2 = 0"""

            matches.append({
                'id': id_,
                'date': 'LIVE',
                'team1': team1,
                'team2': team2,
                't1_id': t1_id,
                't2_id': t2_id
            })

        for date_sect in r.find_all('div', {'class': 'upcomingMatchesSection'}):
            date_ = date_sect.find('span', {'class': 'matchDayHeadline'}).text.split(' ')[-1]
            for match in date_sect.find_all('div', {'class': 'upcomingMatch'}):
                teams_ = match.find_all("div", class_="matchTeamName text-ellipsis")
                id_ = match.find('a')['href'].split('/')[2]
                t1_id = 0
                t2_id = 0
                time_ = match.find('div', {'class', 'matchTime'}).text
                team1_ = 'TBD'
                team2_ = 'TBD'
                try:
                    team1_ = teams_[0].text.strip()
                    team2_ = teams_[1].text.strip()
                    t1_id = match['team1']
                    t2_id = match['team2']
                except IndexError:
                    pass

                matches.append({
                    'id': id_,
                    'date': date_,
                    'time': time_,
                    'team1': team1_,
                    'team2': team2_,
                    't1_id': t1_id,
                    't2_id': t2_id
                })

        return matches

    @staticmethod
    def get_events(r, outgoing, future, max_events):
        events = []

        if outgoing:
            for event in r.find('div', {'class': 'tab-content', 'id': 'TODAY'}).find_all('a', {
                'class': 'a-reset ongoing-event'}):
                event_name = event.find('div', {'class': 'text-ellipsis'}).text.strip()
                event_start_date = dt.normalize_date(
                    event.find('span', {'data-time-format': 'MMM do'}).text.strip().split())

                event_end_date = dt.normalize_date(
                    event.find_all('span', {'data-time-format': 'MMM do'})[1].text.strip().split())
                event_id = event['href'].split('/')[-2]

                events.append({
                    'id': event_id,
                    'title': event_name,
                    'start_date': event_start_date,
                    'end_date': event_end_date,
                })

        if future:
            for i, big_event_div in enumerate(r.find_all('div', {'class': 'big-events'}, start=1)):
                for event in big_event_div.find_all('a', {'class': 'a-reset standard-box big-event'}):

                    if i >= max_events:
                        break

                    event_id = event['href'].split('/')[-2]
                    event_name = event.find('div', {'class': 'big-event-name'}).text.strip()
                    # event_location = event.find('span', {'class': 'big-event-location'}).text.strip()
                    event_start_date = dt.normalize_date(event.find('span', {'class': ''}).text.strip().split())
                    event_end_date = dt.normalize_date(event.find('span', {'class': ''}).text.strip().split())

                    events.append({
                        'id': event_id,
                        'title': event_name,
                        'start_date': event_start_date,
                        'end_date': event_end_date
                    })

        return events

    @staticmethod
    def get_event_info(r, event_id, event_title):
        event = {'id': event_id, 'title': event_title}

        def event_date_process(start_date, end_date):
            current_date = datetime.now()
            st = 0  # Finished
            if current_date < start_date:
                st = 2  # Upcoming
            elif start_date <= current_date <= end_date:
                st = 1  # Ongoing

            return start_date.strftime('%d-%m-%Y'), end_date.strftime('%d-%m-%Y'), st

        date_unix_values = [int(span.get('data-unix')[:-3])
                            for span in r.find('td', {'class', 'eventdate'}).find_all('span') if span.get('data-unix')]
        event['start'], event['end'], event_status = event_date_process(datetime.utcfromtimestamp(date_unix_values[0]),
                                                                        datetime.utcfromtimestamp(date_unix_values[1]))
        status_d = {0: 'Finished', 1: 'Ongoing', 2: 'Upcoming'}
        event['status'] = status_d[event_status]

        event['prize'] = r.find('td', {'class', 'prizepool text-ellipsis'}).text if r.find('td', {'class',
                                                                                                  'prizepool text-ellipsis'}).text else 'TBA'

        event['team_count'] = r.find('td', {'class', 'teamsNumber'}).text if r.find('td', {'class',
                                                                                           'teamsNumber'}).text else 'TBA'

        event['location'] = r.find('td', {'class', 'location gtSmartphone-only'}).get_text().replace('\n', '')

        if event_status == 0:
            try:
                mvp_div = r.find('div', class_='player-and-coin').find('a')
                if mvp_div:
                    event['mvp'] = {'id': mvp_div['href'].split('/')[2], 'nickname': mvp_div.get_text().strip()[1:-1]}
            except IndexError:
                pass

            try:
                winners_div = r.find_all('div', class_='placement')
                winners = []
                for i, winner in enumerate(winners_div, start=1):
                    team_div = winner.find('div', class_='team')
                    team = team_div.get_text().strip()
                    t_id = team_div.find('a')['href'].split('/')[2]
                    prize = winner.find('div', class_='prize').text
                    winners.append({i, team, t_id, prize})
                event['winners'] = winners
            except IndexError:
                pass
        else:
            teams_div = r.find_all('div', class_='col standard-box team-box supports-hover')
            teams = []
            for team in teams_div:
                try:
                    teams.append({team.find('a')['href'].split('/')[2]: team.find('div',
                                                                                  'text-container').get_text().strip()})  # {id:team_name}
                except IndexError:
                    teams.append({'?': '?'})
            event['teams'] = teams

        """try:
            # TO BE REWROTE
            group_div = r.find('div', {'class', 'groups-container'})
            groups = []
            for group in group_div.find_all('table', {'class': 'table standard-box'}):
                group_name = group.find('td', {'class': 'table-header group-name'}).text
                teams = []
                for team in group.find_all('div', 'text-ellipsis'):
                    teams.append(team.find('a').text)
                groups.append({group_name: teams})
        except AttributeError:
            groups = []"""

        return event