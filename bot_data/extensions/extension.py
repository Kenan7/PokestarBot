import logging
from typing import Dict, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Extension(PokestarBotCog):
    """Manage bot extensions (bot owner only)."""

    @discord.ext.commands.group(invoke_without_command=True, brief="Manage bot extensions.", aliases=["ext"])
    async def extension(self, ctx: discord.ext.commands.Context):
        """Manage the bot extensions."""
        await self.bot.generic_help(ctx)

    @extension.command(brief="Get loaded extensions", aliases=["show", "list"])
    async def view(self, ctx: discord.ext.commands.Context):
        """View the loaded bot extensions."""
        embed = Embed(ctx, title="Bot Extensions", description="\n".join(
            "**{}**".format(extension) for package, sep, extension in (key.rpartition(".") for key in self.bot.extensions)))
        await ctx.send(embed=embed)

    @extension.command(brief="Reload extensions", usage="extension_name_or_all [extension_name] [...]")
    @discord.ext.commands.is_owner()
    async def reload(self, ctx: discord.ext.commands.Context, *extensions: str):
        """Reload all or specific extensions"""
        extension_pairings: Dict[str, str] = {}
        successful = []
        failed = []
        for key, value in self.bot.extensions.items():
            package, sep, ext = key.rpartition(".")
            extension_pairings[ext] = key
        if len(extensions) < 1:
            return await ctx.send(embed=Embed(ctx, title="No Extension Specified", color=discord.Color.red(),
                                              description="An extension was not specified. View the current extensions with `{}extension "
                                                          "view`.".format(self.bot.command_prefix)))
        for extension in extensions:
            if "all" in extension:
                for key, value in self.bot.extensions.copy().items():
                    try:
                        self.bot.reload_extension(key)
                    except discord.ext.commands.ExtensionError as exc:
                        await self.bot.on_command_error(ctx, exc, custom_message="There was an exception while reloading the **{}** extension".format(
                            extension))
                        failed.append(key)
                    else:
                        successful.append(key)
            else:
                if extension in extension_pairings:
                    extension = extension_pairings[extension]
                if extension in self.bot.extensions:
                    try:
                        self.bot.reload_extension(extension)
                    except discord.ext.commands.ExtensionError as exc:
                        await self.bot.on_command_error(ctx, exc, custom_message="There was an exception while reloading the **{}** extension".format(
                            extension))
                        failed.append(extension)
                    else:
                        successful.append(extension)
                else:
                    logger.warning("Extension %s does not exist", extension)
                    embed = Embed(ctx, title="Extension Does Not Exist", color=discord.Color.red(),
                                  description="The provided Extension does not exist. Use `{}extension view` to check the avaliable "
                                              "extensions.".format(self.bot.command_prefix))
                    embed.add_field(name="Extension Name", value=extension)
                    await ctx.send(embed=embed)
                    failed.append(extension)
        successful_str = "\n".join("**{}**".format(item) for item in set(successful)) or "None"
        failed_str = "\n".join("**{}**".format(item) for item in set(failed)) or "None"
        embed = Embed(ctx, title="Extension Reload Finished", description="The specified extensions have been reloaded.",
                      color=discord.Color.green() if not failed else discord.Color.red())
        await send_embeds_fields(ctx, embed, [("Successfully Reloaded Extensions", successful_str), ("Failed To Reload Extensions", failed_str)])


def setup(bot: "PokestarBot"):
    bot.add_cog(Extension(bot))
    logger.info("Loaded the Extension extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Extension extension.")
