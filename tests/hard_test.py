from typing import Any, Callable

import pytest

from hltv_async_api import Hltv
from hltv_async_api.sync.syncHltv import Hltv as SyncHltv
import logging
import asyncio
import os
import time
import traceback

PROXY_PATH = 'proxies.txt' if os.path.exists('proxies.txt') else None


class HltvHardTest:
    def __init__(self, hltv: Hltv = None, debug: bool = True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(message)s")
        self.errors = 0
        self.success = 0
        self.failures: list[str] = []
        self.matches: int | str = 0
        self.events: int | str = 0
        self.news: int | str = 0
        self.results: int | str = 0
        self.teams: int | str = 0
        self.players: int | str = 0

        self.hltv = hltv
        self.is_async = isinstance(hltv, Hltv)

    async def parse_and_assert(self, coro, expected_keys=None):
        try:
            data = await coro
            self.success += 1
            if expected_keys:
                assert all(key in data for key in expected_keys)
            self.logger.debug(data)
        except Exception as e:
            self.errors += 1
            self.logger.error(f"Error parsing {coro.__name__}: {e}")

    def parse_and_assert_sync(self, func: Callable, expected_keys=None):
        try:
            data = func()
            self.success += 1
            if expected_keys:
                assert all(key in data for key in expected_keys)
            self.logger.debug(data)
        except Exception as e:
            self.errors += 1
            self.logger.error(f"Error parsing {func.__name__}: {e}")

    async def start_test(self):
        start_time = time.time()
        self.logger.info(f'Starting test')

        await asyncio.gather(
            self.parse_and_assert(self.parse_events()),
            self.parse_and_assert(self.parse_matches_results()),
            self.parse_and_assert(self.parse_last_news()),
            self.parse_and_assert(self.parse_players()),
            self.parse_and_assert(self.parse_teams()),
        )
        await self.hltv.close()
        #self.log_results(start_time)
        return round(time.time() - start_time, 4)

    def start_test_sync(self):
        start_time = time.time()
        self.logger.info(f'Starting sync test')

        self.parse_and_assert_sync(self.parse_events_sync)
        self.parse_and_assert_sync(self.parse_matches_results_sync)
        self.parse_and_assert_sync(self.parse_last_news_sync)
        self.parse_and_assert_sync(self.parse_players_sync)
        self.parse_and_assert_sync(self.parse_teams_sync)
        #self.log_results(start_time)
        return round(time.time() - start_time, 4)

    def log_results(self, elapsed):
        self.logger.info(self.matches)
        self.logger.info(self.events)
        self.logger.info(self.teams)
        self.logger.info(self.players)
        self.logger.info(f'ERRORS={self.errors}')
        self.logger.info(f'SUCCESS={self.success}')
        self.logger.info(f'Total parsed={self.success + self.errors}')
        self.logger.info(f'Total time {elapsed}')
        for failure in self.failures:
            self.logger.info(f'FAILED {failure}')

    async def _try(self, what: str, call):
        """Await one library call. Exceptions and empty answers (None) both count as errors and are listed."""
        try:
            result = await call
        except Exception as e:
            self.errors += 1
            self.failures.append(f'{what}: {type(e).__name__}: {e}')
            self.logger.error(f'{what}: {traceback.format_exc()}')
            return None
        if result is None:
            self.errors += 1
            self.failures.append(f'{what}: returned None (fetch failed)')
            return None
        self.success += 1
        self.logger.debug(f'{what}={result}')
        return result

    async def parse_matches_results(self):
        start_time = time.time()
        self.logger.info('Parsing matches')
        matches, results = await asyncio.gather(self._try('matches', self.hltv.get_matches(7, 0)),
                                                self._try('results', self.hltv.get_results(7, 0, 100)))
        items = (matches or []) + (results or [])
        errors_before = self.errors
        await asyncio.gather(*(
            self._try(f'match id={m["id"]} {m["team1"]} vs {m["team2"]}',
                      self.hltv.get_match_info(m['id'], m['team1'], m['team2'], m['event']))
            for m in items if m['team1'] != 'TBD' and m['id']))
        tot = len(items) + 2
        err = self.errors - errors_before + (matches is None) + (results is None)
        self.matches = f'Parsed {tot} matches.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    async def parse_events(self):
        start_time = time.time()
        self.logger.info('Parsing events')
        events = await self._try('events', self.hltv.get_events(max_events=50))
        errors_before = self.errors
        calls = []
        for event in events or []:
            eid, title = event['id'], event['title']
            calls += [self._try(f'event info id={eid} {title}', self.hltv.get_event_info(eid, title)),
                      self._try(f'event matches id={eid} {title}', self.hltv.get_event_matches(eid, 7)),
                      self._try(f'event results id={eid} {title}', self.hltv.get_event_results(eid, 7, max_=100))]
        await asyncio.gather(*calls)
        tot = len(calls) + 1
        self.events = (f'Parsed {tot} events.({round(time.time() - start_time)}s) '
                       f'ERRORS: {self.errors - errors_before + (events is None)}/{tot}')

    async def parse_teams(self):
        self.logger.info('parsing teams')
        start_time = time.time()
        top_teams = await self._try('top teams', self.hltv.get_top_teams(30))
        errors_before = self.errors
        await asyncio.gather(*(self._try(f'team id={t["id"]} {t["title"]}', self.hltv.get_team_info(t['id'], t['title']))
                               for t in top_teams or []))
        tot = len(top_teams or []) + 1
        self.teams = (f'Parsed {tot} teams.({round(time.time() - start_time)}s) '
                      f'ERRORS: {self.errors - errors_before + (top_teams is None)}/{tot}')

    async def parse_players(self):
        start_time = time.time()
        top_players = await self._try('top players', self.hltv.get_top_players(30))
        errors_before = self.errors
        await asyncio.gather(*(self._try(f'player id={p["id"]} {p["nickname"]}',
                                         self.hltv.get_player_info(p['id'], p['nickname']))
                               for p in top_players or []))
        tot = len(top_players or []) + 1
        self.players = (f'Parsed {tot} players.({round(time.time() - start_time)}s) '
                        f'ERRORS: {self.errors - errors_before + (top_players is None)}/{tot}')

    async def parse_last_news(self):
        news = await self.hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            logging.debug(news)
            self.success += 1
        else:
            logging.critical('error parsing news')
            self.errors += 1

    def parse_matches_results_sync(self):
        start_time = time.time()
        tot = 2
        err = 0
        self.logger.info('Parsing matches')

        matches = self.hltv.get_matches(7, 0)
        if not matches:
            err += 1
            self.logger.error('ERROR PARSING MATCHES')
        self.logger.info('Parsing matches')

        results = self.hltv.get_results(7, 0, 100)
        if not results:
            err += 1
            self.logger.error('ERROR PARSING RESULTS')
        matches = (matches or []) + (results or [])

        if matches:
            self.success += 1
            self.logger.debug(matches)
            for match in matches:
                tot += 1
                match_: Any = None
                self.logger.debug(match)
                if match['team1'] != 'TBD' and match['id'] != '0' and match['id'] != 0:
                    try:
                        match_ = self.hltv.get_match_info(match["id"], match['team1'], match['team2'], match['event'])
                        self.logger.debug(f'match={match_}')
                    except Exception as e:
                        self.logger.error(e)
                        err += 1

                    if match_:
                        self.logger.debug(match_)
                        self.success += 1
                    else:
                        self.errors += 1
                        err += 1
        else:
            self.errors += 1
            self.logger.error("error parsing matches")

        self.matches = f'Parsed {tot} matches.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    def parse_events_sync(self):
        start_time = time.time()
        tot = 1
        err = 0
        self.logger.info('Parsing events')

        events = self.hltv.get_events(max_events=50)
        if events:
            logging.debug(events)
            for event in events:
                event_, event_matches, event_results = None, None, None

                try:
                    event_ = self.hltv.get_event_info(event["id"], event["title"])
                    logging.debug(f'event={event_}')
                except Exception as e:
                    self.logger.error(e)
                    self.failures.append(f'event info id={event["id"]} {event["title"]}: {type(e).__name__}: {e}')
                    self.logger.error(f'TYPE: INFO ID={event["id"]} TITLE={event["title"]}')
                    self.errors += 1
                    err += 1
                finally:
                    tot += 1

                if event_:
                    self.success += 1

                try:
                    event_matches = self.hltv.get_event_matches(event['id'], 7)
                    logging.debug(f'event_matches={event_matches}')
                except Exception as e:
                    self.logger.error(e)
                    self.logger.error(f'TYPE: MATCHES ID={event["id"]} TITLE={event["title"]}')
                    self.errors += 1
                    err += 1
                finally:
                    tot += 1

                if event_matches:
                    self.success += 1

                try:
                    event_results = self.hltv.get_event_results(event['id'], 7, max_=100)
                    logging.debug(f'event_results={event_results}')
                except Exception as e:
                    self.logger.error(e)
                    self.logger.error(f'TYPE: RESULTS ID={event["id"]} TITLE={event["title"]}')
                    self.errors += 1
                    err += 1
                finally:
                    tot += 1

                if event_results:
                    self.success += 1
        else:
            logging.critical("error parsing events")

        self.events = f'Parsed {tot} events.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    def parse_teams_sync(self):
        self.logger.info('parsing teams')
        start_time = time.time()
        err = 0
        tot = 1

        top_teams = self.hltv.get_top_teams(30)
        if top_teams:
            logging.debug(top_teams)
            for team in top_teams:
                tot += 1
                team_: Any = None
                try:
                    team_ = self.hltv.get_team_info(team["id"], team['title'])
                    self.success += 1
                except Exception as e:
                    self.logger.error(e)
                    self.logger.debug(team_)
                    self.errors += 1
                    err += 1
        else:
            logging.critical("error parsing top teams")

        self.teams = f'Parsed {tot} teams.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    def parse_players_sync(self):
        start_time = time.time()
        tot = 1
        err = 0

        top_players = self.hltv.get_top_players(30)
        if top_players:
            self.success += 1
            for player in top_players:
                player_ = None
                try:
                    player_ = self.hltv.get_player_info(player['id'], player['nickname'])
                except Exception as e:
                    self.logger.error(e)
                    self.failures.append(f'player id={player["id"]} {player["nickname"]}: {type(e).__name__}: {e}')
                    self.errors += 1
                    err += 1
                finally:
                    tot += 1

                if player_:
                    self.success += 1
                    self.logger.debug(player_)
        else:
            logging.critical('error parsing players')
            self.errors += 1
            err = 0

        self.players = f'Parsed {tot} players.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    def parse_last_news_sync(self):
        news = self.hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            logging.debug(news)
            self.success += 1
        else:
            logging.critical('error parsing news')
            self.errors += 1


@pytest.mark.asyncio
async def main():
    hltv = Hltv(debug=True, max_retries=10, selenium=True, selenium_options={'pool_size': 4})
    test = HltvHardTest(hltv=hltv, debug=True)
    return await test.start_test(), test



@pytest.mark.sync
def sync_test():
    hltv = SyncHltv(debug=True, safe_mode=False, min_delay=0.5, max_delay=2.5, max_retries=10, proxy_path=PROXY_PATH, proxy_delay=bool(PROXY_PATH), selenium=True)
    test = HltvHardTest(hltv=hltv, debug=True)
    return test.start_test_sync(), test


if __name__ == '__main__':
    t1, h1 = asyncio.run(main())
    t2, h2 = sync_test()
    logging.info(f"---")
    logging.info(f"AIO")
    logging.info(f"---")
    h1.log_results(t1)
    logging.info(f"---")
    logging.info(f"SYNC")
    logging.info(f"---")
    h2.log_results(t2)
    logging.info(f"AIO :{t1}s  |  Sync :{t2}s")
