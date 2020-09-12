import itertools
import logging
import os
from typing import Dict, Iterable, List, Optional, TYPE_CHECKING

import anytree
import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, send_embeds_fields
from ..utils.nodes import BotNode, CogNode

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Help(PokestarBotCog):
    HELP_FILE_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "man"))

    def help_file_exists(self, command: str):
        file_path = (os.path.join(self.HELP_FILE_DIR, command.lower()).rstrip() + ".md")
        return file_path, os.path.exists(file_path)

    def get_help_file(self, command: str) -> str:
        file_path, exists = self.help_file_exists(command)
        if not exists:
            return "[No Extended Help]"
        with open(file_path, encoding="utf-8") as file:
            data = file.read().rstrip()
            if not data:
                return "[No Extended Help]"
            return data.format(prefix=self.bot.command_prefix)

    @discord.ext.commands.group(brief="Get the full extended help on a command.", usage="command",
                                aliases=["extendedhelp", "exthelp", "ext_help", "man"], invoke_without_command=True)
    async def extended_help(self, ctx: discord.ext.commands.Context, *, command: str):
        command = self.bot.get_command(command).qualified_name
        embed = Embed(ctx, title="Extended Help for Command `{}`".format(command))
        await send_embeds_fields(ctx, embed, [("\u200b", self.get_help_file(command))], inline_fields=False)

    @extended_help.command(brief="Pre-create the extended help files for every command.")
    @discord.ext.commands.is_owner()
    async def pre_create(self, ctx: discord.ext.commands.Context):
        count = 0
        commands = {command.qualified_name: command for command in self.bot.walk_commands()}
        commands.update({name: cog for name, cog in self.bot.cogs.items()})
        for name, command_or_cog in commands.items():
            path = os.path.join(self.HELP_FILE_DIR, name.lower() + ".md")
            if not os.path.exists(path) or os.stat(path).st_size == 0:
                with open(path, "w") as file:
                    if isinstance(command_or_cog, discord.ext.commands.Command):
                        params = list(command_or_cog.params.values())[2:]
                        if len(params) > 0:
                            file.write("\n\nArguments:\n")
                            for param in params:
                                file.write(f"* `{param.name}`:\n")
                            file.write("\nExamples:\n")
                count += 1
        logger.info("Created %s files", count)
        embed = Embed(ctx, title="File Creation Was Successful", color=discord.Color.green(),
                      description="The extended help files were successfully created.")
        embed.add_field(name="Files Created", value=str(count))
        await ctx.send(embed=embed)

    @extended_help.command(name="prune", brief="Prune the extended help files for commands that no longer exist.")
    @discord.ext.commands.is_owner()
    async def man_prune(self, ctx: discord.ext.commands.Context):
        count = 0
        commands = [command.qualified_name for command in self.bot.walk_commands()]
        commands.extend(name for name in self.bot.cogs.keys())
        commands = set(command.lower() + ".md" for command in commands)
        files = set(os.listdir(self.HELP_FILE_DIR))
        difference = files - commands
        for file in difference:
            os.remove(os.path.join(self.HELP_FILE_DIR, file))
            count += 1
        logger.info("Pruned %s files", count)
        embed = Embed(ctx, title="File Prune Successful", color=discord.Color.green(),
                      description="The extended help files were successfully pruned.")
        embed.add_field(name="Files Pruned", value=str(count))
        await ctx.send(embed=embed)

    @extended_help.command(name="sync", brief="Both pre-create and prune extended help files.")
    @discord.ext.commands.is_owner()
    async def man_sync(self, ctx: discord.ext.commands.Context):
        await self.pre_create(ctx)
        await self.man_prune(ctx)


