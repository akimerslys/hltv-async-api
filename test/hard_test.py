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
            self.parse_and_assert(self.parse_matches()),
            self.parse_and_assert(self.parse_last_news()),
            self.parse_and_assert(self.parse_top_players()),
            self.parse_and_assert(self.parse_top_teams()),
        )
        await self.hltv.close()
        self.logger.info(self.matches)
        self.logger.info(self.events)
        self.logger.info(self.teams)
        self.logger.info(f'ERRORS={self.errors}')
        self.logger.info(f'SUCCESS={self.success}')
        self.logger.info(f'Total parsed={self.success + self.errors}')
        self.logger.info(f'Total time {round(time.time() - start_time, 4)}')

        assert self.errors == 0

    async def parse_matches(self):
        start_time = time.time()
        tot = 1
        err = 0
        self.logger.info('Parsing matches')
        matches = await self.hltv.get_matches(1, 1)
        if matches:
            self.success += 1
            logging.debug(matches)
            for match in matches:
                tot += 1
                match_: Any = None
                try:
                    match_ = await self.hltv.get_match_info(match["id"], match['team1'], match['team2'], match['event'])
                except BaseException:
                    pass

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
        events = await self.hltv.get_events()
        if events:
            logging.debug(events)
            for event in events:
                event_: Any = None
                tot += 1
                try:
                    event_ = await self.hltv.get_event_info(event["id"], event["title"])
                    logging.debug(event_)
                except BaseException:
                    pass

                if event_:
                    self.logger.debug(event_)
                    self.success += 1
                else:
                    self.errors += 1
                    err += 1
        else:
            logging.error("error parsing events")

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
                except BaseException:
                    pass
                if team_:
                    self.success += 1
                    logging.debug(team_)
                else:
                    self.errors += 1
                    err += 1
        else:
            logging.error("error parsing top teams")

        self.teams = f'Parsed {tot} teams.({round(time.time() - start_time)}s) ERRORS: {err}/{tot}'

    async def parse_top_players(self):
        top_players = await self.hltv.get_best_players(30)
        if top_players:
            logging.debug(top_players)
            self.success += 1
        else:
            logging.error('error parsing matches')
            self.errors += 1

    async def parse_last_news(self):
        news = await self.hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            logging.debug(news)
            self.success += 1
        else:
            logging.error('error parsing news')
            self.errors += 1


@pytest.mark.asyncio
async def main():
    hltv = Hltv(debug=True)
    test = HltvHardTest(hltv=hltv, debug=True)
    await test.start_test()


if __name__ == '__main__':
    asyncio.run(main())

