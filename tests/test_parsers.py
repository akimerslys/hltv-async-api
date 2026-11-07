"""Offline tests for every parser behind the README methods (shared by the async and sync clients)."""

import pytest

from hltv_async_api.Utils import datetools
from hltv_async_api.methods import Events, Matches, News, Players, Teams

from . import fixtures as fx

TZ = 'Europe/Copenhagen'


# --- get_matches -----------------------------------------------------------------

class TestGetMatches:
    def test_live_and_upcoming(self):
        res = Matches(TZ).get_matches(fx.soup(fx.MATCHES), days=1, min_rating=1)
        assert res[0] == {'id': 2371201, 'date': 'LIVE', 'time': 'LIVE', 'team1': 'Imperial', 'team2': 'MIBR',
                          't1_id': 9455, 't2_id': 9215, 'maps': 3, 'rating': 2,
                          'event': 'RES Regional Series 3 LATAM'}
        assert res[1] == {'id': 2370964, 'date': '16-04-2024', 'time': '12:30', 'team1': 'SAW', 'team2': 'Sampi',
                          't1_id': 10567, 't2_id': 10695, 'maps': 3, 'rating': 1,
                          'event': 'Thunderpick World Championship 2024'}
        assert len(res) == 3  # low-rated live match, 0-star upcoming matches, and day two are filtered out

    def test_days_limits_sections(self):
        res = Matches(TZ).get_matches(fx.soup(fx.MATCHES), days=2, min_rating=1, live=False)
        assert [m['id'] for m in res] == [2370964, 2370966, 2371367]

    def test_min_rating(self):
        res = Matches(TZ).get_matches(fx.soup(fx.MATCHES), days=2, min_rating=3)
        assert [m['id'] for m in res] == [2371367]

    def test_tbd_match_has_defaults(self):
        res = Matches(TZ).get_matches(fx.soup(fx.MATCHES), days=1, min_rating=0, live=False)
        tbd = next(m for m in res if m['id'] == 2370965)
        assert (tbd['team1'], tbd['team2'], tbd['t1_id'], tbd['t2_id']) == ('TBD', 'TBD', 0, 0)
        assert tbd['event'] == 'Some Qualifier'

    def test_live_and_future_flags(self):
        m = Matches(TZ)
        assert m.get_matches(fx.soup(fx.MATCHES), live=False, future=False) == []
        assert all(x['date'] == 'LIVE' for x in m.get_matches(fx.soup(fx.MATCHES), future=False))

    def test_timezone_conversion(self):
        res = Matches('UTC').get_matches(fx.soup(fx.MATCHES), live=False)
        assert (res[0]['date'], res[0]['time']) == ('16-04-2024', '10:30')  # Copenhagen is UTC+2 in April


# --- get_match_info --------------------------------------------------------------

class TestGetMatchInfo:
    def test_finished_match(self):
        info = Matches(TZ).get_match_info(fx.soup(fx.MATCH_OVER), 2370931, 'MOUZ', 'FaZe', 'iem-chengdu-2024')
        assert info['id'] == 2370931
        assert info['status'] == 'Match over'
        assert (info['score1'], info['score2']) == (0, 2)
        assert info['maps'] == [
            {'mapname': 'Overpass', 'r_team1': 10, 'r_team2': 13, 'pick': 'MOUZ', 'stats_id': 0},
            {'mapname': 'Nuke', 'r_team1': 6, 'r_team2': 13, 'pick': 'FaZe', 'stats_id': 0},
            {'mapname': 'Mirage', 'r_team1': 0, 'r_team2': 0, 'pick': '', 'stats_id': 0},
        ]
        assert info['stats'][0] == {'id': 18850, 'nickname': 'Jimpphat', 'kd': '33-29', 'adr': 80.9,
                                    'rating': 1.08}
        assert [p['nickname'] for p in info['stats']] == ['Jimpphat', 'torzsi', 'broky']

    def test_stats_can_be_disabled(self):
        info = Matches(TZ).get_match_info(fx.soup(fx.MATCH_OVER), 1, 'a', 'b', 'c', stats=False)
        assert 'stats' not in info

    def test_live_match_scores_maps_won(self):
        info = Matches(TZ).get_match_info(fx.soup(fx.MATCH_LIVE), 2371201, 'Imperial', 'MIBR', 'res')
        assert info['status'] == 'LIVE'
        assert (info['score1'], info['score2']) == (0, 1)  # Vertigo went 6-13
        assert [m['mapname'] for m in info['maps']] == ['Vertigo', 'Mirage', 'Anubis']

    def test_upcoming_match_has_date_status_and_predictions(self):
        info = Matches(TZ).get_match_info(fx.soup(fx.MATCH_UPCOMING), 1, 'a', 'b', 'c')
        assert len(info['status'].split('-')) == 5  # dd-mm-YYYY-HH-MM
        assert (info['predict1'], info['predict2']) == (62, 38)
        assert (info['score1'], info['score2']) == (0, 0)
        assert info['maps'][0]['mapname'] == 'TBA'