class CustomHelp(discord.ext.commands.HelpCommand):
    HELP_FILE_DIR = os.path.abspath(os.path.join(__file__, "..", "..", "man"))

    HELP_PATH_TEMPLATE = "* `{}{}`: **{}**"

    def bot_node(self, cog_mode: bool = True, commands: Optional[Iterable[discord.ext.commands.Command]] = None) -> BotNode:
        return BotNode(self.bot, cog_mode=cog_mode, commands=commands)

    @property
    def ctx(self):
        return self.context

    @property
    def bot(self) -> "PokestarBot":
        return self.context.bot

    @property
    def commands(self) -> Dict[str, discord.ext.commands.Command]:
        return {command.qualified_name: command for command in self.bot.walk_commands()}

    @property
    def command_names(self) -> List[str]:
        return sorted(self.commands.keys())

    async def filtered_commands(self) -> List[discord.ext.commands.Command]:
        commands = self.get_bot_mapping().values()
        return await self.filter_commands(itertools.chain(*commands), sort=True)

    def __init__(self, **options):
        super().__init__(verify_checks=True, **options)

    def cog_node(self, cog: PokestarBotCog):
        return CogNode(cog, self.bot_node())

    async def get_node(self, command: List[str]):
        node = self.bot_node()
        _command = command.copy()
        while command:
            node = node.get_subcommand_node(command.pop(0), )
            if node is None:
                logger.warning("Command %s does not exist.", " ".join(_command))
                raise KeyError(" ".join(_command))
                # return await self.send_error_message(self.command_not_found(" ".join(_command)))
        if not isinstance(node.command, discord.ext.commands.Group):
            return node
        else:
            children = await self.filter_commands(node.command.commands, sort=True)
            node._commands = children
            return node

    def help_file_exists(self, command: str):
        file_path = (os.path.join(self.HELP_FILE_DIR, command.lower()).rstrip() + ".md")
        return file_path, os.path.exists(file_path)

    def get_help_file(self, command: str) -> str:
        command = command.lower()
        file_path, exists = self.help_file_exists(command)
        if not exists:
            return ""
        with open(file_path, encoding="utf-8") as file:
            data = file.read().rstrip()
            if len(data) > 2048:
                return data[:2045] + "..."
            else:
                return data.format(prefix=self.bot.command_prefix)

    @staticmethod
    async def render(node: anytree.NodeMixin, maxlevel: Optional[int] = None):
        string = ""
        for pre, fill, node_obj in anytree.RenderTree(node, maxlevel=maxlevel):
            string += "{}{}\n".format(pre, repr(node_obj))
        return string.rstrip()

    async def with_cog(self):
        embed = Embed(self.ctx, title="Bot Help/Commands", description=self.get_help_file("help") or discord.Embed.Empty)
        fields = []
        for cog in self.bot_node().children:
            fields.append((cog.name, await self.render(cog)))
        await send_embeds_fields(self.get_destination(), embed, fields, template="```\n", ending="\n```")

    async def cog_list(self):
        await send_embeds_fields(self.get_destination(),
                                 Embed(self.ctx, title="Cog List", description=self.get_help_file("help") or discord.Embed.Empty),
                                 [("\u200b", await self.render(self.bot_node(cog_mode=True), maxlevel=2))], template="```\n", ending="\n```")

    async def commands_only(self):
        await send_embeds_fields(self.get_destination(), Embed(self.ctx, title="Bot Help/Commands"),
                                 [("\u200b", await self.render(self.bot_node(cog_mode=False, commands=await self.filtered_commands()), maxlevel=2))],
                                 template="```\n", ending="\n```")

    async def all_commands(self):
        await send_embeds_fields(self.get_destination(),
                                 Embed(self.ctx, title="Bot Help/Commands", description=self.get_help_file("help") or discord.Embed.Empty),
                                 [("\u200b", await self.render(self.bot_node(cog_mode=False), maxlevel=2))],
                                 template="```\n", ending="\n```")

    async def send_bot_help(self, _=None):
        await send_embeds_fields(self.get_destination(),
                                 Embed(self.ctx, title="Bot Help/Commands", description=self.get_help_file("help") or discord.Embed.Empty),
                                 [("\u200b", await self.render(self.bot_node(cog_mode=False, commands=await self.filtered_commands()), maxlevel=2))],
                                 template="```\n", ending="\n```")

    async def send_cog_help(self, cog: PokestarBotCog):
        cog = self.cog_node(cog)
        await send_embeds_fields(self.get_destination(),
                                 Embed(self.ctx, title="Help on Cog {}".format(cog), description=self.get_help_file(str(cog)) or discord.Embed.Empty),
                                 [("Subcommands", await self.render(cog))], template="```\n", ending="\n```")

    async def send_group_help(self, group: discord.ext.commands.Group):
        embed = Embed(self.ctx, title="Help for Command `{}{}`".format(self.bot.command_prefix, group.qualified_name),
                      description=self.get_help_file(group.qualified_name) or discord.Embed.Empty)
        node = await self.get_node([word for word in group.qualified_name.split(" ") if word.strip()])
        fields = [("Aliases", "\n".join(group.aliases) or "None"), ("Brief", group.brief or "None"),
                  ("Usage", "`" + self.bot.command_prefix + group.qualified_name + (" " + group.signature if group.signature else "") + "`")]
        for name, value in fields:
            embed.add_field(name=name, value=value)
        await send_embeds_fields(self.get_destination(), embed, [("Subcommands", await self.render(node))], template="```\n", ending="\n```")

    async def send_command_help(self, command: discord.ext.commands.Command):
        embed = Embed(self.ctx, title="Help for Command `{}{}`".format(self.bot.command_prefix, command.qualified_name),
                      description=self.get_help_file(command.qualified_name) or discord.Embed.Empty)
        fields = [("Aliases", "\n".join(command.aliases) or "None"), ("Brief", command.brief or "None"),
                  ("Usage", "`" + self.bot.command_prefix + command.qualified_name + (" " + command.signature if command.signature else "") + "`")]
        await send_embeds_fields(self.get_destination(), embed, fields)

    def command_not_found(self, string: str):
        return self.bot.invalid_command_msg(string)

    def subcommand_not_found(self, command: discord.ext.commands.Command, string: str):
        return self.bot.invalid_command_msg(command.qualified_name + " " + string)

    async def command_callback(self, ctx, *, command=None):
        if command == "PokestarBot":
            return await self.send_bot_help()
        elif command == "commands":
            return await self.commands_only()
        elif command in ["with_cog", "withcog"]:
            return await self.with_cog()
        elif command in ["cog_list", "coglist"]:
            return await self.cog_list()
        elif command == "all":
            return await self.all_commands()
        return await super().command_callback(ctx, command=command)


def setup(bot: "PokestarBot"):
    cog = Help(bot)
    help_command = CustomHelp()
    bot.help_command = help_command
    help_command.cog = cog
    bot.add_cog(cog)
    logger.info("Loaded the Help extension.")


def teardown(bot: "PokestarBot"):
    default = discord.ext.commands.DefaultHelpCommand()
    bot.help_command = default
    logger.warning("Unloading the Help extension.")
