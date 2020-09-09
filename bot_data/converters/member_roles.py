import logging
from typing import List, Optional, Union

import discord.ext.commands

logger = logging.getLogger(__name__)


class MemberRolesConverter(discord.ext.commands.Converter):
    async def _convert(self, ctx: discord.ext.commands.Context, argument: Union[
        str,  # Member ID as string
        # Role ID as string
        # Username#Discriminator
        # Nickname
        # Role Name
        # Role Number as string
        # Negation of any at the top
        int,  # User ID
        # Role ID
        # Role Number
        discord.Member,  # Member
        discord.Role  # Role
    ]) -> Optional[List[discord.Member]]:
        """Gets a list of member(s) that fall under the given user ID or role ID.

        The given data can be negated, so that everything **except** the user or role members are returned.

        Accepts:

        * Member ID (as a string or integer)

        * Role ID (as a string or integer)

        * A username in the form `Username#XXXX` where the X's represent the **discriminator**, the numbers that follow
        your username.

        * A role name

        * The role number. This is a list where the bottom-most role is Role #0 and the top-most role is the number of
        roles that exist minus 1. You can specify a negative number to reverse this order, but when doing so,
        the top-most role is #-1 instead of #-0.
        """
        try:
            member = await discord.ext.commands.MemberConverter().convert(ctx, argument)
        except discord.ext.commands.BadArgument:
            try:
                logger.debug("Argument %s not detected as a Member, checking for Role", argument)
                role = await discord.ext.commands.RoleConverter().convert(ctx, argument)
            except discord.ext.commands.BadArgument:
                if isinstance(argument, str):
                    if argument.isnumeric():
                        argument = int(argument)
                    else:
                        raise discord.ext.commands.BadArgument("Item `{}` did not represent a member or role.".format(argument))
                if isinstance(argument, int):
                    try:
                        logger.debug("Argument %s not detected as a Role, checking for position in guild roles.", argument)
                        return ctx.guild.roles[argument]
                    except KeyError:
                        raise discord.ext.commands.BadArgument("Item `{}` did not represent a member or role.".format(argument))
            else:
                return role
        else:
            return member

    async def convert(self, ctx: discord.ext.commands.Context, argument: str) -> List[discord.Member]:
        if argument[0] == "!":
            logger.debug("Argument %s detected as a negation, running a negation", argument)
            members = ctx.guild.members
            to_assign = await self.convert(ctx, argument[1:])
            return list(filter(lambda member: member not in to_assign, members))
        member_or_role = await self._convert(ctx, argument)
        if isinstance(member_or_role, discord.Member):
            return [member_or_role]
        elif isinstance(member_or_role, discord.Role):
            return member_or_role.members
        else:
            raise ValueError("Invalid type for member_or_role: {}, value: `{!r}`".format(type(member_or_role), member_or_role))
