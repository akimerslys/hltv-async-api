# hltv-async-api an unofficial asynchronous HLTV API Wrapper for Python


**This page not completed, not all methods and configs are written**


# Features


* **Simple Usage** (its realy simple)


* **New and modern fully async library**


* **Huge amount of options**


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
    
    hltv = Hltv()
    live_matches = await hltv.get_live_matches()
    ```

---

# Proxy Usage

**Load Proxies from list**
    
    ```
    proxy_list = ['http://120.234.203.171:9002', 'http://110.38.68.38:80']
    
    hltv = Hltv(use_proxy=True, proxy_list=proxy_list)
    ```

**Load Proxies from file**

    ```
    hltv = Hltv(use_proxy=True, proxy_path='PATH_TO_PROXY.TXT')
    ```


**One-time proxy**
    
    ```
    hltv = Hltv(use_proxy=True, proxy_path='PATH_TO_PROXY.TXT', proxy_one_time=True)
    ```

**Protocol usage**

    ```
    proxy_list = ['120.234.203.171:9002', '110.38.68.38:80']
    
    hltv = Hltv(use_proxy=True, proxy_list=proxy_list, proxy_protocol='http')
    ```

---
# Methods

* **get_upcoming_matches(days: int = 7, min_star_rating: int = 1)**

    -days (the number of days into the future to fetch matches for)
  
    -min_star_rating (the minimum star rating for matches to include)
  
    ```
    await hltv.get_upcoming_matches(1, 5)
    
    >>> ['date': '11-11', 'matches': [id: '1111', team1: 'Natus Vincere' | 'TBD', team2: 'FaZe' | 'TBD', time: '14:15', maps: '3', stars: 5, 'PGL CS2 Major Copenhagen 2024' | None]]```
    
    ```
* **get_events(outgoing=True, future=True, max_events=10) -> [('id', 'title', 'startdate', 'enddate')]**

    ```
    await hltv.get_events(future=False)
    
    >>>{'id': '7437', 'name': 'IEM Chengdu 2024', 'start_date': '8-4', 'end_date': '14-4'}, {'id': '7757', 'name': 'BetBoom Dacha Belgrade 2024 Europe Closed Qualifier', 'start_date': '2-4', 'end_date': '12-4'}]
    
    ```

* **get_event_results(event_id: int | str)**

  
    ```
    await get_event_results(7148)
    
    >>> ['date': '31-3', 'matches': ['id': '1111', team1': 'FaZe', 'team2': 'Natus Vincere', 'score1': '1', 'score2': '2']]
    
    ```

* **get_event_matches(event_id: str | int):**
  
    ```
    await hltv.get_event_matches(7148)
    
    >>>[{'date': 'LIVE', 'matches': [{'id': '2371135', 'team1': 'GUN5', 'team2': 'KOI', 't1_id': '12471', 't2_id': '12591'}]}, {'date': '2024-04-08', 'matches': [{'id': '2371131', 'time': '20:00', 'team1': 'Aurora', 'team2': 'Metizport', 't1_id': '11861', 't2_id': '11641'}]}]
    ```

* **get_event_info(event_id: str | int, event_title: str) -> (event_id, event_title, event_start, event_end, prize, team_num, location, groups)**

    ```
    await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024')
    
    (7148, 'PGL CS2 Major Copenhagen2024', '21-3', '31-3', '$1,250,000', '16', 'Copenhagen, Denmark', [])
    ```


* **get_top_teams(max_teams=30) -> ['rank', 'title', 'points', 'change', 'id']**

    ```
    await hltv.get_top_teams(2)
    
    >>>[{'id': '1111', 'rank': '1', 'title': 'FaZe', 'points': '939', 'change': '-', 'id': '6667'}, {'id': '1111', 'rank': '2', 'title': 'Natus Vincere', 'points': '757', 'change': '+4', 'id': '4608'}]
    ```

* **get_team_info(team_id: int | str, title: str) -> (team_id, team_title, rank, [players], coach, average_age, weeks_in_top_20, last_trophy, total_trophys)**

    ```
    await hltv.get_team_info(6667, 'faze')
    
    >>>(6667, 'faze', '1', ['karrigan', 'rain', 'frozen', 'ropz', 'broky'], 'NEO', '26.5', '256', 'CS Asia Championships 2023', 21)
    ```

