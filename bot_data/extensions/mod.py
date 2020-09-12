import asyncio
import inspect
import itertools
import logging
from typing import TYPE_CHECKING, Union

import discord.ext.commands

from . import PokestarBotCog
from ..converters import AllConverter, MemberRolesConverter
from ..utils import Embed, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Mod(PokestarBotCog):

    @discord.ext.commands.command(brief="Mass move users to a voice channel", usage="voice_channel_name member [member] [member] ...")
    @discord.ext.commands.guild_only()
    async def move(self, ctx: discord.ext.commands.Context, channel: discord.VoiceChannel,
                   *users: Union[AllConverter, MemberRolesConverter, discord.VoiceChannel]):
        success = []
        fail = []
        full_users = []
        if not users:
            return await ctx.send(embed=Embed(ctx, color=discord.Color.red(), title="No Users Specified",
                                              description="You need to specify a user, role, voice channel, or `all` (pull out of all voice "
                                                          "channels into the current channel) to move into the given voice channel."))
        for user in users:
            if isinstance(user, discord.VoiceChannel):
                full_users.extend(user.members)
            elif user == AllConverter.All:
                for voice_channel in ctx.guild.voice_channels:
                    if voice_channel == channel:
                        break
                    voice_channel: discord.VoiceChannel
                    full_users.extend(voice_channel.members)
            else:
                full_users.extend(user)
        full_users = set(full_users)
        for user in full_users:
            try:
                logger.debug("Moving %s to %s", user, channel)
                await user.move_to(channel, reason="Mass Move requested by {}".format(ctx.author))
            except discord.DiscordException:
                fail.append(user)
            else:
                success.append(user)
        embed = Embed(ctx, title="Voice Channel Mass Move", color=discord.Color.green())
        fields = [("Moved To Voice Channel", str(channel)), ("User That Requested Move", ctx.author.mention),
                  ("Successfully Moved", "\n".join(user.mention for user in success) or "None"),
                  ("Failed To Move", "\n".join(user.mention for user in fail) or "None")]
        if fail:
            logger.warning("Unable to move these users to %s: %s", channel, ", ".join(user.mention for user in fail))
        await send_embeds_fields(ctx, embed, fields)

    @discord.ext.commands.command(brief="Kick all users that belong to a Role (very dangerous)", usage="user_or_role [user_or_role] [...]")
    @discord.ext.commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx: discord.ext.commands.Context, *member_roles: MemberRolesConverter):
        if len(member_roles) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("user_or_role", kind=inspect.Parameter.POSITIONAL_ONLY))
        members = list(itertools.chain(*member_roles))
        fields = []
        mentions = []
        for member in members:
            mentions.append(member.mention)
        fields.append(("Users To Be Kicked", "\n".join(mentions) or "None"))
        embed = Embed(ctx, title="Kicking Users",
                      description="This actions is *irreversible*. Send `cancel` to cancel in 5 seconds. Only starting user can cancel.",
                      color=discord.Color.red())
        await send_embeds_fields(ctx, embed, fields)

        def check(message: discord.Message) -> bool:
            return message.author == ctx.author and message.content.lower() == "cancel" and message.channel == ctx.channel

        try:
            await self.bot.wait_for("message", check=check, timeout=5)
        except asyncio.TimeoutError:
            for member in members:
                guild: discord.Guild = ctx.guild
                await guild.kick(member, reason=f"Mass Kick by {ctx.author}")
            return await ctx.send(
                embed=Embed(ctx, title="Kicked", description="All members specified have been kicked..", color=discord.Color.green()))
        else:
            return await ctx.send(embed=Embed(ctx, title="Kick Canceled", description="The kick has been canceled.", color=discord.Color.green()))

    @discord.ext.commands.command(brief="Mute all members in a voice channel (except the exceptions provided)",
                                  usage="voice_channel [exception] [exception]")
    @discord.ext.commands.has_guild_permissions(mute_members=True)
    async def mute(self, ctx: discord.ext.commands.Context, voice_channel: discord.VoiceChannel, *exceptions: MemberRolesConverter):
        exception_members = list(itertools.chain(*exceptions))
        to_mute = [member for member in voice_channel.members if member not in exception_members]
        await ctx.trigger_typing()
        for member in to_mute:
            member: discord.Member
            await member.edit(mute=True, reason=f"Mass Mute by {ctx.author}")
        embed = Embed(ctx, title="Muted Users", description="The following users (minus exceptions) were muted.", color=discord.Color.green())
        fields = [("Muted", "\n".join(user.mention for user in to_mute) or "None"),
                  ("Exceptions", "\n".join(user.mention for user in exceptions) or "None")]
        await send_embeds_fields(ctx, embed, fields)

    @discord.ext.commands.command(brief="Deafen all members in a voice channel (except the exceptions provided)",
                                  usage="voice_channel [exception] [exception]")
    @discord.ext.commands.has_guild_permissions(deafen_members=True)
    async def deafen(self, ctx: discord.ext.commands.Context, voice_channel: discord.VoiceChannel, *exceptions: MemberRolesConverter):
        exception_members = list(itertools.chain(*exceptions))
        to_deafen = [member for member in voice_channel.members if member not in exception_members]
        await ctx.trigger_typing()
        for member in to_deafen:
            member: discord.Member
            await member.edit(deafen=True, reason=f"Mass Deafen by {ctx.author}")
        embed = Embed(ctx, title="Deafened Users", description="The following users (minus exceptions) were deafened.", color=discord.Color.green())
        fields = [("Deafened", "\n".join(user.mention for user in to_deafen) or "None"),
                  ("Exceptions", "\n".join(user.mention for user in exceptions) or "None")]
        await send_embeds_fields(ctx, embed, fields)

    @discord.ext.commands.command(brief="Unmute all members in a voice channel (except the exceptions provided)",
                                  usage="voice_channel [exception] [exception]")
    @discord.ext.commands.has_guild_permissions(mute_members=True)
    async def unmute(self, ctx: discord.ext.commands.Context, voice_channel: discord.VoiceChannel, *exceptions: MemberRolesConverter):
        exception_members = list(itertools.chain(*exceptions))
        to_mute = [member for member in voice_channel.members if member not in exception_members]
        await ctx.trigger_typing()
        for member in to_mute:
            member: discord.Member
            await member.edit(mute=False, reason=f"Mass Unmute by {ctx.author}")
        embed = Embed(ctx, title="Unmuted Users", description="The following users (minus exceptions) were unmuted.", color=discord.Color.green())
        fields = [("Unmuted", "\n".join(user.mention for user in to_mute) or "None"),
                  ("Exceptions", "\n".join(user.mention for user in exceptions) or "None")]
        await send_embeds_fields(ctx, embed, fields)

    @discord.ext.commands.command(brief="Undeafen all members in a voice channel (except the exceptions provided)",
                                  usage="voice_channel [exception] [exception]")
    @discord.ext.commands.has_guild_permissions(deafen_members=True)
    async def undeafen(self, ctx: discord.ext.commands.Context, voice_channel: discord.VoiceChannel, *exceptions: MemberRolesConverter):
        exception_members = list(itertools.chain(*exceptions))
        to_deafen = [member for member in voice_channel.members if member not in exception_members]
        await ctx.trigger_typing()
        for member in to_deafen:
            member: discord.Member
            await member.edit(deafen=False, reason=f"Mass Undeafen by {ctx.author}")
        embed = Embed(ctx, title="Undeafened Users", description="The following users (minus exceptions) were undeafened.",
                      color=discord.Color.green())
        fields = [("Undeafened", "\n".join(user.mention for user in to_deafen) or "None"),
                  ("Exceptions", "\n".join(user.mention for user in exceptions) or "None")]
        await send_embeds_fields(ctx, embed, fields)


def setup(bot: "PokestarBot"):
    bot.add_cog(Mod(bot))
    logger.info("Loaded the Mod extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Mod extension.")
