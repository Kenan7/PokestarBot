from typing import Union

import discord.ext.commands


class MemberConverter(discord.ext.commands.MemberConverter):
    async def convert(self, ctx: discord.ext.commands.Context, argument: str) -> Union[str, discord.Member]:
        try:
            return await super().convert(ctx, argument)
        except discord.ext.commands.BadArgument:
            return argument
