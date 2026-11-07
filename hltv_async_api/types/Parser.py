import asyncio
import contextlib
import random
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from hltv_async_api.Utils.hints import BLOCKED_HINT


class Parser:
    def __init__(self, client, executor, logger):
        self.logger = logger
        self.client = client
        self.executor = executor
        self.blocked = False
        self._hint_shown = False
        limit = getattr(client, 'max_concurrency', None)
        self._gate = asyncio.Semaphore(limit) if limit else None

    @property
    def session(self):
        return self.client.session

    @staticmethod
    def _f(result):
        return BeautifulSoup(result, "lxml")

    def _parse_html(self, result):
        """Parse + challenge check in one worker hop: (page, blocked)."""
        page = self._f(result)
        return page, self._cloudflare_check(page)

    def _cloudflare_check(self, page) -> bool:
        challenge_page = page.find(id="challenge-error-title")
        if challenge_page is not None:
            if "Enable JavaScript and cookies to continue" in challenge_page.get_text().strip():
                self.logger.debug("Got cloudflare challenge page")
                return True
        return False

    def _parse_error_handler(self, delay: int = 0) -> int:
        if self.client.USE_PROXY:
            self.client.switch_proxy()
            if not self.client.PROXY_DELAY:
                return 0

        if self.client.MIN_DELAY:
            delay = random.uniform(self.client.MIN_DELAY, self.client.MAX_DELAY)
            self.logger.debug(f'Random delay {round(delay, 2)}s')
        elif self.client.MAX_DELAY and delay < self.client.MAX_DELAY:
            delay += 1
            self.logger.info(f"Increasing delay to {delay}s")

        return delay

    async def _parse(self, url, delay):
        proxy = ''
        # setup new proxy, cuz old one was switched
        if self.client.USE_PROXY:
            proxy = self.client.get_proxy()
        elif delay:
            # retry pause, only for non-proxy users and only when min/max_delay were configured
            await asyncio.sleep(delay)
        try:
            async with self._gate or contextlib.nullcontext():
                async with self.session.get(url, headers=self.client.headers, proxy=proxy,
                                            timeout=ClientTimeout(total=self.client.timeout)) as response:
                    self.logger.info(f"Fetching {url}, code: {response.status}")
                    if response.status == 200:
                        result = await response.text()
                        page, forbidden = await self.executor.run(self._parse_html, result)
                        if not forbidden:
                            return True, page
                        self.blocked = True
                    elif response.status == 403:
                        self.blocked = True

                    self.logger.debug(f"Error, Code {response.status=}")
            return False, self._parse_error_handler(delay)

        except Exception as e:
            self.logger.debug(e)

        delay = self._parse_error_handler(delay)
        return False, delay

    async def fetch(self, url, delay: int = 0):
        if not self.client.session:
            self.client._create_session()
        status = False
        try_ = 1
        result = None

        # parse until success or not max retries
        while (not status) and (try_ != self.client.max_retries):
            self.logger.debug(f'Trying connect to {url}, try {try_}/{self.client.max_retries}')

            # if status = True, result = page,
            # if status = False, result = delay (default=0)
            status, result = await self._parse(url, delay)

            if not status and result:
                delay = result
            try_ += 1

        if status:
            return result
        else:
            self.logger.error('Connection failed')
            if self.blocked and not self._hint_shown:
                self._hint_shown = True
                self.logger.error(BLOCKED_HINT)
            return None
