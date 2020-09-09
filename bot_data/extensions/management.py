import atexit
import logging
import os
import re
import signal
import sqlite3
import sys
from typing import Optional, TYPE_CHECKING, Union

import aiosqlite
import discord.ext.commands

from . import PokestarBotCog
from .. import base
from ..converters import AllConverter, MemberRolesConverter
from ..utils import Embed, break_into_groups, send_embeds, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Management(PokestarBotCog):
    log_line = re.compile(r"\((DEBUG|INFO|WARNING|ERROR|CRITICAL)\):")

    @discord.ext.commands.command(brief="Kill the bot")
    @discord.ext.commands.is_owner()
    async def kill(self, _ctx: discord.ext.commands.Context):
        logger.critical("Killing the bot with signal SIGINT.")
        os.kill(os.getpid(), signal.SIGINT)

    @discord.ext.commands.command(brief="Reload the bot with an UNIX exec command")
    @discord.ext.commands.is_owner()
    async def reload(self, _ctx: discord.ext.commands.Context):
        logger.critical("Reloading the bot.")
        await self.bot.close(self_initiated=True)
        atexit._run_exitfuncs()
        os.execvp(sys.executable, [sys.executable] + sys.argv)

    @discord.ext.commands.command(brief="Fetch bot logs.", usage="number")
    @discord.ext.commands.is_owner()
    async def logs(self, ctx: discord.ext.commands.Context, number: int = 20):
        with open(os.path.join(base, "bot.log"), "r", encoding="utf-8") as logfile:
            lines = logfile.read().splitlines(False)
        lines.reverse()
        send_lines = []
        counter = 0
        for line in lines:
            send_lines.append(line)
            if self.log_line.search(line):
                counter += 1
            if counter == number:
                break
        send_lines.reverse()
        groups = await break_into_groups("\n".join(send_lines), template="```\n")
        embed = Embed(ctx, title="Log Lines")
        embed.add_field(name="Amount Requested", value=str(number), inline=False)
        await send_embeds(ctx, embed, groups)

    @discord.ext.commands.command(brief="Resets the bot's permission overrides")
    @discord.ext.commands.has_guild_permissions(administrator=True)
    @discord.ext.commands.guild_only()
    async def reset_perms(self, ctx: discord.ext.commands.Context):
        channels = []
        for channel in ctx.guild.channels:
            channel: discord.abc.GuildChannel
            original_perms = channel.overwrites_for(ctx.me)
            perms = channel.overwrites_for(ctx.me)
            for perm_name, value in perms:
                perms.update(**{perm_name: None})
            if original_perms != perms:
                channels.append(channel.mention if isinstance(channel, discord.TextChannel) else str(channel))
            await channel.set_permissions(ctx.me, overwrite=perms, reason="Resetting channel overrides")
        embed = Embed(ctx, title="Permission Reset Successful", color=discord.Color.green(), description="The permission reset was successful.")
        embed.add_field(name="Number of Channels Reset", value=str(len(channels)))
        await send_embeds_fields(ctx, embed, [("Channels Reset", "\n".join(channels))])

    @discord.ext.commands.group(brief="Work with the guild-channel database", usage="subcommand", invoke_without_command=True)
    @discord.ext.commands.guild_only()
    async def channel(self, ctx: discord.ext.commands.Context):
        return await self.bot.generic_help(ctx)

    @channel.command(name="add", brief="Add channel to the guild-channel database", usage="name [channel]")
    @discord.ext.commands.has_guild_permissions(manage_channels=True)
    @discord.ext.commands.guild_only()
    async def channel_add(self, ctx: discord.ext.commands.Context, name: str, channel: Optional[discord.TextChannel] = None):
        if channel is None:
            channel = ctx.channel
        guild = ctx.guild
        try:
            async with self.bot.conn.execute("""INSERT INTO CHANNEL_DATA(GUILD_ID, CHANNEL_NAME, CHANNEL_ID) VALUES (?, ?, ?)""",
                                             [guild.id, name, channel.id]):
                pass
        except aiosqlite.IntegrityError:
            embed = Embed(ctx, title="Guild-Channel Mapping Already Exists", description="The channel name for this guild already exists.",
                          color=discord.Color.red())
            embed.add_field(name="Guild ID", value=str(guild.id))
            embed.add_field(name="Channel Name", value=name)
            embed.add_field(name="Channel", value=channel.mention)
            await ctx.send(embed=embed)
        else:
            embed = Embed(ctx, title="Guild-Channel Mapping Added", description="The channel name for this guild has been added.",
                          color=discord.Color.green())
            embed.add_field(name="Guild ID", value=str(guild.id))
            embed.add_field(name="Channel Name", value=name)
            embed.add_field(name="Channel", value=channel.mention)
            await ctx.send(embed=embed)
            if name == "message-goals":
                await self.bot.stats_working_on.wait()
                self.bot.stats_working_on.clear()
                await self.bot.get_guild_stats(ctx.guild)
                self.bot.stats_working_on.set()

    @channel.command(name="remove", brief="Delete the channel in the guild-channel database", usage="name", aliases=["delete"])
    @discord.ext.commands.has_guild_permissions(manage_channels=True)
    @discord.ext.commands.guild_only()
    async def channel_remove(self, ctx: discord.ext.commands.Context, name: str):
        guild = ctx.guild
        async with self.bot.conn.execute("""DELETE FROM CHANNEL_DATA WHERE GUILD_ID==? AND CHANNEL_NAME==?""", [guild.id, name]):
            pass
        embed = Embed(ctx, title="Guild-Channel Mapping Deleted", description="The channel name for this guild has been deleted.",
                      color=discord.Color.green())
        embed.add_field(name="Guild ID", value=str(guild.id))
        embed.add_field(name="Channel Name", value=name)
        await ctx.send(embed=embed)

    @channel.command(name="list", brief="Get the list of possible channels that a guild can contain.")
    @discord.ext.commands.guild_only()
    async def channel_list(self, ctx: discord.ext.commands.Context):
        async with self.bot.conn.execute("""SELECT DISTINCT CHANNEL_NAME FROM CHANNEL_DATA""") as cursor:
            data = await cursor.fetchall()
        names = {name for name, in data}
        embed = Embed(ctx, title="Channel List")
        await send_embeds_fields(ctx, embed, [("\u200B", "\n".join(names))], line_template="**{}**")

    @discord.ext.commands.group(brief="Disable a command (or subcommand) for the server", usage="command", invoke_without_command=True)
    @discord.ext.commands.has_guild_permissions(administrator=True)
    @discord.ext.commands.guild_only()
    async def disable(self, ctx: discord.ext.commands.Context, *, command: str):
        if command.startswith(self.bot.command_prefix):
            command = command[len(self.bot.command_prefix):]
        if command.startswith("enable"):
            return await ctx.send(embed=Embed(ctx, title="Cannot Disable the Enable command",
                                              description=f"The `{self.bot.command_prefix}enable` command cannot be disabled.",
                                              color=discord.Color.red()))
        command_obj = self.bot.get_command(command)
        if command_obj is None:
            embed = Embed(ctx, title="Command Does Not Exist", description="The provided command does not exist.", color=discord.Color.red())
            embed.add_field(name="Command", value=command)
            await ctx.send(embed=embed)
            return await ctx.send_help()
        try:
            async with self.bot.conn.execute("""INSERT INTO DISABLED_COMMANDS(GUILD_ID, COMMAND_NAME) VALUES (?, ?)""",
                                             [ctx.guild.id, command_obj.qualified_name]):
                pass
        except sqlite3.IntegrityError:
            embed = Embed(ctx, title="Command Already Disabled", description="The given command is already disabled for the Guild.",
                          color=discord.Color.red())
            embed.add_field(name="Command", value=command_obj.qualified_name)
            await ctx.send(embed=embed)
        else:
            embed = Embed(ctx, title="Command Disabled", description="The given command is disabled for the Guild.",
                          color=discord.Color.green())
            embed.add_field(name="Command", value=command_obj.qualified_name)
            await ctx.send(embed=embed)
            await self.bot.get_disabled_commands()

    @disable.command(name="list", brief="Get the list of disabled commands")
    @discord.ext.commands.guild_only()
    async def disable_commands(self, ctx: discord.ext.commands.Context):
        async with self.bot.conn.execute("""SELECT COMMAND_NAME FROM DISABLED_COMMANDS WHERE GUILD_ID==?""", [ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        names = [f"{self.bot.command_prefix}{name}" for name, in data]
        embed = Embed(ctx, title="Disabled Commands", color=discord.Color.green() if len(names) == 0 else discord.Color.red())
        await send_embeds_fields(ctx, embed, [("\u200B", "\n".join(names) or "None")])

    @discord.ext.commands.command(brief="Enable a command (or subcommand) for the server", usage="command")
    @discord.ext.commands.has_guild_permissions(administrator=True)
    @discord.ext.commands.guild_only()
    async def enable(self, ctx: discord.ext.commands.Context, *, command: str):
        command = self.bot.get_command(command)
        command_obj = self.bot.get_command(command)
        if command_obj is None:
            embed = Embed(ctx, title="Command Does Not Exist", description="The provided command does not exist.", color=discord.Color.red())
            embed.add_field(name="Command", value=command)
            await ctx.send(embed=embed)
            return await ctx.send_help()
        async with self.bot.conn.execute("""DELETE FROM DISABLED_COMMANDS WHERE GUILD_ID==? AND COMMAND_NAME==?""",
                                         [ctx.guild.id, command_obj.qualified_name]):
            pass
        embed = Embed(ctx, title="Command Enabled", description="The given command is enabled for the Guild.", color=discord.Color.green())
        embed.add_field(name="Command", value=command_obj.qualified_name)
        await ctx.send(embed=embed)
        await self.bot.get_disabled_commands()

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


def setup(bot: "PokestarBot"):
    bot.add_cog(Management(bot))
    logger.info("Loaded the Management extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Management extension.")
