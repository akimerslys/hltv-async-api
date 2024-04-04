# hltv-async-api an unofficial asynchronous HLTV API Wrapper for Python


**This page not completed, not all methods and configs are written**


# Features

* New and modern fully async library

* Supports proxy usage for rate-limiting and privacy

* Automatically changes proxy if access is denied


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

* get_upcoming_matches(days: int = 7, min_star_rating: int = 1)

    -days (the number of days into the future to fetch matches for)
  
    -min_star_rating (the minimum star rating for matches to include)
  
```
await hltv.get_upcoming_matches(1, 5)

>>> ['date': '11/11/2024', 'matches': [id: '1111', team1: 'Natus Vincere' | 'TBD', team2: 'FaZe' | 'TBD', time: '14:15', maps: '3', stars: 5, 'PGL CS2 Major Copenhagen 2024' | None]]```

```

* get_event_results(event_id: int | str)

  
```
await get_event_results(7148)

>>> ['date': '31-3', 'matches': ['id': '1111', team1': 'FaZe', 'team2': 'Natus Vincere', 'score1': '1', 'score2': '2']]

```

* get_event_matches(event_id: str | int):
  
```
await hltv.get_event_matches(7148)

>>>['date': '1-1' | 'LIVE, 'matches': ['id': '1111', team1': 'Natus Vincere', 'team2': 'FaZe']
```

* get_event_info(event_id: str | int, event_title: str) -> (event_id, event_title, event_start, event_end, prize, team_num, location, groups)

```
await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024')

(7148, 'PGL CS2 Major Copenhagen2024', '21-3', '31-3', '$1,250,000', '16', 'Copenhagen, Denmark', [])
```


get_top_teams(max_teams=30) -> ['rank', 'title', 'points', 'change', 'id']

```
await hltv.get_top_teams(2)

>>>[{'id': '1111', 'rank': '1', 'title': 'FaZe', 'points': '939', 'change': '-', 'id': '6667'}, {'id': '1111', 'rank': '2', 'title': 'Natus Vincere', 'points': '757', 'change': '+4', 'id': '4608'}]
```

get_team_info(team_id: int | str, title: str) -> (team_id, team_title, rank, [players], coach, average_age, weeks_in_top_20, last_trophy, total_trophys)

```
await hltv.get_team_info(6667, 'faze')

>>>(6667, 'faze', '1', ['karrigan', 'rain', 'frozen', 'ropz', 'broky'], 'NEO', '26.5', '256', 'CS Asia Championships 2023', 21)
```

get_last_news(self, max_reg_news=2, only_today=True, only_featured=False) -> [date, [featured_id, featured_title, featured_desciption], [regular_id, reg_title, reg_time]]

```
await hltv.get_last_news(only_today=True, max_reg_news=1)

>>>[{'date': '02-04', 'f_news': [{'f_id': '38682', 'f_title': 'NIP confirm r1nkle signing', 'f_desc': "Ninjas in Pyjamas only have an anchor player left to sign following the young Ukrainian AWPer's addition."}], 'news': [{'id': '38685', 'title': 'Rounds add sLowi, p3kko', 'posted': 'an hour ago'}, {'id': '38690', 'title': 'n1ssim returns to Sharks after paiN loan deal expires', 'posted': 'an hour ago'}]}]
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


# Requirements:

Python 3.9+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.
