"""Optional Selenium fetcher built on undetected-chromedriver.

Install with ``pip install hltv-async-api[selenium]`` and a Chrome browser. Enable it with
``Hltv(selenium=True)`` (async) or ``Hltv(selenium=True)`` from ``hltv_async_api.sync.syncHltv`` (sync).
"""

import asyncio
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

from hltv_async_api.types.Parser import Parser
from hltv_async_api.Utils.hints import SELENIUM_INSTALL_HINT

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
    """

    def __init__(self,
                 headless: bool = False,
                 version_main: Optional[int] = None,
                 page_load_timeout: float = 30,
                 challenge_timeout: float = 30,
                 proxy: Optional[str] = None,
                 user_data_dir: Optional[str] = None,
                 driver_factory: Optional[Callable[[], Any]] = None,
                 logger: Optional[logging.Logger] = None):
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
            try:
                self._driver.quit()
            except Exception as e:
                self.logger.debug(f'Error while closing Chrome: {e}')
            self._driver = None


class SeleniumParser(Parser):
    """Drop-in replacement for ``Parser`` that fetches pages through a real browser."""

    def __init__(self, client, executor, logger, driver: Optional[SeleniumDriver] = None, **driver_options):
        super().__init__(client, executor, logger)
        self.driver = driver or SeleniumDriver(logger=logger, **driver_options)
        # one browser: selenium is not thread-safe, so every call goes through this single worker
        self._browser_thread = ThreadPoolExecutor(max_workers=1, thread_name_prefix='hltv-selenium')
        self._lock = asyncio.Lock()

    async def fetch(self, url, delay: int = 0):
        attempts = self.client.max_retries or 3
        async with self._lock:
            for attempt in range(1, attempts + 1):
                self.logger.debug(f'Selenium fetching {url}, try {attempt}/{attempts}')
                html = await asyncio.get_running_loop().run_in_executor(self._browser_thread, self.driver.get_html, url)
                if html:
                    page = await self.executor.run(self._f, html)
                    if not await self.executor.run(self._cloudflare_check, page):
                        return page
                await asyncio.sleep(attempt)

        self.logger.error('Connection failed')
        return None

    async def close(self):
        await asyncio.get_running_loop().run_in_executor(self._browser_thread, self.driver.close)
        self._browser_thread.shutdown(wait=False)
