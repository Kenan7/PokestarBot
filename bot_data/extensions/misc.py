import asyncio
import inspect
import io
import logging
import string
from typing import Optional, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Misc(PokestarBotCog):

    @discord.ext.commands.command(brief="Say the message `num` times", usage="num message")
    async def echo(self, ctx: discord.ext.commands.Context, num: int, *, message: str):
        if not ctx.author.guild_permissions.administrator and num > 5:
            embed = Embed(ctx, title="Too Many Echoes", description="You hit the echo limit.", color=discord.Color.red())
            embed.add_field(name="Echoes Requested", value=str(num))
            embed.add_field(name="Max Echoes", value=str(5))
            return await ctx.send(embed=embed)
        if num > 50:
            embed = Embed(ctx, title="Too Many Echoes", description="You hit the echo limit.", color=discord.Color.red())
            embed.add_field(name="Echoes Requested", value=str(num))
            embed.add_field(name="Max Echoes", value=str(50))
            return await ctx.send(embed=embed)
        for i in range(num):
            await ctx.send(message)

    @discord.ext.commands.command(brief="Get the time between sending the message and command processing.")
    async def ping(self, ctx: discord.ext.commands.Context):
        td = self.bot.ping_timedelta
        ms_list = [int(delta.total_seconds() * 1000) for delta in self.bot.pings]
        avg = sum(ms_list) // len(ms_list)
        embed = Embed(ctx, title="Bot Ping")
        embed.add_field(name="Ping (s)", value=str(td))
        embed.add_field(name="Ping (ms)", value=str(int(td.total_seconds() * 1000)))
        embed.add_field(name="Average Ping", value=str(avg))
        embed.add_field(name="Message Sample", value=str(len(ms_list)))
        await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Send the last image message with a spoiler.", usage="[spoiler_text]", aliases=["spoilermsg"])
    @discord.ext.commands.guild_only()
    async def spoiler_msg(self, ctx: discord.ext.commands.Context, spoiler_text: Optional[bool] = False):
        async for message in ctx.history(limit=None, before=ctx.message.created_at).filter(lambda msg: msg.author == ctx.author).filter(
                lambda msg: msg.attachments):
            content = message.content
            attachments = message.attachments
            files = []
            for attachment in attachments:
                attachment: discord.Attachment
                file = io.BytesIO()
                await attachment.save(file)
                files.append(discord.File(file, filename=attachment.filename, spoiler=True))
            if spoiler_text:
                if len(content) >= 1996:
                    await ctx.send(embed=Embed(ctx, title="Message Too Large", description="The message is too large.", color=discord.Color.red()))
                else:
                    content = f"||{content}||"
            await ctx.send(content=content, files=files)
            await message.delete()
            break

    async def expand_message(self, message: discord.Message):
        if len(message.attachments) == 1:
            attachment = message.attachments[0]
            try:
                data = await attachment.read()
            except discord.NotFound:
                return
            else:
                try:
                    text = data.decode()
                except UnicodeDecodeError:
                    return
            if attachment.filename == "message.txt":
                embed = Embed(message, title="Expanded Message", color=discord.Color.green())
                fields = [("User", message.author.mention), ("Content", text)]
                return await send_embeds_fields(await self.bot.get_context(message), embed, fields)

    @discord.ext.commands.command(brief="Get the emoji for a specific letter", usage="letter [letter]")
    async def letter(self, ctx: discord.ext.commands.Context, *letters: str):
        if len(letters) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("letter", kind=inspect.Parameter.POSITIONAL_ONLY))
        letrz = []
        for letter in letters:
            letter = letter.lower()
            if letter == "all":
                letrz.extend(string.ascii_lowercase)
            elif letter not in string.ascii_lowercase:
                embed = Embed(ctx, title="Non-letter", description="The provided character is not a letter.", color=discord.Color.red())
                embed.add_field(name="Character", value=letter)
                await ctx.send(embed=embed)
            else:
                letrz.append(letter)

    @discord.ext.commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        coros = [self.expand_message(message)]
        return await asyncio.gather(*coros)


def setup(bot: "PokestarBot"):
    bot.add_cog(Misc(bot))
    logger.info("Loaded the Misc extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Misc extension.")
