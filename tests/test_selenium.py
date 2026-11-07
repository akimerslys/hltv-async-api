"""Optional Selenium driver and the 403 hint. A fake driver stands in for Chrome, so no browser is needed."""

import asyncio
import logging
import threading

import pytest

from hltv_async_api import Hltv
from hltv_async_api.selenium_driver import SeleniumDriver, SeleniumParser
from hltv_async_api.sync.syncHltv import Hltv as SyncHltv
from hltv_async_api.types import Client, Executor, Parser
from hltv_async_api.Utils.hints import BLOCKED_HINT

from . import fixtures as fx

CHALLENGE = ('Just a moment...', '<html><div id="challenge-running"></div></html>')
PAGE = ('Rankings | HLTV', '<html>' + fx.TOP_TEAMS + '</html>')


class FakeDriver:
    """states: (title, page_source) pairs served one per page_source read; the last one repeats."""

    def __init__(self, states, get_error=None):
        self.states = list(states)
        self.get_error = get_error
        self.urls, self.quit_called, self.timeout = [], False, None
        self.active = self.max_active = 0
        self._current = self.states[0]

    def set_page_load_timeout(self, seconds):
        self.timeout = seconds

    def get(self, url):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.urls.append(url)
        if self.get_error:
            self.active -= 1
            raise self.get_error

    @property
    def title(self):
        return self._current[0]

    @property
    def page_source(self):
        self._current = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        self.active = max(0, self.active - 1)
        return self._current[1]

    def quit(self):
        self.quit_called = True


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr('hltv_async_api.selenium_driver.time.sleep', lambda s: None)


def driver_with(*states, **kw):
    fake = FakeDriver(states, kw.pop('get_error', None))
    return SeleniumDriver(driver_factory=lambda: fake, **kw), fake


# --- SeleniumDriver ---------------------------------------------------------------

@pytest.mark.parametrize('title, html, expected', [
    ('Just a moment...', '', True),
    ('Attention Required! | Cloudflare', '', True),
    ('Rankings | HLTV', '<div id="challenge-error-title"></div>', True),
    ('Rankings | HLTV', '<div id="challenge-running"></div>', True),
    ('Rankings | HLTV', '<html>ok</html>', False),
    ('', '<html>ok</html>', False),
])
def test_is_challenge(title, html, expected):
    assert SeleniumDriver.is_challenge(title, html) is expected


def test_get_html_returns_page():
    driver, fake = driver_with(PAGE, page_load_timeout=12)
    assert driver.get_html('https://www.hltv.org/ranking/teams') == PAGE[1]
    assert fake.urls == ['https://www.hltv.org/ranking/teams'] and fake.timeout == 12


def test_get_html_waits_for_challenge_to_finish():
    driver, _ = driver_with(CHALLENGE, CHALLENGE, PAGE, challenge_timeout=60)
    assert driver.get_html('https://www.hltv.org/') == PAGE[1]


def test_get_html_gives_up_when_challenge_never_ends():
    driver, _ = driver_with(CHALLENGE, challenge_timeout=0)
    assert driver.get_html('https://www.hltv.org/') is None


def test_get_html_returns_none_on_driver_error():
    driver, _ = driver_with(PAGE, get_error=TimeoutError('page load'))
    assert driver.get_html('https://www.hltv.org/') is None


def test_browser_starts_once_and_closes():
    created = []
    fake = FakeDriver([PAGE])
    driver = SeleniumDriver(driver_factory=lambda: created.append(1) or fake)
    driver.get_html('https://www.hltv.org/a')
    driver.get_html('https://www.hltv.org/b')
    assert created == [1]
    driver.close()
    driver.close()  # closing twice is harmless
    assert fake.quit_called


def test_missing_selenium_extra_gives_install_hint(monkeypatch):
    monkeypatch.setitem(__import__('sys').modules, 'undetected_chromedriver', None)
    with pytest.raises(ImportError, match=r'hltv-async-api\[selenium\]'):
        SeleniumDriver().start()


class FakeUC:
    """Stands in for undetected_chromedriver: the newest driver (no version_main) does not match Chrome 156."""

    class ChromeOptions:
        def __init__(self):
            self.args = []

        def add_argument(self, arg):
            self.args.append(arg)

    def __init__(self, installed=156, message=None):
        self.installed, self.calls = installed, []
        self.message = message
        outer = self

        class Chrome(FakeDriver):
            def __init__(self, options=None, version_main=None, **kw):
                outer.calls.append((version_main, kw))
                if version_main != outer.installed:
                    raise RuntimeError(outer.message or
                                       'This version of ChromeDriver only supports Chrome version 157. '
                                       f'Current browser version is {outer.installed}.0.8078.81')
                super().__init__([PAGE])

        self.Chrome = Chrome


def install_fake_uc(monkeypatch, **kw):
    fake = FakeUC(**kw)
    monkeypatch.setitem(__import__('sys').modules, 'undetected_chromedriver', fake)
    return fake


def test_driver_version_mismatch_retries_with_installed_chrome(monkeypatch):
    uc = install_fake_uc(monkeypatch)
    driver = SeleniumDriver()
    assert driver.get_html('https://www.hltv.org/') == PAGE[1]
    assert [version for version, _ in uc.calls] == [None, 156]


def test_driver_explicit_version_is_not_overridden(monkeypatch):
    uc = install_fake_uc(monkeypatch)
    with pytest.raises(RuntimeError, match='Current browser version is 156'):
        SeleniumDriver(version_main=150).start()
    assert [version for version, _ in uc.calls] == [150]


