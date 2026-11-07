import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

import pytz

from hltv_async_api.methods import Matches, Events, Teams, Players, News, Stats, PlayerStats
from functools import partial
from hltv_async_api.Utils.numbers import to_int
from hltv_async_api.methods.PlayerStats import clutch_variant, multikill_variant, player_url
from hltv_async_api.methods.Stats import BASE_URL, url_slug
from hltv_async_api.types import Client, Executor, Parser


class Hltv:
    def __init__(self,
                 client: Client | None = None,
                 executor: Executor | None = None,
                 parser: Parser | None = None,
                 min_delay: float | int = None,
                 max_delay: float | int = None,
                 timeout: int = None,
                 max_retries: int = None,
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 proxy_delay: bool = False,
                 proxy_protocol: str | None = 'http',
                 remove_proxy: bool = False,
                 tz: str | None = None,
                 safe_mode: bool = False,
                 debug: bool = False,
                 selenium: bool = False,
                 selenium_options: dict | None = None,
                 max_concurrency: int | None = None,
                 ):
        """
        :param selenium: fetch pages with an undetected Chrome driver instead of plain HTTP requests.
            Needs ``pip install hltv-async-api[selenium]`` and Google Chrome. Use it when HLTV answers 403.
        :param selenium_options: keyword arguments for ``hltv_async_api.selenium_driver.SeleniumDriver``
            (headless, version_main, proxy, user_data_dir, challenge_timeout, pool_size, ...).
        :param max_concurrency: requests in flight at once (default 10, 0 = unlimited). Run calls with
            ``asyncio.gather`` to use it.
        :param safe_mode: opt-in. Locks the methods that return restricted data. Off by default.
        """
        self.DEBUG = debug
        self._configure_logging()
        self.logger = logging.getLogger(__name__)
        self.loop = asyncio.get_running_loop()

        self.TIMEZONE = tz
        self._init_tz(tz)

        if client is None:
            client = Client(min_delay,
                            max_delay,
                            timeout,
                            max_retries,
                            proxy_path,
                            proxy_list,
                            proxy_delay,
                            proxy_protocol,
                            remove_proxy, max_concurrency=max_concurrency, logger=self.logger)

        self.client = client
        self.session = self.client.get_session()

        if executor is None:
            executor = Executor(loop=self.loop, logger=self.logger)

        self.EXECUTOR = executor

        if parser is None:
            if selenium:
                from hltv_async_api.selenium_driver import SeleniumParser
                parser = SeleniumParser(self.client, self.EXECUTOR, self.logger, **(selenium_options or {}))
            else:
                parser = Parser(self.client, self.EXECUTOR, self.logger)

        self.PARSER = parser
        self._live: list = []

        self.SAFE = safe_mode
        self._init_safe()

        self.MATCHES = Matches(self.TIMEZONE)
        self.EVENTS = Events(self.TIMEZONE)
        self.TEAMS = Teams(self.TIMEZONE)
        self.PLAYERS = Players(self.TIMEZONE)
        self.NEWS = News(self.TIMEZONE)
        self.STATS = Stats(self.TIMEZONE)
        self.PLAYER_STATS = PlayerStats(self.TIMEZONE)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        for live in list(self._live):
            await live.close()
        self._live.clear()
        if self.session:
            self.logger.debug('Closing Session')
            await self.client.session.close()
            self.session = None
        if hasattr(self.PARSER, 'close'):
            await self.PARSER.close()
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

    async def _live_identity(self, options: dict):
        """With the Selenium driver, reuse the browser's cookies and User-Agent for the socket."""
        getter = getattr(self.PARSER, 'browser_identity', None)
        if getter is None:
            return
        cookies, agent = await getter()
        if cookies:
            options.setdefault('cookies', cookies)
        if agent:
            options.setdefault('user_agent', agent)

    async def get_match_data(self, match_id: str | int, timeout: float = 15, settle: float = 1.0, **live_options):
        """One-shot live data of a match from HLTV's scorebot socket.

        Needs ``pip install "hltv-async-api[live]"``. Returns ``{'match_id', 'score', 'scoreboard', 'log'}`` or None
        when the match is not live / nothing arrived within ``timeout`` seconds. ``live_options`` go to
        ``hltv_async_api.live.LiveMatch`` (cookies, user_agent, ...).
        """
        if self._checksafe():
            return

        from hltv_async_api.live import LiveConnectionError, fetch_match_data
        await self._live_identity(live_options)
        try:
            return await fetch_match_data(match_id, timeout, settle, logger=self.logger, **live_options)
        except LiveConnectionError as e:
            self.logger.error(e)

    async def live_match(self, match_id: str | int, on_event=None, **live_options):
        """Open a continuous live subscription and return a connected ``LiveMatch``.

        ``on_event(event, data)`` is called for every socket event, or iterate ``async for event, data in
        live.updates()``. It is closed by ``live.close()`` or ``Hltv.close()``.
        """
        if self._checksafe():
            return

        from hltv_async_api.live import LiveConnectionError, LiveMatch
        await self._live_identity(live_options)
        live = LiveMatch(match_id, on_event=on_event, logger=self.logger, **live_options)
        try:
            await live.start()
        except LiveConnectionError as e:
            self.logger.error(e)
            return None
        self._live.append(live)
        return live

    async def get_map_stats(self, map_stats_id: str | int, team1: str = 'team', team2: str = 'team'):
        """Detailed statistics of one map of a finished match (``/stats/matches/mapstatsid/<id>/...``).

        ``map_stats_id`` is the ``stats_id`` of an entry of ``get_match_info(...)['maps']``. The team names only
        build the URL, HLTV ignores them.
        """
        r = await self._fetch(f"{BASE_URL}/stats/matches/mapstatsid/{int(map_stats_id)}/{url_slug(team1)}-vs-{url_slug(team2)}")
        if r:
            data = await self._run(self.STATS.get_stats_page, r)
            data.pop('maps', None)
            return {'stats_id': int(map_stats_id), **data}

    async def get_match_stats(self, stats_id: str | int, team1: str = 'team', team2: str = 'team'):
        """Detailed statistics of a finished match: the overview of all maps plus every map, fetched in parallel.

        ``stats_id`` is the ``stats_id`` of ``get_match_info``. Returns the overview page with a ``maps`` list in which every
        map carries its own full statistics (``available`` is False for a map whose page could not be loaded).
        """
        r = await self._fetch(f"{BASE_URL}/stats/matches/{int(stats_id)}/{url_slug(team1)}-vs-{url_slug(team2)}")
        if not r:
            return None
        data = await self._run(self.STATS.get_stats_page, r)
        tiles = data.pop('maps')

        async def load(tile):
            page = await self._fetch(BASE_URL + tile['href'])
            if not page:
                return {**tile, 'available': False}
            parsed = await self._run(self.STATS.get_stats_page, page)
            parsed.pop('maps', None)
            return {**tile, **parsed, 'available': True}

        data['maps'] = list(await asyncio.gather(*(load(t) for t in tiles)))
        return {'stats_id': int(stats_id), **data}

    async def get_stats_for_match(self, id_: str | int, team1: str, team2: str, event_title: str):
        """``get_match_info`` + ``get_match_stats`` in one call. None while the match has no statistics yet."""
        info = await self.get_match_info(id_, team1, team2, event_title, stats=False, predicts=False)
        if not info or not info.get('stats_id'):
            return None
        return await self.get_match_stats(info['stats_id'], team1, team2)

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

    async def get_event_matches(self, event_id: str | int, days: int = 1, max_: int = 10):
        r = await self._fetch("https://www.hltv.org/events/" + str(event_id) + "/matches")
        if r:
            return await self._run(self.EVENTS.get_event_matches, r, event_id, days, max_)

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

        r = await self._fetch("https://www.hltv.org/ranking/teams/" + last_monday.strftime('%Y/%B/').lower() + str(last_monday.day))

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

    async def get_top_players(self, top: int = 40, year: str | int | None = None):
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

        if year is None:
            year = datetime.now(pytz.utc).year

        r = await self._fetch(
            f"https://www.hltv.org/stats/players?startDate={year}-01-01&endDate={year}-12-31&rankingFilter=Top20")

        if r:
            return await self._run(self.PLAYERS.get_top_players, r, top)

    async def get_player_info(self, id: int | str, nickname: str):
        r = await self._fetch(f'https://www.hltv.org/player/{str(id)}/{nickname}')

        if not r:
            return

        return await self._run(self.PLAYERS.get_player_info, r, id, nickname)

    async def _player_page(self, parse, page: str, player_id, nickname, variant=None, **filters):
        url = player_url(page, player_id, nickname, variant, **filters)
        r = await self._fetch(url)
        if r:
            data = await self._run(parse, r)
            return {'player_id': int(player_id), 'url': url, **data}

    async def get_player_stats(self, player_id: int | str, nickname: str, **filters):
        """Statistics overview of a player (``/stats/players/<id>``): ratings, summary, the seven role scores with
        every metric per side, similar players, ratings against top opponents and teammates.

        ``filters`` (all optional): ``cs_version`` ('CS2' by default, 'CSGO' or None for both), ``map``, ``match_type``,
        ``start_date`` / ``end_date``, ``ranking`` (5-50), ``best_of``, ``ranked``, ``playoff``, ``team_id``,
        ``opponent_team``, ``event``. Every ``get_player_*`` method below takes the same filters.
        """
        return await self._player_page(self.PLAYER_STATS.get_player_overview, 'overview', player_id, nickname, **filters)

    async def get_player_advanced(self, player_id: int | str, nickname: str, **filters):
        """Advanced statistics: round swing, impact, dueling, round-to-round and map-to-map figures."""
        return await self._player_page(self.PLAYER_STATS.get_player_advanced, 'advanced', player_id, nickname, **filters)

    async def get_player_matches(self, player_id: int | str, nickname: str, offset: int = 0, **filters):
        """Match history (100 maps per page, use ``offset=100`` for the next page)."""
        return await self._player_page(self.PLAYER_STATS.get_player_matches, 'matches', player_id, nickname,
                                       offset=offset, **filters)

    async def get_player_events(self, player_id: int | str, nickname: str, **filters):
        """Every event the player played: placement, maps, KPR / DPR, rating."""
        return await self._player_page(self.PLAYER_STATS.get_player_events, 'events', player_id, nickname, **filters)

    async def get_player_career(self, player_id: int | str, nickname: str, **filters):
        """Rating and maps per year, online / LAN / majors."""
        return await self._player_page(self.PLAYER_STATS.get_player_career, 'career', player_id, nickname, **filters)

    async def get_player_weapons(self, player_id: int | str, nickname: str, **filters):
        """Kills by weapon type, weapons carried and kills per weapon."""
        return await self._player_page(self.PLAYER_STATS.get_player_weapons, 'weapon', player_id, nickname, **filters)

    async def get_player_clutches(self, player_id: int | str, nickname: str, size: int | str = 'all',
                                  offset: int = 0, **filters):
        """Clutch history. ``size``: 'all' or 1-5 (1 on 1 ... 1 on 5)."""
        return await self._player_page(partial(self.PLAYER_STATS.get_player_clutches, size=to_int(clutch_variant(size)[-1:], 0)), 'clutches', player_id, nickname,
                                       clutch_variant(size), offset=offset, **filters)

    async def get_player_multikills(self, player_id: int | str, nickname: str, kills: int | str = 2,
                                    fast: bool = False, offset: int = 0, **filters):
        """Multi-kill history. ``kills``: 'all' or 2-5; ``fast=True`` keeps fast multi-kills only."""
        return await self._player_page(self.PLAYER_STATS.get_player_multikills, 'multikills', player_id, nickname,
                                       multikill_variant(kills), offset=offset, fast=fast, **filters)

    async def get_player_opponents(self, player_id: int | str, nickname: str, **filters):
        """Results against every team the player has met."""
        return await self._player_page(self.PLAYER_STATS.get_player_opponents, 'opponents', player_id, nickname, **filters)

    async def get_player_full_stats(self, player_id: int | str, nickname: str, **filters):
        """Overview, advanced, matches, events, career and weapons in one call (fetched in parallel).
        A section whose page could not be loaded is None."""
        names = ('overview', 'advanced', 'matches', 'events', 'career', 'weapons')
        calls = (self.get_player_stats, self.get_player_advanced, self.get_player_matches, self.get_player_events,
                 self.get_player_career, self.get_player_weapons)
        results = await asyncio.gather(*(call(player_id, nickname, **filters) for call in calls))
        return {'player_id': int(player_id), **dict(zip(names, results))}

    async def get_last_news(self, max_reg_news=2, only_today=True, only_featured=False):

        r = await self._fetch('https://www.hltv.org/')

        if r:
            return await self._run(self.NEWS.get_last_news, r, max_reg_news, only_today, only_featured)


if __name__ == '__main__':
    import random
    async def main():
        async with Hltv(debug=True, safe_mode=False, min_delay=1, max_delay=3,
                        max_retries=10, selenium=True) as hltv:
            print(await hltv.get_match_info(2373774, 'astralis', 'falcons', 'blast-premier-fall-groups-2024'))
            live = await hltv.live_match(2400134, on_event=lambda event, data: print(event, data))
            # or iterate:
            async for event, data in live.updates():
                if event == 'score':
                    print(data['current_map']['scores'])
            await live.close()  # also done by hltv.close()


    asyncio.run(main())
