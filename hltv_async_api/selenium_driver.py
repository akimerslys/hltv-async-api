"""Optional Selenium fetcher built on undetected-chromedriver.

Install with ``pip install hltv-async-api[selenium]`` and a Chrome browser. Enable it with
``Hltv(selenium=True)`` (async) or ``Hltv(selenium=True)`` from ``hltv_async_api.sync.syncHltv`` (sync).
"""

import asyncio
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from hltv_async_api.types.Parser import Parser
from hltv_async_api.Utils.hints import SELENIUM_INSTALL_HINT

# undetected-chromedriver patches one shared driver binary on start, so launches must not overlap
_START_LOCK = threading.Lock()

# Title / markers of the Cloudflare interstitial the browser has to get past on its own.
_CHALLENGE_TITLES = ('just a moment', 'attention required', 'verifying you are human')


class SeleniumDriver:
    """Blocking wrapper around an undetected Chrome driver that returns page HTML.

    :param headless: run Chrome without a window. Cloudflare detects headless mode more often, so the default is False.
    :param version_main: major Chrome version to match the driver to (auto-detected when None).
    :param page_load_timeout: seconds to wait for a page to load.
    :param challenge_timeout: seconds to wait for Cloudflare's check to finish by itself.
    :param proxy: proxy URL such as ``http://1.2.3.4:8080``.
    :param user_data_dir: Chrome profile folder; reusing one keeps the Cloudflare clearance cookie between runs.
    :param driver_factory: callable returning a driver object, mainly for tests.
    :param page_load_strategy: ``eager`` returns at DOMContentLoaded (much faster, HLTV is server-rendered);
        use ``normal`` to wait for every ad and tracker too.
    """

    def __init__(self,
                 headless: bool = False,
                 version_main: Optional[int] = None,
                 page_load_timeout: float = 30,
                 challenge_timeout: float = 30,
                 proxy: Optional[str] = None,
                 user_data_dir: Optional[str] = None,
                 driver_factory: Optional[Callable[[], Any]] = None,
                 logger: Optional[logging.Logger] = None,
                 page_load_strategy: str = 'eager'):
        self.page_load_strategy = page_load_strategy
        self.headless = headless
        self.version_main = version_main
        self.page_load_timeout = page_load_timeout
        self.challenge_timeout = challenge_timeout
        self.proxy = proxy
        self.user_data_dir = user_data_dir
        self.logger = logger or logging.getLogger(__name__)
        self._factory = driver_factory
        self._driver = None

    def _launch(self, uc, version_main: Optional[int]):
        options = uc.ChromeOptions()
        if self.proxy:
            options.add_argument(f'--proxy-server={self.proxy}')
        options.add_argument('--lang=en-US')
        if self.page_load_strategy:
            options.page_load_strategy = self.page_load_strategy
        return uc.Chrome(options=options,
                         headless=self.headless,
                         version_main=version_main,
                         user_data_dir=self.user_data_dir,
                         use_subprocess=True)

    def _create_driver(self):
        if self._factory:
            return self._factory()
        try:
            import undetected_chromedriver as uc
        except ImportError as e:
            raise ImportError(SELENIUM_INSTALL_HINT) from e

        try:
            return self._launch(uc, self.version_main)
        except Exception as e:
            # By default undetected-chromedriver fetches the newest ChromeDriver, which refuses to drive an older
            # Chrome ("Current browser version is 156..."). Retry once with the driver for the installed version.
            installed = re.search(r'Current browser version is (\d+)', str(e))
            if self.version_main is not None or not installed:
                raise
            self.logger.warning(f'ChromeDriver does not match Chrome {installed.group(1)}, retrying with a matching one')
            return self._launch(uc, int(installed.group(1)))

    def start(self):
        if self._driver is None:
            self.logger.debug('Starting undetected Chrome')
            with _START_LOCK:
                self._driver = self._create_driver()
            self._driver.set_page_load_timeout(self.page_load_timeout)
        return self._driver

    @staticmethod
    def is_challenge(title: str, html: str) -> bool:
        if title and title.strip().lower().startswith(_CHALLENGE_TITLES):
            return True
        return 'id="challenge-error-title"' in html or 'id="challenge-running"' in html

    def get_html(self, url: str) -> Optional[str]:
        """Open ``url`` and return its HTML, or None when the page never got past the Cloudflare check."""
        driver = self.start()
        try:
            driver.get(url)
        except Exception as e:  # selenium raises TimeoutException, WebDriverException, ...
            self.logger.debug(f'Selenium error on {url}: {e}')
            return None

        deadline = time.monotonic() + self.challenge_timeout
        while True:
            html = driver.page_source
            if not self.is_challenge(driver.title, html):
                return html
            if time.monotonic() >= deadline:
                self.logger.debug(f'Cloudflare check did not finish for {url}')
                return None
            time.sleep(1)

    def close(self):
        if self._driver is not None:
            driver, self._driver = self._driver, None
            try:
                driver.quit()
            except Exception as e:
                self.logger.debug(f'Error while closing Chrome: {e}')
            # undetected-chromedriver quits again from __del__, which raises "handle is invalid" at interpreter exit
            cls = type(driver)
            if cls.__module__.startswith('undetected_chromedriver') and hasattr(cls, '__del__'):
                cls.__del__ = lambda self: None

    def identity(self):
        """(cookie header for hltv.org, User-Agent) of the running browser, or (None, None)."""
        if self._driver is None:
            return None, None
        try:
            cookies = [c for c in self._driver.get_cookies() if str(c.get('domain', '')).lstrip('.').endswith('hltv.org')]
            header = '; '.join(f"{c['name']}={c['value']}" for c in cookies) or None
            return header, self._driver.execute_script('return navigator.userAgent')
        except Exception as e:
            self.logger.debug(f'Could not read browser identity: {e}')
            return None, None


