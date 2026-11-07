"""Regression tests for edge cases found while reviewing the library."""

import pytest

from hltv_async_api import Hltv
from hltv_async_api.methods import Events, Matches, News, Players
from hltv_async_api.sync.syncHltv import Hltv as SyncHltv
from hltv_async_api.types import Client

from . import fixtures as fx


@pytest.mark.parametrize('text, expected', [
    ('Match over', 0), ('LIVE', 1), ('1d : 2h : 3m : 4s', 2), ('45m : 10s', 2),
    ('Match postponed', 3), ('Match deleted', 3), ('', 3),
])
def test_match_status(text, expected):
    assert Matches._get_match_status(text) == expected


def test_postponed_match_does_not_crash():
    html = '<div class="countdown">Match postponed</div>' + fx._map('TBA')
    info = Matches('Europe/Copenhagen').get_match_info(fx.soup(html), 1, 'a', 'b', 'c')
    assert info['status'] == 'Match postponed'
    assert (info['score1'], info['score2']) == (0, 0)


def test_news_with_more_than_three_day_boxes():
    box = ('<div class="standard-box standard-list"><a class="newsline article" href="/news/1/x">'
           '<div class="newstext">t</div><div class="newsrecent">1 hour ago</div></a></div>')
    res = News('Europe/Copenhagen').get_last_news(fx.soup(box * 5), max_reg_news=5, only_today=False)
    assert [d['date'] for d in res][2:] == ['old', 'old', 'old']


def test_events_page_without_today_tab():
    assert Events('x').get_events(fx.soup('<div class="big-events"></div>'), True, True, 5) == []


def test_event_without_results_yet():
    assert Events('x').get_event_results(fx.soup('<div class="contentCol"></div>'), 1) == []


def test_player_page_with_missing_parts():
    html = ('<div class="playerName"><div class="playerRealname">Some One</div></div>'
            '<div class="player-stat"><span class="statsVal">1.0</span></div>'
            '<div class="trophyRow"><a class="trophy" href="/events/1/x"></a></div>')
    info = Players('x').get_player_info(fx.soup(html), 1, 'x')
    assert info['name'] == 'Some One' and info['rating'] == 0.0 and info['last_trophy'] == ''
    assert (info['team'], info['team_id'], info['nationality'], info['age']) == ('?', 0, '', 0)
    assert info['total_trophies'] == 1 and info['total_mvp'] == 0 and info['last_matches'] == []


def test_player_nationality_from_flag_next_to_name():
    html = ('<div class="header"><img class="flag" title="Ukraine">'
            '<div class="playerName"><div class="playerRealname">Some One</div></div></div>'
            '<img class="flag" title="Brazil">')
    assert Players('x').get_player_info(fx.soup(html), 1, 'x')['nationality'] == 'Ukraine'


def make_client(**kw):
    return Client(None, None, None, None, **kw)


async def test_proxy_list_keeps_blank_entry_as_no_proxy():
    client = make_client(proxy_list=['1.1.1.1:80', '', 'https://2.2.2.2:443'], proxy_protocol='http')
    assert client.PROXY_LIST == ['http://1.1.1.1:80', '', 'https://2.2.2.2:443']
    await client.close_session()


async def test_proxy_file_with_blank_line(tmp_path):
    path = tmp_path / 'proxies.txt'
    path.write_text('1.1.1.1:80\n\n')
    client = make_client(proxy_path=str(path), proxy_protocol='http')
    assert client.PROXY_LIST == ['http://1.1.1.1:80', '']
    await client.close_session()


def test_sync_client_proxy_list_and_own_session():
    a = SyncHltv(proxy_list=['1.1.1.1:80', ''], proxy_protocol='http')
    b = SyncHltv()
    assert a.PROXY_LIST == ['http://1.1.1.1:80', '']
    assert a.session is not b.session


def test_sync_client_sends_proxy_as_requests_mapping(monkeypatch):
    client = SyncHltv(proxy_list=['1.1.1.1:80'], proxy_protocol='http', min_delay=0, max_retries=2)
    seen = {}

    class Response:
        status_code = 200
        text = '<html></html>'

    def fake_get(url, **kw):
        seen.update(kw)
        return Response()

    monkeypatch.setattr(client.session, 'get', fake_get)
    assert client._fetch('https://www.hltv.org/') is not None
    assert seen['proxies'] == {'http': 'http://1.1.1.1:80', 'https': 'http://1.1.1.1:80'}


def test_sync_client_does_not_print_pages(monkeypatch, capsys):
    client = SyncHltv(max_retries=2)

    class Response:
        status_code = 200
        text = '<html>secret page body</html>'

    monkeypatch.setattr(client.session, 'get', lambda url, **kw: Response())
    client._fetch('https://www.hltv.org/')
    assert 'secret page body' not in capsys.readouterr().out


async def test_top_players_year_defaults_to_current_year():
    from datetime import datetime, timezone

    class Stub:
        urls = []

        async def fetch(self, url, delay=0):
            self.urls.append(url)

    stub = Stub()
    hltv = Hltv(parser=stub)
    await hltv.get_top_players()
    await hltv.close()
    assert f'startDate={datetime.now(timezone.utc).year}-01-01' in stub.urls[0]
