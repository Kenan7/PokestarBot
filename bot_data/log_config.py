import inspect
import logging
from typing import Union

import discord.ext.commands


class UserChannelFormatter(logging.Formatter):

    def __init__(self):
        super().__init__("[%(asctime)s] {%(module)s::%(funcName)s} {%(user)s::%(channel)s::%(command)s::%(messageid)s} (%(levelname)s): %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        frame = inspect.currentframe()
        user = channel = command = messageid = msg = None
        while frame.f_back is not None:
            for key, value in frame.f_locals.items():
                if isinstance(value, discord.ext.commands.Context):
                    user = value.author
                    channel = value.channel
                    command = value.command
                    messageid = value.message.id
                    break
                elif isinstance(value, discord.Message):
                    msg = value
            frame = frame.f_back
        if msg and not command:
            user = msg.author
            channel = msg.channel
            messageid = msg.id
        record.user = user
        record.channel = channel
        record.command = command
        record.messageid = messageid
        return super().format(record)


class ShutdownStatusFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> Union[bool, int]:
        """Filters out the bot shutdown messages, which are not unexpected behavior."""
        if record.message in ["Started bot shutdown.", "Killing the bot with signal SIGINT."]:
            return False
        return super().filter(record)
