from datetime import datetime, timezone
from typing import Any, List
from hltv_async_api.Utils import datetools as dt
from hltv_async_api.Utils.numbers import to_int
from hltv_async_api.methods.Matches import Matches


class Events:
    def __init__(self, tz):
        self.TIMEZONE = tz

    def get_event_results(self, r, event_id: int | str, days: int = 1, max_: int = 10) -> list[dict[str, Any]] | None:

        match_results = []

        n = 0
        holder = r.find("div", {'class', 'results-holder'})
        for i, result in enumerate(holder.find_all("div", {'class', 'results-sublist'}) if holder else [], start=1):
            if i > days or n >= max_:
                break
            try:
                date_ = dt.normalize_date_(result.find("span", class_="standard-headline").text.strip())
                date = dt.localize_datetime_to_timezone(self.TIMEZONE, date_str=date_).strftime("%d-%m-%Y")
            except Exception:
                date = None

            for match in result.find_all("a", class_="a-reset"):
                if n >= max_:
                    break

                parts = (match.get('href') or '').split('/')
                teams = match.find_all("div", class_="team")
                score_td = match.find("td", class_="result-score")
                if len(parts) < 3 or len(teams) < 2 or score_td is None:
                    continue  # not a result row (ad, placeholder, ...)
                id_ = to_int(parts[2])
                team1 = teams[0].text.strip()
                team2 = teams[1].text.strip()

                scores = (score_td.text.strip().split('-') + ['', ''])[:2]
                score_t1 = to_int(scores[0])
                score_t2 = to_int(scores[1])

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
        matches = []

        for live in r.select('div.liveMatchesSection div.match-wrapper'):
            base = Matches._match_base(live)
            matches.append({
                'id': base['id'],
                'date': 'LIVE',
                'team1': base['team1'],
                'team2': base['team2'],
                't1_id': base['t1_id'],
                't2_id': base['t2_id']
            })

        for date_sect in r.select('div.matches-list-section'):
            headline = date_sect.find(class_='matches-list-headline')
            date_ = headline.get_text().split()[-1] if headline and headline.get_text().split() else ''
            for match in date_sect.select('div.match-wrapper'):
                base = Matches._match_base(match)
                time_div = match.find(class_='match-time')
                matches.append({
                    'id': base['id'],
                    'date': date_,
                    'time': time_div.get_text(strip=True) if time_div else '',
                    'team1': base['team1'],
                    'team2': base['team2'],
                    't1_id': base['t1_id'],
                    't2_id': base['t2_id']
                })

        return matches

    @staticmethod
    def get_events(r, outgoing, future, max_events):
        events = []
        n_ongoing = 0

        if outgoing:
            today_tab = r.find('div', {'class': 'tab-content', 'id': 'TODAY'})
            for event in (today_tab.find_all('a', {'class': 'a-reset ongoing-event'}) if today_tab else []):
                try:
                    event_name = event.find('div', {'class': 'text-ellipsis'}).text.strip()
                    spans = event.find_all('span', {'data-time-format': 'MMM do'})
                    event_start_date = dt.normalize_date(spans[0].text.strip().split())
                    event_end_date = dt.normalize_date(spans[-1].text.strip().split())  # one-day events: one date
                    event_id = to_int(event['href'].split('/')[-2])
                except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                    continue

                events.append({
                    'id': event_id,
                    'title': event_name,
                    'start_date': event_start_date,
                    'end_date': event_end_date,
                })
            n_ongoing = len(events)

        if future:
            for big_event_div in r.find_all('div', {'class': 'big-events'}):
                for event in big_event_div.find_all('a', {'class': 'a-reset standard-box big-event'}):

                    if len(events) >= max_events + n_ongoing:
                        break

                    try:
                        event_id = to_int(event['href'].split('/')[-2])
                        event_name = event.find('div', {'class': 'big-event-name'}).text.strip()
                        dates = event.find_all('span', {'data-unix': True})
                        event_start_date = dt.normalize_date(dates[0].text.strip().split())
                        event_end_date = dt.normalize_date(dates[-1].text.strip().split())
                    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                        continue

                    events.append({
                        'id': event_id,
                        'title': event_name,
                        'start_date': event_start_date,
                        'end_date': event_end_date
                    })

        return events

    @staticmethod
    def get_event_info(r, event_id, event_title):
        event = {'id': to_int(event_id), 'title': event_title}

        def event_date_process(start_date, end_date):
            current_date = datetime.now(timezone.utc).replace(tzinfo=None)
            st = 0  # Finished
            if current_date < start_date:
                st = 2  # Upcoming
            elif start_date <= current_date <= end_date:
                st = 1  # Ongoing

            return start_date.strftime('%d-%m-%Y'), end_date.strftime('%d-%m-%Y'), st

        def cell(*classes):
            for cls in classes:
                td = r.find('td', {'class', cls})
                if td is not None:
                    return td.get_text().strip()
            return ''

        date_cell = r.find('td', {'class', 'eventdate'})
        date_unix_values = [int(span.get('data-unix')[:-3])
                            for span in (date_cell.find_all('span') if date_cell else []) if span.get('data-unix')]
        if date_unix_values:
            # one-day events publish a single date
            start_ts, end_ts = date_unix_values[0], date_unix_values[-1]
            event['start'], event['end'], event_status = event_date_process(
                datetime.fromtimestamp(start_ts, timezone.utc).replace(tzinfo=None),
                datetime.fromtimestamp(end_ts, timezone.utc).replace(tzinfo=None))
        else:
            event['start'], event['end'], event_status = '', '', 2
        status_d = {0: 'Finished', 1: 'Ongoing', 2: 'Upcoming'}
        event['status'] = status_d[event_status]

        event['prize'] = cell('prizepool text-ellipsis', 'prizepool') or 'TBA'
        event['team_count'] = cell('teamsNumber') or 'TBA'
        event['location'] = cell('location gtSmartphone-only', 'location').replace('\n', '')

        if event_status == 0:
            try:
                mvp_div = r.find('div', class_='player-and-coin').find('a')
                if mvp_div:
                    event['mvp'] = {'id': to_int(mvp_div['href'].split('/')[2]), 'nickname': mvp_div.get_text().strip().split("'")[-2] if "'" in mvp_div.get_text() else mvp_div.get_text().strip()}
            except (IndexError, AttributeError, TypeError):
                pass

            try:
                winners_div = r.find_all('div', class_='placement')
                winners = []
                for i, winner in enumerate(winners_div, start=1):
                    team_div = winner.find('div', class_='team')
                    team = team_div.get_text().strip()
                    link = team_div.find('a')
                    parts = (link.get('href') or '').split('/') if link else []
                    t_id = to_int(parts[2]) if len(parts) > 2 else 0
                    prize_div = winner.find('div', class_='prize')
                    prize = prize_div.text if prize_div else ''
                    winners.append({'place': i, 'team': team, 'id': t_id, 'prize': prize})
                event['winners'] = winners
            except (IndexError, AttributeError, TypeError):
                pass
        else:
            teams_div = r.find_all('div', class_='col standard-box team-box supports-hover')
            teams = []
            for team in teams_div:
                try:
                    teams.append({to_int(team.find('a')['href'].split('/')[2]): team.find('div',
                                                                                  'text-container').get_text().strip()})  # {id:team_name}
                except (IndexError, AttributeError, TypeError, KeyError):
                    teams.append({0: '?'})
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