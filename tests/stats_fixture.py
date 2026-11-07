"""HTML builder that mirrors the markup of HLTV's /stats/matches pages (copied from a real IEM Beijing 2026 page)."""

import html
import json

PLAYER_TIP = '<div class="hidden" id="tip"></div>'

# nickname, id, country, opkd, mks, kast, clutches, kills, hs, assists, flash, deaths, traded, adr, swing, rating
MOUZ_BOTH = [
    ('xertioN', 20312, 'Israel', '6 : 3', 12, '73.2%', 1, 40, 21, 10, 2, 20, 4, '111.0', '+4.93%', '1.67'),
    ('PR', 22279, 'Czech Republic', '9 : 5', 10, '78.0%', 0, 35, 18, 12, 1, 20, 4, '90.5', '+3.35%', '1.43'),
]
MOUZ_CT = [
    ('PR', 22279, 'Czech Republic', '5 : 1', 6, '76.2%', 0, 20, 9, 5, 0, 9, 2, '96.4', '+8.69%', '1.79'),
    ('xertioN', 20312, 'Israel', '3 : 1', 6, '76.2%', 0, 22, 9, 3, 1, 9, 1, '112.5', '+4.21%', '1.59'),
]
MOUZ_T = [
    ('xertioN', 20312, 'Israel', '3 : 2', 6, '70.0%', 1, 18, 12, 7, 1, 11, 3, '109.4', '+5.69%', '1.75'),
    ('PR', 22279, 'Czech Republic', '4 : 4', 4, '80.0%', 0, 15, 9, 7, 1, 11, 2, '84.3', '-2.26%', '1.04'),
]
BB_BOTH = [
    ('S1ren', 18506, 'Russia', '3 : 3', 6, '61.0%', 1, 30, 15, 4, 2, 28, 1, '80.0', '+1.50%', '1.11'),
    ('d1Ledez', 20357, 'Russia', '2 : 4', 2, '65.9%', 0, 18, 8, 7, 0, 34, 5, '56.1', '-6.40%', '0.59'),
]
BB_CT = [BB_BOTH[0][:3] + ('2 : 3', 3, '70.0%', 1, 15, 7, 1, 0, 12, 0, '79.8', '+1.94%', '1.14'),
         BB_BOTH[1][:3] + ('1 : 0', 1, '65.0%', 0, 7, 4, 4, 0, 17, 3, '50.2', '-9.16%', '0.44')]
BB_T = [BB_BOTH[0][:3] + ('1 : 0', 3, '52.4%', 0, 15, 8, 3, 2, 16, 1, '80.2', '+1.08%', '1.08'),
        BB_BOTH[1][:3] + ('1 : 4', 1, '66.7%', 0, 11, 4, 3, 0, 17, 2, '61.8', '-3.76%', '0.73')]


def _row(p):
    nick, pid, country, opkd, mks, kast, clutch, k, hs, a, f, d, t, adr, swing, rating = p
    cls = 'won' if swing.startswith('+') else 'lost'
    rcls = 'ratingPositive' if float(rating) >= 1.05 else 'ratingNegative'
    return (
        f'<tr><td class="st-player"><div class="flag-align"><img alt="{country}" class="flag" title="{country}">'
        f'<a href="/stats/players/{pid}/{nick.lower()}" class="text-ellipsis">{nick}</a></div></td>'
        f'<td class="st-opkd gtSmartphone-only traditional-data">{opkd}</td>'
        f'<td class="st-opkd gtSmartphone-only eco-adjusted-data hidden">{opkd}</td>'
        f'<td class="st-mks gtSmartphone-only">{mks}</td>'
        f'<td class="st-kast gtSmartphone-only traditional-data">{kast}</td>'
        f'<td class="st-kast gtSmartphone-only eco-adjusted-data hidden">70.0%</td>'
        f'<td class="st-clutches gtSmartphone-only">{clutch}</td>'
        f'<td class="st-kills traditional-data">{k}<span class="gtSmartphone-only"> ({hs})</span></td>'
        f'<td class="st-kills eco-adjusted-data hidden">{k + 1}<span class="gtSmartphone-only"> ({hs})</span></td>'
        f'<td class="st-assists">{a}<span class="gtSmartphone-only" title="Flash assists"> ({f})</span></td>'
        f'<td class="st-deaths traditional-data">{d}<span class="gtSmartphone-only"> ({t})</span></td>'
        f'<td class="st-deaths eco-adjusted-data hidden">{d + 1}<span class="gtSmartphone-only"> ({t})</span></td>'
        f'<td class="st-adr traditional-data">{adr}</td><td class="st-adr eco-adjusted-data hidden">100.5</td>'
        f'<td class="st-kast smartphone-only traditional-data">{kast}</td>'
        f'<td class="st-kast smartphone-only eco-adjusted-data hidden">70.0%</td>'
        f'<td class="st-roundSwing {cls}">{swing}</td><td class="st-rating {rcls}">{rating}</td></tr>')


def _table(kind, team, rows):
    hidden = '' if kind == 'totalstats' else ' hidden'
    return (f'<div class="stats-content "><table class="stats-table {kind}{hidden}"><thead><tr>'
            f'<th class="st-teamname text-ellipsis"><img alt="{team}" class="logo" title="{team}">{team}</th>'
            f'<th class="st-rating">Rating<span class="ratingDesc">3.0</span></th></tr></thead><tbody>'
            + ''.join(_row(p) for p in rows) + '</tbody></table></div>' + PLAYER_TIP)


