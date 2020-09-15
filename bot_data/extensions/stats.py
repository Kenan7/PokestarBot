import inspect
import logging
import sqlite3
from typing import List, Optional, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, send_embeds_fields
from ..const import stats_template
if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Stats(PokestarBotCog):
    STATS_TEMPLATE = STATS_CHANNEL_TEMPLATE = stats_template

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        check = self.bot.has_channel("message-goals")
        self.bot.add_check_recursive(self.command_stats, check)

    @discord.ext.commands.group(name="stats", invoke_without_command=True, brief="Get channel statistics",
                                usage="[channel] [...] [min_messages] [limit]")
    async def command_stats(self, ctx: discord.ext.commands.Context, channels: discord.ext.commands.Greedy[discord.TextChannel],
                            min_messages: int = 5, limit: Optional[int] = None):
        channels: List[discord.TextChannel] = list(channels)
        if len(channels) == 0:
            channels.append(ctx.channel)
        if len(channels) > 1:
            for channel in channels:
                await self.command_stats(ctx, channel, min_messages=min_messages)
        else:
            channel: discord.TextChannel = channels[0]
            guild_id = getattr(channel.guild, "id", 0)
            logger.info("Requested stats on channel %s", channel)
            waiting = False
            if not self.bot.stats_working_on.is_set():
                await ctx.send("Bot is updating message cache. Once it is finished, you will be pinged and the stats will be sent.")
                waiting = True
            await self.bot.stats_working_on.wait()
            async with self.bot.conn.execute("""SELECT COUNT(*) FROM STAT WHERE GUILD_ID==? AND CHANNEL_ID==?""", [guild_id, channel.id]) as cursor:
                messages, = await cursor.fetchone()
            if waiting:
                await ctx.send(ctx.author.mention + ", here are the stats you requested:")
            embed = Embed(ctx, title="Stats for Channel **{}**".format(str(channel)),
                          description="The channel contains **{}** messages. The fields below contain the messages sent by each user in the "
                                      "channel.".format(
                              messages))
            fields = []
            num = 0
            async with self.bot.conn.execute("""SELECT DISTINCT AUTHOR_ID FROM STAT WHERE GUILD_ID==? AND CHANNEL_ID==?""",
                                             [guild_id, channel.id]) as cursor:
                user_ids = {user_id async for user_id, in cursor}
            data = {}
            logger.debug("User IDs: %s", user_ids)
            for user_id in user_ids:
                async with self.bot.conn.execute("""SELECT COUNT(MESSAGE_ID) FROM STAT WHERE GUILD_ID==? AND CHANNEL_ID==? AND AUTHOR_ID==?""",
                                                 [guild_id, channel.id, user_id]) as cursor:
                    data[user_id] = (await cursor.fetchone())[0]
            for user_id, user_data in sorted(data.items(), key=lambda keyvaluepair: keyvaluepair[1], reverse=True):
                if user_data < min_messages:
                    continue
                user = non_member_user = ctx.guild.get_member(int(user_id))
                user: Optional[discord.Member]
                if not user:
                    try:
                        non_member_user: discord.User = await self.bot.fetch_user(int(user_id))
                    except discord.errors.NotFound:
                        user_name = "*[Deleted User]*"
                    else:
                        user_name = str(non_member_user) + " *[Not a guild member]*"
                else:
                    user_name = str(user)
                if getattr(user or non_member_user, "bot", None):
                    user_name += " *[BOT]*"
                fields.append((user_name, "**{}** messages".format(user_data)))
                num += 1
                if num == limit:
                    break
            await send_embeds_fields(ctx, embed, fields)

    @command_stats.command(name="global", brief="Gets stats on all channels in the guild", usage="[min_messages] [limit]")
    async def stats_global(self, ctx: discord.ext.commands.Context, min_messages: int = 5, limit: Optional[int] = 25):
        guild: discord.Guild = ctx.guild
        logger.info("Getting global statistics.")
        waiting = False
        if not self.bot.stats_working_on.is_set():
            await ctx.send("Bot is updating message cache. Once it is finished, you will be pinged and the stats will be sent.")
            waiting = True
        await self.bot.stats_working_on.wait()
        channels = guild.text_channels
        async with self.bot.conn.execute("""SELECT COUNT(*) FROM STAT WHERE GUILD_ID==?""", [guild.id]) as cursor:
            messages, = await cursor.fetchone()
        if waiting:
            await ctx.send(ctx.author.mention + ", here are the stats you requested:")
        embed1 = Embed(ctx, title="Guild Statistics")
        embed1.add_field(name="Messages", value=messages)
        await ctx.send(embed=embed1)
        channel_fields = []
        channel_embed = Embed(ctx, title="Guild Stats (Channels)",
                              description="This Embed contains the statistics for the text channels in the Guild.")
        async with self.bot.conn.execute("""SELECT DISTINCT CHANNEL_ID FROM STAT WHERE GUILD_ID==?""", [guild.id]) as cursor:
            channel_ids = {channel_id async for channel_id, in cursor}
        data = {}
        logger.debug("Channel IDs: %s", channel_ids)
        for channel_id in channel_ids:
            async with self.bot.conn.execute("""SELECT COUNT(MESSAGE_ID) FROM STAT WHERE GUILD_ID==? AND CHANNEL_ID==?""",
                                             [guild.id, channel_id]) as cursor:
                data[channel_id] = (await cursor.fetchone())[0]
        for channel in sorted(channels, key=lambda channel: data.get(channel.id, 0), reverse=True):
            msg_sum = data.get(channel.id, 0)
            if msg_sum < min_messages:
                continue
            channel_fields.append((str(channel), "**{}** messages".format(msg_sum)))
            data.pop(channel.id, None)
        await send_embeds_fields(ctx, channel_embed, channel_fields)
        user_fields = []
        user_embed = Embed(ctx, title="Guild Stats (Users)", description="This Embed contains the statistics for the users in the Guild.")
        num = 0
        async with self.bot.conn.execute("""SELECT DISTINCT AUTHOR_ID FROM STAT WHERE GUILD_ID==?""", [guild.id]) as cursor:
            user_ids = {user_id async for user_id, in cursor}
        data = {}
        logger.debug("User IDs: %s", user_ids)
        for user_id in user_ids:
            async with self.bot.conn.execute("""SELECT COUNT(MESSAGE_ID) FROM STAT WHERE GUILD_ID==? AND AUTHOR_ID==?""",
                                             [guild.id, user_id]) as cursor:
                data[user_id] = (await cursor.fetchone())[0]
        for user_id, user_data in sorted(data.items(), key=lambda keyvaluepair: keyvaluepair[1], reverse=True):
            if user_data < min_messages:
                continue
            user = non_member_user = ctx.guild.get_member(int(user_id))
            user: Optional[discord.Member]
            if not user:
                try:
                    non_member_user: discord.User = await self.bot.fetch_user(int(user_id))
                except discord.errors.NotFound:
                    user_name = "*[Deleted User]*"
                else:
                    user_name = str(non_member_user) + " *[Not a guild member]*"
            else:
                user_name = str(user)
            if getattr(user or non_member_user, "bot", None):
                user_name += " *[BOT]*"
            # logger.debug("%s (%s / %s)", user, user.id if hasattr(user, "id") else "", user_id)
            user_fields.append((user_name, "**{}** messages".format(user_data)))
            num += 1
            if num == limit:
                break
        await send_embeds_fields(ctx, user_embed, user_fields)

    @command_stats.command(brief="Reset the messages collected for a channel.", usage="channel [channel] [...]")
    @discord.ext.commands.is_owner()
    async def reset(self, ctx: discord.ext.commands.Context, *channels: discord.TextChannel):
        if len(channels) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("channel", inspect.Parameter.POSITIONAL_ONLY))
        embed = Embed(ctx, title="Reset Statistics", description="Statistics for the following channels have been reset", color=discord.Color.green())
        for channel in channels:
            await self.bot.remove_channel(channel)
        await send_embeds_fields(ctx, embed, ["\n".join(channel.mention for channel in channels)])

    @discord.ext.commands.group(invoke_without_command=True,
                                brief="Manage the printing of message contents in channels that trigger message stats (such as admin channels).",
                                aliases=["stat_channel", "stats_channels", "stat_channels", "statschannel", "statchannel", "statschannels",
                                         "statchannels"], significant=True)
    async def stats_channel(self, ctx: discord.ext.commands.Context):
        await self.bot.generic_help(ctx)

    @stats_channel.command(brief="Disable the printing of message contents for statistics in these channels", usage="channel [channel] [...]")
    @discord.ext.commands.has_guild_permissions(manage_messages=True)
    async def disable(self, ctx: discord.ext.commands.Context, *channels: discord.TextChannel):
        if len(channels) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("channel", inspect.Parameter.POSITIONAL_ONLY))
        embed = Embed(ctx, title="Disabled Printing Of Messages",
                      description="These channels will no longer show the contents of messages of any statistics that get triggered in them.")
        success = []
        failed = []
        for channel in channels:
            try:
                async with self.bot.conn.execute("""INSERT INTO DISABLED_STATS(GUILD_ID, CHANNEL_ID) VALUES (?, ?)""", [ctx.guild.id, channel.id]):
                    pass
            except sqlite3.IntegrityError:
                failed.append(channel)
            else:
                success.append(channel)
        if failed:
            embed.color = discord.Color.red()
        else:
            embed.color = discord.Color.green()
        await send_embeds_fields(ctx, embed, [("Success", "\n".join(chan.mention for chan in success) or "None"),
                                              ("Failed", "\n".join(chan.mention for chan in failed) or "None")])
        await self.bot.get_disabled_channels()

    @stats_channel.command(brief="Enable the printing of message contents for statistics in these channels", usage="channel [channel] [...]")
    @discord.ext.commands.has_guild_permissions(manage_messages=True)
    async def enable(self, ctx: discord.ext.commands.Context, *channels: discord.TextChannel):
        if len(channels) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("channel", inspect.Parameter.POSITIONAL_ONLY))
        embed = Embed(ctx, title="Enabled Printing Of Messages",
                      description="These channels will start showing the contents of messages of any statistics that get triggered in them.", color=discord.Color.green())
        data = [(channel.id, ctx.guild.id) for channel in channels]
        async with self.bot.conn.executemany("""DELETE FROM DISABLED_STATS WHERE CHANNEL_ID==? AND GUILD_ID==?""", data):
            pass
        await send_embeds_fields(ctx, embed, ["\n".join(chan.mention for chan in channels)])
        await self.bot.get_disabled_channels()

    @stats_channel.command(brief="List the disabled channels")
    @discord.ext.commands.guild_only()
    async def list(self, ctx: discord.ext.commands.Context):
        embed = Embed(ctx, title="Disabled Channels", description="These channels are disabled from printing message contents in message goals.")
        async with self.bot.conn.execute("""SELECT CHANNEL_ID FROM DISABLED_STATS WHERE GUILD_ID==?""", [ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        channels = [ctx.guild.get_channel(channel_id) for channel_id, in data]
        await send_embeds_fields(ctx, embed, ["\n".join(channel.mention for channel in channels) or "None"])


def setup(bot: "PokestarBot"):
    bot.add_cog(Stats(bot))
    logger.info("Loaded the Stats extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Stats extension.")
