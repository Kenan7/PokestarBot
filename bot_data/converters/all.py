import discord.ext.commands


class AllConverter(discord.ext.commands.Converter):
    All = object()

    async def convert(self, ctx: discord.ext.commands.Context, argument: str):
        if argument == "all":
            return self.All
        raise discord.ext.commands.BadArgument(f"{argument} != all")
