from typing import Any, List
from datetime import date, datetime, timedelta
import pytz

from bs4 import BeautifulSoup
import asyncio
from asyncio import get_running_loop
from functools import partial

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientProxyConnectionError, ClientResponseError, ClientOSError, \
    ServerDisconnectedError, ClientHttpProxyError
import re


import logging


class Hltv:
    def __init__(self, max_delay: int = 15,
                 timeout: int = 5,
                 use_proxy: bool = False,
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 debug: bool = False,
                 max_retries: int = 0,
                 proxy_protocol: str | None = None,
                 proxy_one_time: bool = False,
                 true_session: bool = False,
                 ):
        self.headers = {
            "referer": "https://www.hltv.org/stats",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "hltvTimeZone": "UTC"
        }
        self.MAX_DELAY = max_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.USE_PROXY = use_proxy
        self.PROXY_PATH = proxy_path
        self.PROXY_LIST = proxy_list
        self.PROXY_PROTOCOL = proxy_protocol
        self.PROXY_ONCE = proxy_one_time
        self.DEBUG = debug
        self._configure_logging()
        self.logger = logging.getLogger(__name__)

        if self.PROXY_PATH:
            with open(self.PROXY_PATH, "r") as file:
                self.PROXY_LIST = [line.strip() for line in file.readlines()]

        self.TRUE_SESSION = true_session
        self.session = None

    def _configure_logging(self):
        level = logging.DEBUG if self.DEBUG else logging.INFO
        logging.basicConfig(level=level, format="%(message)s")

    async def _create_session(self):
        self.logger.debug('Creating Session')
        self.session = ClientSession()

    async def close_session(self):
        if self.session:
            self.logger.debug('Closing Session')
            await self.session.close()

    def config(self, max_delay: int | None = None,
               timeout: int | None = None,
               use_proxy: bool | None = None,
               proxy_file_path: str | None = None,
               proxy_list: list | None = None,
               debug: bool | None = None,
               max_retries: int | None = None,
               proxy_protocol: str | None = None,
               proxy_one_time: bool | None = None,
               true_session: bool | None = None,
               ):
        if max_delay:
            self.MAX_DELAY = max_delay
        if timeout:
            self.timeout = timeout
        if use_proxy is not None:
            self.USE_PROXY = use_proxy
        if proxy_list:
            self.PROXY_LIST = proxy_list
        if max_retries:
            self.max_retries = max_retries
        if proxy_protocol:
            self.PROXY_PROTOCOL = proxy_protocol
        if proxy_one_time is not None:
            self.PROXY_ONCE = proxy_one_time
        if true_session is not None:
            self.TRUE_SESSION = true_session
        if debug is not None:
            self.DEBUG = debug
            self._configure_logging()
        if proxy_file_path:
            with open(self.PROXY_PATH, "r") as file:
                self.PROXY_LIST = [line.strip() for line in file.readlines()]

    async def _get_proxy(self):
        proxy = self.PROXY_LIST[0]

        if self.PROXY_PROTOCOL and proxy != '' and self.PROXY_PROTOCOL not in proxy:
            proxy = self.PROXY_PROTOCOL + '://' + proxy

        return proxy

    async def _switch_proxy(self):
        if self.PROXY_ONCE:
            self.logger.debug(f'Removing proxy {self.PROXY_LIST[0]}')
            self.PROXY_LIST = self.PROXY_LIST[1:]
        else:
            self.logger.debug(f"Switching proxy {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")
            self.PROXY_LIST = self.PROXY_LIST[1:] + [(self.PROXY_LIST[0])]
            self.logger.info(f"New proxy: {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")

    def _f(self, result):
        return BeautifulSoup(result, "lxml")

    async def _cloudflare_check(self, result) -> bool:
        page = self._f(result)
        challenge_page = page.find(id="challenge-error-title")
        if challenge_page is not None:
            if "Enable JavaScript and cookies to continue" in challenge_page.get_text():
                self.logger.debug("Got cloudflare challenge page")
                return True
        return False

    async def _parse_error_handler(self, delay: int = 0) -> int:
        if self.USE_PROXY:
            await self._switch_proxy()
        else:
            if delay < self.MAX_DELAY:
                delay += 1
            else:
                self.logger.debug("Reached max delay limit, try to use proxy")
            self.logger.info(f"Calling again, increasing delay to {delay}s")

        return delay

    async def _parse(self, url, delay):
        proxy = ''
        # setup new proxy, cuz old one was switched
        if self.USE_PROXY:
            proxy = await self._get_proxy()
        else:
            # delay, only for non proxy users. (default = 1-15s)
            await asyncio.sleep(delay)
        try:
            async with self.session.get(url, headers=self.headers, proxy=proxy, timeout=self.timeout, ) as response:
                self.logger.info(f"Fetching {url}, code: {response.status}")
                if response.status == 403 or response.status == 404:
                    self.logger.debug("Got 403 forbitten")
                    return False, await self._parse_error_handler(delay)

                # checking for challenge page.
                result = await response.text()
                if await self._cloudflare_check(result):
                    return False, await self._parse_error_handler(delay)

                return True, result
        except (ClientProxyConnectionError, ClientResponseError, ClientOSError,
                ServerDisconnectedError, TimeoutError, ClientHttpProxyError) as e:
            self.logger.debug(e)
            delay = await self._parse_error_handler(delay)
            return False, delay

    async def _fetch(self, url, delay: int = 0):
        if not self.session:
            await self._create_session()

        status = False
        try_ = 1
        result = None
        while (not status) and (try_ != self.max_retries):
            self.logger.debug(f'Trying connect to {url}, try {try_}/{self.max_retries}')

            # if status = True, result = page,
            # if status = False result = delay (default=0)
            status, result = await self._parse(url, delay)

            if not status and result:
                delay = result
            try_ += 1

        # After Parse
        if not self.TRUE_SESSION:
            # Automaticaly close session after parse
            await self.close_session()
            self.session = None

        if status:
            loop = get_running_loop()
            parsed = await loop.run_in_executor(None, partial(self._f, result))
            return parsed
        else:
            self.logger.error('Connection failed')
            return None

    def save_error(self, page):
        with open("error.html", "w") as file:
            file.write(page.prettify())

    @staticmethod
    def _normalize_date(parts) -> str:
        month_abbreviations = {
            'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4',
            'May': '5', 'Jun': '6', 'Jul': '7', 'Aug': '8',
            'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }
        month = month_abbreviations[parts[0]]
        day = parts[1][:-2]
        return day + '-' + month

    async def get(self, type: str, id: int | str | None = None,
                  title: str | None = None,
                  team1: str | None = None,
                  team2: str | None = None):
        if type == 'event':
            if id:
                return await self.get_event_info(id, title)
            else:
                return await self.get_events()
        elif type == 'match':
            if id:
                return await self.get_match_info(str(id), team1, team2, title)
            else:
                return await self.get_upcoming_matches()
        elif type == 'news':
            return await self.get_last_news()
        elif type == 'team':
            if id:
                return await self.get_team_info(id, title)
            else:
                return await self.get_top_teams()

    async def get_live_matches(self, max_ = 10):
        """returns a list of all LIVE matches on HLTV along with the maps being played and the star ratings"""
        r = await self._fetch("https://www.hltv.org/matches")
        if not r:
            return

        live_matches = r.find("div", {'class', "liveMatchesContainer"})

        #cant find a way, mby use socketio by hltv-score-bot ?? | other url ?


    async def get_upcoming_matches(self, days: int = 7, min_rating: int = 1):
        """returns a list of all upcoming matches on HLTV"""
        r = await self._fetch("https://www.hltv.org/matches")
        if not r:return

        matches = []
        try:


            for i, date_div in enumerate(r.find_all('div', {'class': 'upcomingMatchesSection'}), start=1):
                if i > days:
                    break
                date_ = date_div.find('span', {'class': 'matchDayHeadline'}).text.split()[-1]
                matches_today = []

                for match in date_div.find_all('div', {'class': 'upcomingMatch'}):
                    time_ = match.find('div', {'class': 'matchTime'}).text
                    rating = int(match['stars'])
                    if rating >= min_rating:
                        match_id_ = match.find('a')['href'].split('/')[2]

                        maps = match.find('div', {'class': 'matchMeta'}).text[-1:]
                        try:
                            teams = match.find_all('div', {'class': 'matchTeamName text-ellipsis'})

                            team1 = teams[0].text
                            team2 = teams[1].text
                        except (IndexError, AttributeError):
                            team1 = 'TBD'
                            team2 = 'TBD'

                        try:
                            event = match.find('div', {'class', 'matchEventName gtSmartphone-only'}).text
                        except AttributeError:

                            try:
                                event = match.find('span', {'class': 'line-clamp-3'}).text
                            except AttributeError:
                                event = ''

                        matches_today.append({
                            'match_id': match_id_,
                            'team1': team1,
                            'team2': team2,
                            'time': time_,
                            'maps': maps,
                            'rating': rating,
                            'event': event
                    })

                matches.append({
                    'date': date_,
                    'matches': matches_today
                })
        except AttributeError:
            return None
        return matches

    async def get_match_info(self, match_id: str, team1: str, team2: str, event_title: str, stats: bool = True):
        r = await self._fetch(f"https://www.hltv.org/matches/{match_id}/"
                             f"{team1.replace(' ', '-')}-vs-"
                             f"{team2.replace(' ', '-')}-"
                             f"{event_title.replace(' ', '-')}")
        if not r:
            return

        status = r.find('div', {'class': 'countdown'}).text

        score1, score2 = 0, 0

        if status == 'Match over':
            scores = r.find_all('div', class_='team')
            score1 = scores[0].get_text().replace('\n', '')[-1]
            score2 = scores[1].get_text().replace('\n', '')[-1]


        maps = []
        for map_div in r.find_all('div', {'class': 'mapholder'}):

                mapname = map_div.find('div', {'class': 'mapname'}).text
                try:
                    r_teams = map_div.find_all('div', {'class': 'results-team-score'})
                    r_team1 = r_teams[0].text
                    r_team2 = r_teams[1].text
                except AttributeError:
                    r_team1 = '0'
                    r_team2 = '0'
                maps.append({'mapname': mapname, 'r_team1': r_team1, 'r_team2': r_team2})

        stats_ = []
        if stats and status == 'Match over':
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
                        'name': nickname,
                        'kd': kd,
                        'adr': adr,
                        'rating': rating
                    })

        if status == "LIVE":
            for map in maps:
                if map["r_team1"] == '13':
                    if len(map) != 1:
                        score1 += 1
                    else:
                        score1 = 13
                        score2 = int(map["r_team2"])

                elif map["r_team1"] == '13':
                    if len(map) != 1:
                        score2 += 1
                    else:
                        score2 = 13
                        score1 = int(map["r_team1"])

        return match_id, score1, score2, status, maps, stats_


    async def get_big_results(self, offset=0) -> list[dict[str, Any]] | None:
        """returns a list of big event matches results"""
        r = await self._fetch("https://www.hltv.org/results?offset=" + str(offset))
        if not r:
            return

        big_results = []
        big_res = r.find("div", {'class', "big-results"}).find_all("div", {"class", "result-con"})
        if not big_res:
            return None
        for res in big_res:
            team1 = res.find("div", class_="team").text.strip()
            team2 = res.find("div", class_="team team-won").text.strip()

            scores = res.find("td", class_="result-score").text.strip().split('-')
            s_t1 = scores[0].strip()
            s_t2 = scores[1].strip()

            big_results.append({
                'team1': team1,
                'team2': team2,
                'score1': s_t1,
                'score2': s_t2,
            })

        return big_results

    async def get_event_results(self, event: int | str) -> list[dict[str, Any]] | None:
        r = await self._fetch("https://www.hltv.org/results?event=" + str(event))
        if not r:
            return

        match_results = []

        for result in r.find("div", {'class', 'results-holder'}).find_all("div", {'class', 'results-sublist'}):
            date = result.find("span", class_="standard-headline").text.strip()
            match_date = []
            for match in result.find_all("a", class_="a-reset"):
                id_ = match['href'].split('/')[2]
                teams = match.find_all("div", class_="team")
                team1 = teams[0].text.strip()
                team2 = teams[1].text.strip()

                scores = match.find("td", class_="result-score").text.strip().split('-')
                score_t1 = scores[0].strip()
                score_t2 = scores[1].strip()

                match_date.append({
                    'id': id_,
                    'team1': team1,
                    'team2': team2,
                    'score1': score_t1,
                    'score2': score_t2,
                })
            match_results.append({
                'date': date,
                'matches': match_date,
            })
        return match_results

    async def get_event_matches(self, event_id: str | int, days: int = 1):
        r = await self._fetch("https://www.hltv.org/events/" + str(event_id) + "/matches")
        if not r:
            return

        live_matches: List | Any
        matches = []
        try:
            live_matches = r.find("div", {'class', 'liveMatchesSection'}).find_all("div", {'class', 'liveMatch-container'})
        except AttributeError:
            live_matches = []
        live_mat = []
        for live in live_matches:
            id_ = live.find('a', {'class': 'match a-reset'})['href'].split('/')[2]
            teams = live.find_all("div", class_="matchTeamName text-ellipsis")
            team1 = teams[0].text.strip()
            team2 = teams[1].text.strip()
            t1_id = live['team1']
            t2_id = live['team2']


            # TODO FIX SCORES
            """try:
                scores = live.find("td", class_="matchTeamScore").text.strip().split('-')
                score_team1 = scores[0].strip()
                score_team2 = scores[1].strip()
            except AttributeError:
                score_team1 = 0
                score_team2 = 0"""

            live_mat.append({
                'id': id_,
                'team1': team1,
                'team2': team2,
                't1_id': t1_id,
                't2_id': t2_id
            })

        matches.append({
            'date': 'LIVE',
            'matches': live_mat,
        })
        for date_sect in r.find_all('div', {'class': 'upcomingMatchesSection'}):
            upc_matches = []
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

                upc_matches.append({
                        'id': id_,
                        'time': time_,
                        'team1': team1_,
                        'team2': team2_,
                        't1_id': t1_id,
                        't2_id': t2_id
                    })

            matches.append({'date': date_, 'matches': upc_matches})

        return matches
    async def get_featured_events(self, max_: int = 1):
        r = await self._fetch('https://www.hltv.org/events')

        events = []
        try:
            for i, event in enumerate(r.find('div', {'class': 'tab-content', 'id': 'FEATURED'}).find_all('a', {'class': 'a-reset ongoing-event'}), start=1):
                if i > max_:
                    break
                event_name = event.find('div', {'class': 'text-ellipsis'}).text.strip()
                event_start_date = self._normalize_date(
                    event.find('span', {'data-time-format': 'MMM do'}).text.strip().split())

                event_end_date = self._normalize_date(
                    event.find_all('span', {'data-time-format': 'MMM do'})[1].text.strip().split())
                event_id = event['href'].split('/')[-2]

                events.append({
                    'id': event_id,
                    'name': event_name,
                    'start_date': event_start_date,
                    'end_date': event_end_date,
                })
        except AttributeError:
            pass

        return events
    async def get_events(self, featured=True, outgoing=True, future=True, max_events=10):
        """Returns events
        :params:
        outgoing - include live tournaments
        future - include future tournamets
        max_events - use only if future=True
        :return:
        [('id', 'title', 'startdate', 'enddate')]
        """

        r = await self._fetch('https://www.hltv.org/events')
        if not r:
            return

        events = []

        if outgoing:
            for event in r.find('div', {'class': 'tab-content', 'id': 'TODAY'}).find_all('a', {
                                'class': 'a-reset ongoing-event'}):
                event_name = event.find('div', {'class': 'text-ellipsis'}).text.strip()
                event_start_date = self._normalize_date(
                    event.find('span', {'data-time-format': 'MMM do'}).text.strip().split())

                event_end_date = self._normalize_date(
                    event.find_all('span', {'data-time-format': 'MMM do'})[1].text.strip().split())
                event_id = event['href'].split('/')[-2]

                events.append({
                    'id': event_id,
                    'name': event_name,
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
                    event_start_date = self._normalize_date(event.find('span', {'class': ''}).text.strip().split())
                    event_end_date = self._normalize_date(event.find('span', {'class': ''}).text.strip().split())

                    events.append({
                        'id': event_id,
                        'title': event_name,
                        'start_date': event_start_date,
                        'end_date': event_end_date
                    })

        return events

    async def get_event_info(self, event_id: str | int, event_title: str):
        #TODO ADD PLACEC FOR PAST EVENTS? OR WINNER?

        r = await self._fetch(f"https://www.hltv.org/events/{str(event_id)}/{event_title.replace(' ', '-')}")
        if not r:
            return

        event_date_div = r.find('td', {'class', 'eventdate'}).find_all('span')

        event_start = self._normalize_date(event_date_div[0].text.split())
        event_end = self._normalize_date(event_date_div[1].text.split()[1:-1])

        prize = r.find('td', {'class', 'prizepool text-ellipsis'}).text

        team_num = r.find('td', {'class', 'teamsNumber'}).text

        location = r.find('td', {'class', 'location gtSmartphone-only'}).get_text().replace('\n', '')

        try:
            group_div = r.find('div', {'class', 'groups-container'})
            groups = []
            for group in group_div.find_all('table', {'class': 'table standard-box'}):
                group_name = group.find('td', {'class': 'table-header group-name'}).text
                teams = []
                for team in group.find_all('div', 'text-ellipsis'):
                    teams.append(team.find('a').text)
                groups.append({group_name: teams})
        except AttributeError:
            groups = []

        return event_id, event_title, event_start, event_end, prize, team_num, location, groups

    async def get_top_teams(self, max_teams=30):
        """
        returns a list of the top 1-30 teams
        :params:
        max_teams: int = 30
        :return:
        [('rank','title','points', 'change', 'id')]
        change - difference between last ranking update
        """
        today = date.today()
        current_weekday = today.weekday()
        last_monday = today - timedelta(days=current_weekday)

        teams = []

        r = await self._fetch("https://www.hltv.org/ranking/teams/" + last_monday.strftime('%Y/%B/%d').lower())

        if not r:
            return

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

    async def get_team_info(self, team_id: int | str, title: str) -> tuple | None:
        """
        Returns Information about team
        :params:
        team_id: int | str
        title: str
        :returns:
        (team_id, title, rank, players, coach, age, weeks, last_trophy, total_trophys) | None
        weeks - weeks in top 20
        """
        r = await self._fetch("https://www.hltv.org/team/" + str(team_id) + '/' + title.replace(' ', '-'))
        players = []
        try:
            for player in r.find_all('span', {'class': 'text-ellipsis bold'}):
                players.append(player.text)

            rank = '0'
            weeks = '0'
            age = '0'
            coach = ''

            for i, stat in enumerate(r.find_all('div', {'class': 'profile-team-stat'}), start=1):
                if i == 1:
                    rank = stat.find('a').text[1:]
                elif i == 2:
                    weeks = stat.find('span', {'class': 'right'}).text
                elif i == 3:
                    age = stat.find('span', {'class': 'right'}).text
                elif i == 4:
                    coach = stat.find('span', {'class': 'bold a-default'}).text[1:-1]

            last_trophy = None
            total_trophys = None
            try:
                last_trophy = r.find('div', {'class': 'trophyHolder'}).find('span')['title']
                total_trophys = len(r.find_all('div', {'class': 'trophyHolder'}))
            except AttributeError:
                pass

            return team_id, title, rank, players, coach, age, weeks, last_trophy, total_trophys
        except AttributeError:
            raise AttributeError("Parsing error, probably page not fully loaded")

    async def get_best_players(self, top=40):
        """
        returns a list of the top (1-40) players in top 20 at the year
        :params:
        top: int = 40
        :returns:
        ('rank', 'name', 'team', 'maps', 'rating')
        maps - maps played
        """
        year = datetime.strftime(datetime.utcnow(), '%Y')
        r = await self._fetch(
            f"https://www.hltv.org/stats/players?startDate={year}-01-01&endDate={year}-12-31&rankingFilter=Top20")

        if not r:
            return

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
                    'name': name,
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

    async def get_last_news(self, max_reg_news=2, only_today=True, only_featured=False):
        r = await self._fetch('https://www.hltv.org/')

        today = datetime.now(tz=pytz.timezone('Europe/Copenhagen'))
        article_days = {
            1: today.strftime('%d-%m'),
            2: (today - timedelta(days=1)).strftime('%d-%m'),
            3: 'old'
        }

        news = []
        reg_news_num = 0
        for i, news_date_div in enumerate(r.find_all('div', {'class', 'standard-box standard-list'}), start=1):
            date_ = article_days[i]
            f_news = []
            reg_news = []
            for featured_news_div in news_date_div.find_all('a', {'class': 'newsline article featured breaking-featured'}):
                featured_id = featured_news_div['href'].split('/')[2]
                featured_title = featured_news_div.find('div', {'class': 'featured-newstext'}).text
                featured_description = featured_news_div.find('div', {'class': 'featured-small-newstext'}).text
                f_news.append({
                    'f_id': featured_id,
                    'f_title': featured_title,
                    'f_desc': featured_description,
                })

            if not only_featured and reg_news_num < max_reg_news:
                for news_div in news_date_div.find_all('a',
                                                           {'class': 'newsline article'}):
                    if reg_news_num > max_reg_news:
                        break
                    if news_div['class'] != 'newsline article featured breaking-featured':
                        news_id = news_div['href'].split('/')[2]
                        news_title = news_div.find('div', {'class': 'newstext'}).text
                        news_posted = news_div.find('div', {'class': 'newsrecent'}).text

                        reg_news.append({
                            'id': news_id,
                            'title': news_title,
                            'posted': news_posted,
                        })
                        reg_news_num += 1

            news.append({
                'date': date_,
                'f_news': f_news,
                'news': reg_news,
            })

            if only_today:
                break

        return news


async def test():
    hltv = Hltv(debug=True, timeout=1, max_delay=5, true_session=True, use_proxy=True, proxy_list=['', ''])
    print(await hltv.get_event_matches(7757))
    print(await hltv.get_events())
    print(await hltv.get_event_info(7437, 'betboom-dacha-belgrade-2024-europe-closed-qualifier'))
    print(await hltv.get_event_results(7437))
    print(await hltv.get_upcoming_matches(1, 3))
    print(await hltv.get_match_info('2370913', 'FURIA', 'MOUZ', 'betboom-dacha-belgrade-2024-europe-closed-qualifier'))
    print(await hltv.get_last_news())
    print(await hltv.get_top_teams())
    print(await hltv.get_best_players())

if __name__ == "__main__":
    asyncio.run(test())
