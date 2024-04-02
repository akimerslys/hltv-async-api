# Hltv-aio An unofficial asynchronous HLTV API Wrapper for Python

# Features

* New and modern fully async library

* Supports proxy usage for rate-limiting and privacy

* Automatically changes proxy if access is denied


---

# Installation

```
pip install hltv-aio
```

---


# Simple Usage

```
from hltv-aio import Hltv

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


**Remove bad proxy from file**

```
hltv = Hltv(use_proxy=True, proxy_path='PATH_TO_PROXY.TXT', remove_proxy=True)
```

**Add proxy protocol**

```
proxy_list = ['120.234.203.171:9002', '110.38.68.38:80']

hltv = Hltv(use_proxy=True, proxy_list=proxy_list, proxy_protocol='http')
```
---
# Examples

****Simple Example****

```
async def test():

    hltv = Hltv()
    
    print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```


****Proxy Parser****
```
async def test():

    hltv = Hltv(debug=True, use_proxy=True, proxy_path='proxy_test.txt', timeout=1, remove_proxy=True, proxy_protocol='http')
    
    print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```


# Requirements:

Python 3.9+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.
