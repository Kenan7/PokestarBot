import datetime
import io
import logging
from typing import List, Optional, TYPE_CHECKING, Union

import discord.ext.commands

from . import PokestarBotCog
from ..converters import TimeConverter
from ..utils import Embed

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class History(PokestarBotCog):

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        check = self.bot.has_channel("message-goals")
        self.bot.add_check_recursive(self.clean_message_goals, check)

    @staticmethod
    async def batch_delete(channel: Union[discord.TextChannel, discord.DMChannel, discord.GroupChannel], messages: List[discord.Message]):
        count = len(messages)
        logger.info("Deleting %s messages from channel %s", count, channel)
        while messages:
            batch = messages[:100]
            messages = messages[100:]
            await channel.delete_messages(batch)
        return count

    @discord.ext.commands.command(brief="Remove `-ad` messages by Paisley Park.")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def prune_ad(self, ctx: discord.ext.commands.Context):
        """Prune all of Paisley Park's `Get double rewards with -ad` messages."""
        channel: discord.TextChannel = self.bot.get_channel_data(ctx.guild.id, "bot-spam")
        if channel is None:
            channel = ctx.channel
        messages = await channel.history(limit=None).filter(lambda message: "remove this message with -goaway" in message.content.lower()).flatten()
        count = await self.batch_delete(channel, messages)
        embed = Embed(ctx, color=discord.Color.green(), title="Prune Successful", description="The pruning was successful.")
        embed.add_field(name="Messages Deleted", value=str(count))
        await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Remove all Embeds post in the channel by the bot.")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def clean_embeds(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel] = None):
        if channel is None:
            channel = ctx.channel
        messages = await ctx.history(limit=None).filter(lambda message: message.author == ctx.me).filter(
            lambda message: bool(message.embeds)).filter(
            lambda message: (datetime.datetime.utcnow() - message.created_at).total_seconds() < (3600 * 24 * 14)).flatten()
        count = await self.batch_delete(ctx.channel, messages)
        embed = Embed(ctx, color=discord.Color.green(), title="Batch Delete Successful", description="The batch delete was successful.")
        embed.add_field(name="Channel", value=ctx.channel.mention)
        embed.add_field(name="Messages Deleted", value=str(count))
        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            embed.add_field(name="Note",
                            value="The bot attempted to DM you this info, but was unable to. Check that you have allowed DMs from other people in "
                                  "this Guild.")
            channel: discord.TextChannel = self.bot.get_channel_data(ctx.guild.id, "bot-spam")
            if channel is None:
                return
            await channel.send(ctx.author.mention, embed=embed)

    @discord.ext.commands.command(brief="Remove all messages in the #message-goals channel that are not from the bot.")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def clean_message_goals(self, ctx: discord.ext.commands.Context):
        channel: discord.TextChannel = self.bot.get_channel_data(ctx.guild.id, "message-goals")
        if channel is None:
            return
        messages = await channel.history(limit=None).filter(lambda msg: msg.author != ctx.me).flatten()
        count = await self.batch_delete(channel, messages)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="Messages Deleted", value=str(count))
        await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Replay all messages in a channel starting with a certain prefix or from a certain user.",
                                  usage="[channel] [user] [user] [...] [prefix]", aliases=["replaymode", "replay"])
    @discord.ext.commands.is_owner()
    async def replay_mode(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                          users: discord.ext.commands.Greedy[discord.Member], *, prefix: Optional[str] = "%"):
        if channel is None:
            channel = ctx.channel
        embed = Embed(ctx, title="Started Replay Mode", description="Messages are in this channel are going to get replayed.",
                      color=discord.Color.green())
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Selected Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Prefix", value=prefix)
        await ctx.send(embed=embed)
        base = channel.history(limit=None).filter(lambda message: not (
                message.content.startswith(f"{self.bot.command_prefix}replay_mode") or message.content.startswith(
            f"{self.bot.command_prefix}replaymode") or message.content.startswith(f"{self.bot.command_prefix}replay")))
        if users:
            base = base.filter(lambda message: message.author in users)
        if prefix:
            base = base.filter(lambda message: message.content.startswith(prefix))
        count = 1
        async for message in base:
            logger.info("Replaying message# %s: %s", count, message.id)
            count += 1
            await self.bot.on_message(message, _replay=True)
        embed = Embed(ctx, title="Replay Mode Finished", description="All eligible messages have been replayed.", color=discord.Color.green())
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Selected Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Prefix", value=prefix)
        embed.add_field(name="Replayed Message Count", value=str(count))
        await ctx.send(embed=embed)

    @discord.ext.commands.group(brief="Delete x amount of messages (from all users or certain users).", usage="[channel] [user] [user] [...] amount",
                                invoke_without_command=True)
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def mass_delete(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                          users: discord.ext.commands.Greedy[discord.Member], amount: int):
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None)
        logger.debug("Users: %s", users)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        count = 0
        msgs = []
        async for item in base:
            item: discord.Message
            count += 1
            if count > amount:
                break
            msgs.append(item)
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages before a message (from all users or certain users).",
                         usage="[channel] [user] [user] [...] message")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def before(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                     users: discord.ext.commands.Greedy[discord.Member], message: discord.Message):
        base = ctx.history(limit=None, before=message)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="Before Message", value=message.jump_url)
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages before a certain time (from all users or certain users).",
                         usage="[channel] [user] [user] [...] time")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def before_time(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                          users: discord.ext.commands.Greedy[discord.Member], *, time: TimeConverter):
        if time.dst():
            zone = "EDT"
        else:
            zone = "EST"
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None, before=time)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="Before Time", value=time.strftime("%A, %B %d, %Y at %I:%M:%S %p {}".format(zone)))
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages after a message (from all users or certain users).",
                         usage="[channel] [user] [user] [...] message")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def after(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                    users: discord.ext.commands.Greedy[discord.Member], message: discord.Message):
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None, after=message)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="After Message", value=message.jump_url)
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages after a certain time (from all users or certain users).",
                         usage="[channel] [user] [user] [...] time")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def after_time(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                         users: discord.ext.commands.Greedy[discord.Member], *, time: TimeConverter):
        time: datetime.datetime
        if time.dst():
            zone = "EDT"
        else:
            zone = "EST"
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None, after=time)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="After Time", value=time.strftime("%A, %B %d, %Y at %I:%M:%S %p {}".format(zone)))
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages between two messages (from all users or certain users).",
                         usage="[channel] [user] [user] [...] after_message before_message")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def between(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                      users: discord.ext.commands.Greedy[discord.Member], after_message: discord.Message, before_message: discord.Message):
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None, after=after_message, before=before_message)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="After Message", value=after_message.jump_url)
        embed.add_field(name="Before Message", value=before_message.jump_url)
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @mass_delete.command(brief="Delete all messages between two times (from all users or certain users).",
                         usage="[channel] [user] [user] [...] after_time before_time")
    @discord.ext.commands.has_permissions(manage_messages=True)
    async def between_time(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel],
                           users: discord.ext.commands.Greedy[discord.Member], after_time: TimeConverter, before_time: TimeConverter):
        after_time: datetime.datetime
        before_time: datetime.datetime
        if after_time.dst():
            after_zone = "EDT"
        else:
            after_zone = "EST"
        if before_time.dst():
            before_zone = "EDT"
        else:
            before_zone = "EST"
        if channel is None:
            channel = ctx.channel
        base = channel.history(limit=None, after=after_time, before=before_time)
        if users:
            base = base.filter(lambda msg: msg.author in users)
        msgs = await base.flatten()
        num = await self.batch_delete(channel, msgs)
        embed = Embed(ctx, color=discord.Color.green(), title="Deletion Successful", description="The deletion was successful.")
        embed.add_field(name="After Time", value=after_time.strftime("%A, %B %d, %Y at %I:%M:%S %p {}".format(after_zone)))
        embed.add_field(name="Before Time", value=before_time.strftime("%A, %B %d, %Y at %I:%M:%S %p {}".format(before_zone)))
        embed.add_field(name="Users", value="\n".join(user.mention for user in users) or "None")
        embed.add_field(name="Messages Deleted", value=str(num))
        await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Get a copy of a chat log", usage="[channel] [number]")
    async def chat_log(self, ctx: discord.ext.commands.Context, channel: Optional[discord.TextChannel] = None, number: Optional[int] = None):
        if channel is None:
            channel = ctx.channel
        sio = io.StringIO()
        messages = await channel.history(limit=number, oldest_first=False).flatten()
        for message in reversed(messages):
            sio.write(f"{message.author}: {message.content or ''}\n")
        sio.seek(0)
        await ctx.send(file=discord.File(sio, filename="chat_log.txt"))


def setup(bot: "PokestarBot"):
    bot.add_cog(History(bot))
    logger.info("Loaded the History extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the History extension.")
