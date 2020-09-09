import itertools
from typing import Iterable, List, Optional, Tuple, Union

import anytree
import discord.ext.commands


class CommandNode(anytree.NodeMixin):
    @property
    def full_name(self):
        return self.parent.full_name + (" " if not isinstance(self.parent, (BotNode, CogNode)) else "") + self.name

    @property
    def name(self):
        return self.command.name

    @property
    def brief(self):
        return getattr(self.command, "brief", None)

    __slots__ = ("command", "parent")

    def __init__(self, command: discord.ext.commands.Command, parent: Union["BotNode", "GroupNode"]):
        self.command = command
        self.parent = parent

    def __repr__(self):
        return self.full_name

    def __str__(self):
        return self.name

    def __lt__(self, other: "CommandNode"):
        return self.name < other.name

    def __gt__(self, other: "CommandNode"):
        return self.name > other.name

    def __eq__(self, other: Union[str, "CommandNode"]):
        return (self.name == other) if isinstance(other, str) else (self.command == other.command)

    def __ne__(self, other: Union[str, "CommandNode"]):
        return not (self == other)

    def __le__(self, other: "CommandNode"):
        return self.name <= other.name

    def __ge__(self, other: "CommandNode"):
        return self.name >= other.name


class GroupNode(CommandNode):
    @property
    def children(self):
        return self.make_child_nodes()

    @property
    def commands(self) -> Tuple[discord.ext.commands.Command, ...]:
        return self._commands or self.command.commands

    def __init__(self, command: discord.ext.commands.Group, parent: Union["BotNode", "GroupNode"],
                 commands: Optional[Iterable[discord.ext.commands.Command]] = None):
        super().__init__(command, parent)
        self._commands = tuple(commands or ())

    def make_child_nodes(self) -> List[Union[CommandNode, "GroupNode"]]:
        return sorted([CommandNode(command, parent=self) if not isinstance(command, discord.ext.commands.Group) else GroupNode(command, parent=self)
                       for command in self.commands])

    def subcommands(self, word="subcommands"):
        return " [{} {}]".format(len(self.children), word)

    def get_subcommand_node(self, subcommand_name: str, children: Iterable[Union["GroupNode", CommandNode]] = None):
        for subcommand in (children or self.children):
            if subcommand == subcommand_name:
                return subcommand
        return

    def __repr__(self):
        return super().__repr__() + self.subcommands()

    __slots__ = ("_commands",)


class CogNode(GroupNode):
    @property
    def full_name(self):
        return self.parent.full_name

    def __repr__(self):
        return "{}{}{}".format(self.full_name, self.name, self.subcommands())

    def get_subcommand_node(self, subcommand_name=None, children=None):
        return super().get_subcommand_node("commands")

    __slots__ = ()


class BotNode(GroupNode):
    @property
    def bot_class_name(self):
        return type(self.command).__name__

    def __init__(self, command: discord.ext.commands.Bot, cog_mode: bool = True, commands: Optional[Iterable[discord.ext.commands.Command]] = None):
        self.cog_mode = cog_mode
        super().__init__(command, None, commands)

    def make_child_nodes(self) -> List[Union[CommandNode, GroupNode, CogNode]]:
        return sorted([CogNode(cog, parent=self) for cog in self.command.cogs.values()]) if self.cog_mode else super().make_child_nodes()

    def subcommands(self):
        word = "Cogs" if self.cog_mode else "commands"
        return super().subcommands(word=word)

    def get_subcommand_node(self, subcommand_name: str):
        val = super().get_subcommand_node(subcommand_name, (itertools.chain(*[item.children for item in self.children]) if self.cog_mode else None))
        return val

    def __repr__(self):
        return "{}{}{}".format(self.full_name, self.name, self.subcommands())

    @property
    def full_name(self):
        return self.command.command_prefix

    @property
    def name(self):
        return self.bot_class_name

    __slots__ = ("cog_mode",)
