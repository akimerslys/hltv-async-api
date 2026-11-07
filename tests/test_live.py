"""Optional live socket support. A fake socket.io client stands in for the network."""

import asyncio
import json

import pytest

from hltv_async_api import Hltv
from hltv_async_api.live import LiveMatch, fetch_match_data, parse_score

SCORE = {
    'mapScores': {
        '1': {
            'firstHalf': {'ctTeamDbId': 10, 'ctScore': 7, 'tTeamDbId': 20, 'tScore': 5},
            'secondHalf': {'ctTeamDbId': 20, 'ctScore': 3, 'tTeamDbId': 10, 'tScore': 2},
            'overtime': {},
            'mapOrdinal': 1,
            'scores': {'10': 9, '20': 8},
            'currentCtId': 20,
            'currentTId': 10,
            'defaultWin': False,
            'map': 'de_dust2',
            'mapOver': False,
        }
    },
    'listId': 2400302,
    'wins': {'10': 1, '20': 0},
    'liveLog': {'requireHealth': True},
    'forcedLive': False,
    'forcedDead': False,
}


class FakeSio:
    """Mimics the socketio.AsyncClient parts used by LiveMatch."""

    def __init__(self, script=()):
        self.script, self.handlers, self.emitted = list(script), {}, []
        self.connect_kwargs, self.disconnected = None, False

    def on(self, event, handler):
        self.handlers[event] = handler

    async def connect(self, url, **kw):
        self.url, self.connect_kwargs = url, kw
        await self.handlers['connect']()

    async def emit(self, event, data=None):
        self.emitted.append((event, data))
        for name, payload in self.script:  # the server answers once the client is subscribed
            await self.handlers['*'](name, payload)

    async def disconnect(self):
        self.disconnected = True


def live_with(script=(), **kw):
    sio = FakeSio(script)
    return LiveMatch(2400302, client_factory=lambda: sio, **kw), sio


def test_parse_score_full_payload():
    score = parse_score(SCORE)
    assert score['match_id'] == 2400302
    assert score['wins'] == {10: 1, 20: 0}
    (m,) = score['maps']
    assert (m['map'], m['ordinal'], m['over']) == ('de_dust2', 1, False)
    assert m['scores'] == {10: 9, 20: 8} and (m['ct_team_id'], m['t_team_id']) == (20, 10)
    assert m['first_half'] == {'ct_team_id': 10, 'ct_score': 7, 't_team_id': 20, 't_score': 5}
    assert m['overtime'] is None
    assert score['current_map'] is m
    assert score['live_log'] == {'requireHealth': True}


def test_parse_score_accepts_json_string_and_rejects_garbage():
    assert parse_score(json.dumps(SCORE))['match_id'] == 2400302
    for bad in (None, 'nope', 42, {}, {'listId': 1}):
        assert parse_score(bad) is None


def test_parse_score_tolerates_missing_fields():
    score = parse_score({'mapScores': {'2': {}}, 'listId': '5'})
    assert score['match_id'] == 5 and score['maps'][0]['scores'] == {} and score['wins'] == {}


async def test_subscribes_with_expected_handshake():
    live, sio = live_with([('score', json.dumps(SCORE))], cookies='a=b')
    async with live:
        assert await live.wait_for_score(1)
    assert sio.url == 'https://scorebot-lb.hltv.org'
    assert sio.connect_kwargs['socketio_path'] == '/socket.io'
    headers = sio.connect_kwargs['headers']
    assert headers['Origin'] == 'https://www.hltv.org' and headers['Cookie'] == 'a=b'
    event, payload = sio.emitted[0]
    assert event == 'readyForMatch' and json.loads(payload) == {'token': '', 'listId': '2400302'}
    assert sio.disconnected


async def test_collects_score_scoreboard_and_log():
    live, _ = live_with([('score', SCORE), ('scoreboard', {'ct': []}), ('log', {'a': 1}), ('log', {'a': 2})])
    async with live:
        await live.wait_for_score(1)
    snap = live.snapshot()
    assert snap['match_id'] == 2400302 and snap['score']['maps'][0]['map'] == 'de_dust2'
    assert snap['scoreboard'] == {'ct': []} and snap['log'] == [{'a': 1}, {'a': 2}]


