"""Detailed match / map statistics: parser, client methods (async and sync) and the stats ids on the match page."""

import pytest

from hltv_async_api import Hltv
from hltv_async_api.methods import Matches, Stats
from hltv_async_api.sync.syncHltv import Hltv as SyncHltv

from . import fixtures as fx
from .stats_fixture import stats_page

TZ = 'Europe/Copenhagen'


def parse(**kw):
    return Stats(TZ).get_stats_page(fx.soup(stats_page(**kw)))


def test_header_event_date_and_teams():
    data = parse()
    assert data['event'] == {'id': 8245, 'title': 'IEM Beijing 2026'}
    assert (data['timestamp'], data['date'], data['time']) == (1794044700, '07-11-2026', '10:45')  # Copenhagen
    assert data['map'] == 'All'
    assert (data['team1']['id'], data['team1']['name'], data['team1']['score']) == (4494, 'MOUZ', 2)
    assert (data['team2']['id'], data['team2']['name'], data['team2']['score']) == (12394, 'BETBOOM', 0)


def test_summary_rows_are_numbers():
    summary = parse()['summary']
    assert summary['team_rating_3_0'] == {'team1': 1.24, 'team2': 0.81}
    assert summary['first_kills'] == {'team1': 25, 'team2': 16}
    assert summary['clutches_won'] == {'team1': 3, 'team2': 2}
    assert summary['breakdown'] == {'raw': '8 : 4 (5 : 3)', 'values': [8, 4, 5, 3]}


def test_maps_and_series():
    data = parse()
    assert data['series'] == {'format': 'Best of 3', 'score1': 2, 'score2': 0, 'winner': 'MOUZ'}
    assert [(m['stats_id'], m['map'], m['score1'], m['score2'], m['winner']) for m in data['maps']] == [
        (243791, 'Ancient', 13, 7, 'MOUZ'), (243795, 'Mirage', 13, 8, 'MOUZ')]
    assert data['maps'][0]['href'] == '/stats/matches/mapstatsid/243791/mouz-vs-betboom'


def test_top_players_and_performance():
    data = parse()
    assert data['top_players']['most_kills'] == {'title': 'Most kills', 'player_id': 20312, 'nickname': 'xertioN', 'value': 40}
    assert data['top_players']['most_damage']['value'] == 111.0
    assert data['top_players']['best_rating_3_0']['value'] == 1.67
    assert data['performance'] == [{'nickname': 'xertioN', 'rating': 1.67}, {'nickname': 'd1Ledez', 'rating': 0.59}]


def test_player_totals():
    xertion = parse()['team1']['players'][0]
    assert xertion['id'] == 20312 and xertion['nickname'] == 'xertioN' and xertion['country'] == 'Israel'
    assert (xertion['kills'], xertion['headshots'], xertion['hs_percent']) == (40, 21, 52.5)
    assert (xertion['assists'], xertion['flash_assists'], xertion['deaths'], xertion['traded_deaths']) == (10, 2, 20, 4)
    assert xertion['kd_diff'] == 20 and xertion['adr'] == 111.0 and xertion['kast'] == 73.2
    assert (xertion['opening_kills'], xertion['opening_deaths']) == (6, 3)
    assert (xertion['multi_kills'], xertion['clutches'], xertion['swing'], xertion['rating']) == (12, 1, 4.93, 1.67)
    assert (xertion['e_kills'], xertion['e_deaths'], xertion['e_adr'], xertion['e_kast']) == (41, 21, 100.5, 70.0)


def test_player_sides_are_matched_by_id_not_by_row_order():
    pr = parse()['team1']['players'][1]
    assert pr['nickname'] == 'PR' and pr['ct']['rating'] == 1.79 and pr['t']['rating'] == 1.04
    assert pr['ct']['kills'] == 20 and pr['t']['kills'] == 15  # PR is first in the CT table but second in 'both'
    xertion = parse()['team1']['players'][0]
    assert xertion['ct']['rating'] == 1.59 and xertion['t']['rating'] == 1.75


def test_second_team_players_and_negative_swing():
    siren, ledez = parse()['team2']['players']
    assert (siren['nickname'], siren['rating']) == ('S1ren', 1.11)
    assert ledez['swing'] == -6.4 and ledez['kd_diff'] == -16 and ledez['t']['opening_deaths'] == 4


