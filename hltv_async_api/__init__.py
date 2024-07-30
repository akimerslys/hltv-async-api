"""
:autor: akimerslys
:license: MIT
"""

import asyncio
from contextlib import suppress

from .aiohltv import Hltv
from .__meta__ import __author__, __version__, __default_timezone__
from . import types, methods, beta


with suppress(ImportError):
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

__all__ = ['__author__', '__version__', 'Hltv', 'types', 'methods']

try:
    import requests as r
    from . import sync
    __all__.append('sync')
except ImportError:
    print("You need to install hltv_async_api[sync]")

