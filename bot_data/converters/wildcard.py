import discord.ext.commands


class WildcardConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: discord.ext.commands.Context, argument: str):
        if argument == "*":
            return None
        return argument
