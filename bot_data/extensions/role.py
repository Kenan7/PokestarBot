import itertools
import logging
from typing import Collection, List, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..converters import MemberRolesConverter, RolesConverter
from ..utils import Embed, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Roles(PokestarBotCog):
    USER_TEMPLATE = "* {}\n"
    ROLE_TEMPLATE = "* **{}**: {} members\n"

    @staticmethod
    def symbol(role: discord.Role, attribute: str, permissions: bool = True) -> str:
        """Gets the symbol if a role has a permission"""
        return ":no_entry_sign:" if not getattr(role.permissions if permissions else role, attribute) else ":white_check_mark:"

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        self._last_operation_members = {}

    @discord.ext.commands.group(invoke_without_command=True,
                                brief="Deals with role management",
                                usage="subcommand [subcommand_arg_1] [subcommand_arg_2] [...]")
    @discord.ext.commands.guild_only()
    async def role(self, ctx: discord.ext.commands.Context):
        """Manage the roles of members in the server. This command itself does nothing, but instead has subcommands."""
        await self.bot.generic_help(ctx)

    async def _base(self, remove: bool, ctx: discord.ext.commands.Context, role: discord.Role,
                    members: List[discord.Member]):
        members = list(set(members))
        embed = Embed(ctx, title="Role " + ("Removal" if remove else "Addition"), color=discord.Color.green())
        fields = [("Role", role.mention), ("Number of Users", len(members))]
        done = []
        async with ctx.typing():
            for member in members:
                method = member.add_roles if not remove else member.remove_roles
                await method(role, reason="Mass Role Operation triggered by {}".format(ctx.author))
                done.append(member.mention)
            fields.append(("Users Modified", "\n".join(done)))
        await send_embeds_fields(ctx, embed, fields)

    @role.group(invoke_without_command=True,
                brief="Assign a role en-masse to users.",
                usage="role_to_assign user_or_role_1 [user_or_role_2] [...]")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def add(self, ctx: discord.ext.commands.Context, role: discord.Role, *member_or_roles: MemberRolesConverter):
        """Add a role to all users that are part of the provided user(s) and role(s)."""
        members = list(itertools.chain(*member_or_roles))
        logger.info("Running a role addition operation on %s members with the %s role", len(members), role)
        self._last_operation_members["add"] = {"role": role, "members": members}
        await self._base(False, ctx, role, members)

    @role.command(brief="Create a role and assign members/roles to the created role",
                  usage="\"role_name\" [user_or_role_1] [user_or_role_2] [...]")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def create(self, ctx: discord.ext.commands.Context, role_name: str, *member_or_roles: MemberRolesConverter):
        """Creates a role and then assigns members to it."""
        logger.info("Running role creation operation with role name %s", role_name)
        role = await ctx.guild.create_role(name=role_name, reason="Role creation by {}".format(ctx.author),
                                           permissions=ctx.guild.default_role.permissions)
        embed = Embed(ctx, title="Role Creation Successful", color=discord.Color.green())
        embed.add_field(name="Role", value=role.mention)
        await ctx.send(embed=embed)
        await self.add(ctx, role, *member_or_roles)

    @role.command(brief="List the members of a role or list all roles",
                  usage="[role]")
    @discord.ext.commands.guild_only()
    async def list(self, ctx: discord.ext.commands.Context, *roles: RolesConverter):
        """List data about all roles or an individual role."""
        roles: Collection[discord.Role]
        if len(roles) == 0:  # All roles
            logger.info("Requested information on all roles")
            requested_roles = ctx.guild.roles[1:]
            embed = Embed(ctx, title="All Roles",
                          description="Each field, with the exception of **Total Roles**, represents the amount of members with that role.")
            embed.add_field(name="Total Roles", value=str(len(requested_roles)))
            fields = []
            for role in requested_roles:
                fields.append((str(role), str(len(role.members))))
            await send_embeds_fields(ctx, embed, fields)
        else:
            for role in roles:
                embed = Embed(ctx, title="Role " + str(role), color=role.color)
                fields = [(str(key), str(value)) for key, value in
                          [("Position From Top", len(role.guild.roles) - (role.position + 1)), ("Position From Bottom", role.position),
                           ("Hoisted", role.hoist), ("Mentionable By @everyone", role.mentionable)]]
                members = []
                for permission in (
                        "administrator", "manage_guild", "manage_roles", "manage_channels", "kick_members", "ban_members", "manage_nicknames",
                        "manage_webhooks", "manage_messages", "mute_members", "deafen_members", "move_members", "priority_speaker"):
                    value = getattr(role.permissions, permission)
                    fields.append((permission.replace("_", " ").title(), str(value)))
                for member in role.members:
                    members.append(member.mention)
                fields.append(("Members (**{}**)".format(len(role.members)), "\n".join(members)))
                await send_embeds_fields(ctx, embed, fields)

    @role.group(invoke_without_command=True,
                brief="Unassign a role en-masse to users.",
                usage="role_to_unassign user_or_role_1 [user_or_role_2] [...]")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def remove(self, ctx: discord.ext.commands.Context, role: discord.Role,
                     *member_or_roles: MemberRolesConverter):
        """Remove a role to all users that are part of the provided user(s) and role(s)."""
        members = list(itertools.chain(*member_or_roles))
        logger.info("Running a role removal operation on %s members with the %s role", len(members), role)
        self._last_operation_members["remove"] = {"role": role, "members": members}
        await self._base(True, ctx, role, members)

    @add.command(name="reverse", brief="Reverse the last mass role addition")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def add_reverse(self, ctx: discord.ext.commands.Context):
        """Reverse the last role addition. Will not reverse role additions that occurred before the bot started up (such as roles added before the
        bot restarted)."""
        try:
            role = self._last_operation_members["add"]["role"]
            members = self._last_operation_members["add"]["members"]
            logger.info("Running an addition role reversal for the %s role, impacting %s members", role, len(members))
            await self._base(True, ctx, role, members)
        except KeyError:
            logger.warning("No roles have been added since bot startup")
            await ctx.send(embed=Embed(ctx, color=discord.Color.red(), title="No Role Additions So Far",
                                       description="There have been no role additions since bot startup."))

    @remove.command(name="reverse", brief="Reverse the last mass role addition")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def remove_reverse(self, ctx: discord.ext.commands.Context):
        """Reverse the last role removal. Will not reverse role removals that occurred before the bot started up (
        such as roles removed before the bot restarted)."""
        try:
            role = self._last_operation_members["remove"]["role"]
            members = self._last_operation_members["remove"]["members"]
            logger.info("Running an removal role reversal for the %s role, impacting %s members", role, len(members))
            await self._base(False, ctx, role, members)
        except KeyError:
            logger.warning("No roles have been removed since bot startup")
            await ctx.send(embed=Embed(ctx, color=discord.Color.red(), title="No Role Removals So Far",
                                       description="There have been no role removals since bot startup."))

    @role.command(brief="Distribute role permissions so that they all have the same permissions as the default role.")
    @discord.ext.commands.has_permissions(manage_roles=True)
    @discord.ext.commands.guild_only()
    async def distribute(self, ctx: discord.ext.commands.Context):
        default = ctx.guild.default_role.permissions.value
        for role in ctx.guild.roles:
            perms = role.permissions.value
            new_perms = discord.Permissions(perms | default)
            if new_perms.value != perms:
                logger.info("Copied perms from @everyone onto %s role", role)
                try:
                    await role.edit(permissions=new_perms, reason="Copying permissions from @everyone")
                except discord.Forbidden:
                    logger.warning("Bot unable to edit any roles from here on out.")
                    embed = Embed(ctx, color=discord.Color.red(), title="Unable to edit Role",
                                  description="The bot is unable to edit the role due to permissions.")
                    embed.add_field(name="Role", value=role.mention)
                    await ctx.send(embed=embed)
                    break
                else:
                    embed = Embed(ctx, color=discord.Color.green(), description="The role was updated to have the same permissions as @everyone.",
                                  title="Role Updated")
                    embed.add_field(name="Role", value=role.mention)
                    await ctx.send(embed=embed)


def setup(bot: "PokestarBot"):
    bot.add_cog(Roles(bot))
    logger.info("Loaded the Roles extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Roles extension.")
