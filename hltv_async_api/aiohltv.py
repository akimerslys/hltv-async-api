import pytz
import asyncio
import re
import logging
import random
from typing import Any, List, Optional, Union
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
from functools import partial
from aiohttp import ClientSession


class Hltv:
    def __init__(self,
                 min_delay: float | int = -1.0,
                 max_delay: float | int = 10.0,
                 timeout: int = 5,
                 max_retries: int = 10,
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 proxy_delay: bool = False,
                 proxy_protocol: str | None = None,
                 remove_proxy: bool = False,
                 tz: str | None = None,
                 safe_mode: bool = False,
                 debug: bool = False,
                 ):
        self.headers = {
            "referer": "https://www.hltv.org/stats",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "hltvTimeZone": "Europe/Copenhagen"
        }
        self.DEBUG = debug
        self._configure_logging()
        self.logger = logging.getLogger(__name__)

        self.MIN_DELAY = float(min_delay)
        self.MAX_DELAY = float(max_delay)
        self._init_delay()

        self.timeout = timeout
        self.max_retries = max_retries

        self.TIMEZONE = tz
        self._init_tz(tz)

        self.PROXY_PATH = proxy_path
        self.PROXY_LIST = proxy_list
        self.PROXY_PROTOCOL = proxy_protocol
        self.PROXY_ONCE = remove_proxy
        self.PROXY_DELAY = proxy_delay

        self.USE_PROXY = proxy_path or proxy_list
        if self.USE_PROXY:
            if self.PROXY_PATH:
                with open(self.PROXY_PATH, "r") as file:
                    self.PROXY_LIST = [line.strip() for line in file.readlines()]
            if self.PROXY_PROTOCOL:
                self.PROXY_LIST = [self.PROXY_PROTOCOL + '://' + proxy for proxy in self.PROXY_LIST]

        self.session = None
        self.loop = asyncio.get_running_loop()

        self.SAFE = safe_mode
        self._init_safe()

    async def __aenter__(self):
        self._create_session()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def _create_session(self):
        if not self.session:
            self.logger.debug('Creating Session')
            self.session = ClientSession()

    async def close(self):
        if self.session:
            self.logger.debug('Closing Session')
            await self.session.close()
            self.session = None

    def _configure_logging(self):
        def get_logger(name, **kwargs):
            import logging

            logging.basicConfig(**kwargs)
            logger = logging.getLogger(name)
            logger.debug(f"start logging '{name}'")
            return logger

        self.logger = get_logger(
            __name__,
            **{
                "level": "DEBUG" if self.DEBUG else "INFO",
                "format": "[%(levelname)s] | %(message)s ",
            },
        )

    def config(
            self,
            min_delay: Optional[Union[float, int]],
            max_delay: Optional[Union[float, int]],
            timeout: Optional[int],
            use_proxy: Optional[bool],
            proxy_file_path: Optional[str],
            proxy_list: Optional[List[str]],
            debug: Optional[bool],
            max_retries: Optional[int],
            proxy_protocol: Optional[str],
            remove_proxy: Optional[bool],
            tz: Optional[str],
            safe_mode: Optional[bool],
    ) -> None:
        if min_delay or max_delay:
            self.MIN_DELAY = float(min_delay)
            self.MAX_DELAY = float(max_delay)
            self._init_delay()
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
        if remove_proxy is not None:
            self.PROXY_ONCE = remove_proxy
        if tz is not None:
            self.TIMEZONE = tz
            self._init_tz()
        if debug is not None:
            self.DEBUG = debug
            self._configure_logging()
        if proxy_file_path:
            with open(self.PROXY_PATH, "r") as file:
                self.PROXY_LIST = [line.strip() for line in file.readlines()]
        if safe_mode is not None:
            self.SAFE = safe_mode
            self._init_safe()

    def _init_tz(self, tz: str | None = None):
        if tz:
            try:
                pytz.timezone(self.TIMEZONE)
            except pytz.exceptions.UnknownTimeZoneError:
                self.logger.error('UnknownTimeZoneError, Using default timezone: Europe/Copenhagen')
                self.TIMEZONE = None

    def _init_safe(self):
        if not self.SAFE:
            self.logger.debug('Safe mode deactivated.')

    def _init_delay(self):
        if self.MIN_DELAY != -1.0:
            if self.MAX_DELAY >= self.MIN_DELAY >= 0.0 and self.MAX_DELAY >= 0.0:
                return
            self.logger.warning(f'Invalid min/max delay. Delay will be increasing by 1 sec')
        self.MIN_DELAY = None

    def _get_proxy(self):
        try:
            proxy = self.PROXY_LIST[0]

            if self.PROXY_PROTOCOL and proxy != '' and self.PROXY_PROTOCOL not in proxy:
                proxy = self.PROXY_PROTOCOL + '://' + proxy

            return proxy
        except IndexError:
            self.logger.error('No proxies left')

    def _switch_proxy(self):
        try:
            if self.PROXY_ONCE:
                self.logger.debug(f'Removing proxy {self.PROXY_LIST[0]}')
                self.PROXY_LIST = self.PROXY_LIST[1:]
            else:
                self.logger.debug(f"Switching proxy {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")
                self.PROXY_LIST = self.PROXY_LIST[1:] + [(self.PROXY_LIST[0])]
                self.logger.info(f"New proxy: {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")
        except IndexError:
            self.logger.error('No proxies left')

    @staticmethod
    def _f(result):
        return BeautifulSoup(result, "lxml")

    def _cloudflare_check(self, page) -> bool:
        challenge_page = page.find(id="challenge-error-title")
        if challenge_page is not None:
            if "Enable JavaScript and cookies to continue" in challenge_page.get_text().strip():
                self.logger.debug("Got cloudflare challenge page")
                return True
        return False

    def _parse_error_handler(self, delay: int = 0) -> int:
        if self.USE_PROXY:
            self._switch_proxy()
            if not self.PROXY_DELAY:
                return 0

        if self.MIN_DELAY:
            delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
            self.logger.debug(f'Random delay {round(delay, 2)}s')
        else:
            if delay < self.MAX_DELAY:
                delay += 1
                self.logger.info(f"Increasing delay to {delay}s")

        return delay

    async def _parse(self, url, delay):
        proxy = ''
        # setup new proxy, cuz old one was switched
        if self.USE_PROXY:
            proxy = self._get_proxy()
        else:
            # delay, only for non-proxy users. (default = 1-15s)
            await asyncio.sleep(delay)
        try:
            async with self.session.get(url, headers=self.headers, proxy=proxy, timeout=self.timeout) as response:
                self.logger.info(f"Fetching {url}, code: {response.status}")
                if response.status == 200:
                    result = await response.text()
                    page = await self.loop.run_in_executor(None, partial(self._f, result))
                    forbitten = await self.loop.run_in_executor(None, partial(self._cloudflare_check, page))
                    if not forbitten:
                        return True, page

                self.logger.debug(f"Error, Code {response.status=}")
                return False, await self.loop.run_in_executor(None, partial(self._parse_error_handler, delay))

        except Exception as e:
            self.logger.debug(e)


        delay = self._parse_error_handler(delay)
        return False, delay

    async def _fetch(self, url, delay: int = 0):
        if not self.session:
            self._create_session()
        status = False
        try_ = 1
        result = None

        # parse until success or not max retries
        while (not status) and (try_ != self.max_retries):
            self.logger.debug(f'Trying connect to {url}, try {try_}/{self.max_retries}')

            # if status = True, result = page,
            # if status = False, result = delay (default=0)
            status, result = await self._parse(url, delay)

            if not status and result:
                delay = result
            try_ += 1

        if status:
            return result
        else:
            self.logger.error('Connection failed')
            return None

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

    @staticmethod
    def __normalize_date(date_) -> str:
        words = date_.split()
        num = ''.join(c for c in words[-2] if c.isdigit())
        date_string = words[-3] + num + words[-1]
        date = datetime.strptime(date_string, "%B%d%Y")
        return date.strftime("%d-%m-%Y")

    def _localize_datetime_to_timezone(self, date_: datetime = None, date_str: str = None) -> datetime:
        if not self.TIMEZONE:
            return date_
        if date_str:
            date_ = datetime.strptime(date_str, '%d-%m-%Y')
        if date_.tzinfo:
            return date_.astimezone(pytz.timezone(self.TIMEZONE))

        return pytz.timezone('Europe/Copenhagen').localize(date_).astimezone(pytz.timezone(self.TIMEZONE))

    async def get(self, type: str, id: int | str | None = None,
                  title: str | None = None,
                  team1: str | None = None,
                  team2: str | None = None):
        if type == 'events':
            if id:
                return await self.get_event_info(id, title)
            else:
                return await self.get_events()
        elif type == 'matches':
            if id:
                return await self.get_match_info(id, team1, team2, title)
            else:
                return await self.get_matches()
        elif type == 'news':
            return await self.get_last_news()
        elif type == 'teams':
            if id:
                return await self.get_team_info(id, title)
            else:
                return await self.get_top_teams()

    async def get_matches(self, days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True):
        """returns a list of all upcoming matches on HLTV"""

        if self.SAFE:
            self.logger.error('This function is not safe. Switch safe_mode to False to use this function')
            return

        r = await self._fetch("https://www.hltv.org/matches")
        if not r:
            return

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
                        dtime = self._localize_datetime_to_timezone(date_=dtime_)
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

    async def get_match_info(self, id: str | int,
                             team1: str,
                             team2: str,
                             event_title: str,
                             stats: bool = True,
                             predicts: bool = True):
        if self.SAFE:
            self.logger.error('This function is not safe. Switch safe-mode to False to use this function')
            return

        r = await self._fetch(f"https://www.hltv.org/matches/{str(id)}/"
                              f"{team1.replace(' ', '-')}-vs-"
                              f"{team2.replace(' ', '-')}-"
                              f"{event_title.replace(' ', '-')}")
        if not r:
            return
        status_ = {'Match over': 0, 'LIVE': 1}
        status = r.find('div', {'class': 'countdown'}).text
        status_int = status_[status] if status in status_ else 2

        match_info = {'id': id}

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

            status = self._localize_datetime_to_timezone(date_=date_).strftime('%d-%m-%Y-%H-%M')

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

    async def get_results(self, days: int = 1,
                          min_rating: int = 1,
                          max: int = 30,
                          featured: bool = True,
                          regular: bool = True) -> list[dict[str, Any]] | None:
        """returns a list of big event matches results"""

        if self.SAFE:
            self.logger.error('This function is not safe. Switch safe-mode to False to use this function')
            return

        r = await self._fetch("https://www.hltv.org/results")
        if not r:
            return

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
                    date__ = self.__normalize_date(date_div.find('span', class_='standard-headline').text)
                    date = self._localize_datetime_to_timezone(date_str=date__).strftime('%d-%m-%Y')
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

    async def get_event_results(self, event_id: int | str, days: int = 1, max_: int = 10) -> list[
                                                                                                 dict[str, Any]] | None:

        if self.SAFE:
            self.logger.error('This function is not safe. Switch safe-mode to False to use this function')
            return

        r = await self._fetch("https://www.hltv.org/results?event=" + str(event_id))
        if not r:
            return

        match_results = []

        n = 0
        for i, result in enumerate(
                r.find("div", {'class', 'results-holder'}).find_all("div", {'class', 'results-sublist'}), start=1):
            if i > days or n > max_:
                break
            try:
                date_ = self.__normalize_date(result.find("span", class_="standard-headline").text.strip())
                date = self._localize_datetime_to_timezone(date_str=date_).strftime("%d-%m-%Y")
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

    async def get_event_matches(self, event_id: str | int, days: int = 1):
        r = await self._fetch("https://www.hltv.org/events/" + str(event_id) + "/matches")
        if not r:
            return

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

    #DELETE ?
    async def get_featured_events(self, max_: int = 1):
        r = await self._fetch('https://www.hltv.org/events')

        events = []
        try:
            for i, event in enumerate(r.find('div', {'class': 'tab-content', 'id': 'FEATURED'}).find_all('a', {
                'class': 'a-reset ongoing-event'}), start=1):
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
                    'title': event_name,
                    'start_date': event_start_date,
                    'end_date': event_end_date,
                })
        except AttributeError:
            pass

        return events

    async def get_events(self, outgoing=True, future=True, max_events=10):
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
        r = await self._fetch(f"https://hltv.org/events/{str(event_id)}/{event_title.replace(' ', '-')}")
        if not r:
            return

        event = {'id': event_id, 'title': event_title}

        def event_date_process(start_date, end_date):
            current_date = datetime.now()
            st = 0      # Finished
            if current_date < start_date:
                st = 2  # Upcoming
            elif start_date <= current_date <= end_date:
                st = 1  # Ongoing

            return start_date.strftime('%d-%m-%Y'), end_date.strftime('%d-%m-%Y'), st

        date_unix_values = [int(span.get('data-unix')[:-3])
                            for span in r.find('td', {'class', 'eventdate'}).find_all('span') if span.get('data-unix')]
        event['start'], event['end'], event_status = event_date_process(datetime.utcfromtimestamp(date_unix_values[0]), datetime.utcfromtimestamp(date_unix_values[1]))
        status_d = {0: 'Finished', 1: 'Ongoing', 2: 'Upcoming'}
        event['status'] = status_d[event_status]

        event['prize'] = r.find('td', {'class', 'prizepool text-ellipsis'}).text if r.find('td', {'class', 'prizepool text-ellipsis'}).text else 'TBA'

        event['team_count'] = r.find('td', {'class', 'teamsNumber'}).text if r.find('td', {'class', 'teamsNumber'}).text else 'TBA'

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

    async def get_top_teams(self, max_teams=30, date_str: str = ''):
        """
        returns a list of the top 1-30 teams
        :params:
        max_teams: int = 30
        :return:
        [('rank','title','points', 'change', 'id')]
        change - difference between last ranking update
        """
        day = datetime.strptime(date_str, "%Y-%m-%d") if date_str else date.today()

        current_weekday = day.weekday()
        last_monday = day - timedelta(days=current_weekday)

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

    async def get_team_info(self, team_id: int | str, title: str) -> dict[str, list[str]]:
        """
        Returns Information about team
        :params:
        team_id: int | str
        title: str
        :returns:
        (team_id, title, rank, players, coach, age, weeks, last_trophy, total_trophies) | None
        weeks - weeks in top 20
        """
        r = await self._fetch("https://www.hltv.org/team/" + str(team_id) + '/' + title.replace(' ', '-'))
        players = {}
        try:
            known_players = r.find('div', class_='bodyshot-team g-grid').find_all('a')
            players = {player.find('span', {'class': 'text-ellipsis bold'}).text: int(player['href'].split('/')[2]) for
                       player in known_players}

            #unknown_players = {'unknown' + str(i): 0 for i in range(len(players) + 1, 6)}
            #players.update(unknown_players)

            rank = '0'
            weeks = '0'
            age = '0'
            coach = ''

            for i, stat in enumerate(r.find_all('div', {'class': 'profile-team-stat'}), start=1):
                try:
                    if i == 1:
                        rank = stat.find('a').text[1:]
                    elif i == 2:
                        weeks = stat.find('span', {'class': 'right'}).text
                    elif i == 3:
                        age = stat.find('span', {'class': 'right'}).text
                    elif i == 4:
                        coach = stat.find('span', {'class': 'bold a-default'}).text[1:-1]
                except AttributeError:
                    pass

            last_trophy = None
            total_trophies = None
            try:
                last_trophy = r.find('div', {'class': 'trophyHolder'}).find('span')['title']
                total_trophies = len(r.find_all('div', {'class': 'trophyHolder'}))
            except AttributeError:
                pass

            return {'id': team_id,
                    'title': title,
                    'rank': rank,
                    'players': players,
                    'coach': coach,
                    'age': age,
                    'weekstop30': weeks,
                    'last_trophy': last_trophy,
                    'total_trophies': total_trophies}
        except AttributeError:
            raise AttributeError("Parsing error, probably page not fully loaded")

    async def get_top_players(self, top: int = 40, year: str | int = datetime.strftime(datetime.utcnow(), '%Y')):
        """
        returns a list of the top (1-40) players in top 20 at the year
        :params:
        top: int = 40
        :returns:
        ('rank', 'name', 'team', 'maps', 'rating')
        maps - maps played
        """
        if self.SAFE:
            self.logger.error('This function is not safe. Switch safe_mode to False to use this function')
            return

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

    async def get_player_info(self, id: int | str, nickname: str):
        r = await self._fetch(f'https://www.hltv.org/player/{str(id)}/{nickname}')

        name_div = r.find('div', class_='playerRealname')
        name = name_div.get_text().strip()
        nationality = name_div.find('img')['title']

        try:
            team_div = r.find('div', class_='playerInfoRow playerTeam').find('a')
            team_str = team_div.get_text().strip()
            team_id = int(team_div['href'].split('/', 3)[2])
        except (AttributeError, TypeError):
            team_str = 'None'
            team_id = 0

        age = int(
            r.find('div', class_='playerInfoRow playerAge').find('span', class_='listRight').get_text().strip().split()[
                0])

        rating_div = r.find('div', class_='playerpage-container').find_all('span', class_='statsVal')
        rating = rating_div[0].get_text().strip()
        kpr = rating_div[1].get_text().strip()
        hs = rating_div[2].get_text().strip()

        mvps = 0
        last_trophy = ''
        try:
            trophies_div = r.find('div', class_='trophyRow').find_all(class_='trophy')
            total_trophies = len(trophies_div)

            # Find last trophy
            last_trophy = ''
            for trophy in trophies_div:
                try:
                    if trophy['href'] and 'events' in trophy['href']:
                        last_trophy = trophy.find('span', class_='trophyDescription')['title']
                        break
                except (KeyError, TypeError):
                    pass

            # Find MVPs
            try:
                mvps = int(trophies_div[0].find('div', class_='mvp-count').text)
            except (IndexError, AttributeError, ValueError):
                mvps = 0

        except Exception:
            total_trophies = 0

        matches = []
        matches_div = r.find_all('div', class_='col-6 text-ellipsis')[1]
        for match in matches_div.find_all('a'):
            matches.append(match['href'].split('/', 4)[3])

        return {'id': int(id),
                'nickname': nickname,
                'team': team_str,
                'team_id': team_id,
                'name': name,
                'nationality': nationality,
                'age': age,
                'rating': rating,
                'kpr': kpr,
                'hs': hs,
                'last_matches': matches,
                'last_trophy': last_trophy,
                'total_trophies': total_trophies,
                'total_mvps': mvps,
                }

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
            for featured_news_div in news_date_div.find_all('a',
                                                            {'class': 'newsline article featured breaking-featured'}):
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


async def main():
    async with Hltv(debug=True, safe_mode=False, min_delay=1, max_delay=1, proxy_path='proxies.txt', proxy_delay=True,
                    proxy_protocol='http') as hltv:
        await hltv.get_top_players(30)


if __name__ == '__main__':
    asyncio.run(main())
