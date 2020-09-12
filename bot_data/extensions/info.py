import inspect
import logging
from typing import TYPE_CHECKING, Union

import discord.ext.commands
import pytz

from . import PokestarBotCog
from ..utils import Embed, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)
NY = pytz.timezone("America/New_York")


class Info(PokestarBotCog):

    @discord.ext.commands.command(brief="Get the ID of a user", usage="[user] [...]", aliases=["userid", "userids", "user_ids"])
    async def user_id(self, ctx: discord.ext.commands.Context, *users: discord.Member):
        """Get a user's ID."""
        if len(users) < 1:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("user", kind=inspect.Parameter.POSITIONAL_ONLY))
        embed = Embed(ctx, title="Requested User IDs", description="Here are the requested User IDs.")
        await send_embeds_fields(ctx, embed, [(str(user), str(user.id)) for user in users], line_template="**{}**")

    @discord.ext.commands.command(brief="Get the ID of a channel", usage="[channel] [...]", aliases=["channelid", "channelids", "channel_ids"])
    @discord.ext.commands.guild_only()
    async def channel_id(self, ctx: discord.ext.commands.Context,
                         *channels: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]):
        if len(channels) < 1:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("channel", kind=inspect.Parameter.POSITIONAL_ONLY))
        embed = Embed(ctx, title="Requested Channel IDs", description="Here are the requested Channel IDs.")
        await send_embeds_fields(ctx, embed, [(str(channel), str(channel.id)) for channel in channels], line_template="**{}**")

    @discord.ext.commands.command(brief="Get info on users", usage="user [user] [...]", aliases=["userinfo"])
    @discord.ext.commands.guild_only()
    async def user_info(self, ctx: discord.ext.commands.Context, *users: discord.Member):
        if len(users) < 1:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("user", kind=inspect.Parameter.POSITIONAL_ONLY))
        for user in users:
            role: discord.Role = user.top_role
            flags: discord.PublicUserFlags = user.public_flags
            embed = Embed(ctx, color=role.colour, title=user.display_name)
            guild: discord.Guild = ctx.guild
            fields = [("Username", user.mention),
                      ("Created at", user.created_at.replace(tzinfo=pytz.UTC).astimezone(NY).strftime("%A, %B %d, %Y at %I:%M:%S %p"))]
            if user == guild.owner:
                fields.append(("Guild Owner", True))
            if user.guild_permissions.administrator:
                fields.append(("Administrator", True))
            if user.bot:
                if flags.verified_bot:
                    fields.append(("Verified Bot", True))
                else:
                    fields.append(("Bot", True))
            if flags.verified_bot_developer:
                fields.append(("Verified Bot Developer", True))
            if flags.staff:
                fields.append(("Discord Staff", True))
            if flags.partner:
                fields.append(("Discord Partner", True))
            if flags.hypesquad:
                fields.append(("Hypesquad Events Member", True))
            if flags.bug_hunter:
                fields.append(("Bug Hunter", True))
                if flags.bug_hunter_level_2:
                    fields.append(("Bug Hunter Level", 2))
                else:
                    fields.append(("Bug Hunter Level", 1))
            if not (flags.hypesquad_balance or flags.hypesquad_brilliance or flags.hypesquad_bravery):
                fields.append(("Hypesquad House", "None"))
            elif flags.hypesquad_balance:
                fields.append(("Hypesquad House", "Balance"))
            elif flags.hypesquad_brilliance:
                fields.append(("Hypesquad House", "Brilliance"))
            elif flags.hypesquad_bravery:
                fields.append(("Hypesquad House", "Bravery"))
            else:
                fields.append(("Hypesquad House", "None"))
            if flags.early_supporter:
                fields.append(("Early Supporter", True))
            if flags.team_user:
                fields.append(("Team User", True))
            if flags.system:
                fields.append(("Offical System User", True))
            roles = list(reversed(user.roles[1:]))
            fields.append((f"Roles **({len(roles)})**", "\n".join(map(lambda role: role.mention, roles))))
            await send_embeds_fields(ctx, embed, fields, do_before_send=lambda embed: embed.set_thumbnail(url=user.avatar_url_as(size=4096)))

    @discord.ext.commands.command(brief="Generate a link to a message with the message ID", usage="message_id [channel]")
    async def link(self, ctx: discord.ext.commands.Context, message: int, channel: discord.TextChannel = None):
        """Generate a link to a message given the message ID. The channel can be specified or it is assumed to be the current channel."""
        if channel is None:
            channel = ctx.channel
        embed = Embed(ctx, title="Message Link",
                      description="https://discord.com/channels/{}/{}/{}".format(ctx.guild.id if hasattr(ctx, "guild") else "@me", channel.id,
                                                                                 message))
        embed.add_field(name="Guild", value=(ctx.guild.mention if hasattr(ctx, "guild") else "Direct Messages"))
        embed.add_field(name="Channel", value=channel.mention)
        try:
            msg = await ctx.fetch_message(message)
            embed.add_field(name="Message Exists", value=str(True))
            content = msg.content
            if len(content) > 1000:
                content = "[Message Too Large]"
            elif not content:
                if msg.embeds:
                    content = "[Embed(s)]"
                else:
                    content = "[No Content]"
            embed.add_field(name="Message Content", value=content)
            embed.add_field(name="Author", value=msg.author.mention)
            embed.add_field(name="Message Sent At",
                            value=msg.created_at.replace(tzinfo=pytz.UTC).astimezone(NY).strftime("%A, %B %d, %Y at %I:%M:%S %p"))
        except discord.NotFound:
            embed.add_field(name="Message Exists", value=str(False))
        await ctx.send(embed=embed)


def setup(bot: "PokestarBot"):
    bot.add_cog(Info(bot))
    logger.info("Loaded the Info extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Info extension.")
