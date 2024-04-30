import asyncio
from hltv_async_api import Hltv
from hltv_async_api.unreleased import Unreleased


async def main():
    hltv = Hltv(proxy_path='proxies.txt', proxy_protocol='http', debug=True)
    hltv_beta = Unreleased(hltv)
    teams = await hltv.get_top_teams()
    for team in teams:
        players = await hltv.get_team_info(team['id'], team['title'])
        for player, id_ in players['players'].items():
            await hltv_beta.get_player_imgs(id_, player)


if __name__ == '__main__':
    asyncio.run(main())
