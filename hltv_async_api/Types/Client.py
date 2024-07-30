from aiohttp import ClientSession
import logging

class Client:
    def __init__(self,
                 min_delay: float | int = -1.0,
                 max_delay: float | int = 10.0,
                 timeout: int = 5,
                 max_retries: int = 10,
                 proxy_path: str | None = None,
                 proxy_list: list | None = None,
                 proxy_delay: bool = False,
                 proxy_protocol: str | None = None,
                 remove_proxy: bool = False,
                 logger=logging.getLogger(),
                 ):
        self.logger = logger
        self.MIN_DELAY = float(min_delay)
        self.MAX_DELAY = float(max_delay)

        # user-agent switcher
        self.headers = {
            "referer": "https://www.hltv.org/stats",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "hltvTimeZone": "Europe/Copenhagen"
        }
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

    async def close_session(self):
        await self.session.close()