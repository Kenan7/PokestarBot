import datetime
import inspect
import logging
import re
from typing import Optional, TYPE_CHECKING

import anytree
import asyncpraw.exceptions
import asyncpraw.models
import asyncprawcore.exceptions
import discord.ext.commands
import discord.ext.tasks

from . import PokestarBotCog
from ..creds import client_id, client_secret, user_agent
from ..utils import Embed, send_embeds_fields
from ..utils.nodes import CommentNode, SubmissionNode

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Reddit(PokestarBotCog):
    SUBREDDIT = re.compile("r/([A-Za-z0-9_]{1,21})")
    USER = re.compile("(?:user|u)/([A-Za-z0-9_]{1,32})")
    BLOCKQUOTE = re.compile(r"^>([^\s>])", re.MULTILINE | re.IGNORECASE | re.UNICODE)

    @property
    def conn(self):
        return self.bot.conn

    @property
    def reddit(self):
        return asyncpraw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent,
                                requestor_kwargs={"session": self.bot.session})

    @staticmethod
    async def render(node: CommentNode, maxlevel: Optional[int] = None, num: Optional[int] = None):
        items = []
        for i, data in enumerate(anytree.RenderTree(node, maxlevel=maxlevel), start=1):
            if num is not None and i > num:
                break
            pre, fill, node_obj = data
            items.append("{}{}".format(pre, node_obj.lines[0]))
            for line in node_obj.lines[1:]:
                items.append("{}{}".format(fill, line))
        return "\n".join(items)

    @discord.ext.commands.group(brief="Get information on a submission.", usage="link_or_id [link_or_id] [...]", invoke_without_command=True)
    async def submission(self, ctx: discord.ext.commands.Context, *links: str, _called_from_on_message: bool = False):
        await self.bot.load_session()
        if len(links) == 0 and not _called_from_on_message:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("submission", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    sub = await self.reddit.submission(url=link, lazy=True)
                else:
                    sub = await self.reddit.submission(id=link, lazy=True)
            except (asyncpraw.exceptions.InvalidURL, IndexError):  # Invalid URL
                if _called_from_on_message:
                    raise asyncpraw.exceptions.InvalidURL(link)
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    sub = await self.reddit.submission(id=sub.id)
                except asyncprawcore.exceptions.NotFound:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Does Not Exist", description="The given submission ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Submission ID", value=str(sub.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    embed = Embed(ctx,
                                  timestamp=datetime.datetime.utcfromtimestamp(sub.created_utc), url="https://www.reddit.com" + sub.permalink)
                    description = self.BLOCKQUOTE.sub(r"> \1", sub.selftext or sub.url)
                    if len(description) > 2048:
                        description = description[:2045] + "..."
                    embed.description = description
                    if not sub.over_18 or (sub.over_18 and ctx.channel.is_nsfw()):
                        embed.title = sub.title
                        image_url = sub.url
                        if not (not image_url.endswith(".jpg") and not image_url.endswith(".png") and not image_url.endswith(".jpeg")):
                            embed.set_image(url=image_url)
                        thumb_url = sub.thumbnail
                        if not (not thumb_url.endswith(".jpg") and not thumb_url.endswith(".png") and not thumb_url.endswith(".jpeg")):
                            embed.set_thumbnail(url=thumb_url)
                    else:
                        embed.title = sub.fullname
                    embed.title += " [NSFW]" if sub.over_18 else ""
                    embed.add_field(name="Author",
                                    value=f"[{getattr(sub.author, 'name', '[deleted]') or '[deleted]'}](https://www.reddit.com/user/"
                                          f"{getattr(sub.author, 'name', '[deleted]') or '[deleted]'})")
                    embed.add_field(name="Subreddit", value=f"[{sub.subreddit.display_name}](https://www.reddit.com/r/{sub.subreddit.display_name})")
                    embed.add_field(name="Score", value=sub.score)
                    embed.add_field(name="Score Hidden", value=str(sub.hide_score))
                    embed.add_field(name="Awards", value=str(sub.total_awards_received))
                    embed.add_field(name="Comments", value=str(sub.num_comments))
                    embed.add_field(name="Upvote Ratio", value=str(int(sub.upvote_ratio * 100)) + "%")
                    await ctx.send(embed=embed)

    @submission.command(brief="Get the full body of a Submission, without all of the other information.", usage="link [link]")
    async def body(self, ctx: discord.ext.commands.Context, *links: str):
        await self.bot.load_session()
        if len(links) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("submission", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    sub = await self.reddit.submission(url=link, lazy=True)
                else:
                    sub = await self.reddit.submission(id=link, lazy=True)
            except (asyncpraw.exceptions.InvalidURL, IndexError):  # Invalid URL
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    sub = await self.reddit.submission(id=sub.id)
                except asyncprawcore.exceptions.NotFound:
                    embed = Embed(ctx, title="Does Not Exist", description="The given submission ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Submission ID", value=str(sub.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    embed = Embed(ctx,
                                  timestamp=datetime.datetime.utcfromtimestamp(sub.created_utc), url="https://www.reddit.com" + sub.permalink)
                    description = self.BLOCKQUOTE.sub(r"> \1", sub.selftext or sub.url)
                    await send_embeds_fields(ctx, embed, [description])

    @discord.ext.commands.group(brief="Get the information on a comment.", usage="id_or_link [id_or_link] [...]", invoke_without_command=True)
    async def comment(self, ctx: discord.ext.commands.Context, *links: str, _called_from_on_message: bool = False):
        await self.bot.load_session()
        if len(links) == 0 and not _called_from_on_message:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("comment", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    comment = await self.reddit.comment(url=link, lazy=True)
                else:
                    comment = await self.reddit.comment(id=link, lazy=True)
            except asyncpraw.exceptions.InvalidURL:
                if _called_from_on_message:
                    raise
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    await comment.refresh()
                except asyncprawcore.exceptions.NotFound:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Comment ID", value=str(comment.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    await comment.submission.load()
                    embed = Embed(ctx,
                                  timestamp=datetime.datetime.utcfromtimestamp(comment.created_utc),
                                  url="https://www.reddit.com" + comment.permalink)
                    description = self.BLOCKQUOTE.sub(r"> \1", comment.body)
                    if len(description) > 2048:
                        description = description[:2045] + "..."
                    sub = comment.submission
                    embed.description = description
                    if not sub.over_18 or (sub.over_18 and ctx.channel.is_nsfw()):
                        embed.title = f"Comment in *{comment.submission.title}*"
                        thumb_url = sub.thumbnail
                        if not (not thumb_url.endswith(".jpg") and not thumb_url.endswith(".png") and not thumb_url.endswith(".jpeg")):
                            embed.set_thumbnail(url=thumb_url)
                    else:
                        embed.title = f"Comment in *{comment.submission.fullname}*"
                    embed.title += " [NSFW]" if comment.submission.over_18 else ""
                    embed.add_field(name="Author",
                                    value=f"[{getattr(comment.author, 'name', '[deleted]') or '[deleted]'}](https://www.reddit.com"
                                          f"/user/{getattr(comment.author, 'name', '[deleted]') or '[deleted]'})")
                    embed.add_field(name="Subreddit",
                                    value=f"[{comment.subreddit.display_name}](https://www.reddit.com/r/{comment.subreddit.display_name})")
                    embed.add_field(name="Score", value=comment.score)
                    embed.add_field(name="Score Hidden", value=str(comment.score_hidden))
                    embed.add_field(name="Awards", value=str(comment.total_awards_received))
                    embed.add_field(name="Replies (Estimated)", value=str(len(comment.replies)))
                    await ctx.send(embed=embed)

    @comment.command(name="body", brief="Get the full body of a Submission, without all of the other information.", usage="link [link]")
    async def comment_body(self, ctx: discord.ext.commands.Context, *links: str):
        await self.bot.load_session()
        if len(links) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("comment", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    comment = await self.reddit.comment(url=link, lazy=True)
                else:
                    comment = await self.reddit.comment(id=link, lazy=True)
            except asyncpraw.exceptions.InvalidURL:
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    await comment.refresh()
                except asyncprawcore.exceptions.NotFound:
                    embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Comment ID", value=str(comment.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    await comment.submission.load()
                    embed = Embed(ctx,
                                  timestamp=datetime.datetime.utcfromtimestamp(comment.created_utc),
                                  url="https://www.reddit.com" + comment.permalink)
                    description = self.BLOCKQUOTE.sub(r"> \1", comment.body)
                    await send_embeds_fields(ctx, embed, [description])

    @discord.ext.commands.command(brief="Get the information on a subreddit.", usage="subreddit [subreddit] [...]")
    async def subreddit(self, ctx: discord.ext.commands.Context, *links: str, _called_from_on_message: bool = False):
        await self.bot.load_session()
        if len(links) == 0 and not _called_from_on_message:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("subreddit", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            if "/" in link or link.startswith("r/"):
                if match := self.SUBREDDIT.search(link):
                    try:
                        subreddit = await self.reddit.subreddit(match.group(1), fetch=True)
                    except asyncprawcore.exceptions.NotFound:
                        if _called_from_on_message:
                            return
                        embed = Embed(ctx, title="Does Not Exist", description="The given subreddit does not exist", color=discord.Color.red())
                        embed.add_field(name="Subreddit Name", value=match.group(1))
                        embed.add_field(name="Provided Link", value=link)
                        return await ctx.send(embed=embed)
                else:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                    embed.add_field(name="ID or URL", value=link)
                    return await ctx.send(embed=embed)
            else:
                try:
                    subreddit = await self.reddit.subreddit(link, fetch=True)
                except asyncprawcore.exceptions.NotFound:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Does Not Exist", description="The given subreddit does not exist", color=discord.Color.red())
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
            embed = Embed(ctx, url="https://www.reddit.com" + subreddit.url,
                          timestamp=datetime.datetime.utcfromtimestamp(subreddit.created_utc))
            if hex_code := subreddit.primary_color[1:]:
                embed.colour = discord.Color(int(hex_code, base=16))
            description = subreddit.description
            if len(description) > 2048:
                description = description[:2045] + "..."
            if not _called_from_on_message:
                embed.description = description
            if not subreddit.over18 or (subreddit.over18 and ctx.channel.is_nsfw()):
                embed.title = subreddit.title
                embed.set_thumbnail(url=subreddit.community_icon or discord.Embed.Empty)
                embed.set_image(url=subreddit.banner_background_image or discord.Embed.Empty)
            else:
                embed.title = subreddit.fullname
            embed.title += " [NSFW]" if subreddit.over18 else ""
            embed.add_field(name="Subscribers", value=str(subreddit.subscribers))
            embed.add_field(name="People Currently On Subreddit", value=str(subreddit.accounts_active))
            await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Get the information on a user", usage="user [user] [...]")
    async def user(self, ctx: discord.ext.commands.Context, *links: str, _called_from_on_message: bool = False):
        await self.bot.load_session()
        if len(links) == 0 and not _called_from_on_message:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("user", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            if "/" in link or link.startswith("u/"):
                if match := self.USER.search(link):
                    try:
                        redditor = await self.reddit.redditor(match.group(1), fetch=True)
                    except asyncprawcore.exceptions.NotFound:
                        if _called_from_on_message:
                            return
                        embed = Embed(ctx, title="Does Not Exist", description="The given user does not exist", color=discord.Color.red())
                        embed.add_field(name="Username", value=match.group(1))
                        embed.add_field(name="Provided Link", value=link)
                        return await ctx.send(embed=embed)
                else:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                    embed.add_field(name="ID or URL", value=link)
                    return await ctx.send(embed=embed)
            else:
                try:
                    redditor = await self.reddit.redditor(link, fetch=True)
                except asyncprawcore.exceptions.NotFound:
                    if _called_from_on_message:
                        return
                    embed = Embed(ctx, title="Does Not Exist", description="The given subreddit does not exist", color=discord.Color.red())
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
            subreddit = redditor.subreddit
            if isinstance(subreddit, dict):
                subreddit = asyncpraw.models.Subreddit(self.reddit, _data=subreddit)
            embed = Embed(ctx, title=(getattr(redditor, 'name', '[deleted]') or '[deleted]') + (" [NSFW]" if subreddit.over_18 else ""),
                          url="https://www.reddit.com/user/" + getattr(redditor, 'name', '[deleted]') or '[deleted]',
                          timestamp=datetime.datetime.utcfromtimestamp(redditor.created_utc))
            if not subreddit.over_18 or (subreddit.over_18 and ctx.channel.is_nsfw()):
                embed.set_thumbnail(url=subreddit.icon_img or discord.Embed.Empty)
                embed.set_image(url=subreddit.banner_img or discord.Embed.Empty)
            embed.add_field(name="Total Karma", value=str(redditor.total_karma))
            embed.add_field(name="Post Karma", value=str(redditor.link_karma))
            embed.add_field(name="Comment Karma", value=str(redditor.comment_karma))
            embed.add_field(name="Awarder Karma", value=str(redditor.awarder_karma))
            embed.add_field(name="Awardee Karma", value=str(redditor.awardee_karma))
            await ctx.send(embed=embed)

    @discord.ext.commands.group(brief="Get a comment thread", usage="comment", invoke_without_command=True)
    async def thread(self, ctx: discord.ext.commands.Context, *links: str):
        await self.bot.load_session()
        if len(links) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("comment", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    comment = await self.reddit.comment(url=link, lazy=True)
                else:
                    comment = await self.reddit.comment(id=link, lazy=True)
            except asyncpraw.exceptions.InvalidURL:
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    parent = await comment.parent()
                    await comment.refresh()
                except (asyncprawcore.exceptions.NotFound, asyncpraw.exceptions.ClientException):
                    embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Comment ID", value=str(comment.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    cn = CommentNode(comment, full=True)
                    if isinstance(parent, asyncpraw.models.Submission):
                        sn = SubmissionNode(parent)
                        sn.children = [cn]
                        text = await self.render(sn, num=16)
                    else:
                        text = await self.render(cn, num=15)
                    embed = Embed(ctx, title="Comment Chain", url="https://www.reddit.com" + comment.permalink)
                    if len(text) < 2048:
                        embed.description = text
                        return await ctx.send(embed=embed)
                    await send_embeds_fields(ctx, embed, [("\u200b", text)])

    @thread.command(brief="Get the full comments of a thread for every comment above the given thread.")
    async def above(self, ctx: discord.ext.commands.Context, *links: str):
        await self.bot.load_session()
        if len(links) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("comment", inspect.Parameter.POSITIONAL_ONLY))
        for link in links:
            try:
                if "/" in link:
                    comment = await self.reddit.comment(url=link, lazy=True)
                else:
                    comment = await self.reddit.comment(id=link, lazy=True)
            except asyncpraw.exceptions.InvalidURL:
                embed = Embed(ctx, title="Invalid ID or URL", description="The given URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=link)
                return await ctx.send(embed=embed)
            else:
                try:
                    parent = await comment.parent()
                except (asyncprawcore.exceptions.NotFound, asyncpraw.exceptions.ClientException):
                    embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Comment ID", value=str(comment.id))
                    embed.add_field(name="Provided Link", value=link)
                    return await ctx.send(embed=embed)
                else:
                    cn = CommentNode(comment, full=True)
                    cn.children = []
                    while not isinstance(parent, asyncpraw.models.Submission):
                        child = [cn]
                        cn = CommentNode(parent, full=True)
                        child[0].parent = cn
                        cn.children = child
                        parent = await parent.parent()
                    sn = SubmissionNode(parent)
                    sn.children = [cn]
                    cn.parent = sn
                    text = await self.render(sn)
                    embed = Embed(ctx, title="Comment Chain", url="https://www.reddit.com" + comment.permalink)
                    if len(text) < 2048:
                        embed.description = text
                        return await ctx.send(embed=embed)
                    await send_embeds_fields(ctx, embed, [("\u200b", text)])

    @thread.command(brief="Get the full comments of a thread for every comment between the given comments, including the given comments.")
    async def between(self, ctx: discord.ext.commands.Context, top: str, bottom: str):
        await self.bot.load_session()
        try:
            if "/" in top:
                top_comment = await self.reddit.comment(url=top, lazy=True)
            else:
                top_comment = await self.reddit.comment(id=top, lazy=True)
        except asyncpraw.exceptions.InvalidURL:
            embed = Embed(ctx, title="Invalid Top ID or URL", description="The given top URL or ID was invalid.", color=discord.Color.red())
            embed.add_field(name="ID or URL", value=top)
            return await ctx.send(embed=embed)
        else:
            try:
                if "/" in bottom:
                    bottom_comment = await self.reddit.comment(url=bottom, lazy=True)
                else:
                    bottom_comment = await self.reddit.comment(id=bottom, lazy=True)
            except asyncpraw.exceptions.InvalidURL:
                embed = Embed(ctx, title="Invalid Bottom ID or URL", description="The given bottom URL or ID was invalid.", color=discord.Color.red())
                embed.add_field(name="ID or URL", value=bottom)
                return await ctx.send(embed=embed)
            else:
                try:
                    await top_comment.refresh()
                except (asyncprawcore.exceptions.NotFound, asyncpraw.exceptions.ClientException):
                    embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                    embed.add_field(name="Comment ID", value=str(top_comment.id))
                    embed.add_field(name="Provided Link", value=top)
                    return await ctx.send(embed=embed)
                else:
                    try:
                        parent = await bottom_comment.parent()
                    except (asyncprawcore.exceptions.NotFound, asyncpraw.exceptions.ClientException):
                        embed = Embed(ctx, title="Does Not Exist", description="The given comment ID does not exist", color=discord.Color.red())
                        embed.add_field(name="Comment ID", value=str(bottom_comment.id))
                        embed.add_field(name="Provided Link", value=bottom)
                        return await ctx.send(embed=embed)
                    else:
                        cn = CommentNode(bottom_comment, full=True)
                        cn.children = []
                        while not parent == top_comment:
                            child = [cn]
                            cn = CommentNode(parent, full=True)
                            child[0].parent = cn
                            cn.children = child
                            parent = await parent.parent()
                        text = await self.render(cn)
                        embed = Embed(ctx, title="Comment Chain", url="https://www.reddit.com" + top_comment.permalink)
                        if len(text) < 2048:
                            embed.description = text
                            return await ctx.send(embed=embed)
                        await send_embeds_fields(ctx, embed, [("\u200b", text)])

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        content = message.content
        if message.author.bot or (message.content or "").startswith(self.bot.command_prefix):
            return
        if content and not content.startswith(self.bot.command_prefix):
            context = await self.bot.get_context(message)
            urls = []
            subreddits = []
            users = []
            for word in content.split(" "):
                if not word:
                    continue
                elif word.startswith("http"):
                    if "redd.it" in word or "reddit.com" in word:
                        urls.append(word)
                elif self.SUBREDDIT.match(word):
                    subreddits.append(word)
                elif self.USER.match(word):
                    if not word.startswith("u/"):
                        continue
                    users.append(word)
            if urls:
                logger.debug("Found URLs: %s", urls)
            for url in urls:
                try:
                    await self.comment(context, url, _called_from_on_message=True)
                except asyncpraw.exceptions.InvalidURL:
                    try:
                        await self.submission(context, url, _called_from_on_message=True)
                    except asyncpraw.exceptions.InvalidURL:
                        if "/user" in url:
                            try:
                                await self.user(context, url, _called_from_on_message=True)
                            except Exception:
                                logger.warning("Failed on url %s", url, exc_info=True)
                                continue
                        else:
                            try:
                                await self.subreddit(context, url, _called_from_on_message=True)
                            except Exception:
                                logger.warning("Failed on url %s", url, exc_info=True)
                                continue
                    except Exception:
                        logger.warning("Failed on url %s", url, exc_info=True)
                        continue
                except Exception:
                    logger.warning("Failed on url %s", url, exc_info=True)
                    continue
            if subreddits:
                logger.debug("Found Subreddits: %s", subreddits)
                try:
                    await self.subreddit(context, *subreddits, _called_from_on_message=True)
                except Exception:
                    logger.warning("Failed on subreddits %s", subreddits, exc_info=True)
            if users:
                logger.debug("Found Users: %s", users)
                try:
                    await self.user(context, *users, _called_from_on_message=True)
                except Exception:
                    logger.warning("Failed on users %s", users, exc_info=True)


def setup(bot: "PokestarBot"):
    bot.add_cog(Reddit(bot))
    logger.info("Loaded the Reddit extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Reddit extension.")