def test_driver_unrelated_startup_error_is_raised_without_retry(monkeypatch):
    uc = install_fake_uc(monkeypatch, message='chrome not reachable')
    with pytest.raises(RuntimeError, match='chrome not reachable'):
        SeleniumDriver().start()
    assert len(uc.calls) == 1


# --- SeleniumParser / clients -----------------------------------------------------

async def make_parser(driver, max_retries=2):
    logger = logging.getLogger('test-selenium')
    client = Client(None, None, None, max_retries, logger=logger)
    executor = Executor(loop=asyncio.get_running_loop(), logger=logger)
    parser = SeleniumParser(client, executor, logger, driver=driver)
    return parser, client, executor


async def close_all(parser, client, executor):
    await parser.close()
    await client.close_session()
    executor.close()


async def test_parser_returns_soup():
    driver, _ = driver_with(PAGE)
    parser, client, executor = await make_parser(driver)
    page = await parser.fetch('https://www.hltv.org/ranking/teams')
    assert page.find('div', class_='ranked-team') is not None
    await close_all(parser, client, executor)


async def test_parser_retries_then_gives_up(monkeypatch):
    async def fast_sleep(_):
        pass

    monkeypatch.setattr('hltv_async_api.selenium_driver.asyncio.sleep', fast_sleep)
    driver, fake = driver_with(CHALLENGE, challenge_timeout=0)
    parser, client, executor = await make_parser(driver, max_retries=3)
    assert await parser.fetch('https://www.hltv.org/') is None
    assert len(fake.urls) == 3
    await close_all(parser, client, executor)


async def test_parser_uses_one_browser_thread_for_concurrent_fetches():
    threads = set()
    driver, fake = driver_with(PAGE)
    original = driver.get_html

    def tracking(url):
        threads.add(threading.get_ident())
        return original(url)

    driver.get_html = tracking
    parser, client, executor = await make_parser(driver)
    pages = await asyncio.gather(*(parser.fetch(f'https://www.hltv.org/{i}') for i in range(5)))
    assert all(pages) and len(threads) == 1 and fake.max_active == 1
    await close_all(parser, client, executor)


async def test_async_client_with_selenium_end_to_end():
    fake = FakeDriver([PAGE])
    hltv = Hltv(selenium=True, selenium_options={'driver_factory': lambda: fake})
    teams = await hltv.get_top_teams(2, date_str='2026-10-07')
    assert [t['title'] for t in teams] == ['FaZe', 'Natus Vincere']
    assert fake.urls == ['https://www.hltv.org/ranking/teams/2026/october/5']
    await hltv.close()
    assert fake.quit_called


def test_sync_client_with_selenium_end_to_end():
    fake = FakeDriver([PAGE])
    with SyncHltv(selenium=True, selenium_options={'driver_factory': lambda: fake}) as hltv:
        teams = hltv.get_top_teams(2, date_str='2026-10-07')
    assert [t['title'] for t in teams] == ['FaZe', 'Natus Vincere']
    assert fake.quit_called


def test_sync_client_selenium_failure_returns_none():
    driver_fake = FakeDriver([CHALLENGE])
    hltv = SyncHltv(selenium=True, max_retries=2,
                    selenium_options={'driver_factory': lambda: driver_fake, 'challenge_timeout': 0})
    assert hltv.get_top_teams(2) is None
    assert len(driver_fake.urls) == 2


# --- 403 hint ---------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status):
        self.status = self.status_code = status
        self.text_ = '<html></html>'

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self):
        return self.text_

    @property
    def text_sync(self):
        return self.text_


class FakeSession:
    def __init__(self, status):
        self.status = status

    def get(self, url, **kw):
        return FakeResponse(self.status)


async def test_async_403_recommends_selenium_once(caplog):
    logger = logging.getLogger('test-hint')
    client = Client(0.001, 0.002, 1, 3, logger=logger)
    await client.session.close()
    client.session = FakeSession(403)
    parser = Parser(client, Executor(loop=asyncio.get_running_loop(), logger=logger), logger)
    with caplog.at_level(logging.ERROR, logger='test-hint'):
        assert await parser.fetch('https://www.hltv.org/') is None
        assert await parser.fetch('https://www.hltv.org/') is None
    hints = [r for r in caplog.records if r.getMessage() == BLOCKED_HINT]
    assert len(hints) == 1 and 'selenium' in BLOCKED_HINT


async def test_async_non_block_failure_has_no_hint(caplog):
    logger = logging.getLogger('test-nohint')
    client = Client(0.001, 0.002, 1, 2, logger=logger)
    await client.session.close()
    client.session = FakeSession(500)
    parser = Parser(client, Executor(loop=asyncio.get_running_loop(), logger=logger), logger)
    with caplog.at_level(logging.ERROR, logger='test-nohint'):
        assert await parser.fetch('https://www.hltv.org/') is None
    assert not [r for r in caplog.records if r.getMessage() == BLOCKED_HINT]


def test_sync_403_recommends_selenium_once(monkeypatch, caplog):
    hltv = SyncHltv(min_delay=0.001, max_delay=0.002, max_retries=3)
    monkeypatch.setattr(hltv.session, 'get', lambda url, **kw: FakeResponse(403))
    with caplog.at_level(logging.ERROR):
        assert hltv.get_top_teams(2) is None
        assert hltv.get_top_teams(2) is None
    assert len([r for r in caplog.records if r.getMessage() == BLOCKED_HINT]) == 1