# --- get_results -----------------------------------------------------------------

class TestGetResults:
    def test_featured_only(self):
        res = Matches(TZ).get_results(fx.soup(fx.RESULTS), featured=True, regular=False)
        assert res == [{'id': 2370931, 'team1': 'MOUZ', 'team2': 'FaZe', 'score1': 0, 'score2': 2,
                        'rating': 0, 'event': 'IEM Chengdu 2024'}]

    def test_regular_first_day(self):
        res = Matches(TZ).get_results(fx.soup(fx.RESULTS), days=1, min_rating=1, featured=False)
        assert res[0] == {'id': 2370931, 'date': '14-04-2024', 'team1': 'MOUZ', 'team2': 'FaZe',
                          'score1': 0, 'score2': 2, 'rating': 3, 'event': 'IEM Chengdu 2024'}
        assert [r['id'] for r in res] == [2370931, 2370932]  # unrated result filtered out

    def test_days_and_max(self):
        m = Matches(TZ)
        assert len(m.get_results(fx.soup(fx.RESULTS), days=2, min_rating=0, featured=False)) == 4
        assert len(m.get_results(fx.soup(fx.RESULTS), days=2, min_rating=0, featured=False, max=2)) == 2

    def test_featured_attaches_star_rating(self):
        html = ('<div class="results-sublist"><div class="big-results">'
                + fx._result(1, 'MOUZ', 'FaZe', 0, 2, 'IEM', stars=2) + '</div></div>')
        res = Matches(TZ).get_results(fx.soup(html), featured=True, regular=False)
        assert res[0]['rating'] == 2


# --- events ----------------------------------------------------------------------

