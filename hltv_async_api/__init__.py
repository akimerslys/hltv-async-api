"""
:autor: akimerslys
:license: MIT
"""

import asyncio
from contextlib import suppress

from .aiohltv import Hltv
from .__meta__ import __author__, __version__
#from .sync import Sync
#from .Methods import Methods

with suppress(ImportError):
    import uvloop as _uvloop

    asyncio.set_event_loop_policy(_uvloop.EventLoopPolicy())


__all__ = ['__author__', '__version__', 'Hltv', 'Sync']