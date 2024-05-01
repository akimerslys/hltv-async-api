import asyncio
from functools import partial
from typing import TYPE_CHECKING
import io
import os
from aiohttp import ClientResponseError, ClientProxyConnectionError, ServerDisconnectedError, ClientHttpProxyError, \
    ClientTimeout, ClientOSError
try:
    from .aiohltv import Hltv
except ImportError:
    from aiohltv import Hltv

try:
    import aiofiles
    import cairo
except ImportError:
    print('To use unreleased functions you need to install AIOFILES')


class Unreleased(Hltv):
    def __init__(self, hltv: Hltv):
        super().__init__(
                max_delay=hltv.MAX_DELAY,
                timeout=hltv.timeout,
                proxy_path=hltv.PROXY_PATH,
                proxy_list=hltv.PROXY_LIST,
                debug=hltv.DEBUG,
                max_retries=hltv.max_retries,
                proxy_protocol=hltv.PROXY_PROTOCOL,
                remove_proxy=hltv.PROXY_ONCE,
                tz=hltv.TIMEZONE
            )

    async def _parse_image(self, url, delay):
        proxy = ''
        # setup new proxy, cuz old one was switched
        if self.USE_PROXY:
            proxy = self._get_proxy()
        else:
            # delay, only for non-proxy users. (default = 1-15s)
            await asyncio.sleep(delay)
        try:
            async with self.session.get(url, headers=self.headers, proxy=proxy, timeout=self.timeout) as response:
                self.logger.info(f"Fetching {url}, code: {response.status}")
                if response.status == 200:
                    result = await response.read()
                    return True, result
                self.logger.debug("Got 403 forbitten")
                return False, await self.loop.run_in_executor(None, partial(self._parse_error_handler, delay))
        except (ClientProxyConnectionError, ClientResponseError, ClientOSError,
                ServerDisconnectedError, TimeoutError, ClientHttpProxyError, ClientTimeout) as e:
            self.logger.debug(e)
            delay = self._parse_error_handler(delay)
            return False, delay

    async def _fetch_save_image(self, url, delay: int = 0, team: str = '', svg: bool = False):
        if not self.session:
            self._create_session()
        status = False
        try_ = 1
        result = None

        # parse until success or not max retries
        while (not status) and (try_ != self.max_retries):
            self.logger.debug(f'Trying connect to {url}, try {try_}/{self.max_retries}')

            # if status = True, result = page,
            # if status = False, result = delay (default=0)
            status, result = await self._parse_image(url, delay)

            if not status and result:
                delay = result
            try_ += 1

        if status:
            if svg:
                f = await aiofiles.open(f'teams/{team}.svg', mode='wb')
                await f.write(result)
                await f.close()
            else:
                f = await aiofiles.open(f'players/{team}.png', mode='wb')
                await f.write(result)
                await f.close()

        else:
            self.logger.error('Connection failed')
            return None

    async def get_player_imgs(self, id: str | int, nickname: str):
        r = await self._fetch(f'https://www.hltv.org/player/{str(id)}/{nickname}')

        imgs = r.find('div', class_='playerBodyshot').find_all('img')

        team_str = r.find('div', class_='playerInfoRow playerTeam').find('a').get_text().strip()

        if not os.path.exists(f'teams/{team_str}.svg'):
            await self._fetch_save_image(imgs[-2]['src'].replace('amp;', ''), team=team_str, svg=True)
        if not os.path.exists(f'players/{nickname}.png'):
            await self._fetch_save_image(imgs[-1]['src'].replace('amp;', ''), team=nickname)


async def main():
    hltv = Hltv(proxy_path='proxies.txt', proxy_protocol='http', debug=True)
    hltv_beta = Unreleased(hltv)
    await hltv_beta.get_player_imgs('7998', 's1mple')


if __name__ == '__main__':
    asyncio.run(main())

