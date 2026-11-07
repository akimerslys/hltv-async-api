"""Player statistics pages (real pages saved in tests/data), URL filters and the client methods."""

import pytest

from hltv_async_api import Hltv
from hltv_async_api.methods import PlayerStats, Players
from hltv_async_api.methods.PlayerStats import clutch_variant, multikill_variant, number, player_query, player_url
from hltv_async_api.sync.syncHltv import Hltv as SyncHltv

from . import fixtures as fx

TZ = 'Europe/Copenhagen'
P = PlayerStats(TZ)
OVERVIEW = 'stats_players_20312_xertion'  # saved with the filter map=de_mirage


def named(name):
    return f'stats_players_{name}_20312_xertion'


# --- overview --------------------------------------------------------------------

def test_overview_header_and_summary(page):
    data = P.get_player_overview(page(OVERVIEW))
    assert (data['id'], data['nickname'], data['name'], data['age'], data['country']) == (20312, 'xertioN', 'Dorian Berman', 22, 'Israel')
    assert data['team'] == {'id': 4494, 'name': 'MOUZ'} and data['maps'] == 126  # Mirage only
    assert data['summary'] == {'round_swing': 1.08, 'dpr': 0.68, 'kast': 73.6, 'multi_kill': 18.6, 'adr': 83.3, 'kpr': 0.74,
                               'rating': 1.15, 't_rating': 1.13, 'ct_rating': 1.17}
    assert data['verdicts']['adr'] == 'Good' and data['verdicts']['rating'] == 'Good'


def test_overview_roles_have_scores_per_side(page):
    roles = P.get_player_overview(page(OVERVIEW))['roles']
    assert list(roles) == ['firepower', 'entrying', 'trading', 'opening', 'closing', 'sniping', 'utility']
    firepower = roles['firepower']
    assert (firepower['score'], firepower['ct_score'], firepower['t_score']) == (93, 90, 85)
    kprw = firepower['stats']['kills_per_round_win']
    assert (kprw['value'], kprw['ct'], kprw['t'], kprw['band']) == (1.02, 1.06, 0.98, 'aboveAverage')
    assert roles['opening']['stats']['first_duel_time']['value'] == 49  # '0m 49s' -> seconds
    assert roles['entrying']['stats']['deaths_traded']['value'] == 23.2


def test_overview_similar_featured_and_teammates(page):
    data = P.get_player_overview(page(OVERVIEW))
    assert len(data['similar_players']) == 10
    assert data['similar_players'][0] == {'id': 16693, 'nickname': 'flameZ', 'country': 'Israel', 'team': 'Vitality', 'similarity': 93}
    assert data['featured_ratings'][0] == {'label': 'vs top 5 opponents', 'top': 5, 'rating': 1.09, 'maps': 41}
    assert [t['nickname'] for t in data['teammates']] == ['PR', 'Spinx', 'xelex', 'torzsi']
    assert data['teammates'][0]['rating'] == 1.15


# --- advanced --------------------------------------------------------------------

def test_advanced_sections(page):
    data = P.get_player_advanced(page(named('advanced')))
    assert (data['maps'], data['rounds']) == (574, 12490)
    assert data['headline']['round_swing']['value'] == 0.65
    impact = {t['label']: t for t in data['sections']['impact']['tiles']}
    assert impact['Deducted']['value'] == -10.8  # U+2212 minus sign
    assert impact['Advantage']['detail'] == {'kpr': 0.47, 'dpr': 0.37}
    assert data['sections']['dueling_and_eco_adjustment']['tiles']
    radar = data['sections']['summary']['chart']
    assert 'Rating 3.0' in radar['labels'] and 'xertioN' in radar['datasets']


# --- tables ----------------------------------------------------------------------

def test_matches(page):
    data = P.get_player_matches(page(named('matches')))  # saved with offset=100: the second page
    assert data['pagination'] == {'from': 101, 'to': 200, 'total': 574} and len(data['matches']) == 100
    assert data['summary'] == {'avg_rating': 1.11, 'maps_won': 60.3, 'maps_with_1_plus_rating': 65.5,
                               'best_1_plus_rating_streak': 17}
    assert data['matches'][0] == {'stats_id': 229637, 'timestamp': 1779512400, 'date': '23-05-2026',
                                  'team': {'id': 4494, 'name': 'MOUZ', 'score': 7},
                                  'opponent': {'id': 11283, 'name': 'Falcons', 'score': 13},
                                  'map_code': 'd2', 'map': 'Dust2', 'kills': 8, 'deaths': 15, 'kd_diff': -7,
                                  'rating': 0.75, 'won': False}
    assert any(not m['won'] for m in data['matches'])


