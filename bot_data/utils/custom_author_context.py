from typing import Optional, Union

import discord.ext.commands


class CustomContext(discord.ext.commands.Context):
    __slots__ = ["_author", "_channel"]

    _author: Optional[Union[discord.User, discord.Member]]
    _channel: Optional[discord.TextChannel]

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._author = self._channel = None

    @property
    def author(self) -> Union[discord.User, discord.Member]:
        return self._author or super().author

    @author.setter
    def author(self, new_author: Union[discord.User, discord.Member]):
        self._author = new_author

    @property
    def channel(self) -> discord.TextChannel:
        return self._channel or super().channel

    @channel.setter
    def channel(self, new_channel: discord.TextChannel):
        self._channel = new_channel
