import datetime
from typing import Union

import discord.ext.commands


class Embed(discord.Embed):
    def __init__(self, message_or_context: Union[discord.Message, discord.ext.commands.Context], **kwargs):
        author = message_or_context.author
        if not kwargs.get("timestamp", discord.Embed.Empty):
            kwargs.update(timestamp=datetime.datetime.utcnow())
        super().__init__(**kwargs)
        self.set_author(name=author, icon_url=author.avatar_url_as(size=4096))