def test_events(page):
    data = P.get_player_events(page(named('events')))
    assert data['pagination']['total'] == 56 and len(data['events']) == 56
    assert data['events'][0] == {'event_id': 8245, 'event': 'IEM Beijing 2026', 'placement': '-', 'place': 0, 'team_id': 4494,
                                 'team': 'MOUZ', 'maps': 8, 'kpr': 0.76, 'dpr': 0.61, 'kd_diff': 25, 'rating': 1.23}
    assert data['events'][1]['placement'] == '3rd' and data['events'][1]['place'] == 3


def test_career(page):
    periods = P.get_player_career(page(named('career')))['periods']
    assert [p['period'] for p in periods][:2] == ['2020', '2021'] and periods[-1]['period'] == 'Career'
    assert periods[0] == {'period': '2020', 'all': {'rating': 0.8, 'maps': 5}, 'online': {'rating': 0.8, 'maps': 5},
                          'lan': None, 'majors': None}
    assert periods[-1]['all'] == {'rating': 1.02, 'maps': 944}


def test_weapons(page):
    data = P.get_player_weapons(page(named('weapon')))
    assert data['kills_by_type'][0] == {'type': 'Rifles', 'count': 6867, 'share': 77.7}
    assert data['carried_by_type'][0] == {'type': 'Rifles', 'count': 9043, 'share': 72.4}
    assert len(data['weapons']) == 24
    assert data['weapons'][0] == {'rank': 1, 'weapon': 'AK-47', 'kills': 3468, 'share': 39.2}


def test_clutches(page):
    data = P.get_player_clutches(page('stats_players_clutches_20312_all_xertion'))
    assert data['summary'] == {'wins': 119, 'losses': 39, 'difference': 80}
    assert data['pagination']['total'] == 158 and len(data['clutches']) == 100
    assert data['clutches'][0] == {'stats_id': 243791, 'timestamp': 1794044700, 'date': '07-11-2026',
                                   'team1': {'id': 4494, 'name': 'MOUZ', 'score': 13},
                                   'team2': {'id': 12394, 'name': 'BETBOOM', 'score': 7},
                                   'map_code': 'anc', 'map': 'Ancient', 'won': True, 'clutch': 3, 'round': 20}
    assert any(not c['won'] for c in data['clutches'])


def test_multikills(page):
    data = P.get_player_multikills(page('stats_players_multikills_20312_two_xertion'))  # saved with fast=true
    assert data['summary'] == {'multi_kills': 1617, 'fast_multi_kills': 953}
    assert data['pagination'] == {'from': 1, 'to': 100, 'total': 953} and data['multikills'][0]['round'] == 12
    assert data['multikills'][0]['map'] == 'Ancient'


def test_multikills_three(page):
    data = P.get_player_multikills(page('stats_players_multikills_20312_three_xertion'))
    assert data['summary'] == {'multi_kills': 473, 'fast_multi_kills': 130}
    assert data['pagination']['total'] == 473 and data['multikills'][0]['round'] == 7


def test_clutches_of_a_single_size_have_no_type_column(page):
    data = P.get_player_clutches(page('stats_players_clutches_20312_1on3_xertion'), size=3)
    assert data['summary'] == {'wins': 10, 'losses': None, 'difference': None}  # hidden boxes on this page
    assert data['pagination']['total'] == 10 and len(data['clutches']) == 10
    assert {c['clutch'] for c in data['clutches']} == {3} and all(c['won'] for c in data['clutches'])
    assert data['clutches'][0]['round'] == 20 and data['clutches'][0]['map'] == 'Ancient'


def test_opponents(page):
    data = P.get_player_opponents(page('stats_players_opponents_team_20312_xertion'))
    assert data['pagination']['total'] == 53 and len(data['opponents']) == 53
    assert data['opponents'][0] == {'team_id': 10672, 'team': 'VERTEX', 'maps': 1, 'kd_diff': 10, 'kd': 2.67, 'rating': 2.19}