def test_round_history_is_empty_without_the_section():
    assert parse()['round_history'] == []


def test_round_history_on_a_map_page():
    first, second = parse(map_name='Ancient', rounds=True)['round_history']
    assert first['team'] == 'MOUZ' and [r['won'] for r in first['rounds']] == [True, False, True]
    assert [r['outcome'] for r in first['rounds']] == ['ct_win', 'emptyHistory', 'bomb_exploded']
    assert second['team'] == 'BETBOOM' and [r['won'] for r in second['rounds']] == [False, True, False]


def test_page_without_tables_or_header_does_not_crash():
    data = Stats(TZ).get_stats_page(fx.soup('<div></div>'))
    assert data['team1'] == {'id': 0, 'name': '', 'score': 0, 'players': []}
    assert data['maps'] == [] and data['top_players'] == {} and data['performance'] == []
    assert parse(tables=False)['team1']['players'] == []


# --- match page ids ----------------------------------------------------------------

def test_match_page_exposes_stats_ids(page):
    info = Matches(TZ).get_match_info(page('match_recent'), 1, 'FURIA', 'BETBOOM', 'c')
    assert info['stats_id'] == 132166
    assert [m['stats_id'] for m in info['maps']] == [242084, 242090, 242103, 242111, 242114]


def test_match_without_statistics_has_zero_ids():
    html = '<div class="countdown">1d : 2h</div>' + fx._map('TBA')
    info = Matches(TZ).get_match_info(fx.soup(html), 1, 'a', 'b', 'c')
    assert info['stats_id'] == 0 and info['maps'][0]['stats_id'] == 0


# --- client methods ----------------------------------------------------------------

class Stub:
    """Serves stats pages by URL and records what was asked for."""

    def __init__(self, pages):
        self.pages, self.urls = pages, []

    async def fetch(self, url, delay=0):
        self.urls.append(url)
        for part, html in self.pages.items():
            if part in url:
                return fx.soup(html) if html else None


def hltv_with(pages):
    stub = Stub(pages)
    return Hltv(parser=stub), stub


PAGES = {
    '/stats/matches/mapstatsid/243791/': stats_page('Ancient', rounds=True),
    '/stats/matches/mapstatsid/243795/': stats_page('Mirage'),
    '/stats/matches/132835/': stats_page(),
}


async def test_get_match_stats_fetches_the_overview_and_every_map():
    hltv, stub = hltv_with(PAGES)
    data = await hltv.get_match_stats(132835, 'MOUZ', 'BETBOOM')
    assert stub.urls[0] == 'https://www.hltv.org/stats/matches/132835/mouz-vs-betboom'
    assert sorted(stub.urls[1:]) == ['https://www.hltv.org/stats/matches/mapstatsid/243791/mouz-vs-betboom',
                                     'https://www.hltv.org/stats/matches/mapstatsid/243795/betboom-vs-mouz']
    assert data['stats_id'] == 132835 and data['map'] == 'All' and len(data['team1']['players']) == 2
    ancient, mirage = data['maps']
    assert ancient['stats_id'] == 243791 and ancient['map'] == 'Ancient' and ancient['available']
    assert ancient['team1']['players'][0]['kills'] == 40 and len(ancient['round_history']) == 2
    assert mirage['stats_id'] == 243795 and 'maps' not in mirage
    await hltv.close()


async def test_get_match_stats_marks_unavailable_maps():
    hltv, _ = hltv_with({**PAGES, '/stats/matches/mapstatsid/243795/': ''})
    data = await hltv.get_match_stats(132835)
    assert [m['available'] for m in data['maps']] == [True, False]
    assert data['maps'][1]['stats_id'] == 243795 and data['maps'][1]['score1'] == 13
    await hltv.close()


async def test_get_match_stats_returns_none_when_the_overview_fails():
    hltv, _ = hltv_with({})
    assert await hltv.get_match_stats(1) is None
    await hltv.close()


async def test_get_map_stats():
    hltv, stub = hltv_with(PAGES)
    data = await hltv.get_map_stats(243791, 'MOUZ', 'BetBoom')
    assert stub.urls == ['https://www.hltv.org/stats/matches/mapstatsid/243791/mouz-vs-betboom']
    assert data['stats_id'] == 243791 and data['map'] == 'Ancient' and 'maps' not in data
    await hltv.close()


