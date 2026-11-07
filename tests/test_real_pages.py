"""Parsers against real HLTV HTML.

The pages in tests/data are Internet Archive snapshots of the URLs the library requests (the live site blocks
scripted clients). tests/data/_sources.json records each URL and snapshot time. The matches, results, events,
rankings, team and player pages are from Oct-Nov 2026, the finished-event pages from 2024.
"""

import pytest

from hltv_async_api.methods import Events, Matches, News, Players, Teams

TZ = 'Europe/Copenhagen'


def assert_keys(items, keys):
    assert items, 'parser returned nothing'
    for item in items:
        assert set(keys) <= set(item), item


def test_get_matches(page):
    matches = Matches(TZ).get_matches(page('matches'), days=2, min_rating=0)
    assert_keys(matches, ['id', 'date', 'time', 'team1', 'team2', 't1_id', 't2_id', 'maps', 'rating', 'event'])
    assert len(matches) == 47
    live = [m for m in matches if m['date'] == 'LIVE']
    assert live[0] == {'id': 2399417, 'date': 'LIVE', 'time': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM',
                       't1_id': 8297, 't2_id': 12394, 'maps': 5, 'rating': 4,
                       'event': 'Thunderpick World Championship 2026'}
    first_upcoming = matches[len(live)]
    assert (first_upcoming['date'], first_upcoming['time']) == ('18-10-2026', '23:00')
    assert (first_upcoming['team1'], first_upcoming['team2']) == ('6yuBoJlbl', 'HYPERSPIRIT')
    assert all(isinstance(m['id'], int) and m['id'] > 0 for m in matches)
    assert all(m['maps'] in (0, 1, 2, 3, 5) for m in matches)


def test_get_matches_filters(page):
    m = Matches(TZ)
    assert len(m.get_matches(page('matches'), days=1, min_rating=1)) == 1
    assert len(m.get_matches(page('matches'), days=1, min_rating=0)) == 3
    assert len(m.get_matches(page('matches'), future=False, min_rating=0)) == 2


def test_matches_tbd_teams(page):
    matches = Matches(TZ).get_matches(page('matches'), days=15, min_rating=0, live=False)
    tbd = [m for m in matches if m['team1'] == 'TBD']
    assert tbd and all(m['t1_id'] == 0 and m['t2_id'] == 0 for m in tbd)


def test_matches_one_team_known(page):
    matches = Matches(TZ).get_matches(page('matches'), days=15, min_rating=0, live=False)
    faze = next(m for m in matches if m['id'] == 2399610)
    assert (faze['team1'], faze['team2'], faze['t1_id'], faze['t2_id']) == ('FaZe', 'TBD', 6667, 0)


@pytest.mark.parametrize('name, score, first_stats, maps', [
    ('match_over', (0, 2), {'id': 18850, 'nickname': 'Jimpphat', 'kd': '33-29', 'adr': 80.9,
                                'rating': 1.08}, 3),
    ('match_recent', (3, 2), {'id': 15631, 'nickname': 'KSCERATO', 'kd': '82-72', 'adr': 81.1,
                                  'rating': 1.13}, 5),
])
def test_get_match_info(page, name, score, first_stats, maps):
    info = Matches(TZ).get_match_info(page(name), 1, 'a', 'b', 'c')
    assert info['status'] == 'Match over'
    assert (info['score1'], info['score2']) == score
    assert len(info['maps']) == maps
    assert info['stats'][0] == first_stats
    assert len(info['stats']) == 10


def test_get_match_info_maps_recent(page):
    maps = Matches(TZ).get_match_info(page('match_recent'), 1, 'FURIA', 'BETBOOM', 'c')['maps']
    assert maps[0] == {'mapname': 'Dust2', 'r_team1': 13, 'r_team2': 6, 'pick': 'FURIA', 'stats_id': 242084}
    assert maps[1]['pick'] == 'BETBOOM'


def test_get_results(page):
    res = Matches(TZ).get_results(page('results'), days=1, min_rating=0)
    assert len(res) == 35
    assert res[0] == {'id': 2400004, 'team1': 'Natus Vincere', 'team2': 'Falcons', 'score1': 2, 'score2': 1,
                      'rating': 3, 'event': 'IEM Beijing 2026'}
    dated = [r for r in res if 'date' in r]
    assert len(dated) == 19 and all(r['date'] == '04-11-2026' for r in dated)
    assert all(isinstance(r['score1'], int) and isinstance(r['score2'], int) for r in res)


def test_get_results_filters(page):
    m = Matches(TZ)
    assert len(m.get_results(page('results'), featured=True, regular=False)) == 16
    assert len(m.get_results(page('results'), featured=False, min_rating=0, max=5)) == 5


