# Hltv-async: An unofficial asynchronous HLTV API Wrapper for Python

# Features

Fetches live, upcoming, and important upcoming matches
Retrieves match scores and events
Provides information about teams and events
Retrieves lists of top teams and best players
Supports proxy usage for rate-limiting and privacy
Automaticaly swap proxy if page is forbitten
Includes error handling and logging

---

# Installation

>pip install hltv-async

---


# Simple Usage

>from hltv-async import Hltv
hltv = Hltv()
live_matches = await hltv.get_live_matches()

---

# Proxy Usage
# Load Proxies from file

hltv = Hltv(use_proxy=True, proxy_path='PATH_TO_PROXY.TXT')

# Load Proxies from list

proxy_list = ['http://120.234.203.171:9002', 'http://110.38.68.38:80']
hltv = Hltv(use_proxy=True, proxy_list=proxy_list)

---

# Requirements:

Python 3.7+

License:
HLTV Async is licensed under the MIT License, allowing for personal and commercial use with minimal restrictions.