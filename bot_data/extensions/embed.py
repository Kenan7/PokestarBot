import importlib
import logging
import os
from typing import TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed as EmbedClass, break_into_groups, send_embeds

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Embed(PokestarBotCog):

    @staticmethod
    def make_directory(guild_id: int):
        path = os.path.abspath(os.path.join(__file__, "..", "..", "embeds", f"g_{guild_id}"))
        os.makedirs(path, exist_ok=True)
        open(os.path.join(path, "__init__.py"), "a").close()

    @discord.ext.commands.group(invoke_without_command=True, brief="Spawn the custom Embed with the given name.", usage="name")
    @discord.ext.commands.guild_only()
    async def embed(self, ctx: discord.ext.commands.Context, name: str):
        try:
            module = importlib.import_module(f"bot_data.embeds.g_{ctx.guild.id}." + name)
        except ModuleNotFoundError:
            embed = EmbedClass(ctx, color=discord.Color.red(), title="Invalid Custom Embed",
                               description="The given custom Embed does not exist. Type `{}embed list` to get the list of Embeds.".format(
                                   self.bot.command_prefix))
            embed.add_field(name="Embed Name", value=name)
            await ctx.send(embed=embed)
        else:
            new_mod = importlib.reload(module)
            data = await new_mod.generate_embed(self.bot)
            for content, embed in data:
                await ctx.send(content=content, embed=embed)

    @embed.command(brief="List all custom Embeds.")
    @discord.ext.commands.guild_only()
    async def list(self, ctx: discord.ext.commands.Context):
        self.make_directory(ctx.guild.id)
        embed_path = os.path.abspath(os.path.join(__file__, "..", "..", "embeds", f"g_{ctx.guild.id}"))
        embed = EmbedClass(ctx, title="Custom Embeds", description="A list of the custom Embeds that the bot can send.")
        items = []
        for file in os.listdir(embed_path):
            if not os.path.isfile(os.path.join(embed_path, file)) or file.startswith("_") or not file.endswith(".py"):
                logger.debug("Skipped %s (full path: %s) (not isfile: %s, startswith _: %s, not endswith .py: %s", file,
                             os.path.join(embed_path, file), not os.path.isfile(os.path.join(embed_path, file)), file.startswith("_"),
                             not file.endswith(".py"))
                continue
            items.append(file.rpartition(".")[0])
            logger.debug("Found Embed file: %s, shown as %s", file, file.rpartition(".")[0])
        groups = await break_into_groups(template="", ending="", line_template="* **{}**", lines=items)
        await send_embeds(ctx, embed, groups, description="A list of the custom Embeds that the bot can send.")


def setup(bot: "PokestarBot"):
    bot.add_cog(Embed(bot))
    logger.info("Loaded the Embed extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Embed extension.")
