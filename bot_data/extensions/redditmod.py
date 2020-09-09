import asyncio
import datetime
import logging
import sqlite3
from typing import List, TYPE_CHECKING, Union

import asyncpraw.exceptions
import asyncpraw.models
import asyncprawcore.exceptions
import discord.ext.commands
import discord.ext.tasks

from . import PokestarBotCog
from ..creds import client_id, client_secret, refresh_token, user_agent
from ..utils import BoundedDict, CustomAuthorContext, Embed, RedditItemStash, aenumerate, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)

reddit = asyncpraw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent, refresh_token=refresh_token)


class RedditMod(PokestarBotCog):
    @property
    def conn(self):
        return self.bot.conn

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        self.modqueue = RedditItemStash("modqueue", itemtype=BoundedDict)
        self.modlog = RedditItemStash("modlog")
        self.unmoderated = RedditItemStash("unmoderated")
        self.bot.add_check_recursive(self.modqueue_command, self.bot.has_channel("modqueue"))
        # self.bot.add_check_recursive(self.modlog_command, self.bot.has_channel("modlog"))
        # self.bot.add_check_recursive(self.unmoderated_command, self.bot.has_channel("unmoderated"))
        self.modqueue_task.start()
        self.modlog_task.start()
        self.unmoderated_task.start()

    def cog_unload(self):
        self.modqueue_task.stop()
        self.modlog_task.stop()
        self.unmoderated_task.stop()

    async def pre_create(self):
        await self.bot.wait_until_ready()
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS MODQUEUE(ID INTEGER PRIMARY KEY AUTOINCREMENT, SUBREDDIT_NAME TEXT NOT NULL, GUILD_ID BIGINT NOT 
                NULL, UNIQUE(SUBREDDIT_NAME, GUILD_ID))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS MODLOG(ID INTEGER PRIMARY KEY AUTOINCREMENT, SUBREDDIT_NAME TEXT NOT NULL, GUILD_ID BIGINT NOT NULL, 
                UNIQUE(SUBREDDIT_NAME, GUILD_ID))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS UNMODERATED(ID INTEGER PRIMARY KEY AUTOINCREMENT, SUBREDDIT_NAME TEXT NOT NULL, GUILD_ID BIGINT NOT 
                NULL, UNIQUE(SUBREDDIT_NAME, GUILD_ID))"""):
            pass

    @discord.ext.tasks.loop(seconds=20)
    async def modqueue_task(self):
        await self.pre_create()
        async with self.conn.execute("""SELECT DISTINCT SUBREDDIT_NAME FROM MODQUEUE""") as cursor:
            data = await cursor.fetchall()
        for subreddit_name, in data:
            async with self.conn.execute("""SELECT GUILD_ID FROM MODQUEUE WHERE SUBREDDIT_NAME==?""", [subreddit_name]) as cursor:
                data2 = await cursor.fetchall()
            guilds = [guild for guild, in data2]
            try:
                async for item in (await reddit.subreddit(subreddit_name)).mod.modqueue(limit=10):
                    await self.modqueue_item(item, guilds)
            except Exception as e:
                logger.warning("Unable to get items for subreddit r/%s", subreddit_name, exc_info=e)

    async def modqueue_item(self, item: Union[asyncpraw.models.Submission, asyncpraw.models.Comment], guilds: List[int]):
        if not self.modqueue.check(item, getattr(item, "num_reports", 0)):
            self.modqueue.add(item, getattr(item, "num_reports", 0))
        else:
            return
        for guild in guilds:
            if channel := self.bot.get_channel_data(guild, "modqueue"):
                embed = discord.Embed(title="New Modqueue Item", timestamp=datetime.datetime.utcfromtimestamp(item.created_utc),
                                      url="https://www.reddit.com" + item.permalink)
                embed.add_field(name="Subreddit",
                                value=f"[{item.subreddit.display_name}](https://www.reddit.com/r/{item.subreddit.display_name})")
                embed.add_field(name="Item Type", value=item.__class__.__name__)
                embed.add_field(name="Fullname", value=item.fullname)
                embed.add_field(name="# Of Reports", value=str(item.num_reports))
                fields = [("Mod Reports", "\n".join(
                    [f"u/{user}: {reason}" for reason, user in item.mod_reports + (getattr(item, "mod_reports_dismissed", []) or [])]) or "None"),
                          ("User Reports", "\n".join([f"{num} Users: {reason}" for reason, num in item.user_reports]) or "None"), ("Author",
                                                                                                                                   f"[{getattr(item.author, 'name', '[deleted]') or '[deleted]'}](https://www.reddit.com/user/{getattr(item.author, 'name', '[deleted]') or '[deleted]'})")]
                if isinstance(item, asyncpraw.models.Comment):
                    description = item.body
                    if len(description) > 1024:
                        description = description[:1021] + "..."
                    fields.extend([("Description", description)])
                else:
                    description = item.selftext or item.url
                    if len(description) > 1024:
                        description = description[:1021] + "..."
                    fields.extend([("Title", item.title), ("Description", description)])
                    image_url = item.url
                    if not (not image_url.endswith(".jpg") and not image_url.endswith(".png") and not image_url.endswith(".jpeg")):
                        embed.set_image(url=image_url)
                    if hasattr(item, "gallery_data"):  # Gallery
                        fields.append(("Is Gallery", "True"))
                msg = (await send_embeds_fields(channel, embed, fields))[0]
                await msg.add_reaction("✅")
                await msg.add_reaction("🚫")
                await msg.add_reaction("📛")
                if isinstance(item, asyncpraw.models.Submission):
                    await msg.add_reaction("🔞")
            else:
                continue

    @discord.ext.commands.group(name="modqueue", invoke_without_command=True, brief="Manage the modqueue")
    async def modqueue_command(self, ctx: discord.ext.commands.Context):
        await self.bot.generic_help(ctx)

    @modqueue_command.command(name="add", brief="Add a subreddit to the Guild's modqueue channel.", usage="subreddit [subreddit]")
    async def modqueue_add(self, ctx: discord.ext.commands.Context, *subreddits: str):
        for subreddit in subreddits:
            try:
                subreddit_obj = await reddit.subreddit(subreddit, fetch=True)
            except asyncprawcore.exceptions.Redirect:
                embed = Embed(ctx, title="Subreddit Does Not Exist", description="The specified subreddit does not exist.", color=discord.Color.red())
                embed.add_field(name="Subreddit", value=f"r/{subreddit}")
                await ctx.send(embed=embed)
            else:
                try:
                    async for _ in subreddit_obj.mod.removal_reasons:
                        break
                except (asyncpraw.exceptions.PRAWException, asyncprawcore.exceptions.AsyncPrawcoreException):
                    embed = Embed(ctx, title="No Mod Permissions",
                                  description="The Reddit account used by the bot does not have the appropriate permissions.",
                                  color=discord.Color.red())
                    embed.add_field(name="Subreddit", value=f"r/{subreddit}")
                    await ctx.send(embed=embed)
                else:
                    try:
                        async with self.bot.conn.execute("""INSERT INTO MODQUEUE(SUBREDDIT_NAME, GUILD_ID) VALUES (?, ?)""",
                                                         [subreddit, ctx.guild.id]):
                            pass
                    except sqlite3.IntegrityError:
                        embed = Embed(ctx, title="Subreddit Exists", description="The subreddit is already part of the Guild's modqueue.",
                                      color=discord.Color.red())
                    else:
                        embed = Embed(ctx, title="Subreddit Added to Modqueue",
                                      description="The subreddit has been added to the Guild's modqueue database.", color=discord.Color.green())
                    embed.add_field(name="Subreddit", value=f"r/{subreddit}")
                    await ctx.send(embed=embed)

    @modqueue_command.command(name="remove", brief="Remove a subreddit from the Guild's modqueue channel.", usage="subreddit [subreddit]",
                              aliases=["delete"])
    async def modqueue_remove(self, ctx: discord.ext.commands.Context, *subreddits: str):
        for subreddit in subreddits:
            async with self.bot.conn.execute("""DELETE FROM MODQUEUE WHERE SUBREDDIT_NAME==? AND GUILD_ID==?""", [subreddit, ctx.guild.id]):
                pass
            embed = Embed(ctx, title="Subreddit Removed From Modqueue",
                          description="The subreddit has been removed from the Guild's modqueue database.",
                          color=discord.Color.green())
            embed.add_field(name="Subreddit", value=f"r/{subreddit}")
            await ctx.send(embed=embed)

    @modqueue_command.group(name="loop", brief="Get the status of the modqueue loop.", aliases=["modqueue_loop", "modqueueloop"],
                            invoke_without_command=True)
    async def modqueue_loop(self, ctx: discord.ext.commands.Context):
        await self.bot.loop_stats(ctx, self.modqueue_task, "Modqueue")

    @discord.ext.tasks.loop(seconds=20)
    async def unmoderated_task(self):
        await self.pre_create()
        async with self.conn.execute("""SELECT DISTINCT SUBREDDIT_NAME FROM UNMODERATED""") as cursor:
            data = await cursor.fetchall()
        for subreddit_name, in data:
            async with self.conn.execute("""SELECT GUILD_ID FROM UNMODERATED WHERE SUBREDDIT_NAME==?""", [subreddit_name]) as cursor:
                data2 = await cursor.fetchall()
            guilds = [guild for guild, in data2]
            try:
                async for item in (await reddit.subreddit(subreddit_name)).mod.unmoderated(limit=10):
                    await self.unmoderated_item(item, guilds)
            except Exception as e:
                logger.warning("Unable to get items for subreddit r/%s", subreddit_name, exc_info=e)

    @discord.ext.tasks.loop(seconds=20)
    async def modlog_task(self):
        await self.pre_create()
        async with self.conn.execute("""SELECT SUBREDDIT_NAME, GUILD_ID FROM MODLOG""") as cursor:
            data = await cursor.fetchall()
        for subreddit_name, guild_id in data:
            guild = self.bot.get_guild(guild_id)
            try:
                async for item in (await reddit.subreddit(subreddit_name)).mod.modlog(limit=10):
                    await self.modlog_item(item, guild)
            except Exception as e:
                logger.warning("Unable to get items for subreddit r/%s", subreddit_name, exc_info=e)

    @modqueue_task.error
    async def on_modqueue_error(self, exception: Exception):
        logger.exception("Exception in the modqueue task, aborting task:", exc_info=exception)

    @modlog_task.error
    async def on_modlog_error(self, exception: Exception):
        logger.exception("Exception in the modlog task, aborting task:", exc_info=exception)

    @unmoderated_task.error
    async def on_unmoderated_error(self, exception: Exception):
        logger.exception("Exception in the unmoderated task, aborting task:", exc_info=exception)

    async def on_reaction(self, msg: discord.Message, emoji: Union[discord.PartialEmoji, discord.Emoji, str], user: discord.Member):
        if user.id == self.bot.user.id or user.bot or msg.author.id != self.bot.user.id:
            return
        embed: discord.Embed = msg.embeds[0]
        ctx: CustomAuthorContext = await self.bot.get_context(msg, cls=CustomAuthorContext)
        ctx.author = user
        #
        if embed.title == "New Modqueue Item":
            if "✅" in str(emoji):
                async for item in reddit.info([embed.fields[2].value]):
                    await item.mod.approve()
                    embed = Embed(ctx, title="Approved Item", color=discord.Color.green())
                    embed.add_field(name="Fullname", value=item.fullname)
                    return await ctx.send(embed=embed)
            elif "🚫" in str(emoji):
                async for item in reddit.info([embed.fields[2].value]):
                    await self.remove_item(ctx, item, spam=False)
            elif "📛" in str(emoji):
                async for item in reddit.info([embed.fields[2].value]):
                    await self.remove_item(ctx, item, spam=True)
            elif "🔞" in str(emoji):
                async for item in reddit.info([embed.fields[2].value]):
                    await item.mod.nsfw()
                    embed = Embed(ctx, title="Marked Item as NSFW", color=discord.Color.green())
                    embed.add_field(name="Fullname", value=item.fullname)
                    return await ctx.send(embed=embed)

    async def remove_item(self, ctx: discord.ext.commands.Context, item: Union[asyncpraw.models.Comment, asyncpraw.models.Submission], spam: bool):
        subreddit: asyncpraw.models.Subreddit = item.subreddit
        embed = Embed(ctx, title="Removal Reasons for " + subreddit.display_name_prefixed, description="Type the number of the removal reason.")
        reasons = [None]
        num = 0
        async for num, reason in aenumerate(subreddit.mod.removal_reasons, start=1):
            reason: asyncpraw.models.RemovalReason
            embed.add_field(name=str(num) + ": " + reason.title, value=reason.message)
            reasons.append(reason)
        embed.add_field(name=str(num + 1) + ": " + "No Reason", value="\u200b")
        reasons.append(None)
        await ctx.send(embed=embed)
        try:
            msg = await self.bot.wait_for("message", check=lambda message: message.content.isnumeric(), timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(embed=Embed(ctx, title="Cancelled", color=discord.Color.red()))
        else:
            rsn = reasons[int(msg.content)]
            await item.mod.remove(spam=spam)
            embed = Embed(ctx, title="Spammed" if spam else "Removed", color=discord.Color.green())
            if rsn is not None:
                await item.mod.send_removal_message(message=rsn.message, title="Removed Item", type="private")
                embed.add_field(name="Removal Reason", value=f"{rsn.title}: {rsn.message}")
            else:
                embed.add_field(name="Removal Reason", value="No Reason")
            await ctx.send(embed=embed)

    @discord.ext.commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        user: discord.Member = guild.get_member(payload.user_id)
        emoji = payload.emoji
        logger.debug(message)
        logger.debug(user)
        logger.debug(emoji)
        await self.on_reaction(message, emoji, user)


def setup(bot: "PokestarBot"):
    bot.add_cog(RedditMod(bot))
    logger.info("Loaded the RedditMod extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the RedditMod extension.")
