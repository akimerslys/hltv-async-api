"""Concurrency, retry pacing, the Selenium browser pool, numeric return types and parser edge cases."""

import asyncio
import logging
import threading
import time

import pytest

from hltv_async_api import Hltv
from hltv_async_api.methods import Events, Matches, Players
from hltv_async_api.selenium_driver import SeleniumParser
from hltv_async_api.types import Client, Executor, Parser
from hltv_async_api.Utils.numbers import to_float, to_int

from . import fixtures as fx
from .test_selenium import PAGE, FakeDriver

OK = '<html><body><div class="ranked-team standard-box"></div></body></html>'


class SlowSession:
    """aiohttp session stand-in that answers after `latency` seconds and records the peak of parallel requests."""

    def __init__(self, latency=0.05, status=200):
        self.latency, self.status = latency, status
        self.active = self.peak = self.calls = 0

    def get(self, url, **kw):
        session = self

        class Ctx:
            async def __aenter__(self):
                session.calls += 1
                session.active += 1
                session.peak = max(session.peak, session.active)
                await asyncio.sleep(session.latency)
                return self

            async def __aexit__(self, *exc):
                session.active -= 1
                return False

            status = session.status

            async def text(self):
                return OK

        return Ctx()


async def make_parser(session, **client_kw):
    logger = logging.getLogger('test-speed')
    client = Client(client_kw.pop('min_delay', None), client_kw.pop('max_delay', None), 1, client_kw.pop('retries', 3),
                    logger=logger, **client_kw)
    await client.session.close()
    client.session = session
    return Parser(client, Executor(loop=asyncio.get_running_loop(), logger=logger), logger), client


async def test_requests_run_in_parallel_up_to_the_cap():
    session = SlowSession(latency=0.05)
    parser, _ = await make_parser(session, max_concurrency=5)
    pages = await asyncio.gather(*(parser.fetch(f'https://www.hltv.org/{i}') for i in range(20)))
    assert all(pages) and session.peak == 5  # five at a time, never more


async def test_zero_concurrency_means_unlimited():
    session = SlowSession(latency=0.02)
    parser, _ = await make_parser(session, max_concurrency=0)
    await asyncio.gather(*(parser.fetch(f'https://www.hltv.org/{i}') for i in range(15)))
    assert session.peak == 15


async def test_default_concurrency_is_ten():
    session = SlowSession(latency=0.02)
    parser, client = await make_parser(session)
    await asyncio.gather(*(parser.fetch(f'https://www.hltv.org/{i}') for i in range(30)))
    assert client.max_concurrency == 10 and session.peak == 10


async def test_retries_do_not_wait_unless_delays_are_configured(monkeypatch):
    sleeps = []
    real_sleep = asyncio.sleep

    async def spy(seconds, *a, **kw):
        if seconds:
            sleeps.append(seconds)
        await real_sleep(0)

    session = SlowSession(latency=0, status=500)
    parser, _ = await make_parser(session)
    monkeypatch.setattr(asyncio, 'sleep', spy)
    assert await parser.fetch('https://www.hltv.org/') is None
    assert session.calls == 2 and sleeps == []  # max_retries=3 -> two real tries, no pause between them


async def test_max_delay_opts_in_to_growing_pause(monkeypatch):
    sleeps = []
    real_sleep = asyncio.sleep

    async def spy(seconds, *a, **kw):
        if seconds:
            sleeps.append(seconds)
        await real_sleep(0)

    session = SlowSession(latency=0, status=500)
    parser, _ = await make_parser(session, max_delay=5, retries=4)
    monkeypatch.setattr(asyncio, 'sleep', spy)
    assert await parser.fetch('https://www.hltv.org/') is None
    assert sleeps == [1, 2]


async def test_session_replaced_after_parser_creation_is_used():
    session = SlowSession(latency=0)
    parser, client = await make_parser(SlowSession(latency=0))
    client.session = session
    assert await parser.fetch('https://www.hltv.org/')
    assert session.calls == 1


async def test_hltv_passes_max_concurrency_to_client():
    hltv = Hltv(max_concurrency=3)
    assert hltv.client.max_concurrency == 3
    await hltv.close()


# --- Selenium pool -----------------------------------------------------------------

class GatedDriver(FakeDriver):
    """get() only returns once `barrier.parties` browsers are loading at the same time."""

    def __init__(self, barrier):
        super().__init__([PAGE])
        self.barrier = barrier

    def get(self, url):
        self.barrier.wait(timeout=5)
        super().get(url)


