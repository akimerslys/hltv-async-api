import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Union

import pytz

from hltv_async_api.Methods import Matches, Events, Teams, Players, News
from hltv_async_api.Types import Executor, Client, Parser


class Hltv:
    def __init__(self,
                 min_delay: float | int = None,
                 max_delay: float | int = None,
                 timeout: int = None,
                 max_retries: int = None,
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 proxy_delay: bool = False,
                 proxy_protocol: str | None = None,
                 remove_proxy: bool = False,
                 tz: str | None = None,
                 safe_mode: bool = False,
                 debug: bool = False,
                 ):
        self.DEBUG = debug
        self._configure_logging()
        self.logger = logging.getLogger(__name__)

        self.TIMEZONE = tz
        self._init_tz(tz)

        self.client = Client(min_delay,
                             max_delay,
                             timeout,
                             max_retries,
                             proxy_path,
                             proxy_list,
                             proxy_delay,
                             proxy_protocol,
                             remove_proxy, logger=self.logger)
        self.session = self.client.get_session()
        self.loop = asyncio.get_running_loop()
        self.EXECUTOR = Executor(self.loop)

        self.PARSER = Parser(self.client, self.EXECUTOR, self.logger)

        self.SAFE = safe_mode
        self._init_safe()

        self.MATCHES = Matches(self.TIMEZONE)
        self.EVENTS = Events(self.TIMEZONE)
        self.TEAMS = Teams(self.TIMEZONE)
        self.PLAYERS = Players(self.TIMEZONE)
        self.NEWS = News(self.TIMEZONE)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        if self.session:
            self.logger.debug('Closing Session')
            self.session = None
        if self.EXECUTOR:
            self.EXECUTOR.close()

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

    async def _run(self, func, *args, **kwargs):
        return await self.EXECUTOR.run(func, *args, **kwargs)

    async def _fetch(self, url: str) -> Optional[str]:
        return await self.PARSER.fetch(url, 0)

    """    
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
            #self._init_delay()
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
            with open(self.client.PROXY_PATH, "r") as file:
                self.PROXY_LIST = [line.strip() for line in file.readlines()]
        if safe_mode is not None:
            self.SAFE = safe_mode
            self._init_safe()
            """

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

    def _checksafe(self):
        if self.SAFE:
            self.logger.error('Safe mode is activated. Function is locked')
            return True

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

        if self._checksafe():
            return

        r = await self._fetch("https://www.hltv.org/matches")

        if r:
            return await self._run(self.MATCHES.get_matches, r, days, min_rating, live, future)

    async def get_match_info(self, id_: str | int,
                             team1: str,
                             team2: str,
                             event_title: str,
                             stats: bool = True,
                             predicts: bool = True):
        if self._checksafe():
            return

        r = await self._fetch(f"https://www.hltv.org/matches/{str(id_)}/"
                              f"{team1.replace(' ', '-')}-vs-"
                              f"{team2.replace(' ', '-')}-"
                              f"{event_title.replace(' ', '-')}")
        if r:
            return await self._run(self.MATCHES.get_match_info, r, id_, team1, team2, event_title, stats, predicts)

    async def get_results(self, days: int = 1,
                          min_rating: int = 1,
                          max: int = 30,
                          featured: bool = True,
                          regular: bool = True) -> list[dict[str, Any]] | None:
        """returns a list of big event matches results"""

        if self._checksafe():
            return

        r = await self._fetch("https://www.hltv.org/results")
        if r:
            return await self._run(self.MATCHES.get_results, r, days, min_rating, max, featured, regular)

    async def get_event_results(self, event_id: int | str, days: int = 1, max_: int = 10) -> list[
                                                                                                 dict[str, Any]] | None:

        if self._checksafe():
            return

        r = await self._fetch("https://www.hltv.org/results?event=" + str(event_id))
        if r:
            return await self._run(self.EVENTS.get_event_results, r, event_id, days, max_)

    async def get_event_matches(self, event_id: str | int, days: int = 1):
        r = await self._fetch("https://www.hltv.org/events/" + str(event_id) + "/matches")
        if r:
            return await self._run(self.EVENTS.get_event_matches, r, event_id, days)

    #DELETE ? // repair ??
    """async def get_featured_events(self, max_: int = 1):
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

        return events"""

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
        if r:
            return await self._run(self.EVENTS.get_events, r, outgoing, future, max_events)

    async def get_event_info(self, event_id: str | int, event_title: str):
        r = await self._fetch(f"https://hltv.org/events/{str(event_id)}/{event_title.replace(' ', '-')}")
        if r:
            return await self._run(self.EVENTS.get_event_info, r, event_id, event_title)

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

        r = await self._fetch("https://www.hltv.org/ranking/teams/" + last_monday.strftime('%Y/%B/%d').lower())

        if r:
            return await self._run(self.TEAMS.get_top_teams, r, max_teams)

    async def get_team_info(self, team_id: int | str, title: str) -> dict[str, list[str]] | None:
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

        if r:
            return await self._run(self.TEAMS.get_team_info, r, team_id, title)

    async def get_top_players(self, top: int = 40, year: str | int = datetime.strftime(datetime.utcnow(), '%Y')):
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

        r = await self._fetch(
            f"https://www.hltv.org/stats/players?startDate={year}-01-01&endDate={year}-12-31&rankingFilter=Top20")

        if r:
            return await self._run(self.PLAYERS.get_top_players, r, top)

    async def get_player_info(self, id: int | str, nickname: str):
        r = await self._fetch(f'https://www.hltv.org/player/{str(id)}/{nickname}')

        if not r:
            return

        return await self._run(self.PLAYERS.get_player_info, r, id, nickname)

    async def get_last_news(self, max_reg_news=2, only_today=True, only_featured=False):

        r = await self._fetch('https://www.hltv.org/')

        if r:
            return await self._run(self.NEWS.get_last_news, r, max_reg_news, only_today, only_featured)


if __name__ == '__main__':
    async def main():
        async with Hltv(debug=True, safe_mode=False, min_delay=1, max_delay=3, proxy_delay=True,
                        proxy_protocol='http', max_retries=30) as hltv:
            print(await hltv.get_match_info(2373774, 'astralis', 'falcons', 'blast-premier-fall-groups-2024'))


    asyncio.run(main())
