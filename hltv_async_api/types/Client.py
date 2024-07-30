import random
from typing import Optional, Union
from fake_useragent import UserAgent
from aiohttp import ClientSession
import logging


class Client:
    def __init__(self,
                 min_delay: Optional[float | int],
                 max_delay: Optional[float | int],
                 timeout: Optional[int],
                 max_retries: Optional[int],
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 proxy_delay: bool = False,
                 proxy_protocol: str | None = None,
                 remove_proxy: bool = False,
                 user_agent: str = None,
                 logger=logging.getLogger(),
                 ):
        if min_delay is None:
            min_delay = -1.0
        if max_delay is None:
            max_delay = 10.0
        if timeout is None:
            timeout = 5
        if max_retries is None:
            max_retries = 10

        self.logger = logger

        self.MIN_DELAY = float(min_delay)
        self.MAX_DELAY = float(max_delay)

        self.UA = UserAgent()
        if user_agent is None:
            user_agent = self.UA.random
        self.user_agent = user_agent

        rand_v = f"127.0.{round(random.random() * 10000)}.{round(random.random() * 100)}"

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en;q=0.9,en-US;q=0.8",
            "Cache-Control": "max-age=0",
            "Cookie": "nightmode=on; promode=on; hltvTimeZone=Europe/Copenhagen;",
            "Priority": "u=0, i",
            "Referer": "https://www.hltv.org/",
            "sec-ch-ua": f'"Microsoft Edge";v="127", "Chromium";v="{rand_v}"',
            "sec-ch-ua-arch": "x86",
            "sec-ch-ua-bitness": "64",
            "sec-ch-ua-full-version": f"{rand_v}",
            "sec-ch-ua-full-version-list": f'"Not)A;Brand";v="99.0.0.0", "Microsoft Edge";v="{rand_v}", "Chromium";v="{rand_v}"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "",
            "sec-ch-ua-platform": "Windows",
            "sec-ch-ua-platform-version": "15.0.0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": self.user_agent,
        }

        # user-agent switcher

        self.PROXY_PATH = proxy_path
        self.PROXY_LIST = proxy_list
        self.PROXY_PROTOCOL = proxy_protocol
        self.PROXY_ONCE = remove_proxy
        self.PROXY_DELAY = proxy_delay
        self.init_proxy()

        self._init_delay()
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = None
        self._create_session()

    def _create_session(self):
        if not self.session:
            self.logger.debug('Creating Session')
            self.session = ClientSession()

    def get_session(self):
        if not self.session:
            self._create_session()
        return self.session

    def set_session(self, aiohttp_client: ClientSession):
        self.session = aiohttp_client

    def _init_delay(self):
        if self.MIN_DELAY != -1.0:
            if self.MAX_DELAY >= self.MIN_DELAY >= 0.0 and self.MAX_DELAY >= 0.0:
                return
            self.logger.warning(f'Invalid min/max delay. Delay will be increasing by 1 sec')
        self.MIN_DELAY = None

    def init_proxy(self):
        self.USE_PROXY = self.PROXY_PATH or self.PROXY_LIST
        if self.USE_PROXY:
            if self.PROXY_PATH:
                with open(self.PROXY_PATH, "r") as file:
                    self.PROXY_LIST = [line.strip() for line in file.readlines()]
            if self.PROXY_PROTOCOL:
                self.PROXY_LIST = [self.PROXY_PROTOCOL + '://' + proxy for proxy in self.PROXY_LIST]

    def get_proxy(self):
        try:
            proxy = self.PROXY_LIST[0]

            if self.PROXY_PROTOCOL and proxy != '' and self.PROXY_PROTOCOL not in proxy:
                proxy = self.PROXY_PROTOCOL + '://' + proxy

            return proxy
        except IndexError:
            self.logger.error('No proxies left')

    def switch_proxy(self):
        try:
            if self.PROXY_ONCE:
                self.logger.debug(f'Removing proxy {self.PROXY_LIST[0]}')
                self.PROXY_LIST = self.PROXY_LIST[1:]
            else:
                self.logger.debug(f"Switching proxy {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")
                self.PROXY_LIST = self.PROXY_LIST[1:] + [(self.PROXY_LIST[0])]
                self.logger.info(f"New proxy: {self.PROXY_LIST[0] if self.PROXY_LIST[0] else 'No Proxy'}")
        except IndexError:
            self.logger.error('No proxies left')

    def switch_user_agent(self):
        if self.user_agent:
            self.headers['user-agent'] = self.UA.random

    async def close_session(self):
        await self.session.close()