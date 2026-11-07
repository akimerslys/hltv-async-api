# hltv-async-api an **unofficial** asynchronous HLTV API Wrapper for Python.

# IMPORTANT

HLTV sits behind Cloudflare and often answers plain HTTP requests with **403**. An optional **Selenium undetected driver** is now available: see [Selenium (undetected driver)](#selenium-undetected-driver).

Dont forget to star a repo.

# Future

* **0.10.0** stats & images update, more stats scrapers, team logos, player photos, images, more data, team_map stats, map stats, more functions such as get_news_id, get_team_logo, get_player_photo, get_demo_id, get_match_stats. Coverage. (?) Rotating user agent

* **FUTURE** Switch from requests to Selenium driver && Live data with socket.io && Provide to use Hltv-async-api on any system, language, by creating a RESTful service.


# Features


* **Simple Usage** (its really simple)


* **New and modern fully async library**


* **Huge amount of options and methods**


* **Supports proxy usage**


* **Made with love <3**


---

# Installation

```
pip install hltv-async-api
```

Optional extras:

```
pip install "hltv-async-api[sync]"      # synchronous client (requests)
pip install "hltv-async-api[selenium]"  # undetected Chrome driver, use it when HLTV answers 403
pip install "hltv-async-api[live]"      # live match data over sockets
```

---


# Simple Usage

  ```
    
    from hltv_async_api import Hltv
    
    async def main():
      async with Hltv() as hltv:
        print(await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))
        
    if __name__ == '__main__':
      import asyncio
      asyncio.run(main())

  ```


# Synchronus Usage (Beta)

  _For high perfomance usage recommended to use async version, it's 5x faster, and more stable._

  ```
  
    from hltv_async_api.sync import Hltv
    
    hltv = Hltv()

    print(hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))
  
  ```


---

# Selenium (undetected driver)

HLTV protects its pages with Cloudflare, so plain HTTP requests often fail with `403`. When that happens the library
logs a hint once:

```
[ERROR] | HLTV answered 403 / Cloudflare challenge, plain HTTP requests are being blocked. Install the optional browser
driver with: pip install "hltv-async-api[selenium]" and create the client with Hltv(selenium=True).
```

The optional driver opens a real Chrome window through [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
and reads the pages from it. Every method keeps the same name, arguments and output; only the way pages are fetched changes.

**Requirements**

* Google Chrome installed on the machine.
* `pip install "hltv-async-api[selenium]"`. On the first run undetected-chromedriver downloads a ChromeDriver that
  matches your Chrome version.

**Async usage**

```
import asyncio
from hltv_async_api import Hltv


async def main():
    async with Hltv(selenium=True) as hltv:   # the browser is closed when the block ends
        print(await hltv.get_top_teams(5))
        print(await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))


if __name__ == '__main__':
    asyncio.run(main())
```

**Sync usage**

```
from hltv_async_api.sync import Hltv

with Hltv(selenium=True) as hltv:
    print(hltv.get_top_teams(5))
```

Without `with`, call `await hltv.close()` (async) or `hltv.close()` (sync) when you are done, otherwise Chrome stays open.

**Options**

Pass them as a dict in `selenium_options`:

```
hltv = Hltv(selenium=True, selenium_options={
    'headless': False,                 # Cloudflare detects headless Chrome more often, so the default is False
    'version_main': 130,               # force the ChromeDriver for this Chrome major version
    'challenge_timeout': 30,           # seconds to wait for the Cloudflare check to finish on its own
    'page_load_timeout': 30,           # seconds to wait for a page to load
    'proxy': 'http://1.2.3.4:8080',
    'user_data_dir': './chrome-profile',   # keeps the Cloudflare clearance cookie between runs
    'pool_size': 4,                    # Chrome windows working in parallel (default 1)
    'page_load_strategy': 'eager',     # 'normal' waits for every ad and tracker too
})
```

**Good to know**

* One browser loads one page at a time. Set `pool_size` (for example `selenium_options={'pool_size': 4}`) to run several
  Chrome windows side by side; `asyncio.gather` then fetches that many pages in parallel. Each window is a full Chrome, mind your RAM.
  With `user_data_dir` every window gets its own copy (`<dir>-1`, `<dir>-2`, ...).
* `page_load_strategy` is `'eager'` by default: a page is read as soon as its HTML is ready instead of waiting for every ad and tracker,
  which is much faster. Use `'normal'` to wait for everything.
* `max_retries` is respected (3 attempts when it is `0`). `min_delay`, `max_delay`, `max_concurrency` and the proxy options of the HTTP
  client are not used in this mode; use `pool_size` and `proxy` in `selenium_options` instead.
* It does not guarantee a pass: Cloudflare changes its checks regularly. If a page never gets through, the method
  returns `None` and logs `Connection failed`. Try `user_data_dir`, a different `version_main`, or a clean IP.
* If the downloaded ChromeDriver does not match your Chrome (`This version of ChromeDriver only supports Chrome version X`), the
  library reads your Chrome version from the error and retries with a matching driver. You can also set `version_main` yourself.
* If the extra is missing, `Hltv(selenium=True)` raises an `ImportError` telling you what to install.
* Use it responsibly and respect HLTV's terms and `robots.txt`. The library is meant for non-commercial use.

---

# Live match data (sockets)

HLTV's live scoreboard is fed by a Socket.IO "scorebot". The optional `live` extra connects to it:

```bash
pip install "hltv-async-api[live]"      # or: pip install -r requirements-live.txt
```

One-shot snapshot of a live match (returns `None` if the match is not live or nothing arrived within `timeout`):

```python
data = await hltv.get_match_data(2400302, timeout=15)
# {'match_id': 2400302,
#  'score': {'wins': {team_id: maps_won},
#            'maps': [{'map': 'de_dust2', 'ordinal': 1, 'over': False, 'scores': {team_id: rounds},
#                      'ct_team_id': .., 't_team_id': .., 'first_half': {..}, 'second_half': {..}, 'overtime': None}],
#            'current_map': {...}, 'forced_live': False, 'forced_dead': False},
#  'scoreboard': <raw>, 'log': [<raw>, ...]}
```

Continuous updates:

```python
live = await hltv.live_match(2400302, on_event=lambda event, data: print(event, data))
# or iterate:
async for event, data in live.updates():
    if event == 'score':
        print(data['current_map']['scores'])
await live.close()   # also done by hltv.close()
```

* `score` events are parsed into the structure above. `scoreboard`, `log` and `fullLog` events are passed through
  exactly as the socket sends them, because their format is not documented.
* Extra options (`cookies`, `user_agent`) are passed to `hltv_async_api.live.LiveMatch`.
* The socket needs no HLTV page request, but Cloudflare may still refuse it; the library does not try to bypass
  any bot protection. If the extra is missing, a clear `ImportError` explains what to install.

# Configs

* max_delay: float | None = None

  Nothing is waited between retries unless you set `min_delay` / `max_delay`. With only `max_delay` the pause grows by 1 sec
  per failed try up to that value:

  ```
    hltv = Hltv(max_delay=5)

    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Increasing delay to 1s
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Increasing delay to 2s
  ```

* min_delay: float | None = None

  Wait a random time between `min_delay` and `max_delay` before every retry instead.

```
  [DEBUG] Random delay 9.55s
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 3/10
  [DEBUG] Random delay 3.9s
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 4/10
```

* max_concurrency: int = 10

  How many requests may be in flight at once. `0` removes the limit. Start your calls together to use it:

  ```
  teams = await hltv.get_top_teams(30)
  infos = await asyncio.gather(*(hltv.get_team_info(t['id'], t['title']) for t in teams))
  ```
  Raise it for speed, lower it if HLTV answers 429 / 403.

* proxy_delay: bool = False

    Delay for proxy uses.
* 
  ```
  [INFO] New proxy: http://123.123.123.123:123 
  [DEBUG] Random delay 9.55s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 3/10
  [DEBUG] Switching proxy http://123.123.123.123:123 
  [INFO] New proxy: http://111.111.111.11:111 
  [DEBUG] Random delay 3.9s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 4/10
  ```

* max_retries: int = 10

    0 for infinity retries
    
    ```
    hltv = Hltv(max_retries=2, debug=True)
    print(await hltv.get_top_players())
    
    >>>Creating Session
    >>>Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 1/2
    >>>Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 2/2
    >>>Connection failed
    ```

* proxy_list: list | None = None

    Proxys. _len(proxy_list) >= 1_
    Note: To add non-proxy to list just put '' to it, you can find template in examples.

* proxy_path: str | None = None

    Path to your proxy file(proxy_list will be ignored). One proxy per line.

* proxy_protocol: str | None = None,

    Proxy protocol. Your proxies ```hltv = Hltv(proxy_protocol='http' ...) -> '11.11.11.11:1111' -> 'http://11.11.11.11:1111'

* remove_proxy: bool = False

    Removes proxy from list if connection unsuccessfully (proxy_path included)

* timeout: int = 5

    Timeout for connection in seconds.

* debug: bool = False

* tz: str = 'Europe/Copenhagen':
    
    Timezone config. 
 
    <a href='https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568'>Tap here </a> to see all available timezones

* safe_mode: bool = False

    Opt-in. When `True`, the methods that return restricted data (`get_matches`, `get_match_info`, `get_results`, `get_top_players`, `get_match_data`, `live_match`) are locked and
    return `None`. Nothing is locked by default.

* aiohttp_session: aiohttp.ClientSession | None = None

    Custom aiohttp session, if you want to use your own session.

* selenium: bool = False

    Fetch pages with an undetected Chrome driver instead of plain HTTP requests. Needs `pip install "hltv-async-api[selenium]"`, see [Selenium (undetected driver)](#selenium-undetected-driver).

* selenium_options: dict | None = None

    Options for the Selenium driver: `headless`, `version_main`, `challenge_timeout`, `page_load_timeout`, `proxy`, `user_data_dir`, `pool_size`, `page_load_strategy`.

---

# Proxy Usage

**Load Proxies from list**
    
    ```
    proxy_list = ['http://120.234.203.171:9002', 'http://110.38.68.38:80']
    
    hltv = Hltv(proxy_list=proxy_list)

    ```

**Load Proxies from file**

    ```
    hltv = Hltv(proxy_path='PATH_TO_PROXY.TXT')
    ```


**Remove proxy**

    Removes bad proxies
    
    ```
    hltv = Hltv(proxy_path='PATH_TO_PROXY.TXT', remove_proxy=True)
    ```

**Protocol usage**

    ```
    proxy_list = ['120.234.203.171:9002', '110.38.68.38:80']
    
    hltv = Hltv(proxy_list=proxy_list, proxy_protocol='http')
    ```

---

# Methods

Every id, score, rank and count is returned as a number (`int`), ratings / ADR / age / headshot ratio as `float`.
Fields that can legitimately be text stay text: names, dates, `status`, `prize`, `team_count` (can be `'TBA'`),
`kd` (`'33-29'`) and `posted` (`'an hour ago'`). A value that is not available yet is `0` / `0.0`, never `'-'` or `''`.

* **get_matches(days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True)**

    -days (the number of days into the future to fetch matches for)

    -min_rating (the minimum star rating for matches to include)

    ```
    await hltv.get_matches(days=1, min_rating=3)

    >>> [{'id': 2399417, 'date': 'LIVE', 'time': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM', 't1_id': 8297, 't2_id': 12394, 'maps': 5, 'rating': 4, 'event': 'Thunderpick World Championship 2026'}]
    ```
    `maps` is the best-of (`0` when unknown), `date` is `'dd-mm-yyyy'` and `t1_id` / `t2_id` are `0` for `TBD` teams.

* **get_match_info(match_id: int | str, team1, team2, event_title, stats: bool = True, predicts: bool = True)**

    ```
    await hltv.get_match_info(2373774, 'Astralis', 'Falcons', 'BLAST Premier Fall Groups 2024')

    >>> {'id': 2373774, 'status': 'Match over',
         'maps': [{'mapname': 'Dust2', 'r_team1': 13, 'r_team2': 7, 'pick': 'Falcons', 'stats_id': 180037},
                  {'mapname': 'Ancient', 'r_team1': 13, 'r_team2': 9, 'pick': 'Astralis', 'stats_id': 180040},
                  {'mapname': 'Nuke', 'r_team1': 0, 'r_team2': 0, 'pick': '', 'stats_id': 0}],
         'stats': [{'id': 17956, 'nickname': 'jabbi', 'kd': '42-30', 'adr': 91.6, 'rating': 1.43}, ...],
         'stats_id': 132835, 'score1': 2, 'score2': 0}
    ```
    `stats_id` (and `stats_id` of every map) lead to [get_match_stats](#methods); `0` when the match has no statistics.
    `status` is `'Match over'`, `'LIVE'` or the start time (`'dd-mm-yyyy-HH-MM'`) of an upcoming match, which also gets
    `predict1` / `predict2` (win chance in percent, `int`). `r_team1` / `r_team2` are `0` while a map is not played.

* **get_results(days: int = 1, min_rating: int = 1, max: int = 30, featured: bool = True, regular: bool = True)**

    ```
    await hltv.get_results(days=1, min_rating=3, max=1)

    >>> [{'id': 2400004, 'team1': 'Natus Vincere', 'team2': 'Falcons', 'score1': 2, 'score2': 1, 'rating': 3, 'event': 'IEM Beijing 2026'}]
    ```

* **get_events(outgoing: bool = True, future: bool = True, max_events: int = 10)**

    ```
    await hltv.get_events(max_events=2)

    >>> [{'id': 9407, 'title': '1win Private Club Season 2', 'start_date': '19-10', 'end_date': '22-10'}, ...]
    ```

* **get_event_results(event_id: int | str, days: int = 1, max_: int = 10)**

    ```
    await hltv.get_event_results(7148)

    >>> [{'id': 2370727, 'date': '31-03-2024', 'team1': 'FaZe', 'team2': 'Natus Vincere', 'score1': 1, 'score2': 2}]
    ```

* **get_event_matches(event_id: int | str, days: int = 1, max_: int = 10)**

    ```
    await hltv.get_event_matches(7148)

    >>> [{'id': 2399417, 'date': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM', 't1_id': 8297, 't2_id': 12394},
         {'id': 2370771, 'date': '2024-04-18', 'time': '15:30', 'team1': 'Monte', 'team2': 'paiN', 't1_id': 11811, 't2_id': 4773}]
    ```

* **get_event_info(event_id: int | str, event_title: str)**

    ```
    await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen 2024')

    >>> {'id': 7148, 'title': 'PGL CS2 Major Copenhagen 2024', 'start': '21-03-2024', 'end': '31-03-2024', 'status': 'Finished',
         'prize': '$1,250,000', 'team_count': '16', 'location': 'Copenhagen, Denmark',
         'mvp': {'id': 19206, 'nickname': 'jL'},
         'winners': [{'place': 1, 'team': 'Natus Vincere', 'id': 4608, 'prize': '$500,000'}, ...]}
    ```
    `status` is `'Finished'`, `'Ongoing'` or `'Upcoming'`. Finished events have `mvp` and `winners`, the others
    have `teams`: `[{team_id: 'name'}, ...]`.

* **get_top_teams(max_teams: int = 30, date_str: str = '')**

    ```
    await hltv.get_top_teams(2)

    >>> [{'id': 7020, 'rank': 1, 'title': 'Spirit', 'points': 904, 'change': 0}, {'id': 9565, 'rank': 2, 'title': 'Vitality', 'points': 898, 'change': 0}]
    ```
    `change` is the places moved since the previous ranking (`+3` -> `3`, `-1` -> `-1`, `0` when unchanged).

* **get_team_info(team_id: int | str, title: str)**

    ```
    await hltv.get_team_info(6667, 'faze')

    >>> {'id': 6667, 'title': 'faze', 'rank': 17, 'players': {'frozen': 9960, 'Twistzz': 10394}, 'coach': 'enkay J', 'age': 23.3, 'weekstop30': 56, 'last_trophy': 'IEM Chengdu 2024', 'total_trophies': 22}
    ```

* **get_last_news(max_reg_news: int = 2, only_today: bool = True, only_featured: bool = False)**

    ```
    await hltv.get_last_news(only_today=True)

    >>> [{'date': '07-11', 'f_news': [], 'news': [{'id': 45914, 'title': 'IEM Beijing 2026 playoff bracket set', 'posted': 'an hour ago'}]}]
    ```

* **get_top_players(top: int = 40, year: int | str | None = None)**

    ```
    await hltv.get_top_players(2)

    >>> [{'id': 11893, 'rank': 1, 'nickname': 'ZywOo', 'team': 'Vitality', 'maps': 1572, 'rating': 1.27}, {'id': 21167, 'rank': 2, 'nickname': 'donk', 'team': 'Spirit', 'maps': 673, 'rating': 1.25}]
    ```

* **get_player_info(id: int | str, nickname: str)** - profile page (`/player/<id>/<nickname>`)

    ```
    await hltv.get_player_info(20312, 'xertioN')

    >>> {'id': 20312, 'nickname': 'xertioN', 'team': 'MOUZ', 'team_id': 4494, 'name': 'Dorian Berman', 'nationality': 'Israel',
         'age': 22, 'born': '22-07-2004', 'prize_money': 769684,
         'top20': [{'rank': 14, 'year': 2024, 'article_id': 40643}, {'rank': 16, 'year': 2025, 'article_id': 43512}],
         'rating': 1.12, 'rating_top_percent': 25, 'rating_percentile': 80, 'hs': 52.0,
         'stats_period': 'Past 3 months', 'stats_maps': 72,
         'roles': {'firepower': 89, 'entrying': 78, 'trading': 38, 'opening': 93, 'closing': 26, 'sniping': 0, 'utility': 48},
         'socials': {'twitter': 'https://...', 'twitch': 'https://...', 'instagram': 'https://...', 'faceit': 'https://...'},
         'upcoming_matches': [{'id': 2400011, 'opponent': 'The MongolZ', 'event': 'IEM Beijing 2026', 'timestamp': 1794123000}, ...],
         'recent_matches': [{'stats_id': 132835, 'opponent': 'BETBOOM', 'event': 'IEM Beijing 2026', 'score1': 2, 'score2': 0, 'won': True}, ...],
         'img': 'https://...', 'total_trophies': 7, 'last_trophy': 'BLAST Bounty 2026 Season 2 Finals', 'total_mvp': 0,
         'last_matches': [132835, 132758, ...]}
    ```
    `recent_matches[...]['stats_id']` goes straight to [get_match_stats](#methods). `last_matches` keeps the old
    flat list: the first number of every link of the match list (match id for upcoming matches, statistics id for finished ones).

## Player statistics

Pages of `hltv.org/stats/players/...`. Every method below accepts the same optional **filters** as keyword arguments:

| argument | values |
|---|---|
| `cs_version` | `'CS2'` (default), `'CSGO'`, `None` = both |
| `map` | `'mirage'`, `'de_nuke'`, ... |
| `match_type` | `'majors'`, `'big_events'`, `'mvp_events'`, `'lan'`, `'online'` |
| `start_date` / `end_date` | `'YYYY-MM-DD'`; `start_date='all'` = no date limit |
| `ranking` | `5`, `10`, `20`, `30`, `50` (only matches against the top N teams) |
| `best_of` | `1`, `3`, `5` |
| `ranked` | `True` / `False` (Valve ranked events) |
| `playoff` | `'grand_final'`, `'playoffs'`, `'pre_playoff'` |
| `team_id`, `opponent_team`, `event` | only matches for / against this team, or at this event |

Tables show 100 rows; every result has a `pagination` (`{'from': 1, 'to': 100, 'total': 574}`): pass `offset=100` for the next page.
Every result also carries `player_id` and the `url` it was read from.

* **get_player_stats(player_id, nickname, \*\*filters)** - overview

    ```
    await hltv.get_player_stats(20312, 'xertioN', map='mirage', match_type='lan', ranking=10)

    >>> {'player_id': 20312, 'url': 'https://www.hltv.org/stats/players/20312/xertion?csVersion=CS2&maps=de_mirage&...',
         'id': 20312, 'nickname': 'xertioN', 'name': 'Dorian Berman', 'age': 22, 'country': 'Israel',
         'team': {'id': 4494, 'name': 'MOUZ'}, 'maps': 574,
         'summary': {'rating': 1.11, 't_rating': 1.1, 'ct_rating': 1.12, 'round_swing': 0.65, 'dpr': 0.68, 'kast': 72.9,
                     'multi_kill': 17.5, 'adr': 81.3, 'kpr': 0.71},
         'verdicts': {'rating': 'Okay', 'adr': 'Good', ...},
         'roles': {'firepower': {'score': 90, 'ct_score': 84, 't_score': 83, 'stats': {
                       'kills_per_round_win': {'title': 'Kills per Round Win', 'value': 0.99, 'ct': 1.03, 't': 0.94, 'band': 'aboveAverage'},
                       'round_win_shares': {...}, ...}},
                   'entrying': {...}, 'trading': {...}, 'opening': {...}, 'closing': {...}, 'sniping': {...}, 'utility': {...}},
         'similar_players': [{'id': 16693, 'nickname': 'flameZ', 'country': 'Israel', 'team': 'Vitality', 'similarity': 93}, ...],
         'featured_ratings': [{'label': 'vs top 5 opponents', 'top': 5, 'rating': 1.01, 'maps': 178}, ...],
         'teammates': [{'id': 18221, 'nickname': 'Spinx', 'country': 'Israel', 'rating': 1.12}, ...]}
    ```
    Times are seconds (`'0m 51s'` -> `51`), percentages are plain numbers (`23.3`). `band` is HLTV's own verdict for the value
    (`aboveAverage`, `average`, `belowAverage`).

* **get_player_advanced(player_id, nickname, \*\*filters)** - round swing, impact, dueling, round-to-round, map-to-map

    ```
    >>> {'maps': 574, 'rounds': 12490,
         'headline': {'round_swing': {'value': 0.65, 'text': '+0.65%', 'band': 'aboveAverage', ...}, 'eco_swing': {...}},
         'sections': {'impact': {'title': 'Impact', 'tiles': [{'label': 'Advantage', 'value': -0.01, 'detail': {'kpr': 0.47, 'dpr': 0.37}, 'band': '...'}, ...]},
                      'dueling_and_eco_adjustment': {...}, 'round_to_round': {...}, 'map_to_map': {...},
                      'summary': {'chart': {'labels': ['Rating 3.0', ...], 'datasets': {'xertioN': [...], 'Typical IGL': [...]}}}}}
    ```

* **get_player_matches(player_id, nickname, offset=0, \*\*filters)** - every map played

    ```
    >>> {'summary': {'avg_rating': 1.11, 'maps_won': 60.3, 'maps_with_1_plus_rating': 65.5, 'best_1_plus_rating_streak': 17},
         'pagination': {'from': 1, 'to': 100, 'total': 574},
         'matches': [{'stats_id': 243795, 'timestamp': 1794044700, 'date': '07-11-2026',
                      'team': {'id': 4494, 'name': 'MOUZ', 'score': 13}, 'opponent': {'id': 12394, 'name': 'BETBOOM', 'score': 8},
                      'map_code': 'mrg', 'map': 'Mirage', 'kills': 19, 'deaths': 9, 'kd_diff': 10, 'rating': 1.38, 'won': True}, ...]}
    ```
    `stats_id` is the map id for [get_map_stats](#methods).

* **get_player_events(player_id, nickname, \*\*filters)** - `[{'event_id': 8245, 'event': 'IEM Beijing 2026', 'placement': '3rd', 'place': 3, 'team_id': 4494, 'team': 'MOUZ', 'maps': 8, 'kpr': 0.76, 'dpr': 0.61, 'kd_diff': 25, 'rating': 1.23}, ...]` under `events` (`placement` is `'-'` and `place` `0` while the event is running)

* **get_player_career(player_id, nickname, \*\*filters)** - `{'periods': [{'period': '2025', 'all': {'rating': 1.01, 'maps': 191}, 'online': {...}, 'lan': {...}, 'majors': {...}}, ..., {'period': 'Career', ...}]}`; a split without maps is `None`

* **get_player_weapons(player_id, nickname, \*\*filters)**

    ```
    >>> {'kills_by_type': [{'type': 'Rifles', 'count': 6867, 'share': 77.7}, ...], 'carried_by_type': [{'type': 'Rifles', 'count': 9043, 'share': 72.4}, ...],
         'weapons': [{'rank': 1, 'weapon': 'AK-47', 'kills': 3468, 'share': 39.2}, ...]}
    ```

* **get_player_clutches(player_id, nickname, size='all', offset=0, \*\*filters)** - `size`: `'all'` or `1`-`5` (1 on 1 ... 1 on 5)

    ```
    >>> {'summary': {'wins': 119, 'losses': 39, 'difference': 80}, 'pagination': {...},
         'clutches': [{'stats_id': 243791, 'date': '07-11-2026', 'team1': {'id': 4494, 'name': 'MOUZ', 'score': 13}, 'team2': {...},
                       'map_code': 'anc', 'map': 'Ancient', 'won': True, 'clutch': 3, 'round': 20}, ...]}
    ```

* **get_player_multikills(player_id, nickname, kills=2, fast=False, offset=0, \*\*filters)** - `kills`: `'all'` or `2`-`5`; `fast=True` = fast multi-kills only (less than 5 s between kills)

    ```
    >>> {'summary': {'multi_kills': 1617, 'fast_multi_kills': 953}, 'pagination': {...},
         'multikills': [{'stats_id': 243791, 'date': '07-11-2026', 'team1': {...}, 'team2': {...}, 'map': 'Ancient', 'round': 5}, ...]}
    ```

* **get_player_opponents(player_id, nickname, \*\*filters)** - `{'opponents': [{'team_id': 10672, 'team': 'VERTEX', 'maps': 1, 'kd_diff': 10, 'kd': 2.67, 'rating': 2.19}, ...]}`

* **get_player_full_stats(player_id, nickname, \*\*filters)** - overview, advanced, matches, events, career and weapons in one call, fetched in parallel: `{'player_id': ..., 'overview': {...}, 'advanced': {...}, 'matches': {...}, 'events': {...}, 'career': {...}, 'weapons': {...}}` (a page that could not be loaded is `None`)

The sync client has the same methods. Checked against live pages: the default views, a map filter, `offset`, clutches `1 on 3`,
multi-kills `3x` and `fast=True`. A single-size clutch page has hidden loss / difference boxes (`losses` and `difference` are `None`).
The other filters and sizes use HLTV's URL scheme but were not captured: if one returns an unexpected shape, open an issue with the page.

## Match statistics

* **get_match_stats(stats_id: int | str, team1: str = 'team', team2: str = 'team')**

    Detailed statistics of a **finished** match (`hltv.org/stats/matches/<stats_id>/...`): the overview of all maps and,
    fetched in parallel, the page of every map. `stats_id` is the `stats_id` field of `get_match_info`; the team names
    only build the URL and are optional.

    ```
    info = await hltv.get_match_info(2400009, 'MOUZ', 'BETBOOM', 'IEM Beijing 2026')
    # info['stats_id'] == 132835, info['maps'][0]['stats_id'] == 243791 (0 while there are no statistics)

    stats = await hltv.get_match_stats(info['stats_id'], 'MOUZ', 'BETBOOM')

    >>> {'stats_id': 132835, 'event': {'id': 8245, 'title': 'IEM Beijing 2026'},
         'timestamp': 1794044700, 'date': '07-11-2026', 'time': '10:45', 'map': 'All',
         'team1': {'id': 4494, 'name': 'MOUZ', 'score': 2, 'players': [
             {'id': 20312, 'nickname': 'xertioN', 'country': 'Israel', 'rating': 1.67,
              'kills': 40, 'headshots': 21, 'hs_percent': 52.5, 'assists': 10, 'flash_assists': 2,
              'deaths': 20, 'traded_deaths': 4, 'kd_diff': 20, 'adr': 111.0, 'kast': 73.2, 'swing': 4.93,
              'opening_kills': 6, 'opening_deaths': 3, 'multi_kills': 12, 'clutches': 1,
              'e_kills': 41, 'e_deaths': 21, 'e_adr': 110.1, 'e_kast': 72.2, 'e_opening_kills': 6, 'e_opening_deaths': 3,
              'ct': {... same fields for the CT side ...}, 't': {... same fields for the T side ...}}, ...]},
         'team2': {...},
         'series': {'format': 'Best of 3', 'score1': 2, 'score2': 0, 'winner': 'MOUZ'},
         'summary': {'team_rating_3_0': {'team1': 1.24, 'team2': 0.81}, 'first_kills': {'team1': 25, 'team2': 16},
                     'clutches_won': {'team1': 3, 'team2': 2}},
         'top_players': {'most_kills': {'title': 'Most kills', 'player_id': 20312, 'nickname': 'xertioN', 'value': 40}, ...},
         'performance': [{'nickname': 'xertioN', 'rating': 1.67}, ...],
         'round_history': [],
         'maps': [{'stats_id': 243791, 'map': 'Ancient', 'score1': 13, 'score2': 7, 'winner': 'MOUZ',
                   'available': True, 'team1': {...}, 'team2': {...}, 'summary': {...}, 'round_history': [...], ...},
                  {'stats_id': 243795, 'map': 'Mirage', 'score1': 13, 'score2': 8, ...}]}
    ```
    `e_*` are the economy-adjusted values, `ct` / `t` the same fields per side. `available` is `False` for a map whose
    page could not be loaded. `summary` holds every row of the info box under its snake_case title (two numbers become
    `{'team1', 'team2'}`, anything else `{'raw', 'values'}`). `round_history` (per team: which rounds it won and how) and `rounds` (one entry per round:
    `{'round': 1, 'half': 1, 'winner': 'BETBOOM', 'side': 't', 'reason': 'bomb_exploded', 'score1': 0, 'score2': 1}`;
    `reason` is `elimination`, `bomb_defused`, `bomb_exploded` or `time`) only exist on map pages, where `summary['breakdown']`
    also gives the halves: `{'team1': 13, 'team2': 7, 'halves': [{'team1': 7, 'team2': 5, 'team1_side': 'ct'}, ...]}`.

* **get_map_stats(map_stats_id: int | str, team1: str = 'team', team2: str = 'team')**

    One map only, same structure as above without `maps`.

    ```
    await hltv.get_map_stats(243791, 'MOUZ', 'BETBOOM')
    ```

* **get_stats_for_match(match_id, team1, team2, event_title)**

    `get_match_info` + `get_match_stats` in one call. `None` while the match has no statistics yet.

* **get_match_data(match_id: int | str, timeout: float = 15)** / **live_match(match_id, on_event=None)**

    Live data over sockets, see [Live match data](#live-match-data-sockets).

* **get(type: str, id: int | str | None = None, title: str | None = None, team1: str | None = None, team2: str | None = None)**
  (BETA) Shortcut for the methods above. Types: `'events'`, `'matches'`, `'news'`, `'teams'`.

---
# Examples

****Simple Example****

```
from hltv_async_api import Hltv


async def test():

    async with Hltv() as hltv:
      print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```

****Proxy Parser****

```
from hltv_async_api import Hltv


async def test():

    hltv = Hltv(debug=True, proxy_path='proxy_test.txt', timeout=1, remove_proxy=True, proxy_protocol='http')
    
    print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```

****Automatic parser with arq and redis****

- to run type "arq PATH_TO_FILE.WorkerSettings"

    ```
    import ujson
    import asyncio
    from arq import cron
    from redis.asyncio import Redis, ConnectionPool
    
    from hltv_async_api import Hltv
    
    
    
    async def startup(ctx):
        async with Hltv(max_delay=5, proxy_path='proxies.txt', debug=True) as hltv:
              ctx["hltv"] = hltv
  
        ctx["redis"] = redis_client = Redis(
            connection_pool=ConnectionPool.from_url(settings.redis_url))
        logger.success(f"Scheduler started. UTC time {datetime.utcnow()}")
    
    
    async def shutdown(ctx):
        await ctx["redis"].close()
    
    
    async def parse_matches(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        matches = await hltv.get_upcoming_matches(1, 1)
        if matches:
            await redis.set("matches", ujson.dumps(matches))
        else:
            logger.error("error parsing matches")
    
    async def parse_events(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        events = await hltv.get_events()
        if events:
            await redis.set("events", ujson.dumps(events))
        else:
            logger.error("error parsing events")
    
    
    async def parse_top_teams(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        top_teams = await hltv.get_top_teams(30)
        if top_teams:
            await redis.set("top_teams", ujson.dumps(top_teams))
        else:
            logger.error("error parsing top teams")
    
    
    async def parse_top_players(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        top_players = await hltv.get_top_players(30)
        if top_players:
            await redis.set("top_teams", ujson.dumps(top_players))
        else:
            logger.error("error parsing top players")
    
    
    async def parse_last_news(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        news = await hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            await redis.set("news", ujson.dumps(news))
        else:
            logger.error("error parsing news")
    
    
    class WorkerSettings:
        redis_settings = settings.redis_pool
        on_startup = startup
        on_shutdown = shutdown
        functions = [parse_matches,
                     parse_events,
                     parse_top_teams,
                     parse_top_players,
                     parse_last_news,
                     ]
        cron_jobs = [
            cron(parse_matches, minute=59),
            cron(parse_events, hour=0, minute=0, second=0),
            cron(parse_top_teams, day=0, hour=18, minute=1, second=30),
            cron(parse_top_players, day=0, hour=20, minute=0, second=0),
            cron(parse_last_news, minute=55),
        ]

    ```

# Tests:

**<a href='https://github.com/akimerslys/hltv-async-api/blob/main/test/hard_test.py'>To test library you can use temporarily test file</a>**

```

Parsed 208 matches.(97s) ERRORS: 0/208
Parsed 25 events.(23s) ERRORS: 0/25
Parsed 31 teams.(41s) ERRORS: 0/31
Parsed 31 players.(28s) ERRORS: 0/31
ERRORS=0
SUCCESS=284
Total parsed=284
Total time 96.8368

```

# Beta / Unreleased

from hltv_async_api.beta import Beta

# Requirements:

Python 3.10+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.

# Contributing

Why not ?

