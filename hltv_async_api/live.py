"""Optional live match data over HLTV's scorebot socket (Socket.IO).

Install with ``pip install "hltv-async-api[live]"``. Use it through ``Hltv.get_match_data`` / ``Hltv.live_match``
or directly with :class:`LiveMatch`.

The socket sends several events. ``score`` is parsed into a stable structure; ``scoreboard``, ``log`` and
``fullLog`` formats are not documented, so they are kept as received (``raw``) without being interpreted.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

from hltv_async_api.Utils.hints import LIVE_BLOCKED_HINT, LIVE_INSTALL_HINT

SCOREBOT_URL = 'https://scorebot-lb.hltv.org'
SOCKET_PATH = '/socket.io'
HEADERS = {
    'Origin': 'https://www.hltv.org',
    'Referer': 'https://www.hltv.org/',
}
DEFAULT_USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')


class LiveConnectionError(ConnectionError):
    """The scorebot socket refused or dropped the connection."""


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _half(data: Any) -> Optional[dict]:
    if not isinstance(data, dict) or not data:
        return None
    return {
        'ct_team_id': _int(data.get('ctTeamDbId')),
        'ct_score': _int(data.get('ctScore')),
        't_team_id': _int(data.get('tTeamDbId')),
        't_score': _int(data.get('tScore')),
    }


def _by_team(data: Any) -> dict[int, int]:
    return {_int(k): _int(v) for k, v in data.items()} if isinstance(data, dict) else {}


def parse_score(payload: Any) -> Optional[dict]:
    """Normalise a ``score`` event. Returns None when the payload is not a score object."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return None
    if not isinstance(payload, dict) or 'mapScores' not in payload:
        return None

    maps = []
    raw_maps = payload.get('mapScores') or {}
    for key in sorted(raw_maps, key=lambda k: _int(k)):
        m = raw_maps[key]
        if not isinstance(m, dict):
            continue
        maps.append({
            'ordinal': _int(m.get('mapOrdinal'), _int(key)),
            'map': m.get('map') or '',
            'over': bool(m.get('mapOver')),
            'default_win': bool(m.get('defaultWin')),
            'scores': _by_team(m.get('scores')),
            'ct_team_id': _int(m.get('currentCtId')),
            't_team_id': _int(m.get('currentTId')),
            'first_half': _half(m.get('firstHalf')),
            'second_half': _half(m.get('secondHalf')),
            'overtime': _half(m.get('overtime')),
        })

    live_log = payload.get('liveLog')
    return {
        'match_id': _int(payload.get('listId')),
        'maps': maps,
        'wins': _by_team(payload.get('wins')),
        'live_log': live_log if isinstance(live_log, dict) else {},
        'forced_live': bool(payload.get('forcedLive')),
        'forced_dead': bool(payload.get('forcedDead')),
        'current_map': next((m for m in reversed(maps) if not m['over']), maps[-1] if maps else None),
    }


def _decode(arg: Any) -> Any:
    """Events may carry JSON as a string; decode it when possible."""
    if isinstance(arg, str):
        try:
            return json.loads(arg)
        except ValueError:
            return arg
    return arg


Callback = Callable[[str, Any], Optional[Awaitable[None]]]


