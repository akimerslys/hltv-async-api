"""Synthetic HLTV pages.

The live site sits behind a Cloudflare challenge, so these pages are hand-written to
follow the markup the parsers select on. They guard against parser regressions; they do
not prove the parsers match HLTV's current markup. Refresh them from real saved pages
when possible.
"""

from bs4 import BeautifulSoup


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, 'lxml')




def _wrapper(match_id, stars, t1, t2, ids, meta, event, time=None, logo=True):
    event_html = (f'<img class="match-event-logo" title="{event}">' if logo
                  else event)
    teams = ''.join(
        f'<div class="match-team"><div class="match-teamname">{n}</div></div>' if n else '<div class="match-team"></div>'
        for n in (t1, t2))
    time_html = f'<div class="match-time">{time}</div>' if time else '<div class="match-meta match-meta-live">Live</div>'
    return (f'<div class="match-wrapper" data-match-id="{match_id}" data-stars="{stars}" '
            f'team1="{ids[0]}" team2="{ids[1]}"><div class="match">'
            f'<a class="match-top"><div class="match-event">{event_html}</div></a>'
            f'<div class="match-bottom"><a class="match-info">{time_html}<div class="match-meta">{meta}</div></a>'
            f'<a class="match-teams">{teams}</a></div></div></div>')


MATCHES = (
    '<div class="liveMatchesSection">'
    + _wrapper(2371201, 2, 'Imperial', 'MIBR', (9455, 9215), 'bo3', 'RES Regional Series 3 LATAM')
    + _wrapper(1, 0, 'Low', 'Rated', (1, 2), 'bo1', 'x')
    + '</div>'
    '<div class="matches-list-section"><span class="matches-list-headline">Tuesday - 2024-04-16</span>'
    + _wrapper(2370964, 1, 'SAW', 'Sampi', (10567, 10695), 'bo3', 'Thunderpick World Championship 2024', '12:30')
    + _wrapper(2370965, 0, None, None, ('', ''), 'bo3', 'Some Qualifier', '14:00', logo=False)
    + _wrapper(2370966, 1, 'FaZe', None, (6667, ''), 'bo1', 'Some Qualifier', '16:00', logo=False)
    + '</div>'
    '<div class="matches-list-section"><span class="matches-list-headline">Wednesday - 2024-04-17</span>'
    + _wrapper(2371367, 3, 'Gaimin Gladiators', 'Permitta', (11571, 12009), 'bo3',
               'Elisa Invitational Spring 2024', '14:00')
    + '</div>'
)


def _map(name, left=None, right=None, pick=None):
    score = ''
    if left is not None:
        score = (f'<div class="results-left{" pick" if pick == 1 else ""}">'
                 f'<div class="results-team-score">{left}</div></div>'
                 f'<span class="results-right{" pick" if pick == 2 else ""}">'
                 f'<div class="results-team-score">{right}</div></span>')
    return f'<div class="mapholder"><div class="mapname">{name}</div>{score}</div>'


def _stat_rows(players):
    rows = '<tr><th>Player</th></tr>'
    for pid, slug, nick, kd, adr, rating in players:
        rows += (f'<tr><td><a class="flagAlign" href="/player/{pid}/{slug}">'
                 f'<div class="statsPlayerName">First \'{nick}\' Last</div></a></td>'
                 f'<td class="kd">{kd}</td><td class="adr">{adr}</td>'
                 f'<td class="rating">{rating}</td></tr>')
    return f'<table class="table totalstats">{rows}</table>'


MATCH_OVER = (
        '<div class="countdown">Match over</div>'
        '<div class="team"><div class="teamName">MOUZ</div>\n<div class="lost">0</div></div>'
        '<div class="team"><div class="teamName">FaZe</div>\n<div class="won">2</div></div>'
        + _map('Overpass', 10, 13, pick=1) + _map('Nuke', 6, 13, pick=2) + _map('Mirage')
        + _stat_rows([(18850, 'jimpphat', 'Jimpphat', '33-29', '80.9', '1.08'),
                      (18072, 'torzsi', 'torzsi', '26-25', '70.5', '1.02')])
        + _stat_rows([(18053, 'broky', 'broky', '34-22', '79.3', '1.33')])
)

MATCH_LIVE = (
        '<div class="countdown">LIVE</div>'
        + _map('Vertigo', 6, 13) + _map('Mirage', '-', '-') + _map('Anubis', '-', '-')
)

MATCH_UPCOMING = (
        '<div class="countdown">1d : 2h : 3m : 4s</div>'
        + _map('TBA')
        + '<div class="standard-box pick-a-winner"><div class="percentage">62%</div>'
          '<div class="percentage">38%</div></div>'
)


def _result(match_id, t1, t2, s1, s2, event, stars=0):
    star_html = '<i class="fa fa-star star"></i>' * stars
    return (f'<a class="a-reset" href="/matches/{match_id}/{t1}-vs-{t2}">'
            f'<div class="result"><table><tr><td class="team-cell">{t1}</td><td class="team-cell">{t2}</td>'
            f'<td class="result-score">{s1} - {s2}</td></tr></table></div>'
            f'<span class="event-name">{event}</span>{star_html}</a>')