async def test_get_stats_for_match_follows_the_match_page_link(page):
    match_page = page('match_recent')
    hltv, stub = hltv_with(PAGES)

    async def fetch(url, delay=0):
        stub.urls.append(url)
        if '/matches/2400000/' in url:
            return match_page
        return await Stub.fetch(stub, url)

    stub.fetch = fetch
    hltv.PARSER = stub
    # the saved page points at stats id 132166, the stub only knows 132835: the second call must therefore fail softly
    assert await hltv.get_stats_for_match(2400000, 'FURIA', 'BETBOOM', 'c') is None
    assert stub.urls[-1] == 'https://www.hltv.org/stats/matches/132166/furia-vs-betboom'
    await hltv.close()


async def test_get_stats_for_match_without_statistics():
    hltv, _ = hltv_with({'/matches/5/': '<div class="countdown">1d : 2h</div>' + fx._map('TBA')})
    assert await hltv.get_stats_for_match(5, 'a', 'b', 'c') is None
    await hltv.close()


def test_sync_client_get_match_stats(monkeypatch):
    client = SyncHltv()
    seen = []

    def fetch(url):
        seen.append(url)
        for part, html in PAGES.items():
            if part in url:
                return fx.soup(html)

    monkeypatch.setattr(client, '_fetch', fetch)
    data = client.get_match_stats(132835, 'MOUZ', 'BETBOOM')
    assert len(seen) == 3 and [m['map'] for m in data['maps']] == ['Ancient', 'Mirage']
    assert client.get_map_stats(243791)['team1']['name'] == 'MOUZ'


# --- a real map page (IEM Beijing 2026, MOUZ vs BETBOOM, Ancient) ----------------------

MAP_PAGE = 'stats_matches_mapstatsid_243791_mouz_vs_betboom'


def test_real_map_page_header_and_summary(page):
    data = Stats(TZ).get_stats_page(page(MAP_PAGE))
    assert (data['map'], data['team1']['score'], data['team2']['score']) == ('Ancient', 13, 7)
    assert data['summary']['breakdown'] == {'team1': 13, 'team2': 7, 'halves': [
        {'team1': 7, 'team2': 5, 'team1_side': 'ct'}, {'team1': 6, 'team2': 2, 'team1_side': 't'}]}
    assert data['summary']['team_rating_3_0'] == {'team1': 1.27, 'team2': 0.89}
    assert data['summary']['first_kills'] == {'team1': 11, 'team2': 9}
    assert data['top_players']['most_awp_kills']['nickname'] == 'zorte'


def test_real_map_page_players_and_sides(page):
    data = Stats(TZ).get_stats_page(page(MAP_PAGE))
    xertion = data['team1']['players'][0]
    assert (xertion['nickname'], xertion['kills'], xertion['rating'], xertion['kast']) == ('xertioN', 21, 2.02, 75.0)
    assert xertion['ct']['rating'] == 1.74 and xertion['t']['rating'] != xertion['ct']['rating']
    assert len(data['team2']['players']) == 5 and data['team2']['players'][0]['nickname'] == 'S1ren'


def test_real_map_page_round_history(page):
    data = Stats(TZ).get_stats_page(page(MAP_PAGE))
    rounds = data['rounds']
    assert len(rounds) == 20 and [r['round'] for r in rounds] == list(range(1, 21))
    assert rounds[0] == {'round': 1, 'half': 1, 'winner': 'BETBOOM', 'side': 't', 'reason': 'bomb_exploded',
                         'score1': 0, 'score2': 1}
    assert (rounds[-1]['score1'], rounds[-1]['score2']) == (13, 7) and rounds[-1]['winner'] == 'MOUZ'
    assert {r['reason'] for r in rounds} <= {'elimination', 'bomb_defused', 'bomb_exploded', 'time'}
    assert sum(r['winner'] == 'MOUZ' for r in rounds) == 13
    assert [r['half'] for r in rounds][:1] == [1] and 2 in {r['half'] for r in rounds}


def test_rounds_of_the_fixture_page_are_merged():
    rounds = parse(map_name='Ancient', rounds=True)['rounds']
    assert [(r['winner'], r['side'], r['reason']) for r in rounds] == [('MOUZ', 'ct', 'elimination'),
                                                                        ('BETBOOM', 't', 'elimination'),
                                                                        ('MOUZ', 't', 'bomb_exploded')]
