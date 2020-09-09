import discord.ext.commands


class RolesConverter(discord.ext.commands.RoleConverter):
    async def convert(self, ctx: discord.ext.commands.Context, argument: str) -> discord.Role:
        try:
            return await super().convert(ctx, argument)
        except discord.ext.commands.BadArgument as ba:
            if argument.isnumeric():
                try:
                    return ctx.guild.roles[int(argument)]
                except IndexError:
                    raise ba