class TestEvents:
    def test_event_results(self):
        res = Events(TZ).get_event_results(fx.soup(fx.EVENT_RESULTS), 7148, days=1, max_=10)
        assert res == [
            {'id': 2370931, 'date': '14-04-2024', 'team1': 'MOUZ', 'team2': 'FaZe', 'score1': 0, 'score2': 2},
            {'id': 2370932, 'date': '14-04-2024', 'team1': 'NAVI', 'team2': 'G2', 'score1': 2, 'score2': 1},
        ]

    def test_event_results_days_and_max(self):
        e = Events(TZ)
        assert len(e.get_event_results(fx.soup(fx.EVENT_RESULTS), 1, days=2, max_=10)) == 3
        assert len(e.get_event_results(fx.soup(fx.EVENT_RESULTS), 1, days=2, max_=1)) == 1

    def test_event_matches(self):
        res = Events(TZ).get_event_matches(fx.soup(fx.EVENT_MATCHES), 7148, 1, 10)
        assert res[0] == {'id': 2371201, 'date': 'LIVE', 'team1': 'Imperial', 'team2': 'MIBR',
                          't1_id': 9455, 't2_id': 9215}
        assert res[1] == {'id': 2370771, 'date': '2024-04-18', 'time': '15:30', 'team1': 'Monte', 'team2': 'paiN',
                          't1_id': 11811, 't2_id': 4773}
        assert res[2] == {'id': 2370775, 'date': '2024-04-18', 'time': '21:30', 'team1': 'TBD', 'team2': 'TBD',
                          't1_id': 0, 't2_id': 0}

    def test_get_events_ongoing(self):
        res = Events(TZ).get_events(fx.soup(fx.EVENTS), outgoing=True, future=False, max_events=10)
        assert res == [
            {'id': 7749, 'title': 'Thunderpick World Championship 2024 EU Closed Qualifier 1',
             'start_date': '1-4', 'end_date': '22-4'},
            {'id': 7621, 'title': 'ESL Challenger League Season 47 North America',
             'start_date': '13-2', 'end_date': '16-6'},
        ]

    def test_get_events_future_and_max(self):
        e = Events(TZ)
        res = e.get_events(fx.soup(fx.EVENTS), outgoing=False, future=True, max_events=10)
        assert [(x['id'], x['title'], x['start_date'], x['end_date']) for x in res] == [
            (7900, 'IEM Cologne 2024', '13-8', '15-8'), (7901, 'BLAST X 2024', '2-9', '4-9')]
        assert len(e.get_events(fx.soup(fx.EVENTS), outgoing=False, future=True, max_events=1)) == 1

    def test_event_info_finished(self):
        html = fx.event_info('1710979200000', '1711843200000', finished=True)
        info = Events(TZ).get_event_info(fx.soup(html), 7148, 'PGL CS2 Major Copenhagen2024')
        assert info['id'] == 7148 and info['title'] == 'PGL CS2 Major Copenhagen2024'
        assert (info['start'], info['end'], info['status']) == ('21-03-2024', '31-03-2024', 'Finished')
        assert (info['prize'], info['team_count'], info['location']) == ('$1,250,000', '16', 'Copenhagen, Denmark')
        assert info['mvp'] == {'id': 18053, 'nickname': 'broky'}
        assert info['winners'][0] == {'place': 1, 'team': 'FaZe', 'id': 6667, 'prize': '$500,000'}
        assert len(info['winners']) == 2

    def test_event_info_finished_without_mvp(self):
        html = fx.event_info('1710979200000', '1711843200000', finished=True)
        html = html.replace('<div class="player-and-coin"><a href="/player/18053/broky">\'broky\'</a></div>', '')
        info = Events(TZ).get_event_info(fx.soup(html), 1, 'x')
        assert 'mvp' not in info and info['status'] == 'Finished'

    def test_event_info_upcoming_lists_teams(self):
        html = fx.event_info('4070908800000', '4071686400000', finished=False)
        info = Events(TZ).get_event_info(fx.soup(html), 7148, 'x')
        assert info['status'] == 'Upcoming'
        assert info['teams'] == [{6667: 'FaZe'}, {4608: 'Natus Vincere'}]


# --- teams -----------------------------------------------------------------------

class TestTeams:
    def test_top_teams(self):
        res = Teams(TZ).get_top_teams(fx.soup(fx.TOP_TEAMS), 30)
        assert res == [
            {'id': 6667, 'rank': 1, 'title': 'FaZe', 'points': 939, 'change': 0},
            {'id': 4608, 'rank': 2, 'title': 'Natus Vincere', 'points': 757, 'change': +4},
            {'id': 9565, 'rank': 3, 'title': 'Vitality', 'points': 700, 'change': -1},
        ]

    def test_top_teams_max(self):
        assert len(Teams(TZ).get_top_teams(fx.soup(fx.TOP_TEAMS), 2)) == 2

    def test_top_teams_unloaded_page_raises(self):
        with pytest.raises(AttributeError):
            Teams(TZ).get_top_teams(fx.soup('<div class="ranked-team standard-box"></div>'), 5)

    def test_team_info(self):
        info = Teams(TZ).get_team_info(fx.soup(fx.TEAM_INFO), 6667, 'faze')
        assert info == {'id': 6667, 'title': 'faze', 'rank': 1, 'players': {'karrigan': 429, 'rain': 8183},
                        'coach': 'NEO', 'age': 26.6, 'weekstop30': 260, 'logo': '/logo.svg',
                        'last_trophy': 'IEM Chengdu 2024', 'total_trophies': 2}

    def test_team_info_unloaded_page_raises(self):
        with pytest.raises(AttributeError):
            Teams(TZ).get_team_info(fx.soup('<html></html>'), 1, 'x')


