"""
:autor: akimerslys
:license: MIT
"""

import asyncio
from contextlib import suppress

from .aiohltv import Hltv
from .__meta__ import __author__, __version__, __default_timezone__
from . import types, methods, sync, beta


with suppress(ImportError):
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

__all__ = ['__author__', '__version__', 'Hltv', 'types', 'methods', 'sync']
