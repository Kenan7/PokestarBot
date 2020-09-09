from typing import TYPE_CHECKING

import discord.ext.commands

if TYPE_CHECKING:
    from ..bot import PokestarBot


class PokestarBotCog(discord.ext.commands.Cog):
    @property
    def commands(self):
        return set(self.get_commands())

    @property
    def name(self):
        return self.qualified_name

    def __repr__(self) -> str:
        return "<{} Cog with {} main commands and {} total commands>".format(type(self).__name__, len(self.get_commands()),
                                                                             len(list(self.walk_commands())))

    def __init__(self, bot: "PokestarBot"):
        self.bot = bot