# --- players ---------------------------------------------------------------------

OLD_PLAYER_KEYS = {'id', 'nickname', 'team', 'team_id', 'name', 'nationality', 'age', 'rating', 'hs', 'img',
                   'total_trophies', 'last_trophy', 'total_mvp', 'last_matches'}


class TestPlayers:
    def test_top_players(self):
        res = Players(TZ).get_top_players(fx.soup(fx.top_players()), 40)
        assert res[0] == {'id': 19230, 'rank': 1, 'nickname': 'm0nesy', 'team': 'G2', 'maps': 44,
                          'rating': 1.37}
        assert [p['rating'] for p in res] == [1.37, 1.19, 1.00]  # positive and neutral rating cells

    def test_top_players_limit(self):
        assert len(Players(TZ).get_top_players(fx.soup(fx.top_players()), 2)) == 2

    def test_top_players_unloaded_page_raises(self):
        with pytest.raises(AttributeError):
            Players(TZ).get_top_players(fx.soup('<html></html>'), 5)

    def test_player_info(self):
        info = Players(TZ).get_player_info(fx.soup(fx.PLAYER_INFO), 7998, 's1mple')
        assert {k: v for k, v in info.items() if k in OLD_PLAYER_KEYS} == {'id': 7998, 'nickname': 's1mple', 'team': 'Natus Vincere', 'team_id': 4608,
                        'name': 'Oleksandr Kostyliev', 'nationality': 'Ukraine', 'age': 26, 'rating': 0.94,
                        'hs': 57.9, 'img': '/s1mple.png', 'total_trophies': 3,
                        'last_trophy': 'BLAST Premier Spring Final 2022', 'total_mvp': 21,
                        'last_matches': [2399613, 99745]}
        assert info['born'] == '' and info['roles'] == {} and info['upcoming_matches'] == [] and info['top20'] == []


# --- news ------------------------------------------------------------------------

class TestNews:
    def test_today_only(self):
        res = News(TZ).get_last_news(fx.soup(fx.news()), max_reg_news=2, only_today=True)
        assert len(res) == 1
        assert res[0]['f_news'] == [{'f_id': 38790, 'f_title': 'Big news', 'f_desc': 'Details'}]
        assert res[0]['news'] == [{'id': 38784, 'title': 'Story 0', 'posted': '1 hours ago'},
                                  {'id': 38783, 'title': 'Story 1', 'posted': '2 hours ago'}]

    def test_works_without_explicit_timezone(self):
        assert News(None).get_last_news(fx.soup(fx.news()))[0]['date']

    def test_only_featured(self):
        res = News(TZ).get_last_news(fx.soup(fx.news()), only_featured=True)
        assert res[0]['news'] == [] and len(res[0]['f_news']) == 1

    def test_all_days(self):
        res = News(TZ).get_last_news(fx.soup(fx.news(1)), max_reg_news=5, only_today=False)
        assert len(res) == 2 and res[1]['news'][0]['id'] == 38000


# --- date helpers ----------------------------------------------------------------

class TestDateTools:
    def test_normalize_date(self):
        assert datetools.normalize_date(['Apr', '1st']) == '1-4'
        assert datetools.normalize_date(['Feb', '13th']) == '13-2'

    def test_normalize_date_headline(self):
        assert datetools.normalize_date_('Results for April 14th 2024') == '14-04-2024'

    @pytest.mark.parametrize('tz', [None, 'UTC', 'Europe/Copenhagen'])
    def test_localize_from_date_string(self, tz):
        assert datetools.localize_datetime_to_timezone(tz, date_str='14-04-2024').strftime('%d-%m-%Y') in (
            '14-04-2024', '13-04-2024')
