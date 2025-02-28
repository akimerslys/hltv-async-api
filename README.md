# hltv-async-api an **unofficial** asynchronous HLTV API Wrapper for Python.

# IMPORTANT

Selenium update soon.

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

# Configs

* max_delay: float = 10.0

  Automatically increasing delay by 1 sec to 10s

  ```
    hltv = Hltv(max_delay=5)
    
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Got 403 forbitten
    >>>Calling again, increasing delay to 4s
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Got 403 forbitten
    >>>Calling again, increasing delay to 5s
  ```

* min_delay: float = -1

``` 
  [DEBUG] Random delay 9.55s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 3/10
  [DEBUG] Random delay 3.9s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 4/10
```



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
    print(await hltv.get_best_players())
    
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

* safe_mode: bool = True

    Disallow to wrap restricted data which . Switch to False only at your own risk.

* aiohttp_session: aiohttp.ClientSession | None = None

    Custom aiohttp session, if you want to use your own session.

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

* **get_matches(days: int = 1, min_star_rating: int = 1, live: bool = True, future: bool = True)**

    -days (the number of days into the future to fetch matches for)
  
    -min_star_rating (the minimum star rating for matches to include)
  
    ```
    await hltv.get_matches(days=1)
    
    >>> [{'id': '2371201', 'date': 'LIVE', 'time': 'LIVE', 'team1': 'Imperial', 'team2': 'MIBR', 't1_id': '9455', 't2_id': '9215', 'maps': '3', 'rating': 1, 'event': 'RES Regional Series 3 LATAM'}, {'id': '2370964', 'date': '2024-04-16', 'time': '12:30', 'team1': 'SAW', 'team2': 'Sampi', 't1_id': '10567', 't2_id': '10695', 'maps': '3', 'rating': 1, 'event': 'Thunderpick World Championship 2024 EU Closed Qualifier 1'}, {'id': '2371367', 'date': '2024-04-16', 'time': '14:00', 'team1': 'Gaimin Gladiators', 'team2': 'Permitta', 't1_id': '11571', 't2_id': '12009', 'maps': '3', 'rating': 1, 'event': 'Elisa Invitational Spring 2024'}]
    
    ```

* **get_match_info(match_id: int | str, team1, team2, event_title, stats: bool = True, predicts: bool = True)**
  
    ```
    await hltv.get_match_info(2370931, 'Mouz', 'faze', 'iem-chengdu-2024')  
  
    >>>(2370931, '0', '2', 'Match over', [{'mapname': 'Overpass', 'r_team1': '10', 'r_team2': '13'}, {'mapname': 'Nuke', 'r_team1': '6', 'r_team2': '13'}, {'mapname': 'Mirage', 'r_team1': '-', 'r_team2': '-'}], [{'id': '18850', 'nickname': 'Jimpphat', 'kd': '33-29', 'adr': '80.9', 'rating': '1.08'}, 
  
    {'id': '18072', 'nickname': 'torzsi', 'kd': '26-25', 'adr': '70.5', 'rating': '1.02'}, {'id': '13666', 'nickname': 'Brollan', 'kd': '25-31', 'adr': '68.4', 'rating': '0.90'}, {'id': '20312', 'nickname': 'xertioN', 'kd': '23-31', 'adr': '62.4', 'rating': '0.82'}, {'id': '16820', 'nickname': 'siuhy', 'kd': '17-30', 'adr': '51.6', 'rating': '0.70'}, {'id': '18053', 'nickname': 'broky', 'kd': '34-22', 'adr': '79.3', 'rating': '1.33'}, {'id': '9960', 'nickname': 'frozen', 'kd': '33-23', 'adr': '85.5', 'rating': '1.31'}, {'id': '11816', 'nickname': 'ropz', 'kd': '31-26', 'adr': '73.0', 'rating': '1.20'}, {'id': '8183', 'nickname': 'rain', 'kd': '27-26', 'adr': '82.0', 'rating': '1.18'}, {'id': '429', 'nickname': 'karrigan', 'kd': '20-28', 'adr': '49.7', 'rating': '0.81'}])  
    
    ```
  
* **get_results(days: int = 1, min_rating: int = 1, max: int = 30, featured: bool = True, regular: bool = True)) ->**
    
    ```
    print(await hltv.get_results())
  
    [{'id': '2370931', 'team1': 'MOUZ', 'team2': 'FaZe', 'score1': '0', 'score2': '2', 'rating': 0, 'event': 'IEM Chengdu 2024'}]
    ```
  
* **get_events(outgoing=True, future=True, max_events=10) -> [('id', 'title', 'startdate', 'enddate')]**

    ```
    await hltv.get_events(future=False)
    
    >>>[{'id': '7749', 'title': 'Thunderpick World Championship 2024 EU Closed Qualifier 1', 'start_date': '1-4', 'end_date': '22-4'}, {'id': '7621', 'title': 'ESL Challenger League Season 47 North America', 'start_date': '13-2', 'end_date': '16-6'}]
      
    ```

* **get_event_results(event_id: int | str, days: int = 1, max_: int = 10)**

  
    ```
    await get_event_results(7148)
    
    >>>[{'id': '2370931', 'date': '14-04-2024', 'team1': 'MOUZ', 'team2': 'FaZe', 'score1': '0', 'score2': '2'}]

    ```