class LiveMatch:
    """A live subscription to one match. Keeps the latest data and optionally calls ``on_event``.

    :param match_id: HLTV match id.
    :param on_event: ``callback(event_name, data)`` (sync or async). For ``score`` events ``data`` is the parsed
        score, for anything else the decoded payload.
    :param cookies: optional cookie header string for the socket (e.g. copied from your own browser session).
    :param user_agent: User-Agent for the socket requests.
    :param client_factory: returns a python-socketio ``AsyncClient``, mainly for tests.
    """

    def __init__(self, match_id: int | str,
                 on_event: Optional[Callback] = None,
                 cookies: Optional[str] = None,
                 user_agent: str = DEFAULT_USER_AGENT,
                 url: str = SCOREBOT_URL,
                 client_factory: Optional[Callable[[], Any]] = None,
                 logger: Optional[logging.Logger] = None):
        self.match_id = str(match_id)
        self.on_event = on_event
        self.url = url
        self.headers = {**HEADERS, 'User-Agent': user_agent}
        if cookies:
            self.headers['Cookie'] = cookies
        self.logger = logger or logging.getLogger(__name__)
        self._factory = client_factory
        self.sio = None
        self.score: Optional[dict] = None
        self.scoreboard: Any = None
        self.log: list = []
        self.events: list[tuple[str, Any]] = []
        self._score_ready = asyncio.Event()
        self._changed = asyncio.Event()

    # --- connection -----------------------------------------------------------------

    def _make_client(self):
        if self._factory:
            return self._factory()
        try:
            import socketio
        except ImportError as e:
            raise ImportError(LIVE_INSTALL_HINT) from e
        return socketio.AsyncClient(reconnection=True, logger=False, engineio_logger=False)

    async def start(self) -> 'LiveMatch':
        if self.sio is not None:
            return self
        self.sio = self._make_client()
        self.sio.on('connect', self._on_connect)
        self.sio.on('*', self._on_any)
        try:
            await self.sio.connect(self.url, headers=self.headers, socketio_path=SOCKET_PATH,
                                   transports=['websocket', 'polling'], wait_timeout=15)
        except Exception as e:
            await self._discard_client()
            raise LiveConnectionError(f'{LIVE_BLOCKED_HINT} ({e})') from e
        return self

    async def _discard_client(self):
        """Release everything a failed connect leaves open (python-engineio keeps its aiohttp session)."""
        sio, self.sio = self.sio, None
        if sio is None:
            return
        try:
            await sio.disconnect()
        except Exception:
            pass
        http = getattr(getattr(sio, 'eio', None), 'http', None)
        if http is not None and not getattr(http, 'closed', True):
            try:
                await http.close()
            except Exception:
                pass

    async def _on_connect(self, *args):
        # (re)subscribe whenever the socket connects, also after an automatic reconnect
        await self.sio.emit('readyForMatch', json.dumps({'token': '', 'listId': self.match_id}))

    async def _on_any(self, event, *args):
        data = _decode(args[0]) if len(args) == 1 else [_decode(a) for a in args]
        await self.handle_event(event, data)

    async def handle_event(self, event: str, data: Any):
        if event == 'score':
            parsed = parse_score(data)
            if parsed is None:
                self.logger.debug(f'Unreadable score payload: {data!r}')
                return
            self.score = parsed
            self._score_ready.set()
            data = parsed
        elif event == 'scoreboard':
            self.scoreboard = data
        elif event in ('log', 'fullLog'):
            if event == 'fullLog' and isinstance(data, list):
                self.log = list(data)
            else:
                self.log.append(data)
        self.events.append((event, data))
        self._changed.set()
        if self.on_event:
            try:
                result = self.on_event(event, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:  # a broken callback must not kill the socket
                self.logger.error(f'on_event callback failed: {e}')

    # --- reading --------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            'match_id': int(self.match_id) if self.match_id.isdigit() else self.match_id,
            'score': self.score,
            'scoreboard': self.scoreboard,
            'log': list(self.log),
        }

    async def wait_for_score(self, timeout: float = 15) -> bool:
        try:
            await asyncio.wait_for(self._score_ready.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def updates(self):
        """Async iterator yielding ``(event, data)`` as they arrive until the match is closed."""
        seen = 0
        while self.sio is not None:
            while seen < len(self.events):
                yield self.events[seen]
                seen += 1
            self._changed.clear()
            if seen < len(self.events):
                continue
            await self._changed.wait()

    async def close(self):
        sio, self.sio = self.sio, None
        self._changed.set()
        if sio is not None:
            try:
                await sio.disconnect()
            except Exception as e:
                self.logger.debug(f'Error while closing socket: {e}')

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *exc):
        await self.close()


async def fetch_match_data(match_id: int | str, timeout: float = 15, settle: float = 1.0, **options) -> Optional[dict]:
    """Connect, wait for the first ``score`` event plus ``settle`` seconds of extra events, then disconnect.

    Returns the :meth:`LiveMatch.snapshot` dict, or None when nothing arrived within ``timeout`` seconds
    (match not live, blocked, or no connection).
    """
    live = LiveMatch(match_id, **options)
    try:
        await live.start()
        if not await live.wait_for_score(timeout):
            return None
        if settle > 0:
            await asyncio.sleep(settle)
        return live.snapshot()
    finally:
        await live.close()