* **get_last_news(max_reg_news=2, only_today=True, only_featured=False) -> [date, [featured_id, featured_title, featured_desciption], [regular_id, reg_title, reg_time]]**

    ```
    await hltv.get_last_news(only_today=True, max_reg_news=1)
    
    >>>[{'date': '02-04', 'f_news': [{'f_id': '38682', 'f_title': 'NIP confirm r1nkle signing', 'f_desc': "Ninjas in Pyjamas only have an anchor player left to sign following the young Ukrainian AWPer's addition."}], 'news': [{'id': '38685', 'title': 'Rounds add sLowi, p3kko', 'posted': 'an hour ago'}, {'id': '38690', 'title': 'n1ssim returns to Sharks after paiN loan deal expires', 'posted': 'an hour ago'}]}]
    ```

* **get_best_players(top=40) -> ('rank', 'name', 'team', 'maps', 'rating')**

    ```
    await hltv.get_best_players(2)
    
    >>>[{'rank': 1, 'name': 'donk', 'team': 'Spirit', 'maps': '33', 'rating': '1.52'}, {'rank': 2, 'name': 'm0NESY', 'team': 'G2', 'maps': '34', 'rating': '1.38'}]
    ```

---
# Configs

* max_delay: int = 15

    We automaticly increasing reconnecting delay by 1 sec to max_delay (from 1s to 5s)

    ```
    hltv = Hltv(max_delay=5, use_proxy=False)
    
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Got 403 forbitten
    >>>Calling again, increasing delay to 4s
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Got 403 forbitten
    >>>Calling again, increasing delay to 5s
    ```

* max_retries: int = 0

    Max retries. 0 or -1 for infinity tries.
    
    ```
    hltv = Hltv(max_retries=2, debug=True)
    print(await hltv.get_best_players())
    
    Creating Session
    Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 1/2
    Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 2/2
    Connection failed
    ```

* use_proxy: bool = False

    Proxy Usage. No compatibility with max_delay (max_delay will be ignored)

* proxy_list: list | None = None

    list of your proxies, if your proxies doesnt have any protocol you can use proxy_protocol.
    Note: To add nonproxy to list just put '' to it, you can find example with ar

* proxy_path: str | None = None

    Path to your proxy (proxy_list will be ignored). If your proxies doesnt have any protocol you can use proxy_protocol

* proxy_protocol: str | None = None,

    Proxy protocol. Your proxies ```hltv = Hltv(proxy_protocol='http' ...) -> '11.11.11.11:1111' -> 'http://11.11.11.11:1111'

* proxy_one_time: bool = False

    Removes proxy from list (proxy_path included) if connection unsuccessfull

* timeout: int = 5

    Max time to close connection. Recommended to use timeout=1 if you are using random proxies.

* debug: bool = False

    More loggs

* true_session=False
  
    **(BETA)**
    This parser automaticaly creating and clossing session after every call, if you want to let your session open even when parser is inactive
    use this method. **!! IMPORTANT YOU SHOULD CLOSE YOUR SESSION BEFORE KILLING PROGRAM**

    ```
    async def test():
        hltv = Hltv(true_session=True)
        print(await hltv.get_best_players())
        print(await hltv.get_upcoming_matches())
        await hltv.close_session()

    if __name__ == "__main__":
        asyncio.run(test())
    ```
    
---
# Examples

****Simple Example****

```
from hltv_async_api import Hltv


async def test():

    hltv = Hltv()
    
    print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```

****Proxy Parser****

```
from hltv_async_api import Hltv


async def test():

    hltv = Hltv(debug=True, use_proxy=True, proxy_path='proxy_test.txt', timeout=1, proxy_one_time=True, proxy_protocol='http')
    
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
        ctx["hltv"] = Hltv(max_delay=5, use_proxy=True, proxy_list=[settings.PROXY_MAIN, ''], true_session=True, debug=True)
        ctx["redis"] = redis_client = Redis(
            connection_pool=ConnectionPool.from_url(settings.redis_url),
        )
        logger.success(f"Scheduler started. UTC time {datetime.utcnow()}")
    
    
    async def shutdown(ctx):
        await ctx["hltv"].close_session()
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

# Requirements:

Python 3.9+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.