def _most(title, pid, nick, value):
    return (f'<div class="most-x-box standard-box"><div class="name"><a href="/stats/players/{pid}/{nick.lower()}">{nick}</a>'
            f'<br><span class="most-x-title">{title}</span></div><div class="value"><span class="valueName">{value}</span></div></div>')


def _tile(href, score, name, winner):
    return (f'<a href="{href}" class="col stats-match-map standard-box a-reset inactive"><div class="stats-match-map-desc">'
            f'<div class="stats-match-map-result"><div class="stats-match-map-result-score">{score}</div>'
            f'<div class="stats-match-map-result-mapname dynamic-map-name-short">{name[:3].lower()}</div>'
            f'<div class="stats-match-map-result-mapname dynamic-map-name-full">{name}</div></div>'
            f'<div class="stats-match-map-winner-logo-con"><img class="stats-match-map-winner-logo" title="{winner}"></div>'
            f'</div></a>')


def stats_page(map_name='All', rounds=False, tables=True):
    chart = {'data': {'datasets': [{'data': [{'category': 'xertioN', 'value': 1.67, 'showLabel': True},
                                             {'category': 'd1Ledez', 'value': 0.59, 'showLabel': True}]}]}}
    history = ''
    if rounds:
        def img(name, title):
            return f'<img src="/img/static/scoreboard/{name}.svg" title="{title}" class="round-history-outcome">'
        history = ('<div class="round-history-con">'
                   '<div class="round-history-team-row"><img title="MOUZ" class="round-history-team">'
                   + img('ct_win', '1-0') + img('emptyHistory', '') + img('bomb_exploded', '2-1') + '</div>'
                   '<div class="round-history-team-row"><img title="BETBOOM" class="round-history-team">'
                   + img('emptyHistory', '') + img('t_win', '1-1') + img('emptyHistory', '') + '</div></div>')
    body = ''
    if tables:
        body = (_table('totalstats', 'MOUZ', MOUZ_BOTH) + _table('ctstats', 'MOUZ', MOUZ_CT) + _table('tstats', 'MOUZ', MOUZ_T)
                + _table('totalstats', 'BETBOOM', BB_BOTH) + _table('ctstats', 'BETBOOM', BB_CT) + _table('tstats', 'BETBOOM', BB_T))
    return (
        '<div class="stats-section stats-match"><div class="stats-match-maps"><div class="columns">'
        '<a href="/stats/matches/132835/mouz-vs-betboom" class="col stats-match-map standard-box a-reset">'
        '<div class="stats-match-map-desc"><div class="stats-match-map-result"><div class="stats-match-map-result-score">2 - 0</div>'
        '<div class="stats-match-map-result-mapname dynamic-map-name-short">bo3</div>'
        '<div class="stats-match-map-result-mapname dynamic-map-name-full">Best of 3</div></div>'
        '<div class="stats-match-map-winner-logo-con"><img class="stats-match-map-winner-logo" title="MOUZ"></div></div></a>'
        + _tile('/stats/matches/mapstatsid/243791/mouz-vs-betboom', '13 - 7', 'Ancient', 'MOUZ')
        + _tile('/stats/matches/mapstatsid/243795/betboom-vs-mouz', '13 - 8', 'Mirage', 'MOUZ')
        + '<div class="col stats-match-map"></div></div></div>'
        '<div class="match-info-box-con"><div class="match-info-box">'
        '<a href="/stats?event=8245" class="block text-ellipsis">IEM Beijing 2026</a>'
        '<div class="small-text"><span data-time-format="yyyy-MM-dd HH:mm" data-unix="1794044700000">2026-11-07 09:45</span>'
        f'<br><br><span class="bold">Map</span></div>{map_name}'
        '<div class="team-left"><img alt="MOUZ" class="team-logo" title="MOUZ"><a href="/stats/teams/4494/mouz" class="block text-ellipsis">MOUZ</a>'
        '<div class="bold won">2</div></div>'
        '<div class="team-right"><img alt="BETBOOM" class="team-logo" title="BETBOOM"><a href="/stats/teams/12394/betboom" class="block text-ellipsis">BETBOOM</a>'
        '<div class="bold lost">0</div></div>'
        '<div class="match-info-row"><div class="right">1.24 : 0.81</div><div class="bold">Team rating 3.0</div></div>'
        '<div class="match-info-row"><div class="right">25 : 16</div><div class="bold">First kills</div></div>'
        '<div class="match-info-row"><div class="right">3 : 2</div><div class="bold">Clutches won</div></div>'
        '<div class="match-info-row"><div class="right">8 : 4 (5 : 3)</div><div class="bold">Breakdown</div></div>'
        '<a href="/matches/2400009/mouz-vs-betboom-iem-beijing-2026" class="match-page-link button">More info on match page</a>'
        '</div></div>'
        '<div class="col top-players">' + _most('Most kills', 20312, 'xertioN', 40) + _most('Most damage', 20312, 'xertioN', '111.0')
        + _most('Best rating 3.0', 20312, 'xertioN', '1.67') + '</div>'
        f'<worker-ignore class="graph" data-chartjs-config="{html.escape(json.dumps(chart), quote=True)}"></worker-ignore>'
        + history + body + '</div>')