@pytest.mark.parametrize('parse', ['get_player_overview', 'get_player_advanced', 'get_player_matches', 'get_player_events',
                                   'get_player_career', 'get_player_weapons', 'get_player_clutches',
                                   'get_player_multikills', 'get_player_opponents'])
def test_empty_page_does_not_crash(parse):
    assert isinstance(getattr(P, parse)(fx.soup('<html></html>')), dict)


# --- profile page ---------------------------------------------------------------

def test_profile_page_new_ui(page):
    info = Players(TZ).get_player_info(page('player_20312_xertion'), 20312, 'xertioN')
    assert (info['team'], info['team_id'], info['name'], info['nationality'], info['age']) == ('MOUZ', 4494, 'Dorian Berman', 'Israel', 22)
    assert (info['born'], info['prize_money']) == ('22-07-2004', 769684)
    assert info['top20'] == [{'rank': 14, 'year': 2024, 'article_id': 40643}, {'rank': 16, 'year': 2025, 'article_id': 43512}]
    assert (info['stats_period'], info['stats_maps'], info['rating'], info['rating_percentile']) == ('Past 3 months', 72, 1.12, 80)
    assert info['roles'] == {'firepower': 89, 'entrying': 78, 'trading': 38, 'opening': 93, 'closing': 26, 'sniping': 0, 'utility': 48}
    assert set(info['socials']) == {'twitter', 'twitch', 'instagram', 'faceit'}
    assert info['upcoming_matches'][0]['id'] == 2400011 and info['upcoming_matches'][0]['opponent'] == 'The MongolZ'
    assert info['recent_matches'][0] == {'opponent': 'BETBOOM', 'opponent_name': 'BETBOOM', 'event': 'IEM Beijing 2026',
                                         'stats_id': 132835, 'score1': 2, 'score2': 0, 'won': True}


# --- urls / filters ------------------------------------------------------------

def test_player_urls():
    assert player_url('overview', 20312, 'xertioN') == 'https://www.hltv.org/stats/players/20312/xertion?csVersion=CS2'
    assert player_url('advanced', '20312', 'xertioN') == 'https://www.hltv.org/stats/players/advanced/20312/xertion?csVersion=CS2'
    assert player_url('clutches', 20312, 'xertioN', '1on3') == 'https://www.hltv.org/stats/players/clutches/20312/1on3/xertion?csVersion=CS2'
    assert player_url('multikills', 20312, 'xertioN', 'three').endswith('/multikills/20312/three/xertion?csVersion=CS2')
    assert player_url('opponents', 20312, 'xertioN').endswith('/opponents/team/20312/xertion?csVersion=CS2')
    assert player_url('overview', 1, "s1mple 'x'").endswith('/stats/players/1/s1mple-x?csVersion=CS2')


def test_filters_build_the_query_hltv_uses():
    query = player_query(map='Mirage', match_type='big_events', start_date='2026-01-01', end_date='2026-12-31',
                         ranking=10, best_of=3, ranked=True, playoff='grand final', team_id=4494, opponent_team=12394,
                         event=8245, offset=100, fast=True)
    assert query == ('offset=100&fast=true&csVersion=CS2&maps=de_mirage&matchType=BigEvents&startDate=2026-01-01'
                     '&endDate=2026-12-31&rankingFilter=Top10&bestOfX=BestOf3&valveRanked=RANKED'
                     '&playoffMatchType=GRAND_FINAL&teamId=4494&opponentTeam=12394&event=8245')
    assert player_query(cs_version=None) == ''
    assert player_query(map='de_nuke', ranked=False).endswith('de_nuke&valveRanked=UNRANKED')
    assert player_query(start_date='all') == 'csVersion=CS2&startDate=all'


@pytest.mark.parametrize('kwargs', [{'match_type': 'sometimes'}, {'playoff': 'semi'}])
def test_bad_filter_values_raise(kwargs):
    with pytest.raises(ValueError):
        player_query(**kwargs)


@pytest.mark.parametrize('value, expected', [('all', 'all'), (1, '1on1'), ('1 on 4', '1on4'), ('1on5', '1on5')])
def test_clutch_variant(value, expected):
    assert clutch_variant(value) == expected


@pytest.mark.parametrize('value, expected', [('all', 'all'), (2, 'two'), ('3x', 'three'), ('four', 'four'), (5, 'five')])
def test_multikill_variant(value, expected):
    assert multikill_variant(value) == expected


