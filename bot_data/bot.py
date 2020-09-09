import asyncio
import atexit
import datetime
import logging
import os
import re
import subprocess
import sys
import traceback
from typing import Dict, Optional, Union

import aiohttp
import aiosqlite
import discord.ext.commands
import discord.ext.tasks
import pytz

from bot_data.creds import TOKEN, owner_id
from bot_data.utils import BoundedList, Embed, StaticNumber, StopCommand, Sum, break_into_groups, send_embeds, send_embeds_fields

logger = logging.getLogger(__name__)

stats_type = Dict[Union[int, str], Dict[Union[str, int], Union[Sum, int, Dict[Union[int, str], Union[Sum, StaticNumber]]]]]
NY = pytz.timezone("America/New_York")


class PokestarBot(discord.ext.commands.Bot):
    INVALID_SPOILER = re.compile(r"(?<!\|)(\|\|[^|]+\||\|[^|]+\|\|)(?!\|)", flags=re.UNICODE | re.MULTILINE | re.IGNORECASE)
    URL_REGEX = re.compile(
        r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s("
        r")<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", flags=re.UNICODE | re.IGNORECASE)
    WARNING = "You seem to have posted improperly tagged spoilers. As a convenience, the bot has removed the spoiler for you in order to avoid " \
              "accidentally spoiling other people. The next two messages contain the message and the raw markdown for it. If the message is >1000 " \
              "characters, the raw markdown might not send. If the bot has made a mistake, send the *exact* same message again and it will not be " \
              "removed. You can copy-paste and send the Markdown text in order to send the *exact* same message."
    WARNING_FAIL = "You seem to have posted improperly tagged spoilers. The bot has tried to delete your message, but was forbidden from doing so. " \
                   "Please try to properly mark spoilers. Note that the spoiler syntax is `||<content>||`, where `<content>` is what you want to be" \
                   " spoilered. Another option to mark spoilers is to start your message with `/spoiler`, but note that this spoilers your *entire*" \
                   " message. You *cannot* use `/spoiler` partway into a message."
    QUOTE_MARKER = re.compile(r"^[\s>]+")
    BAD_ARGUMENT = re.compile(r'Converting to "([\S]+)" failed for parameter "([\S]+)".')

    def __init__(self):
        super().__init__("%", max_messages=100, activity=discord.Game("%help"), case_insensitive=True)
        self.collections = {}
        self.stats: stats_type = {}
        self.stats_working_on = asyncio.Event()
        self.stats_lock = asyncio.Lock()
        self.pings = BoundedList()
        self.spoiler_hashes = BoundedList()
        self.ping_timedelta = datetime.timedelta(seconds=0)
        self.owner_id = owner_id
        self.obj_ids = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.conn: Optional[aiosqlite.Connection] = None
        self.channel_data = {}
        self.disabled_commands = {}

        for file in os.listdir(os.path.abspath(os.path.join(__file__, "..", "extensions"))):
            if not file.startswith("_"):
                name, sep, ext = file.rpartition(".")
                self.load_extension("bot_data.extensions.{}".format(name))

    def get_channel_data(self, guild_id: int, channel_name: str) -> Optional[discord.TextChannel]:
        guild_data = self.channel_data.get(guild_id, None)
        if guild_data is None:
            return None
        else:
            channel_id = guild_data.get(channel_name, None)
            if channel_id is None:
                return None
            return self.get_guild(guild_id).get_channel(channel_id)

    def command_disabled(self, ctx: discord.ext.commands.Context):
        if not hasattr(ctx.guild, "id"):
            return True
        guild_data = self.disabled_commands.get(ctx.guild.id, [])
        cmd_name = ctx.command.qualified_name
        for name in guild_data:
            if name.startswith(cmd_name):
                return True
        return False

    async def pre_create(self):
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS CHANNEL_DATA(ID INTEGER PRIMARY KEY AUTOINCREMENT, GUILD_ID BIGINT NOT NULL, CHANNEL_NAME TEXT NOT 
                NULL, CHANNEL_ID BIGINT NOT NULL, UNIQUE (GUILD_ID, CHANNEL_NAME))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS DISABLED_COMMANDS(ID INTEGER PRIMARY KEY AUTOINCREMENT, GUILD_ID BIGINT NOT NULL, COMMAND_NAME TEXT 
                NOT NULL, UNIQUE (GUILD_ID, COMMAND_NAME))"""):
            pass

    @staticmethod
    def add_check_recursive(command: discord.ext.commands.Command, check):
        command.add_check(check)
        if isinstance(command, discord.ext.commands.Group):
            for subcommand in command.walk_commands():
                subcommand.add_check(check)

    async def get_channel_mappings(self):
        async with self.conn.execute("""SELECT GUILD_ID, CHANNEL_NAME, CHANNEL_ID FROM CHANNEL_DATA""") as cursor:
            data = await cursor.fetchall()
        for guild_id, channel_name, channel_id in data:
            guild_data = self.channel_data.setdefault(guild_id, {})
            guild_data[channel_name] = channel_id

    async def get_disabled_commands(self):
        self.disabled_commands = {}
        async with self.conn.execute("""SELECT GUILD_ID, COMMAND_NAME FROM DISABLED_COMMANDS""") as cursor:
            data = await cursor.fetchall()
        for guild_id, command_name in data:
            l = self.disabled_commands.setdefault(guild_id, [])
            l.append(command_name)

    def has_channel(self, name: str):
        async def predicate(ctx: discord.ext.commands.Context):
            return bool(self.get_channel_data(ctx.guild.id, name))

        return discord.ext.commands.check(predicate)

    async def check_spoiler(self, msg: discord.Message):
        msg_hash = hash(msg.content)
        forbidden_to_delete = False
        if (self.INVALID_SPOILER.search(msg.content) or "/spoiler" in msg.content) and msg_hash not in self.spoiler_hashes:
            self.spoiler_hashes.append(msg_hash)
            try:
                await msg.delete()
            except discord.Forbidden:
                forbidden_to_delete = True
            author: Union[discord.User, discord.Member] = msg.author
            warning = self.WARNING if not forbidden_to_delete else self.WARNING_FAIL
            try:
                if len(msg.content) < 1012:
                    embed = Embed(msg, color=discord.Color.red(), title="Invalid Spoiler Sent", description=warning)
                    embed.add_field(name="Message", value=msg.content, inline=False)
                    await author.send(embed=embed)
                    await author.send("```markdown\n{}```".format(msg.content))
                else:
                    embed = Embed(msg, color=discord.Color.red(), title="Invalid Spoiler Sent", description=warning)
                    await author.send(embed=embed)
                    embed2 = Embed(msg, color=discord.Color.red(), title="Message Content", description=msg.content)
                    await author.send(embed=embed2)
                    # embed3 = Embed(msg, color=discord.Color.red(), title="Raw Markdown",description="```markdown\n{}```".format(msg.content))
                    # await author.send(embed=embed3)
                    await author.send("```markdown\n{}```".format(msg.content))
            except discord.Forbidden:
                chan: discord.TextChannel = self.get_channel_data(msg.guild.id, "bot-spam")
                if chan is None:
                    return
                if len(msg.content) < 1012:
                    embed = Embed(msg, color=discord.Color.red(), title="Invalid Spoiler Sent", description=warning)
                    embed.add_field(name="Unable to DM",
                                    value="The bot attempted to DM you this information, but was unable to do so due to a Forbidden error, "
                                          "which means that you have most likely disabled DMs from server members. If you want the bot to DM you "
                                          "next time instead of messaging you from the bot spam channel, enable DMs from server members.",
                                    inline=False)
                    embed.add_field(name="Message", value=msg.content, inline=False)
                    await author.send(embed=embed)
                    await author.send("```markdown\n{}```".format(msg.content))
                else:
                    embed = Embed(msg, color=discord.Color.red(), title="Invalid Spoiler Sent", description=warning)
                    embed.add_field(name="Unable to DM",
                                    value="The bot attempted to DM you this information, but was unable to do so due to a Forbidden error, "
                                          "which means that you have most likely disabled DMs from server members. If you want the bot to DM you "
                                          "next time instead of messaging you from the bot spam channel, enable DMs from server members.",
                                    inline=False)
                    await chan.send(embed=embed)
                    embed2 = Embed(msg, color=discord.Color.red(), title="Message Content", description=msg.content)
                    await chan.send(embed=embed2)
                    # embed3 = Embed(msg, color=discord.Color.red(), title="Raw Markdown", description="```markdown\n{}```".format(msg.content))
                    # embed3.set_author(name=str(msg.author), icon_url=msg.author.avatar_url_as(size=4096))
                    # await chan.send(embed=embed3)
                    await chan.send("```markdown\n{}```".format(msg.content))

    async def load_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def on_ready(self):
        async with self.stats_lock:
            self.stats.setdefault("messages", {})
        logger.info("Bot ready.")
        print("Bot ready. All future output is going to the log file.")
        await self.get_all_stats()

    @staticmethod
    async def loop_stats(ctx: discord.ext.commands.Context, loop: discord.ext.tasks.Loop, name: str):
        current_loop = loop.current_loop
        next_iteration = loop.next_iteration
        running = loop.is_running()
        canceling = loop.is_being_cancelled()
        failed = loop.failed()
        embed = Embed(ctx, title=f"{name} Loop", color=discord.Color.green() if running else discord.Color.red())
        fields = [("Current Loop", str(current_loop)),
                  ("Next Iteration", next_iteration.replace(tzinfo=pytz.UTC).astimezone(NY).strftime("%A, %B %d, %Y at %I:%M:%S %p")),
                  ("Running", str(running)), ("Cancelling", str(canceling)), ("Failed", str(failed))]
        await send_embeds_fields(ctx, embed, fields)

    async def can_run(self, ctx: discord.ext.commands.Context, *, call_once=False):
        message = ctx.message
        if hasattr(message.channel, "guild"):
            perms: discord.Permissions = message.channel.permissions_for(message.channel.guild.get_member(self.user.id))
        else:
            perms: discord.Permissions = discord.Permissions(send_messages=True)
        if self.command_disabled(ctx):
            raise discord.ext.commands.DisabledCommand(f"The `{ctx.command.qualified_name}` command is disabled on this Guild.")
        if perms.send_messages:
            return await super().can_run(ctx, call_once=call_once)
        else:
            raise discord.ext.commands.BotMissingPermissions(["send_messages"])

    async def ping_time(self, message: discord.Message):
        cur_time = datetime.datetime.utcnow()
        difference = cur_time - message.created_at
        self.pings.append(difference)
        if "{}ping".format(self.command_prefix) in message.content.lower():
            self.ping_timedelta = difference

    async def on_message(self, message: discord.Message, _replay=False):
        if _replay:
            return await super().on_message(message)
        coros = [self.ping_time(message)]
        if message.author.bot:
            if "remove this message with -goaway" in message.content.lower() or "undefinedgoaway" in message.content.lower():
                logger.debug("Removed Paisley Park ad message.")
                coros.append(message.delete())
            else:
                coros.extend([self.add_stat_on_message(message), self.check_channel(message)])
        else:
            coros.extend((self.add_stat_on_message(message), self.check_spoiler(message), self.check_channel(message), super().on_message(message)))
        return await asyncio.gather(*coros)

    async def add_stat_on_message(self, message: discord.Message):
        await self.stats_working_on.wait()
        await self.add_stat(message)

    @classmethod
    def get_message_content_formatted(cls, content: str):
        lines = []
        for line in content.splitlines(False):
            if match := cls.QUOTE_MARKER.match(line):
                find = match.group(0)
                line.replace(find, find.replace(">", "Quote:"))
            lines.append("> {}".format(line))
        return "\n".join(lines)

    @classmethod
    async def send_message(cls, location: discord.TextChannel, static_number: Union[StaticNumber, Sum], message: discord.Message,
                           channel: bool = False,
                           user: discord.Member = None):
        number = static_number.value
        if user:
            if channel:
                description = ":tada::partying_face: {} has sent {} messages in {}!".format(user.mention, number, message.channel.mention)
            else:
                description = ":tada::partying_face: {} has sent a total of {} messages to the entire server!".format(user.mention, number)
        else:
            if channel:
                description = ":tada::partying_face: There has been a total of {} messages sent to the {} channel!".format(number,
                                                                                                                           message.channel.mention)
            else:
                description = ":tada::partying_face: There has been a total of {} messages sent to the entire guild!".format(number)
        embed = discord.Embed(timestamp=datetime.datetime.utcnow(), title="Message Goal Reached", color=discord.Color.green(),
                              description=description)
        embed.set_thumbnail(url=message.author.avatar_url_as(size=4096))
        if user:
            if not channel:
                embed.add_field(name="Channel", value=message.channel.mention)
        else:
            if channel:
                embed.add_field(name="User", value=message.author.mention)
            else:
                embed.add_field(name="Channel", value=message.channel.mention)
                embed.add_field(name="User", value=message.author.mention)
        if len(message.content) < 1000:
            if len(message.content.strip('"').strip("'")):
                content = message.content
            else:
                content = "**No Content.**"
        else:
            content = "**Message too large.**"
        embed.add_field(name="Message", value=content)
        embed.add_field(name="Message URL", value=message.jump_url)
        msg = await location.send(embed=embed)
        return msg

    async def check_channel(self, message: discord.Message):
        if message.guild is None:
            return
        guild_id = message.guild.id
        channel_id = message.channel.id
        user_id = message.author.id
        chan = self.get_channel_data(message.guild.id, "message-goals")
        if chan is None:
            return
        await self.stats_working_on.wait()
        async with self.stats_lock:
            msg_sum = self.stats[guild_id][channel_id]["messages"]
            guild_sum = self.stats[guild_id]["messages"]
            user_num = self.stats[guild_id][channel_id][user_id]
            user_guild_sum = self.stats[guild_id][user_id]
        if msg_sum.value in [100, 250, 500, 750] or (msg_sum.value % 1000 == 0 and msg_sum.value > 0):
            if id(msg_sum) not in self.obj_ids or self.obj_ids.setdefault(id(msg_sum), msg_sum.value) < msg_sum.value:
                self.obj_ids[id(msg_sum)] = msg_sum.value
                await self.send_message(chan, msg_sum, message, channel=True)
        if guild_sum.value % 10000 == 0:
            if id(guild_sum) not in self.obj_ids or self.obj_ids.setdefault(id(guild_sum), guild_sum.value) < guild_sum.value:
                self.obj_ids[id(guild_sum)] = guild_sum.value
                message = await self.send_message(chan, guild_sum, message)
        if user_num.value in [100, 250, 500, 750] or (user_num.value % 1000 == 0 and user_num.value > 0):
            if id(user_num) not in self.obj_ids or self.obj_ids.setdefault(id(user_num), user_num.value) < user_num.value:
                self.obj_ids[id(user_num)] = user_num.value
                await self.send_message(chan, user_num, message, channel=True, user=message.author)
        if user_guild_sum.value in [100, 250, 500, 750] or (user_guild_sum.value % 1000 == 0 and user_guild_sum.value > 0):
            if id(user_guild_sum) not in self.obj_ids or self.obj_ids.setdefault(id(user_guild_sum), user_guild_sum.value) < user_guild_sum.value:
                self.obj_ids[id(user_guild_sum)] = user_guild_sum.value
                await self.send_message(chan, user_guild_sum, message, user=message.author)

    async def on_command_error(self, ctx: discord.ext.commands.Context, exception: Union[discord.ext.commands.MissingRequiredArgument,
                                                                                         discord.ext.commands.BotMissingPermissions,
                                                                                         discord.ext.commands.CommandNotFound,
                                                                                         discord.ext.commands.CommandInvokeError,
                                                                                         discord.ext.commands.CommandError,
                                                                                         discord.ext.commands.BadArgument,
                                                                                         discord.ext.commands.CheckFailure,
                                                                                         discord.ext.commands.DisabledCommand,
                                                                                         BaseException],
                               custom_message: Optional[str] = None):
        if isinstance(exception, discord.ext.commands.MissingRequiredArgument):
            embed = Embed(ctx, title="Missing Argument", color=discord.Colour.red(),
                          description="Missing a required parameter. Please view the help command (provided below) to find usage instructions.")
            embed.add_field(name="Parameter", value=exception.param.name)
            embed.add_field(name="Command", value=ctx.command)
            await ctx.send(embed=embed)
            return await ctx.send_help(ctx.command)
        if isinstance(exception, discord.ext.commands.CommandNotFound):
            embed = Embed(ctx, title="Invalid Command", color=discord.Colour.red(), description="An invalid command has been specified.")
            command = ctx.message.content.partition(" ")[0].lstrip(self.command_prefix)
            if ctx.command:
                command_obj: discord.ext.commands.Command = ctx.command
                command = command_obj.name
            embed.add_field(name="Command", value=command)
            if ctx.subcommand_passed:
                embed.add_field(name="Subcommand", value=ctx.subcommand_passed)
            await ctx.send(embed=embed)
            return await ctx.send_help()
        if isinstance(exception, discord.ext.commands.BotMissingPermissions):
            if "send_messages" in exception.missing_perms:
                logger.warning("Requested command on channel where bot cannot speak.")
                chan: discord.TextChannel = self.get_channel_data(ctx.guild.id, "bot-spam")
                if chan is None:
                    return
                embed = Embed(ctx, title="Could Not Speak", color=discord.Colour.red(),
                              description="The bot cannot speak in the channel where the command was requested.")
                embed.add_field(name="Channel", value=ctx.channel.mention)
                return await chan.send(ctx.author.mention, embed=embed)
        if isinstance(exception, discord.ext.commands.CheckFailure):
            msg = exception.args[0] if len(exception.args) > 0 else ""
            embed = Embed(ctx, title="Unable To Run Command", description=msg, color=discord.Color.red())
            embed.add_field(name="Command", value=f"{self.command_prefix}{ctx.command.qualified_name}")
            return await ctx.send(embed=embed)
        if isinstance(exception, discord.ext.commands.DisabledCommand):
            embed = Embed(ctx, title="Command is Disabled", description="The given command is disabled.", color=discord.Color.red())
            embed.add_field(name="Command", value=ctx.command.qualified_name)
            return await ctx.send(embed=embed)
        if isinstance(exception, discord.ext.commands.BadArgument):
            msg = exception.args[0] if len(exception.args) > 0 else ""
            embed = Embed(ctx, title="Invalid Argument Type", description="An invalid type was provided.")
            if match := self.BAD_ARGUMENT.match(msg):
                embed.add_field(name="Expected Type", value=match.group(1))
                embed.add_field(name="Parameter Name", value=match.group(2))
            else:
                embed.add_field(name="Message", value=msg or "None")
            await ctx.send(embed=embed)
            return await ctx.send_help(ctx.command)
        if not custom_message:
            meth = logger.exception
        else:
            meth = logger.warning
        if hasattr(exception, "original") and isinstance(exception.original, StopCommand):
            return
        meth("Exception in Bot Command:", exc_info=exception)
        embed = Embed(ctx, title="Exception During Bot Command", color=discord.Color.red(),
                      description=custom_message or "While processing a bot command, an exception occurred.")
        embed.add_field(name="Exception", value=type(exception).__name__)
        if isinstance(exception, discord.ext.commands.CommandInvokeError):
            embed.add_field(name="Original Exception", value=type(exception.original).__name__)
        embed.add_field(name="Exception Content", value=str(exception))
        groups = await break_into_groups("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
        await ctx.send(f"Pinging {ctx.guild.get_member(self.owner_id).mention}")
        await send_embeds(ctx, embed, groups, first_name="Exception Traceback", timestamp=ctx.message.created_at,
                          color=discord.Color.red())

    async def on_error(self, event_method, *_args, **_kwargs):
        logger.exception("Error occurred in event handler %s", event_method)

    async def close(self, self_initiated=False):
        logger.critical("Started bot shutdown.")
        if self.session is not None:
            await self.session.close()
        await self.conn.close()
        await super().close()
        if not self_initiated:
            subprocess.Popen(["/bin/sh", os.path.abspath(os.path.join(__file__, "..", "terminate-process.sh")), str(os.getpid())], close_fds=True)
        logger.info("Bot shutdown has finished, running final cleanup and exit.")

    async def on_connect(self):
        if self.conn is None or not self.conn.is_alive():
            self.conn = await aiosqlite.connect(os.path.abspath(os.path.join(__file__, "..", "database.db")), isolation_level=None)
        await self.pre_create()
        await self.get_channel_mappings()
        await self.get_disabled_commands()
        logger.info("Bot has connected to Discord.")

    async def on_disconnect(self):
        logger.critical("Bot has disconnected from Discord.")

    async def generic_help(self, ctx: discord.ext.commands.Context):
        embed = Embed(ctx, title="Subcommand Required", color=discord.Colour.red(), description="A valid subcommand is needed for the given command.")
        embed.add_field(name="Command", value=str(ctx.command))
        if ctx.subcommand_passed:
            raise discord.ext.commands.CommandNotFound()
        await ctx.send(embed=embed)
        return await ctx.send_help(ctx.command)

    async def add_stat(self, message: discord.Message):
        guild_messages_sum = Sum()
        guild_user_messages_sum = Sum()
        async with self.stats_lock:
            message_id = message.id
            author_id = user_id = message.author.id
            channel_id = message.channel.id
            guild_id = getattr(message.guild, "id", None) or 0
            if message.id in self.stats["messages"]:
                return
            else:
                self.stats["messages"].setdefault(message_id, author_id)
            guild_data: dict = self.stats.setdefault(guild_id, {"messages": guild_messages_sum})
            if guild_data["messages"] != guild_messages_sum:
                guild_messages_sum = guild_data["messages"]
            guild_user_data = guild_data.setdefault(author_id, guild_user_messages_sum)
            if guild_user_data != guild_user_messages_sum:
                guild_user_messages_sum = guild_user_data
            if channel_id not in guild_data:
                channel_messages_sum = guild_messages_sum.make_sub_sum()
                channel_data = guild_data.setdefault(channel_id, {"messages": channel_messages_sum})
            else:
                channel_data = guild_data[channel_id]
                channel_messages_sum = channel_data["messages"]
            if user_id not in channel_data:
                channel_user_messages = channel_messages_sum.make_static_number()
                channel_data.setdefault(user_id, channel_user_messages)
            else:
                user_data = channel_data[user_id]
                channel_user_messages = user_data
            if channel_user_messages not in guild_user_messages_sum:
                guild_user_messages_sum.append(channel_user_messages)
            channel_user_messages += 1

    async def remove_stat(self, guild_id: int, channel_id: int, *message_ids: int):
        if not self.get_channel_data(guild_id, "message-goals"):
            return
        async with self.stats_lock:
            for message_id in message_ids:
                if message_id not in self.stats["messages"]:
                    return
                user_data = self.stats[guild_id][channel_id][self.stats["messages"][message_id]]
                channel_user_messages = user_data
                channel_user_messages -= 1
                self.stats["messages"].pop(message_id)

    async def get_all_stats(self):
        logger.warning("Bot is updating message stat cache. Some bot features may be unavailable while this happens.")
        self.stats_working_on.clear()
        await asyncio.gather(*[self.get_guild_stats(guild) for guild in self.guilds])
        self.stats_working_on.set()
        logger.info("Update complete.")

    async def get_guild_stats(self, guild: discord.Guild):
        if not self.get_channel_data(guild.id, "message-goals"):
            return
        # channel: discord.TextChannel = self.bot.get_channel_data(ctx.guild.id, "bot-spam")
        # if channel is None:
        #     return
        # await chan.send("Bot is updating message stat cache. Some bot features may be unavailable while this happens.")
        # msg = await chan.send("[Will be updated] Showing current progress")
        channels = guild.text_channels
        # await msg.edit(
        #    content="(**{:.2f}**%) Gathering stats for channel: {}".format((num / len(channels)) * 100,
        #                                                                   channel.mention if hasattr(channel, "mention") else channel))
        await asyncio.gather(*[self.get_channel_stats(channel) for num, channel in enumerate(channels)])

    async def get_channel_stats(self, channel: discord.TextChannel):
        async for message in channel.history(limit=None):
            await self.add_stat(message)

    async def remove_channel(self, channel: Union[
        discord.TextChannel, discord.VoiceChannel, discord.DMChannel, discord.GroupChannel, discord.CategoryChannel]):
        if isinstance(channel, (discord.VoiceChannel, discord.CategoryChannel)) or not self.get_channel_data(channel.guild.id, "message-goals"):
            return
        if hasattr(channel, "guild") and getattr(channel.guild, "id", None):
            guild_id = channel.guild.id
        else:
            guild_id = 0
        self.stats[guild_id][channel.id]["messages"].delete()
        self.stats[guild_id].pop(channel.id)

    async def on_guild_channel_delete(self, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]):
        await self.remove_channel(channel)

    async def on_private_channel_delete(self, channel: Union[discord.DMChannel, discord.GroupChannel]):
        await self.remove_channel(channel)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        await self.remove_stat(payload.guild_id, payload.channel_id, payload.message_id)

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        await self.remove_stat(payload.guild_id, payload.channel_id, *payload.message_ids)

    @staticmethod
    def invalid_command_msg(command: Optional[str] = None):
        return ":x: The command provided{} does not exist.".format(" (**{}**)".format(command) if command else "")


def main():
    lock_path = os.path.abspath(os.path.join(__file__, "..", "bot.lock"))
    if os.path.exists(lock_path):
        logger.critical(
            "Bot already running. Please either shutdown the other bot (with the %kill command) or delete the bot.lock file if the program crashed.")
        print(
            "Bot already running. Please either shutdown the other bot (with the %kill command) or delete the bot.lock file if the program crashed.")
        sys.exit(1)
    else:
        open(lock_path, "w").close()

        @atexit.register
        def delete_lock_file():
            os.remove(lock_path)
    try:
        pokestarbot_instance = PokestarBot()
    except Exception:
        logger.critical("Critical error occured during bot initialization. Bot will be exiting.", exc_info=True)
        print("Critical error occured during bot initialization. Bot will be exiting. Check bot_error.log for details", file=sys.stderr)
        sys.exit(1)
    else:
        pokestarbot_instance.run(TOKEN)
