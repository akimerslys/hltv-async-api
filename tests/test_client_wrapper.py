"""Async client: every README method goes fetch -> parse with a stubbed network layer."""

import pytest

from hltv_async_api import Hltv

from . import fixtures as fx


class StubParser:
    """Stands in for Parser: records requested URLs and serves canned pages."""

    def __init__(self, pages):
        self.pages = pages
        self.urls = []

    async def fetch(self, url, delay=0):
        self.urls.append(url)
        for key, html in self.pages.items():
            if key in url:
                return fx.soup(html)
        return None


@pytest.fixture
async def make_hltv():
    clients = []

    def _make(pages, **kw):
        stub = StubParser(pages)
        hltv = Hltv(parser=stub, tz='Europe/Copenhagen', **kw)
        clients.append(hltv)
        return hltv, stub

    yield _make
    for h in clients:
        await h.close()


async def test_get_matches(make_hltv):
    hltv, stub = make_hltv({'/matches': fx.MATCHES})
    res = await hltv.get_matches(days=1)
    assert stub.urls == ['https://www.hltv.org/matches']
    assert res[0]['id'] == '2371201' and res[1]['date'] == '16-04-2024'


async def test_get_match_info(make_hltv):
    hltv, stub = make_hltv({'/matches/': fx.MATCH_OVER})
    res = await hltv.get_match_info(2370931, 'Mouz', 'faze', 'iem chengdu 2024')
    assert stub.urls == ['https://www.hltv.org/matches/2370931/Mouz-vs-faze-iem-chengdu-2024']
    assert res['status'] == 'Match over' and res['stats']


async def test_get_results(make_hltv):
    hltv, stub = make_hltv({'/results': fx.RESULTS})
    res = await hltv.get_results()
    assert stub.urls == ['https://www.hltv.org/results']
    assert res[0]['rating'] == 0 and res[1]['date'] == '14-04-2024'


async def test_get_event_results(make_hltv):
    hltv, stub = make_hltv({'/results?event=': fx.EVENT_RESULTS})
    res = await hltv.get_event_results(7148)
    assert stub.urls == ['https://www.hltv.org/results?event=7148']
    assert len(res) == 2


async def test_get_event_matches(make_hltv):
    hltv, stub = make_hltv({'/matches': fx.EVENT_MATCHES})
    res = await hltv.get_event_matches(7148)
    assert stub.urls == ['https://www.hltv.org/events/7148/matches']
    assert [m['id'] for m in res] == ['2371201', '2370771', '2370775']


async def test_get_events(make_hltv):
    hltv, _ = make_hltv({'/events': fx.EVENTS})
    res = await hltv.get_events(future=False)
    assert [e['id'] for e in res] == ['7749', '7621']


async def test_get_event_info(make_hltv):
    hltv, stub = make_hltv({'/events/': fx.event_info('1710979200000', '1711843200000', True)})
    res = await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024')
    assert stub.urls == ['https://hltv.org/events/7148/PGL-CS2-Major-Copenhagen2024']
    assert res['status'] == 'Finished'


async def test_get_top_teams(make_hltv):
    hltv, stub = make_hltv({'/ranking/teams/': fx.TOP_TEAMS})
    res = await hltv.get_top_teams(2, date_str='2024-04-17')
    assert stub.urls == ['https://www.hltv.org/ranking/teams/2024/april/15']  # snaps back to Monday
    assert [t['title'] for t in res] == ['FaZe', 'Natus Vincere']


async def test_top_teams_url_day_is_not_zero_padded(make_hltv):
    hltv, stub = make_hltv({'/ranking/teams/': fx.TOP_TEAMS})
    await hltv.get_top_teams(2, date_str='2026-10-07')
    assert stub.urls == ['https://www.hltv.org/ranking/teams/2026/october/5']


async def test_get_team_info(make_hltv):
    hltv, stub = make_hltv({'/team/': fx.TEAM_INFO})
    res = await hltv.get_team_info(6667, 'faze')
    assert stub.urls == ['https://www.hltv.org/team/6667/faze']
    assert res['players'] == {'karrigan': 429, 'rain': 8183}


async def test_get_top_players(make_hltv):
    hltv, stub = make_hltv({'/stats/players': fx.top_players()})
    res = await hltv.get_top_players(2, year=2024)
    assert stub.urls == ['https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31'
                         '&rankingFilter=Top20']
    assert [p['nickname'] for p in res] == ['m0nesy', 'broky']


async def test_get_player_info(make_hltv):
    hltv, stub = make_hltv({'/player/': fx.PLAYER_INFO})
    res = await hltv.get_player_info(7998, 's1mple')
    assert stub.urls == ['https://www.hltv.org/player/7998/s1mple']
    assert res['nationality'] == 'Ukraine'


async def test_get_last_news(make_hltv):
    hltv, stub = make_hltv({'hltv.org/': fx.news()})
    res = await hltv.get_last_news(only_today=True)
    assert stub.urls == ['https://www.hltv.org/']
    assert len(res[0]['news']) == 2


async def test_generic_get_dispatch(make_hltv):
    hltv, _ = make_hltv({'/events': fx.EVENTS, '/team/': fx.TEAM_INFO})
    assert (await hltv.get('events'))[0]['id'] == '7749'
    assert (await hltv.get('teams', 6667, 'faze'))['rank'] == '1'


async def test_returns_none_when_fetch_fails(make_hltv):
    hltv, _ = make_hltv({})
    assert await hltv.get_matches() is None
    assert await hltv.get_top_players() is None


async def test_safe_mode_locks_restricted_methods(make_hltv):
    hltv, stub = make_hltv({'/matches': fx.MATCHES}, safe_mode=True)
    assert await hltv.get_matches() is None
    assert stub.urls == []