class SeleniumParser(Parser):
    """Drop-in replacement for ``Parser`` that fetches pages through real browsers.

    ``pool_size`` browsers run side by side (each on its own worker thread, because selenium is not thread-safe),
    so concurrent ``fetch`` calls are served in parallel. Every browser is a full Chrome: mind your RAM.
    """

    def __init__(self, client, executor, logger, driver: Optional[SeleniumDriver] = None, pool_size: int = 1,
                 **driver_options):
        super().__init__(client, executor, logger)
        drivers = [driver or SeleniumDriver(logger=logger, **driver_options)]
        for i in range(1, max(1, pool_size)):
            options = dict(driver_options)
            if options.get('user_data_dir'):  # a Chrome profile can only be open once
                options['user_data_dir'] = f"{options['user_data_dir']}-{i}"
            drivers.append(SeleniumDriver(logger=logger, **options))
        self.driver = drivers[0]
        self._pool = [(d, ThreadPoolExecutor(max_workers=1, thread_name_prefix=f'hltv-selenium-{i}'))
                      for i, d in enumerate(drivers)]
        self._browser_thread = self._pool[0][1]
        self._free: asyncio.Queue = asyncio.Queue()
        for slot in self._pool:
            self._free.put_nowait(slot)

    async def fetch(self, url, delay: int = 0):
        attempts = self.client.max_retries or 3
        driver, thread = await self._free.get()
        try:
            for attempt in range(1, attempts + 1):
                self.logger.debug(f'Selenium fetching {url}, try {attempt}/{attempts}')
                html = await asyncio.get_running_loop().run_in_executor(thread, driver.get_html, url)
                if html:
                    page, blocked = await self.executor.run(self._parse_html, html)
                    if not blocked:
                        return page
                if attempt < attempts:
                    await asyncio.sleep(attempt)
        finally:
            self._free.put_nowait((driver, thread))

        self.logger.error('Connection failed')
        return None

    async def browser_identity(self):
        return await asyncio.get_running_loop().run_in_executor(self._browser_thread, self.driver.identity)

    async def close(self):
        loop = asyncio.get_running_loop()
        await asyncio.gather(*(loop.run_in_executor(thread, driver.close) for driver, thread in self._pool))
        for _, thread in self._pool:
            thread.shutdown(wait=False)
