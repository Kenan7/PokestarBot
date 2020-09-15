import inspect
import itertools
import logging
from typing import Collection, List, Optional, TYPE_CHECKING, Tuple, Union

import discord.ext.commands

from . import PokestarBotCog
from ..const import color_str_set, css_colors, discord_colors, role_template_role, user_template_role
from ..converters import ColorConverter, MemberRolesConverter, RolesConverter
from ..utils import Embed, rgb_string_from_int, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Roles(PokestarBotCog):
    USER_TEMPLATE = user_template_role
    ROLE_TEMPLATE = role_template_role
    DISCORD_COLORS = discord_colors
    CSS_COLORS = css_colors
    VALID_NAMES = list(DISCORD_COLORS) + list(CSS_COLORS)

    @classmethod
    def contains_color_roles(cls, item: Union[discord.Guild, discord.Member]):
        roles = []
        for role in item.roles:
            role: discord.Role
            name = str(role)
            if name in cls.VALID_NAMES or (len(name) == 7 and color_str_set.issuperset(set(name))):
                roles.append(role)
        return roles

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        self._last_operation_members = {}

    @discord.ext.commands.group(invoke_without_command=True,
                                brief="Deals with role management",
                                usage="subcommand [subcommand_arg_1] [subcommand_arg_2] [...]")
    @discord.ext.commands.guild_only()
    async def role(self, ctx: discord.ext.commands.Context):
        """Manage the roles of members in the Guild. This command itself does nothing, but instead has subcommands."""
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
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    async def add(self, ctx: discord.ext.commands.Context, role: discord.Role, *member_or_roles: MemberRolesConverter):
        """Add a role to all users that are part of the provided user(s) and role(s)."""
        members = list(itertools.chain(*member_or_roles))
        logger.info("Running a role addition operation on %s members with the %s role", len(members), role)
        self._last_operation_members["add"] = {"role": role, "members": members}
        await self._base(False, ctx, role, members)

    @role.command(brief="Create a role and assign members/roles to the created role",
                  usage="\"role_name\" [user_or_role_1] [user_or_role_2] [...]")
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
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
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
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
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    async def remove(self, ctx: discord.ext.commands.Context, role: discord.Role,
                     *member_or_roles: MemberRolesConverter):
        """Remove a role to all users that are part of the provided user(s) and role(s)."""
        members = list(itertools.chain(*member_or_roles))
        logger.info("Running a role removal operation on %s members with the %s role", len(members), role)
        self._last_operation_members["remove"] = {"role": role, "members": members}
        await self._base(True, ctx, role, members)

    @add.command(name="reverse", brief="Reverse the last mass role addition")
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
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
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
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
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
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

    async def pre_create(self):
        async with self.bot.conn.execute(
                """CREATE TABLE IF NOT EXISTS SNAPSHOTS(ID INTEGER PRIMARY KEY AUTOINCREMENT, GUILD_ID BIGINT NOT NULL, ROLE BOOLEAN NOT NULL 
                DEFAULT TRUE, KEY_ID BIGINT NOT NULL, VALUE_ID BIGINT NOT NULL, UNIQUE (GUILD_ID, KEY_ID, VALUE_ID))"""):
            pass

    async def add_user_snapshot(self, user: discord.Member):
        roles = user.roles[1:]
        async with self.bot.conn.execute("""DELETE FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                         [user.guild.id, user.id]), self.bot.conn.executemany(
            """INSERT INTO SNAPSHOTS(GUILD_ID, ROLE, KEY_ID, VALUE_ID) VALUES(?, ?, ?, ?)""",
            [(user.guild.id, False, user.id, role.id) for role in roles]):
            pass
        return roles

    async def add_role_snapshot(self, role: discord.Role):
        members = role.members
        async with self.bot.conn.execute("""DELETE FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                         [role.guild.id, role.id]), self.bot.conn.executemany(
            """INSERT INTO SNAPSHOTS(GUILD_ID, ROLE, KEY_ID, VALUE_ID) VALUES(?, ?, ?, ?)""",
            [(role.guild.id, True, role.id, member.id) for member in members]):
            pass
        return members

    @discord.ext.commands.group(brief="Manage the Role Snapshots system.", invoke_without_command=True, aliases=["role_snapshot", "rolesnapshot"])
    async def snapshot(self, ctx: discord.ext.commands.Context):
        await self.bot.generic_help(ctx)

    @snapshot.command(name="add", brief="Add a Role Snapshot.", usage="user_or_role")
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    async def snapshot_add(self, ctx: discord.ext.commands.Context, user_or_role: Union[discord.Member, discord.Role]):
        await self.pre_create()
        if isinstance(user_or_role, discord.Role):
            l_item_name = "Provided Role"
            r_item_name = "Members"
            r_item = await self.add_role_snapshot(user_or_role)
        else:
            l_item_name = "Provided Member"
            r_item_name = "Roles"
            r_item = await self.add_user_snapshot(user_or_role)
        embed = Embed(ctx, title="Snapshot Saved", description="The snapshot has been saved.", color=discord.Color.green())
        await send_embeds_fields(ctx, embed,
                                 [(l_item_name, user_or_role.mention), (r_item_name, "\n".join(item.mention for item in r_item) or "None")])

    @snapshot.command(name="list", brief="List all Guild Role Snapshots.", usage="[user_or_role]")
    async def snapshot_list(self, ctx: discord.ext.commands.Context, user_or_role: Optional[Union[discord.Member, discord.Role]] = None):
        await self.pre_create()
        if user_or_role is None:
            async with self.bot.conn.execute("""SELECT DISTINCT KEY_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND ROLE==TRUE""", [ctx.guild.id]) as cursor:
                role_ids = {role async for role, in cursor}
            async with self.bot.conn.execute("""SELECT DISTINCT KEY_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND ROLE==FALSE""", [ctx.guild.id]) as cursor:
                member_ids = {member async for member, in cursor}
            roles = [ctx.guild.get_role(role_id) for role_id in role_ids]
            members = [ctx.guild.get_member(member_id) for member_id in member_ids]
            embed = Embed(ctx, title="Role Snapshots For Current Guild")
            fields = [("Roles", "\n".join(role.mention if role else "[Deleted Role]" for role in roles) or "None"),
                      ("Members", "\n".join(member.mention if member else "[Not in Guild/Deleted User]" for member in members) or "None")]
            await send_embeds_fields(ctx, embed, fields)
        else:
            if isinstance(user_or_role, discord.Role):
                async with self.bot.conn.execute("""SELECT VALUE_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                                 [ctx.guild.id, user_or_role.id]) as cursor:
                    member_ids = {member async for member, in cursor}
                if len(member_ids) == 0:  # Not Found or Empty Snapshot
                    embed = Embed(ctx, title="Snapshot Not Found",
                                  description="The Snapshot for the provided role does not exist. This can also occur if a Snapshot was saved for a "
                                              "role that contained no users.",
                                  color=discord.Color.red())
                    embed.add_field(name="Role", value=user_or_role.mention)
                    return await ctx.send(embed=embed)
                members = [ctx.guild.get_member(member_id) for member_id in member_ids]
                embed = Embed(ctx, title="Snapshot", description=f"The Snapshot for role {user_or_role.mention} contains **{len(members)}** members.",
                              color=discord.Color.green())
                await send_embeds_fields(ctx, embed, ["\n".join(member.mention if member else "[Not in Guild/Deleted User]" for member in members)])
            else:
                async with self.bot.conn.execute("""SELECT VALUE_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                                 [ctx.guild.id, user_or_role.id]) as cursor:
                    role_ids = {role async for role, in cursor}
                if len(role_ids) == 0:  # Not Found or Empty Snapshot
                    embed = Embed(ctx, title="Snapshot Not Found",
                                  description="The Snapshot for the provided Member does not exist. This can also occur if a Snapshot was saved for "
                                              "a "
                                              "Member that contained no roles.",
                                  color=discord.Color.red())
                    embed.add_field(name="Member", value=user_or_role.mention)
                    return await ctx.send(embed=embed)
                roles = [ctx.guild.get_role(role_id) for role_id in role_ids]
                embed = Embed(ctx, title="Snapshot", description=f"The Snapshot for Member {user_or_role.mention} contains **{len(roles)}** roles.",
                              color=discord.Color.green())
                await send_embeds_fields(ctx, embed, ["\n".join(role.mention if role else "[Deleted Role]" for role in roles)])

    @snapshot.command(name="use", aliases=["release", "replay", "apply", "copy"], brief="Copy the members or roles in a Snapshot back to the guild.",
                      usage="user_or_role")
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    async def snapshot_use(self, ctx: discord.ext.commands.Context, user_or_role: Union[discord.Member, discord.Role]):
        await self.pre_create()
        if isinstance(user_or_role, discord.Role):
            async with self.bot.conn.execute("""SELECT VALUE_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                             [ctx.guild.id, user_or_role.id]) as cursor:
                member_ids = {member async for member, in cursor}
            if len(member_ids) == 0:  # Not Found or Empty Snapshot
                embed = Embed(ctx, title="Snapshot Not Found",
                              description="The Snapshot for the provided role does not exist. This can also occur if a Snapshot was saved for a "
                                          "role that contained no users.",
                              color=discord.Color.red())
                embed.add_field(name="Role", value=user_or_role.mention)
                return await ctx.send(embed=embed)
            members = [ctx.guild.get_member(member_id) for member_id in member_ids]
            failed = []
            success = []
            for member in members:
                member: Optional[discord.Member]
                if member:
                    try:
                        await member.add_roles(user_or_role, reason=f"Replaying of Snapshot for Role {user_or_role}")
                    except discord.Forbidden:
                        failed.append(member)
                    else:
                        success.append(member)
                else:
                    failed.append(member)
            embed = Embed(ctx, title="Snapshot Used",
                          description=f"The Snapshot for role {user_or_role.mention} was added to **{len(members)}** members.",
                          color=discord.Color.green())
            await send_embeds_fields(ctx, embed, [
                ("Succeeded", "\n".join(member.mention if member else "[Not in Guild/Deleted User]" for member in success) or None),
                ("Failed", "\n".join(member.mention if member else "[Not in Guild/Deleted User]" for member in failed) or None)])
        else:
            async with self.bot.conn.execute("""SELECT VALUE_ID FROM SNAPSHOTS WHERE GUILD_ID==? AND KEY_ID==?""",
                                             [ctx.guild.id, user_or_role.id]) as cursor:
                role_ids = {role async for role, in cursor}
            if len(role_ids) == 0:  # Not Found or Empty Snapshot
                embed = Embed(ctx, title="Snapshot Not Found",
                              description="The Snapshot for the provided Member does not exist. This can also occur if a Snapshot was saved for a "
                                          "Member that contained no roles.",
                              color=discord.Color.red())
                embed.add_field(name="Member", value=user_or_role.mention)
                return await ctx.send(embed=embed)
            roles = [ctx.guild.get_role(role_id) for role_id in role_ids]
            failed = []
            success = []
            for role in roles:
                if role:
                    try:
                        await user_or_role.add_roles(role, reason=f"Replaying of Snapshot for User {user_or_role}")
                    except discord.Forbidden:
                        failed.append(role)
                    else:
                        success.append(role)
                else:
                    failed.append(role)
            embed = Embed(ctx, title="Snapshot Used",
                          description=f"The Snapshot for Member {user_or_role.mention} was used to add **{len(roles)}** roles.",
                          color=discord.Color.green())
            await send_embeds_fields(ctx, embed, [("Succeeded", "\n".join(role.mention if role else "[Deleted Role]" for role in success) or None),
                                                  ("Failed", "\n".join(role.mention if role else "[Deleted Role]" for role in failed) or "None")])

    @snapshot.command(name="all", brief="Generate a Snapshot for all users and all roles.")
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    async def snapshot_all(self, ctx: discord.ext.commands.Context):
        await ctx.send(embed=Embed(ctx, title="Starting Generation Of All Snapshots.", color=discord.Color.green()))
        for member in ctx.guild.members:
            await self.snapshot_add(ctx, member)
        for role in ctx.guild.roles:
            await self.snapshot_add(ctx, role)
        await ctx.send(embed=Embed(ctx, title="Finished Generation Of All Snapshots.", color=discord.Color.green()))

    @discord.ext.commands.group(brief="Give yourself a role with the specified color", usage="[member] color", invoke_without_command=True)
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    async def color(self, ctx: discord.ext.commands.Context, member: Optional[discord.Member], color: ColorConverter):
        member = member or ctx.author
        if member != ctx.author:
            if not ctx.author.guild_permissions.manage_roles:
                raise discord.ext.commands.MissingPermissions(["manage_roles"])
        color: Tuple[Optional[str], int]
        if color[0]:
            search_str = color[0]
        else:
            search_str = rgb_string_from_int(color[1])
        existing_role = None
        for role in ctx.guild.roles:
            role: discord.Role
            if str(role) == search_str:
                existing_role = role
                break
        user_has_roles = self.contains_color_roles(member)
        if user_has_roles:
            embed = Embed(ctx, title="Removed Existing Roles", description="The existing color roles that the user had has been removed.",
                          color=discord.Color.green())
            embed.add_field(name="User", value=member.mention)
            await member.remove_roles(*(role for role in user_has_roles if role != existing_role), reason="Removing Duplicate Color Roles")
            await send_embeds_fields(ctx, embed, [("Role(s)", "\n".join(role.mention for role in user_has_roles if role != existing_role))])
        if existing_role:
            role = existing_role
            if existing_role in member.roles:
                embed = Embed(ctx, title="Already Has Role",
                              description=f"{member.mention} already has the color role, so they will not be assigned the role again.",
                              color=discord.Color.green())
                embed.add_field(name="Role", value=existing_role.mention)
                return await ctx.send(embed=embed)
            try:
                await member.add_roles(existing_role, reason=f"Assigning Color by {ctx.author}")
            except discord.Forbidden:
                embed = Embed(ctx, title="Cannot Assign",
                              description="The bot could not assign the role as the color role is higher than the bot's role.",
                              color=discord.Color.red())
                embed.add_field(name="Role", value=existing_role.mention)
                return await ctx.send(embed=embed)
        else:
            role = await ctx.guild.create_role(name=search_str, color=discord.Color(color[1]), permissions=ctx.guild.default_role.permissions,
                                               reason=f"Assigning Color by {ctx.author}")
            await member.add_roles(role, reason=f"Assigning Color by {ctx.author}")
        embed = Embed(ctx, title="Assigned Color Role", description=f"Assigned role to {member.mention}", color=discord.Color(color[1]))
        embed.add_field(name="Role", value=role.mention)
        await ctx.send(embed=embed)

    @color.group(name="list", brief="Get the color names that can be used.", invoke_without_command=True)
    async def color_list(self, ctx: discord.ext.commands.Context):
        discord_colors_str = "\n".join(f"{key}: {value}" for key, value in self.DISCORD_COLORS.items())
        css_colors_str = "\n".join(f"{key}: {value}" for key, value in self.CSS_COLORS.items())
        fields = [("Discord Colors", discord_colors_str), ("Other Colors", css_colors_str)]
        await send_embeds_fields(ctx, Embed(ctx, title="Valid Colors"), fields)

    @color_list.command(name="existing", brief="Get the list of color roles that currently exist on the server.")
    @discord.ext.commands.guild_only()
    async def color_existing(self, ctx: discord.ext.commands.Context):
        roles = self.contains_color_roles(ctx.guild)
        await send_embeds_fields(ctx, Embed(ctx, title="Existing Color Roles"), [("Count", str(len(roles))), (
            "Roles", "\n".join(f"{role}: {' '.join(member.mention for member in role.members) or 'No Members'}" for role in roles))])

    @color.command(name="info", brief="Get information about a color", usage="color [color] [...]")
    async def color_info(self, ctx: discord.ext.commands.Context, *colors: ColorConverter):
        if len(colors) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("color", inspect.Parameter.POSITIONAL_ONLY))
        for color in colors:
            color: Tuple[Optional[str], int]
            if color[0]:
                title = color[0]
                hex_str = rgb_string_from_int(color[1])
            else:
                title = hex_str = rgb_string_from_int(color[1])
            embed = Embed(ctx, title=title, color=discord.Color(color[1]))
            embed.add_field(name="Hex Value", value=hex_str)
            await ctx.send(embed=embed)

    @color.command(name="remove", brief="Remove your color role", usage="[member]")
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    async def color_remove(self, ctx: discord.ext.commands.Context, member: Optional[discord.Member]):
        member = member or ctx.author
        if member != ctx.author:
            if not ctx.author.guild_permissions.manage_roles:
                raise discord.ext.commands.MissingPermissions(["manage_roles"])
        user_has_roles = self.contains_color_roles(member)
        if user_has_roles:
            embed = Embed(ctx, title="Removed Existing Roles", description="The existing color roles that the user had has been removed.",
                          color=discord.Color.green())
            embed.add_field(name="User", value=member.mention)
            await member.remove_roles(*(role for role in user_has_roles), reason="Removing Duplicate Color Roles")
            await send_embeds_fields(ctx, embed, ["\n".join(role.mention for role in user_has_roles)])
        else:
            embed = Embed(ctx, title="Had No Roles", description="The user had no color roles.", color=discord.Color.green())
            embed.add_field(name="User", value=member.mention)
            await ctx.send(embed=embed)

    @color.command(name="clean", brief="Cleans all other roles of color.")
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    async def color_clean_all(self, ctx: discord.ext.commands.Context):
        roles = self.contains_color_roles(ctx.guild)
        cleaned = []
        for role in ctx.guild.roles:
            role: discord.Role
            if role not in roles and role.color != discord.Color.default():
                await role.edit(color=discord.Color.default(), reason="Cleaning all non-color roles of color.")
                cleaned.append(role)
        await send_embeds_fields(ctx, Embed(ctx, title="Cleaned Roles", description="All non-color roles are now cleaned of color.",
                                            color=discord.Color.green()), [("Roles Cleaned", "\n".join(role.mention for role in cleaned) or "None")])

    @color.command(name="prune", brief="Prunes all color roles that aren't being used.")
    @discord.ext.commands.bot_has_guild_permissions(manage_roles=True)
    @discord.ext.commands.has_guild_permissions(manage_roles=True)
    async def color_prune(self, ctx: discord.ext.commands.Context):
        roles = self.contains_color_roles(ctx.guild)
        cleaned = []
        for role in roles:
            if len(role.members) < 1:
                await role.delete(reason="Pruning Unused Roles")
                cleaned.append(role)
        await send_embeds_fields(ctx, Embed(ctx, title="Pruned Roles", description="All color roles without any members are now pruned.",
                                            color=discord.Color.green()),
                                 [("Roles Pruned", "\n".join(str(role) + " (" + role.mention + ")" for role in cleaned) or "None")])


def setup(bot: "PokestarBot"):
    bot.add_cog(Roles(bot))
    logger.info("Loaded the Roles extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Roles extension.")