async def test_full_log_replaces_log():
    live, _ = live_with()
    await live.handle_event('log', {'a': 1})
    await live.handle_event('fullLog', [{'b': 1}, {'b': 2}])
    assert live.log == [{'b': 1}, {'b': 2}]


async def test_wait_for_score_times_out():
    live, _ = live_with()
    async with live:
        assert await live.wait_for_score(0.01) is False


async def test_callbacks_sync_async_and_failing():
    seen = []
    live, _ = live_with(on_event=lambda e, d: seen.append(e))
    await live.handle_event('log', 1)

    async def acb(e, d):
        seen.append(('async', e))

    live.on_event = acb
    await live.handle_event('log', 2)

    def broken(e, d):
        raise RuntimeError('boom')

    live.on_event = broken
    await live.handle_event('log', 3)  # must not raise
    assert seen == ['log', ('async', 'log')] and len(live.events) == 3


async def test_updates_iterator_ends_on_close():
    live, _ = live_with([('log', 1), ('log', 2)])
    await live.start()
    got = []

    async def consume():
        async for event, data in live.updates():
            got.append(data)

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.01)
    await live.close()
    await asyncio.wait_for(task, 1)
    assert got == [1, 2]


async def test_fetch_match_data_one_shot(monkeypatch):
    sio = FakeSio([('score', SCORE)])
    data = await fetch_match_data(2400302, timeout=1, settle=0, client_factory=lambda: sio)
    assert data['score']['wins'] == {10: 1, 20: 0} and sio.disconnected


async def test_fetch_match_data_returns_none_when_not_live():
    sio = FakeSio()
    assert await fetch_match_data(1, timeout=0.01, settle=0, client_factory=lambda: sio) is None
    assert sio.disconnected


async def test_hltv_get_match_data_and_live_match(monkeypatch):
    sio = FakeSio([('score', SCORE)])
    monkeypatch.setattr('hltv_async_api.live.LiveMatch._make_client', lambda self: sio)
    hltv = Hltv()
    data = await hltv.get_match_data(2400302, timeout=1, settle=0)
    assert data['score']['match_id'] == 2400302

    sio2 = FakeSio([('score', SCORE)])
    monkeypatch.setattr('hltv_async_api.live.LiveMatch._make_client', lambda self: sio2)
    live = await hltv.live_match(2400302)
    assert await live.wait_for_score(1)
    await hltv.close()
    assert sio2.disconnected


async def test_safe_mode_blocks_live():
    hltv = Hltv(safe_mode=True)
    assert await hltv.get_match_data(1) is None and await hltv.live_match(1) is None
    await hltv.close()


async def test_missing_live_extra_gives_install_hint(monkeypatch):
    monkeypatch.setitem(__import__('sys').modules, 'socketio', None)
    with pytest.raises(ImportError, match=r'hltv-async-api\[live\]'):
        await LiveMatch(1).start()


class FailingSio(FakeSio):
    async def connect(self, url, **kw):
        raise ConnectionError('Connection error')


async def test_failed_connect_returns_none_and_cleans_up(monkeypatch):
    sio = FailingSio()
    monkeypatch.setattr('hltv_async_api.live.LiveMatch._make_client', lambda self: sio)
    hltv = Hltv()
    assert await hltv.get_match_data(1, timeout=1) is None
    assert await hltv.live_match(1) is None
    assert sio.disconnected
    await hltv.close()


async def test_live_uses_selenium_browser_identity(monkeypatch):
    sio = FakeSio([('score', SCORE)])
    monkeypatch.setattr('hltv_async_api.live.LiveMatch._make_client', lambda self: sio)
    hltv = Hltv()

    class Parser:
        async def browser_identity(self):
            return 'cf_clearance=abc', 'UA/1.0'

    hltv.PARSER = Parser()
    assert await hltv.get_match_data(2400302, timeout=1, settle=0)
    headers = sio.connect_kwargs['headers']
    assert headers['Cookie'] == 'cf_clearance=abc' and headers['User-Agent'] == 'UA/1.0'
