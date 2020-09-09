import logging
from typing import List, Optional, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, StaticNumber, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Stats(PokestarBotCog):
    STATS_TEMPLATE = STATS_CHANNEL_TEMPLATE = "* **{}**{}: **{}** messages (max **{}** messages)"

    @property
    def stats(self):
        return self.bot.stats

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
            logger.info("Requested stats on channel %s", channel)
            waiting = False
            if not self.bot.stats_working_on.is_set():
                await ctx.send("Bot is updating message cache. Once it is finished, you will be pinged and the stats will be sent.")
                waiting = True
            await self.bot.stats_working_on.wait()
            async with self.bot.stats_lock:
                data = self.stats[ctx.guild.id][channel.id].copy()
            messages = data.pop("messages")
            if waiting:
                await ctx.send(ctx.author.mention + ", here are the stats you requested:")
            embed = Embed(ctx, title="Stats for Channel **{}**".format(str(channel)),
                          description="The channel contains **{}** messages. The fields below contain the messages sent by each user in the "
                                      "channel.".format(
                              messages.value))
            fields = []
            num = 0
            for user_id, user_data in sorted(data.items(), key=lambda keyvaluepair: keyvaluepair[1].value, reverse=True):
                if user_data.value < min_messages:
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
                fields.append((user_name, "**{}** messages".format(user_data.value)))
                num += 1
                if num == limit:
                    break
            await send_embeds_fields(ctx, embed, fields)

    @command_stats.command(name="global", brief="Gets stats on all channels in the guild", usage="[min_messages] [limit]")
    async def stats_global(self, ctx: discord.ext.commands.Context, min_messages: int = 5, limit: Optional[int] = None):
        guild: discord.Guild = ctx.guild
        logger.info("Getting global statistics.")
        waiting = False
        if not self.bot.stats_working_on.is_set():
            await ctx.send("Bot is updating message cache. Once it is finished, you will be pinged and the stats will be sent.")
            waiting = True
        await self.bot.stats_working_on.wait()
        async with self.bot.stats_lock:
            data = self.bot.stats[guild.id].copy()
        channels = guild.text_channels
        messages = data.pop("messages")
        if waiting:
            await ctx.send(ctx.author.mention + ", here are the stats you requested:")
        embed1 = Embed(ctx, title="Server Statistics")
        embed1.add_field(name="Messages", value=messages.value)
        await ctx.send(embed=embed1)
        channel_fields = []
        channel_embed = Embed(ctx, title="Server Stats (Channels)",
                              description="This Embed contains the statistics for the text channels in the server.")
        for channel in sorted(channels, key=lambda channel: data.get(channel.id, {}).get("messages", StaticNumber(0)).value, reverse=True):
            msg_sum = data.get(channel.id, {}).get("messages", StaticNumber(0))
            if msg_sum.value < min_messages:
                continue
            channel_fields.append((str(channel), "**{}** messages".format(msg_sum.value)))
            data.pop(channel.id, None)
        await send_embeds_fields(ctx, channel_embed, channel_fields)
        user_fields = []
        user_embed = Embed(ctx, title="Server Stats (Users)", description="This Embed contains the statistics for the users in the server.")
        num = 0
        for user_id, user_data in sorted(data.items(), key=lambda keyvaluepair: getattr(keyvaluepair[1], "value", 0), reverse=True):
            if getattr(user_data, "value", 0) < min_messages:
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
            user_fields.append((user_name, "**{}** messages".format(getattr(user_data, "value", 0))))
            num += 1
            if num == limit:
                break
        await send_embeds_fields(ctx, user_embed, user_fields)


def setup(bot: "PokestarBot"):
    bot.add_cog(Stats(bot))
    logger.info("Loaded the Stats extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Stats extension.")
