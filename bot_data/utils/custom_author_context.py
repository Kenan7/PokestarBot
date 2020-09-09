import discord.ext.commands


class CustomAuthorContext(discord.ext.commands.Context):
    __slots__ = ["_author"]

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._author = None

    @property
    def author(self):
        return self._author or super().author()

    @author.setter
    def author(self, new_author: discord.Member):
        self._author = new_author