* **get_event_matches(event_id: str | int, days: int = 1):**
  
    ```
    await hltv.get_event_matches(7148)
    
    >>>[{'id': '2370771', 'date': '2024-04-18', 'time': '15:30', 'team1': 'Monte', 'team2': 'paiN', 't1_id': '11811', 't2_id': '4773'}, {'id': '2370772', 'date': '2024-04-18', 'time': '17:00', 'team1': 'Imperial', 'team2': 'Metizport', 't1_id': '9455', 't2_id': '11641'}, {'id': '2370773', 'date': '2024-04-18', 'time': '18:30', 'team1': 'FURIA', 'team2': '9z', 't1_id': '8297', 't2_id': '9996'}, {'id': '2370774', 'date': '2024-04-18', 'time': '20:00', 'team1': 'MIBR', 'team2': 'OG', 't1_id': '9215', 't2_id': '10503'}, {'id': '2370775', 'date': '2024-04-18', 'time': '21:30', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370776', 'date': '2024-04-18', 'time': '23:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370777', 'date': '2024-04-19', 'time': '00:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370778', 'date': '2024-04-19', 'time': '15:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370779', 'date': '2024-04-19', 'time': '17:30', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370780', 'date': '2024-04-19', 'time': '20:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370781', 'date': '2024-04-19', 'time': '22:30', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370782', 'date': '2024-04-20', 'time': '00:30', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370783', 'date': '2024-04-20', 'time': '15:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}, {'id': '2370784', 'date': '2024-04-20', 'time': '18:00', 'team1': 'TBD', 'team2': 'TBD', 't1_id': 0, 't2_id': 0}]
  
    ```

* **get_event_info(event_id: str | int, event_title: str) -> (event_id, event_title, event_start, event_end, prize, team_num, location, groups)**

    ```
    await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024')
    
    {'id': 7148, 'title': 'PGL CS2 Major Copenhagen2024', 'start': '21-3', 'end': '31-3', 'prize': '$1,250,000', 'teams': '16', 'location': 'Copenhagen, Denmark', 'group': []}
   
    ```


* **get_top_teams(max_teams=30) -> ['rank', 'title', 'points', 'change', 'id']**

    ```
    await hltv.get_top_teams(2)
    
    >>>[{'id': '1111', 'rank': '1', 'title': 'FaZe', 'points': '939', 'change': '-', 'id': '6667'}, {'id': '1111', 'rank': '2', 'title': 'Natus Vincere', 'points': '757', 'change': '+4', 'id': '4608'}]
    ```

* **get_team_info(team_id: int | str, title: str) -> (team_id, team_title, rank, {'player':player_id}, coach, average_age, weeks_in_top_20, last_trophy, total_trophys)**

    ```
    await hltv.get_team_info(6667, 'faze')
    
    >>>{'id': 6667, 'title': 'faze', 'rank': '1', 'players': {'karrigan': 429, 'rain': 8183, 'frozen': 9960, 'ropz': 11816, 'broky': 18053}, 'coach': 'NEO', 'age': '26.6', 'weekstop30': '260', 'last_trophy': 'IEM Chengdu 2024', 'total_trophies': 22}
    ```

* **get_last_news(max_reg_news=2, only_today=True, only_featured=False) -> [date, [featured_id, featured_title, featured_desciption], [regular_id, reg_title, reg_time]]**

    ```
    await hltv.get_last_news(only_today=True)
    
    >>>[{'date': '15-04', 'f_news': [], 'news': [{'id': '38784', 'title': 'Media: FURIA practicing with kye in place of arT', 'posted': 'an hour ago'}, {'id': '38783', 'title': 'electroNic to play for Virtus.pro at ESL Pro League S19', 'posted': '2 hours ago'}, {'id': '38781', 'title': 'The EVPs and Best Five of IEM Chengdu', 'posted': '7 hours ago'}]}]
  
    ```

* **get_best_players(top: int = 40) -> ('rank', 'name', 'team', 'maps', 'rating')**

    ```
    await hltv.get_best_players(2)
    
    >>>[{'id': '19230', 'rank': 1, 'name': 'm0NESY', 'team': 'G2', 'maps': '44', 'rating': '1.37'}, {'id': '18053', 'rank': 2, 'name': 'broky', 'team': 'FaZe', 'maps': '54', 'rating': '1.19'}]
    ```

* **get_player_info(id: str | int, nickname: str)**
  
  ```
  await hltv.get_player_info(7998, 's1mple')
  
  {'id': 7998, 'nickname': 's1mple', 'team': 'Natus Vincere', 'team_id': 4608, 'name': 'Oleksandr Kostyliev', 'nationality': 'Ukraine', 'age': 26, 'rating': '0.94', 'kpr': '0.60', 'hs': '57.9%', 'last_matches': [103059, 99745, 99728, 99696, 99471, 99364], 'last_trophy': 'BLAST Premier Spring Final 2022', 'total_trophies': 30, 'total_mvps': 21}
  ```

* **get(type: str, id: int | str | None = None, title: str | None = None, team1: str | None = None, team2: str | None = None):**
  (BETA) This method is not finished. Possible types 'events', 'matches', 'teams', also u can add id | title | team1 | team2, to parse more.
  
  ```
  
  await hltv.get('matches', 2371201, 'res-regional-series-3-latam', 'IMPERIAL', 'MIBR')
  
  >>> (2371201, 0, 0, 'LIVE', [{'mapname': 'Vertigo', 'r_team1': '6', 'r_team2': '13'}, {'mapname': 'Mirage', 'r_team1': '-', 'r_team2': '-'}, {'mapname': 'Anubis', 'r_team1': '-', 'r_team2': '-'}], [])
  
  ```


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
        top_players = await hltv.get_best_players(30)
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

Python 3.9+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.

# Contributing

Why not ?

