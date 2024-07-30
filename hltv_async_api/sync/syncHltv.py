import logging
import random
import time
from datetime import datetime, date, timedelta
from typing import Optional, Union, List, Any

import pytz
from bs4 import BeautifulSoup

from ..methods import Matches, Teams, Events, Players, News
import requests


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

        self.SAFE = safe_mode
        self._init_safe()
        self.MATCHES = Matches(self)
        self.TEAMS = Teams(self)
        self.EVENTS = Events(self)
        self.PLAYERS = Players(self)
        self.NEWS = News(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

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

    def _checksafe(self):
        if self.SAFE:
            self.logger.error('Safe mode is activated. Function is locked')
            return True

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

    def _parse(self, url, delay):
        proxy = ''
        # setup new proxy, cuz old one was switched
        if self.USE_PROXY:
            proxy = self._get_proxy()
        else:
            # delay, only for non-proxy users. (default = 1-15s)
            time.sleep(delay)
        try:
            response = requests.get(url, headers=self.headers, proxies=proxy, timeout=self.timeout)
            self.logger.info(f"Fetching {url}, code: {response.status_code}")
            if response.status_code == 200:
                result = response.text
                page = self._f(result)
                forbidden = self._cloudflare_check(page)
                if not forbidden:
                    return True, page

                self.logger.debug(f"Error, Code {response.status_code=}")
                return False, self._parse_error_handler(delay)

        except Exception as e:
            self.logger.debug(e)

        delay = self._parse_error_handler(delay)
        return False, delay

    def _fetch(self, url, delay: int = 0):

        status = False
        try_ = 1
        result = None

        # parse until success or not max retries
        while (not status) and (try_ != self.max_retries):
            self.logger.debug(f'Trying connect to {url}, try {try_}/{self.max_retries}')

            # if status = True, result = page,
            # if status = False, result = delay (default=0)
            status, result = self._parse(url, delay)

            if not status and result:
                delay = result
            try_ += 1

        if status:
            return result
        else:
            self.logger.error('Connection failed')
            return None

    def get_matches(self, days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True):
        """returns a list of all upcoming matches on HLTV"""

        if self._checksafe():
            return

        r = self._fetch("https://www.hltv.org/matches")

        if r:
            return self.MATCHES.get_matches(r, days, min_rating, live, future)

    def get_match_info(self, id_: str | int,
                       team1: str,
                       team2: str,
                       event_title: str,
                       stats: bool = True,
                       predicts: bool = True):

        if self._checksafe():
            return

        r = self._fetch(f"https://www.hltv.org/matches/{str(id_)}/"
                        f"{team1.replace(' ', '-')}-vs-"
                        f"{team2.replace(' ', '-')}-"
                        f"{event_title.replace(' ', '-')}")
        if r:
            return self.MATCHES.get_match_info(r, id_, team1, team2, event_title, stats, predicts)

    def get_results(self, days: int = 1,
                    min_rating: int = 1,
                    max: int = 30,
                    featured: bool = True,
                    regular: bool = True) -> list[dict[str, Any]] | None:
        """returns a list of big event matches results"""

        if self._checksafe():
            return

        r = self._fetch("https://www.hltv.org/results")
        if r:
            return self.MATCHES.get_results(r, days, min_rating, max, featured, regular)

    def get_event_results(self, event_id: int | str, days: int = 1, max_: int = 10) -> list[
                                                                                           dict[str, Any]] | None:

        if self._checksafe():
            return

        r = self._fetch("https://www.hltv.org/results?event=" + str(event_id))
        if r:
            return self.EVENTS.get_event_results(r, event_id, days, max_)

    def get_event_matches(self, event_id: str | int, days: int = 1, max_: int = 10):
        r = self._fetch("https://www.hltv.org/events/" + str(event_id) + "/matches")
        if r:
            return self.EVENTS.get_event_matches(r, event_id, days, max_)

    def get_events(self, outgoing=True, future=True, max_events=10):
        """Returns events
        :params:
        outgoing - include live tournaments
        future - include future tournamets
        max_events - use only if future=True
        :return:
        [('id', 'title', 'startdate', 'enddate')]
        """

        r = self._fetch('https://www.hltv.org/events')
        if r:
            return self.EVENTS.get_events(r, outgoing, future, max_events)

    def get_event_info(self, event_id: str | int, event_title: str):
        r = self._fetch(f"https://hltv.org/events/{str(event_id)}/{event_title.replace(' ', '-')}")
        if r:
            return self.EVENTS.get_event_info(r, event_id, event_title)

    def get_top_teams(self, max_teams=30, date_str: str = ''):
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

        r = self._fetch("https://www.hltv.org/ranking/teams/" + last_monday.strftime('%Y/%B/%d').lower())

        if r:
            return self.TEAMS.get_top_teams(r, max_teams)

    def get_team_info(self, team_id: int | str, title: str) -> dict[str, list[str]] | None:
        """
        Returns Information about team
        :params:
        team_id: int | str
        title: str
        :returns:
        (team_id, title, rank, players, coach, age, weeks, last_trophy, total_trophies) | None
        weeks - weeks in top 20
        """
        r = self._fetch("https://www.hltv.org/team/" + str(team_id) + '/' + title.replace(' ', '-'))

        if r:
            return self.TEAMS.get_team_info(r, team_id, title)

    def get_top_players(self, top: int = 40, year: str | int = datetime.strftime(datetime.utcnow(), '%Y')):
        """
        returns a list of the top (1-40) players in top 20 at the year
        :params:
        top: int = 40
        :returns:
        ('rank', 'name', 'team', 'maps', 'rating')
        maps - maps played
        """
        if self._checksafe():
            return

        r = self._fetch(
            f"https://www.hltv.org/stats/players?startDate={year}-01-01&endDate={year}-12-31&rankingFilter=Top20")

        if r:
            return self.PLAYERS.get_top_players(r, top)

    def get_player_info(self, id: int | str, nickname: str):
        r = self._fetch(f'https://www.hltv.org/player/{str(id)}/{nickname}')

        if not r:
            return

        return self.PLAYERS.get_player_info(r, id, nickname)

    def get_last_news(self, max_reg_news=2, only_today=True, only_featured=False):

        r = self._fetch('https://www.hltv.org/')

        if r:
            return self.NEWS.get_last_news(r, max_reg_news, only_today, only_featured)


if __name__ == '__main__':
    hltv = Hltv()
    print(hltv.get_match_info(2373774, 'astralis', 'falcons', 'blast-premier-fall-groups-2024'))
