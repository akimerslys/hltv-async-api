from typing import Any

import pytest

from hltv_async_api import Hltv
import logging
import asyncio
import time


class HltvHardTest:
    def __init__(self, hltv: Hltv = None, debug: bool = True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(message)s")
        self.errors = 0
        self.success = 0
        self.matches: int | str = 0
        self.events: int | str = 0
        self.news: int | str = 0
        self.results: int | str = 0
        self.teams: int | str = 0
        self.players: int | str = 0

        if hltv:
            self.hltv = hltv
        else:
            self.hltv = Hltv(debug=True, timeout=1, max_delay=5)

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

    async def start_test(self):
        start_time = time.time()
        self.logger.info(f'Starting test')

        await asyncio.gather(
            self.parse_and_assert(self.parse_events()),
            self.parse_and_assert(self.parse_matches_results()),
            self.parse_and_assert(self.parse_last_news()),
            self.parse_and_assert(self.parse_top_players()),
            self.parse_and_assert(self.parse_top_teams()),
        )
        await self.hltv.close()
        self.logger.info(self.matches)
        self.logger.info(self.events)
        self.logger.info(self.teams)
        self.logger.info(self.players)
        self.logger.info(f'ERRORS={self.errors}')
        self.logger.info(f'SUCCESS={self.success}')
        self.logger.info(f'Total parsed={self.success + self.errors}')
        self.logger.info(f'Total time {round(time.time() - start_time, 4)}')

        assert self.errors == 0

    async def parse_matches_results(self):
        start_time = time.time()
        tot = 2
        err = 0
        self.logger.info('Parsing matches')
        matches = await self.hltv.get_matches(7, 0)
        if not matches:
            err += 1
            self.logger.error('ERROR PARSING MATCHES')
        self.logger.info('Parsing matches')
        results = await self.hltv.get_results(7, 0, 100)
        if not results:
            err += 1
            self.logger.error('ERROR PARSING RESULTS')
        matches = matches + results
        if matches:
            self.success += 1
            self.logger.debug(matches)
            for match in matches:
                tot += 1
                match_: Any = None
                self.logger.debug(match)
                if match['team1'] != 'TBD' and match['id'] != '0' and match['id'] != 0:
                    try:
                        match_ = await self.hltv.get_match_info(match["id"], match['team1'], match['team2'], match['event'])
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

        self.matches = f'Parsed {tot} matches.({round(time.time()-start_time)}s) ERRORS: {err}/{tot}'

    async def parse_events(self):
        start_time = time.time()
        tot = 1
        err = 0
        self.logger.info('Parsing events')
        events = await self.hltv.get_events(max_events=50)
        if events:
            logging.debug(events)
            for event in events:
                event_, event_matches, event_results = None, None, None

                try:
                    event_ = await self.hltv.get_event_info(event["id"], event["title"])
                    logging.debug(f'event={event_}')

                except Exception as e:
                    self.logger.error(e)
                    self.logger.error(f'TYPE: INFO ID={event["id"]} TITLE={event["title"]}')
                    self.errors += 1
                    err += 1
                finally:
                    tot += 1

                if event_:
                    self.success += 1

                try:
                    event_matches = await self.hltv.get_event_matches(event['id'], 7)
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
                    event_results = await self.hltv.get_event_results(event['id'], 7, max_=100)
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

    async def parse_top_teams(self):
        self.logger.info('parsing teams')
        start_time = time.time()
        err = 0
        tot = 1
        top_teams = await self.hltv.get_top_teams(30)
        if top_teams:
            logging.debug(top_teams)
            for team in top_teams:
                tot += 1
                team_: Any = None
                try:
                    team_ = await self.hltv.get_team_info(team["id"], team['title'])
                    self.success += 1
                except Exception as e:
                    self.logger.error(e)
                    self.logger.debug(team_)
                    self.errors += 1
                    err += 1
        else:
            logging.critical("error parsing top teams")

        self.teams = f'Parsed {tot} teams.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    async def parse_top_players(self):
        start_time = time.time()
        tot = 1
        err = 0
        top_players = await self.hltv.get_top_players(30)
        if top_players:
            self.success += 1
            for player in top_players:
                tot += 1
                try:
                    player_ = await self.hltv.get_player_info(player['id'], player['nickname'])
                    self.success += 1
                except Exception as e:
                    self.logger.error(e)
                    self.logger.debug(player_)
                    self.errors += 1
                    err += 1
        else:
            logging.critical('error parsing players')
            self.errors += 1
            err = 0

        self.players = f'Parsed {tot} players.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    async def parse_last_news(self):
        news = await self.hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            logging.debug(news)
            self.success += 1
        else:
            logging.critical('error parsing news')
            self.errors += 1


@pytest.mark.asyncio
async def main():
    async with Hltv(debug=True, safe_mode=False) as hltv:
        test = HltvHardTest(hltv=hltv, debug=True)
        await test.start_test()


if __name__ == '__main__':
    asyncio.run(main())