async def test_selenium_pool_loads_pages_in_parallel():
    barrier = threading.Barrier(2)
    drivers = []

    def factory():
        drivers.append(GatedDriver(barrier))
        return drivers[-1]

    logger = logging.getLogger('test-pool')
    client = Client(None, None, None, 2, logger=logger)
    executor = Executor(loop=asyncio.get_running_loop(), logger=logger)
    parser = SeleniumParser(client, executor, logger, pool_size=2, driver_factory=factory)
    pages = await asyncio.gather(parser.fetch('https://www.hltv.org/a'), parser.fetch('https://www.hltv.org/b'))
    assert all(pages) and len(drivers) == 2 and all(len(d.urls) == 1 for d in drivers)
    await parser.close()
    await client.close_session()
    executor.close()
    assert all(d.quit_called for d in drivers)


async def test_selenium_pool_gives_each_browser_its_own_profile():
    logger = logging.getLogger('test-pool')
    client = Client(None, None, None, 2, logger=logger)
    executor = Executor(loop=asyncio.get_running_loop(), logger=logger)
    parser = SeleniumParser(client, executor, logger, pool_size=3, user_data_dir='profile')
    assert [d.user_data_dir for d, _ in parser._pool] == ['profile', 'profile-1', 'profile-2']
    await parser.close()
    await client.close_session()
    executor.close()


# --- numbers -----------------------------------------------------------------------

@pytest.mark.parametrize('text, expected', [('1,000', 1000), ('+4', 4), ('-1', -1), ('62%', 62), ('bo3', 3),
                                            ('-', 0), ('', 0), (None, 0), ('TBA', 0), (7, 7), ('(939 points)', 939)])
def test_to_int(text, expected):
    assert to_int(text) == expected


@pytest.mark.parametrize('text, expected', [('1.18', 1.18), ('51.2%', 51.2), ('+4.54%', 4.54), ('', 0.0), ('x', 0.0)])
def test_to_float(text, expected):
    assert to_float(text) == expected


def test_numeric_fields_are_numbers(page):
    match = Matches('Europe/Copenhagen').get_match_info(page('match_over'), '2373774', 'a', 'b', 'c')
    assert isinstance(match['id'], int) and isinstance(match['score1'], int) and isinstance(match['score2'], int)
    assert all(isinstance(m['r_team1'], int) and isinstance(m['r_team2'], int) for m in match['maps'])
    assert all(isinstance(s['id'], int) and isinstance(s['adr'], float) and isinstance(s['rating'], float)
               for s in match['stats'])


# --- parser edge cases found while reviewing the hard test -------------------------

def test_event_with_a_single_date_and_no_prize():
    html = ('<table><tr><td class="eventdate"><span data-unix="4070908800000">Jan 1st</span></td>'
            '<td class="location gtSmartphone-only">Online</td></table>')
    info = Events('x').get_event_info(fx.soup(html), '5', 'One day cup')
    assert (info['id'], info['status'], info['start'], info['end']) == (5, 'Upcoming', '01-01-2099', '01-01-2099')
    assert info['prize'] == 'TBA' and info['team_count'] == 'TBA' and info['location'] == 'Online'


def test_event_without_dates_does_not_crash():
    info = Events('x').get_event_info(fx.soup('<div></div>'), 5, 'Mystery')
    assert info['status'] == 'Upcoming' and info['start'] == '' and info['teams'] == []


def test_finished_event_with_tbd_winner_and_unlinked_team():
    html = fx.event_info('1710979200000', '1711843200000', finished=True)
    html = html.replace('<a href="/team/6667/faze">', '<a>')
    info = Events('x').get_event_info(fx.soup(html), 1, 'x')
    assert info['status'] == 'Finished' and 'winners' in info


def test_event_results_skip_rows_without_score():
    html = ('<div class="results-holder"><div class="results-sublist">'
            '<a class="a-reset" href="/matches/1/a-vs-b"><div class="team">A</div></a></div></div>')
    assert Events('x').get_event_results(fx.soup(html), 1) == []


def test_player_without_age_nickname_or_stat_boxes():
    html = ('<div class="playerInfoRow playerAge"><span class="listLeft">Age</span></div>'
            '<div class="all-time-stat">Headshots</div>'
            '<div class="col-6 text-ellipsis">Matches<a class="playerpage-matchbox" href="/matches/x/y"></a></div>')
    info = Players('x').get_player_info(fx.soup(html), '77', 'nick')
    assert info['id'] == 77 and info['name'] == '' and info['age'] == 0 and info['hs'] == 0.0
    assert info['last_matches'] == []