RESULTS = (
        '<div class="results-sublist"><div class="big-results">'
        + _result(2370931, 'MOUZ', 'FaZe', 0, 2, 'IEM Chengdu 2024')
        + '</div></div>'
        + '<div class="results-sublist"><span class="standard-headline">Results for April 14th 2024</span>'
        + _result(2370931, 'MOUZ', 'FaZe', 0, 2, 'IEM Chengdu 2024', stars=3)
        + _result(2370932, 'NAVI', 'G2', 2, 1, 'IEM Chengdu 2024', stars=1)
        + _result(2370933, 'Low', 'Rated', 1, 0, 'Minor Cup')
        + '</div>'
        + '<div class="results-sublist"><span class="standard-headline">Results for April 13th 2024</span>'
        + _result(2370900, 'Vitality', 'Spirit', 2, 0, 'IEM Chengdu 2024', stars=2)
        + '</div>'
)

EVENT_RESULTS = (
        '<div class="results-holder">'
        '<div class="results-sublist"><span class="standard-headline">Results for April 14th 2024</span>'
        '<a class="a-reset" href="/matches/2370931/mouz-vs-faze"><div class="team">MOUZ</div>'
        '<div class="team">FaZe</div><div class="result"><table><tr><td class="result-score">0 - 2</td></tr></table></div></a>'
        '<a class="a-reset" href="/matches/2370932/navi-vs-g2"><div class="team">NAVI</div>'
        '<div class="team">G2</div><div class="result"><table><tr><td class="result-score">2 - 1</td></tr></table></div></a>'
        '</div>'
        '<div class="results-sublist"><span class="standard-headline">Results for April 13th 2024</span>'
        '<a class="a-reset" href="/matches/2370900/vit-vs-spirit"><div class="team">Vitality</div>'
        '<div class="team">Spirit</div><div class="result"><table><tr><td class="result-score">2 - 0</td></tr></table></div></a>'
        '</div></div>'
)

EVENT_MATCHES = (
    '<div class="liveMatchesSection">'
    + _wrapper(2371201, 2, 'Imperial', 'MIBR', (9455, 9215), 'bo3', 'x')
    + '</div>'
    '<div class="matches-list-section"><span class="matches-list-headline">Thursday - 2024-04-18</span>'
    + _wrapper(2370771, 0, 'Monte', 'paiN', (11811, 4773), 'bo3', 'x', '15:30')
    + _wrapper(2370775, 0, None, None, ('', ''), 'bo3', 'x', '21:30', logo=False)
    + '</div>'
)

EVENTS = """
<div class="tab-content" id="TODAY">
  <a class="a-reset ongoing-event" href="/events/7749/thunderpick-closed">
    <div class="text-ellipsis">Thunderpick World Championship 2024 EU Closed Qualifier 1</div>
    <span data-time-format="MMM do">Apr 1st</span><span data-time-format="MMM do">Apr 22nd</span>
  </a>
  <a class="a-reset ongoing-event" href="/events/7621/ecl-47">
    <div class="text-ellipsis">ESL Challenger League Season 47 North America</div>
    <span data-time-format="MMM do">Feb 13th</span><span data-time-format="MMM do">Jun 16th</span>
  </a>
</div>
<div class="big-events">
  <a class="a-reset standard-box big-event" href="/events/7900/iem-cologne">
    <div class="big-event-name">IEM Cologne 2024</div>
    <span data-unix="1">Aug 13th</span><span> - Aug 15th</span><span data-unix="2">Aug 15th</span>
  </a>
  <a class="a-reset standard-box big-event" href="/events/7901/blast-x">
    <div class="big-event-name">BLAST X 2024</div>
    <span data-unix="1">Sep 2nd</span><span> - Sep 4th</span><span data-unix="2">Sep 4th</span>
  </a>
</div>
"""


def event_info(start_ms, end_ms, finished: bool):
    base = (f'<table><tr><td class="eventdate"><span data-unix="{start_ms}"></span>'
            f'<span data-unix="{end_ms}"></span></td>'
            '<td class="prizepool text-ellipsis">$1,250,000</td>'
            '<td class="teamsNumber">16</td>'
            '<td class="location gtSmartphone-only">\nCopenhagen, Denmark\n</td>')
    if finished:
        return (base + '<div class="player-and-coin"><a href="/player/18053/broky">\'broky\'</a></div>'
                       '<div class="placement"><div class="team"><a href="/team/6667/faze">FaZe</a></div>'
                       '<div class="prize">$500,000</div></div>'
                       '<div class="placement"><div class="team"><a href="/team/4608/navi">NAVI</a></div>'
                       '<div class="prize">$200,000</div></div>')
    return (base + '<div class="col standard-box team-box supports-hover"><a href="/team/6667/faze"></a>'
                   '<div class="text-container">FaZe</div></div>'
                   '<div class="col standard-box team-box supports-hover"><a href="/team/4608/navi"></a>'
                   '<div class="text-container">Natus Vincere</div></div>')


