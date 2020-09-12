from typing import TYPE_CHECKING

import aiohttp.client_exceptions

if TYPE_CHECKING:
    from ..bot import PokestarBot


class ReloadingClient(aiohttp.ClientSession):
    def __init__(self, *, bot: "PokestarBot", **kwargs):
        super().__init__(**kwargs)
        self.bot = bot

    async def _request(self, method: str, str_or_url: str, **kwargs):
        try:
            return await super()._request(method, str_or_url, **kwargs)
        except aiohttp.client_exceptions.ClientConnectorError as exc:
            if exc.errno == 24:
                return await self.bot.run_reload()