def test_get_event_results(page):
    res = Events(TZ).get_event_results(page('event_results'), 7148, days=1, max_=10)
    assert res == [
        {'id': 2370727, 'date': '31-03-2024', 'team1': 'FaZe', 'team2': 'Natus Vincere', 'score1': 1,
         'score2': 2},
        {'id': 2370726, 'date': '31-03-2024', 'team1': 'Natus Vincere', 'team2': 'G2', 'score1': 2,
         'score2': 1},
    ]
    assert len(Events(TZ).get_event_results(page('event_results'), 7148, days=2, max_=10)) > 2


def test_get_event_matches(page):
    res = Events(TZ).get_event_matches(page('event_matches'), 8932, 1, 10)
    assert res == [{'id': 2399417, 'date': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM',
                    't1_id': 8297, 't2_id': 12394}]


def test_get_events(page):
    e = Events(TZ)
    events = e.get_events(page('events'), True, True, 5)
    assert_keys(events, ['id', 'title', 'start_date', 'end_date'])
    assert len(events) == 16 and len(e.get_events(page('events'), False, True, 5)) == 5
    assert len(e.get_events(page('events'), True, False, 5)) == 11
    assert events[11] == {'id': 8050, 'title': 'PGL Masters Bucharest 2026', 'start_date': '24-10',
                          'end_date': '31-10'}
    assert events[-1]['start_date'] != events[-1]['end_date']  # future events carry their own end date


def test_get_event_info_finished(page):
    info = Events(TZ).get_event_info(page('event_info_finished'), 7148, 'PGL CS2 Major Copenhagen 2024')
    assert (info['start'], info['end'], info['status']) == ('21-03-2024', '31-03-2024', 'Finished')
    assert (info['prize'], info['team_count'], info['location']) == ('$1,250,000', '16', 'Copenhagen, Denmark')
    assert info['mvp'] == {'id': 19206, 'nickname': 'jL'}
    assert info['winners'][0] == {'place': 1, 'team': 'Natus Vincere', 'id': 4608, 'prize': '$500,000'}
    assert len(info['winners']) == 16


def test_get_top_teams(page):
    teams = Teams(TZ).get_top_teams(page('ranking'), 30)
    assert_keys(teams, ['id', 'rank', 'title', 'points', 'change'])
    assert len(teams) == 30
    assert teams[0] == {'id': 7020, 'rank': 1, 'title': 'Spirit', 'points': 904, 'change': 0}
    assert teams[-1] == {'id': 11251, 'rank': 30, 'title': 'Eternal Fire', 'points': 62, 'change': +13}
    assert [t['rank'] for t in teams] == list(range(1, 31))


def test_get_team_info(page):
    info = Teams(TZ).get_team_info(page('team'), 6667, 'faze')
    assert info['id'] == 6667 and info['title'] == 'faze'
    assert (info['rank'], info['coach'], info['age'], info['weekstop30']) == (17, 'enkay J', 23.3, 56)
    assert info['players'] == {'frozen': 9960, 'Twistzz': 10394, 'Neityu': 21972, 'jcobbb': 22383, 'JBOEN': 22866}
    assert info['last_trophy'] == 'IEM Chengdu 2024' and info['total_trophies'] == 22
    assert info['logo'].startswith('https://img-cdn.hltv.org/teamlogo/')


def test_get_top_players(page):
    players = Players(TZ).get_top_players(page('top_players'), 40)
    assert_keys(players, ['id', 'rank', 'nickname', 'team', 'maps', 'rating'])
    assert len(players) == 40
    assert players[0] == {'id': 11893, 'rank': 1, 'nickname': 'ZywOo', 'team': 'Vitality', 'maps': 1572,
                          'rating': 1.27}
    assert len(Players(TZ).get_top_players(page('top_players'), 3)) == 3


def test_get_player_info(page):
    info = Players(TZ).get_player_info(page('player'), 7998, 's1mple')
    assert info['team'] == 'BC.Game' and info['team_id'] == 12878
    assert (info['name'], info['nationality'], info['age']) == ('Oleksandr Kostyliev', 'Ukraine', 29)
    assert (info['rating'], info['hs']) == (1.23, 48.0)
    assert info['img'].startswith('https://img-cdn.hltv.org/playerbodyshot/')
    assert (info['total_trophies'], info['total_mvp']) == (30, 21)
    assert info['last_trophy'] == 'BLAST Premier Spring Final 2022'
    assert info['last_matches'][0] == 2399613 and len(info['last_matches']) == 6


def test_get_last_news(page):
    res = News(TZ).get_last_news(page('home'), max_reg_news=3, only_today=False)
    assert [d['date'] for d in res][-1] == 'old' and len(res) == 3
    assert [n['id'] for n in res[0]['news']] == [45914, 45881, 45913]
    assert res[0]['news'][0] == {'id': 45914, 'title': 'IEM Beijing 2026 playoff bracket set',
                                 'posted': 'an hour ago'}
    assert sum(len(d['news']) for d in res) == 3  # max_reg_news is shared across days