def _ranked(rank, name, points, change, change_cls, team_id):
    cls = 'teamLine sectionTeamPlayers teamLineExpanded' if rank == 1 else 'teamLine sectionTeamPlayers'
    return (f'<div class="ranked-team standard-box"><span class="position">#{rank}</span>'
            f'<div class="{cls}"><span class="name">{name}</span>'
            f'<span class="points">({points} points)</span></div>'
            f'<div class="change {change_cls}">{change}</div>'
            f'<a class="details moreLink" href="/team/{team_id}">Details</a></div>')


TOP_TEAMS = (_ranked(1, 'FaZe', 939, '-', 'neutral', 6667)
             + _ranked(2, 'Natus Vincere', 757, '+4', 'positive', 4608)
             + _ranked(3, 'Vitality', 700, '-1', 'negative', 9565))

TEAM_INFO = """
<div class="bodyshot-team g-grid">
  <a href="/player/429/karrigan"><span class="text-ellipsis bold">karrigan</span></a>
  <a href="/player/8183/rain"><span class="text-ellipsis bold">rain</span></a>
</div>
<div class="profile-team-stat"><b><span class="regional-name-full">Valve ranking</span></b>
  <span class="right"><a href="/valve-ranking">#19(EU#14)</a></span></div>
<div class="profile-team-stat"><b>World ranking</b><span class="right"><a href="/ranking/teams">#1(#1)</a></span></div>
<div class="profile-team-stat"><b>Weeks in top30 for core</b><span class="right">260</span></div>
<div class="profile-team-stat"><b>Average player age</b><span class="right">26.6</span></div>
<div class="profile-team-stat"><b>Coach</b><a class="a-reset right" href="/coach/1/neo">
  <img class="flag" title="Poland"> Filip <span class="bold a-default">'NEO'</span> Kubski</a></div>
<div class="profile-team-logo-container"><img src="/dark.svg"><img src="/logo.svg"></div>
<div class="trophyHolder"><span title="IEM Chengdu 2024"></span></div>
<div class="trophyHolder"><span title="Older Cup"></span></div>
"""


def top_players(n=3):
    rows = ''
    data = [(19230, 'm0nesy', 'G2', 44, '1.37', 'Positive'),
            (18053, 'broky', 'FaZe', 54, '1.19', 'Positive'),
            (7998, 's1mple', 'Natus Vincere', 50, '1.00', 'Neutral')]
    for pid, nick, team, maps, rating, kind in data[:n]:
        rows += (f'<tr><td class="playerCol"><a href="/stats/players/{pid}/{nick}">{nick}</a></td>'
                 f'<td class="teamCol" data-sort="{team}"></td><td class="statsDetail">{maps}</td>'
                 f'<td class="ratingCol rating{kind}">{rating}</td></tr>')
    return f'<table><tbody>{rows}</tbody></table>'


PLAYER_INFO = """
<div class="playerInfoRow playerTeam"><span class="listRight"><a href="/team/4608/natus-vincere">Natus Vincere</a></span></div>
<img class="flag" title="Ukraine"><div class="playerRealname"> Oleksandr Kostyliev</div>
<div class="playerInfoRow playerAge"><span class="listRight">26 years</span></div>
<div class="player-stat"><b>Rating 3.0</b><span class="statsVal"><p>0.94</p></span></div>
<div class="player-stat"><b>Firepower</b><span class="statsVal"><p>78</p></span></div>
<div class="all-time-stat"><div class="stat">57.9%</div><div class="description">Headshots</div></div>
<img class="player-summary-stat-box-left-bodyshot" src="/s1mple.png">
<div class="trophyRow">
  <div class="trophy"><div class="trophyHolder"><span class="trophyDescription" title="MVP winner at: x"></span></div>
    <div class="mvp-count">21</div></div>
  <a class="trophy" href="/events/6000/blast-spring-final-2022">
    <span class="trophyDescription" title="BLAST Premier Spring Final 2022"></span></a>
  <a class="trophy" href="/news/1/top-20-players"><span class="trophyDescription" title="#7 best player in 23"></span></a>
</div>
<div class="col-6 text-ellipsis"><h2>s1mple statistics</h2></div>
<div class="col-6 text-ellipsis"><h2>Upcoming &amp; recent matches</h2>
  <a class="playerpage-matchbox a-reset" href="/matches/2399613/navi-vs-x"></a>
  <a class="playerpage-matchbox a-reset" href="/stats/matches/mapstatsid/99745/navi-vs-y"></a>
</div>
"""


def news(today_count=3):
    featured = ('<a class="newsline article featured breaking-featured" href="/news/38790/big-news">'
                '<div class="featured-newstext">Big news</div>'
                '<div class="featured-small-newstext">Details</div></a>')
    regular = ''.join(
        f'<a class="newsline article" href="/news/{38784 - i}/story-{i}">'
        f'<div class="newstext">Story {i}</div><div class="newsrecent">{i + 1} hours ago</div></a>'
        for i in range(today_count))
    return (f'<div class="standard-box standard-list">{featured}{regular}</div>'
            '<div class="standard-box standard-list"><a class="newsline article" href="/news/38000/yesterday">'
            '<div class="newstext">Yesterday</div><div class="newsrecent">1 day ago</div></a></div>')