@pytest.mark.parametrize('bad', [0, 6, 'x'])
def test_bad_variants_raise(bad):
    with pytest.raises(ValueError):
        clutch_variant(bad)
    with pytest.raises(ValueError):
        multikill_variant(bad)


@pytest.mark.parametrize('text, expected', [('+0.65%', 0.65), ('−10.8%', -10.8), ('$2,293', 2293), ('0m 51s', 51),
                                            ('1m 5s', 65), ('-', None), ('', None), ('12', 12), ('3.16', 3.16)])
def test_number(text, expected):
    assert number(text) == expected


# --- client --------------------------------------------------------------------

class Stub:
    def __init__(self, pages):
        self.pages, self.urls = pages, []

    async def fetch(self, url, delay=0):
        self.urls.append(url)
        for part, soup in self.pages.items():
            if part in url:
                return soup


def all_pages(page, **override):
    pages = {'/stats/players/20312/xertion': page(OVERVIEW),
             '/advanced/': page(named('advanced')),
             '/matches/20312': page(named('matches')),
             '/events/': page(named('events')),
             '/career/': page(named('career')),
             '/weapon/': page(named('weapon')),
             '/clutches/20312/1on3/': page('stats_players_clutches_20312_all_xertion'),
             '/multikills/20312/three/': page('stats_players_multikills_20312_two_xertion'),
             '/opponents/team/': page('stats_players_opponents_team_20312_xertion')}
    pages.update(override)
    return pages


async def test_client_methods_build_urls_and_parse(page):
    stub = Stub(all_pages(page))
    hltv = Hltv(parser=stub)
    overview = await hltv.get_player_stats(20312, 'xertioN', map='mirage', ranking=10)
    assert stub.urls[-1] == 'https://www.hltv.org/stats/players/20312/xertion?csVersion=CS2&maps=de_mirage&rankingFilter=Top10'
    assert overview['player_id'] == 20312 and overview['url'] == stub.urls[-1] and overview['summary']['rating'] == 1.15
    assert (await hltv.get_player_advanced(20312, 'xertioN'))['rounds'] == 12490
    matches = await hltv.get_player_matches(20312, 'xertioN', offset=100)
    assert stub.urls[-1].endswith('/matches/20312/xertion?offset=100&csVersion=CS2') and len(matches['matches']) == 100
    assert len((await hltv.get_player_events(20312, 'xertioN'))['events']) == 56
    assert (await hltv.get_player_career(20312, 'xertioN'))['periods']
    assert (await hltv.get_player_weapons(20312, 'xertioN'))['weapons']
    assert (await hltv.get_player_clutches(20312, 'xertioN', size=3))['summary']['wins'] == 119
    assert (await hltv.get_player_multikills(20312, 'xertioN', kills=3, fast=True))['summary']
    assert 'fast=true' in stub.urls[-1]
    assert (await hltv.get_player_opponents(20312, 'xertioN'))['opponents']
    await hltv.close()


async def test_full_stats_collects_every_section(page):
    stub = Stub(all_pages(page, **{'/career/': None}))
    hltv = Hltv(parser=stub)
    full = await hltv.get_player_full_stats(20312, 'xertioN', start_date='all')
    assert list(full) == ['player_id', 'overview', 'advanced', 'matches', 'events', 'career', 'weapons']
    assert full['career'] is None and full['overview']['summary'] and full['weapons']['weapons']
    assert len(stub.urls) == 6 and all('startDate=all' in url for url in stub.urls)
    await hltv.close()


async def test_client_rejects_bad_variant():
    hltv = Hltv(parser=Stub({}))
    with pytest.raises(ValueError):
        await hltv.get_player_clutches(1, 'x', size=9)
    await hltv.close()


def test_sync_client(page, monkeypatch):
    client = SyncHltv()
    seen = []

    def fetch(url):
        seen.append(url)
        return page(named('advanced')) if '/advanced/' in url else page(OVERVIEW)

    monkeypatch.setattr(client, '_fetch', fetch)
    assert client.get_player_stats(20312, 'xertioN', map='nuke')['summary']['rating'] == 1.15
    assert client.get_player_advanced(20312, 'xertioN')['maps'] == 574
    full = client.get_player_full_stats(20312, 'xertioN')
    assert full['overview']['maps'] == 126 and len(seen) == 8
