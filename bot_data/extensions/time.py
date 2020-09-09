import datetime
import logging
from typing import TYPE_CHECKING

import discord.ext.commands
import discord.ext.commands
import pytz

from . import PokestarBotCog
from ..utils import Embed, break_into_groups, send_embeds, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Time(PokestarBotCog):
    STRFTIME_FORMAT = "%A, %B %d, %Y @ %I:%M:%S %p"

    @discord.ext.commands.command(brief="Display the time in various timezones", usage="[timezone]")
    async def time(self, ctx: discord.ext.commands.Context, timezone: str = None):
        base_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        if timezone is None:
            logger.info("Requested default times.")
            timezones = ["America/New_York", "UTC", "Asia/Kolkata", "Asia/Dhaka"]
            fields = []
            for tz in timezones:
                tzobj = pytz.timezone(tz)
                fields.append((tz, base_time.astimezone(tzobj).strftime(self.STRFTIME_FORMAT)))
            embed = Embed(ctx, title="Current Time", description="Here is the current time in **{}** timezones.".format(len(timezones)))
            await send_embeds_fields(ctx, embed, fields)
        else:
            try:
                tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                embed = Embed(ctx, color=discord.Color.red(), title="Invalid Timezone",
                              description="The provided timezone does not exist. Please double check that the timezone exists by doing `{}"
                                          "timezones`.".format(self.bot.command_prefix))
                embed.add_field(name="Timezone", value=timezone)
                await ctx.send(embed=embed)
            else:
                logger.info("Requested time in %s", timezone)
                await ctx.send(embed=Embed(ctx, title="Current Time in **{}**".format(timezone),
                                           description=base_time.astimezone(tz).strftime(self.STRFTIME_FORMAT)))

    @discord.ext.commands.group(invoke_without_command=True, brief="Display the list of timezones", usage="[prefix]")
    async def timezones(self, ctx: discord.ext.commands.Context, prefix: str = None):
        if prefix is None:
            data = list(pytz.all_timezones)
            items = {}
            for tz in data:
                prefix, sep, suffix = tz.partition("/")
                if not sep:
                    prefix = "No Prefix"
                l = items.setdefault(prefix, [])
                l.append(tz)
            final_items = [(prefix, "\n".join(prefix_data)) for prefix, prefix_data in items.items()]
            embed = Embed(ctx, title="All Timezones", description="Here is the list of all timezones, delimited by prefix.")
            await send_embeds_fields(ctx, embed, final_items)
        else:
            data = list(filter(lambda _tz: _tz.startswith(prefix), pytz.all_timezones))
            if len(data) == 0:
                embed = Embed(ctx, color=discord.Color.red(), title="No Timezones Found",
                              description="There were no timezones found with the given prefix.")
                embed.add_field(name="Prefix", value=prefix)
                return await ctx.send(embed=embed)
            else:
                groups = await break_into_groups(template="", ending="", lines=data)
                embed = Embed(ctx, title="Timezones".format(prefix), description="Here is the list of timezones that contain this prefix.")
                embed.add_field(name="Prefix", value=prefix)
                await send_embeds(ctx, embed, groups)

    @timezones.command(brief="Get the list of prefixes")
    async def prefix(self, ctx: discord.ext.commands.Context):
        data = list({tz.partition("/")[0] for tz in pytz.all_timezones if tz.count("/") >= 1})
        embed = Embed(ctx, title="Prefixes",
                      description="Here is the list of timezones prefixes that can be used with the `{}timezones` command.".format(
                          self.bot.command_prefix))
        groups = await break_into_groups(template="", ending="", lines=data)
        await send_embeds(ctx, embed, groups)


def setup(bot: "PokestarBot"):
    bot.add_cog(Time(bot))
    logger.info("Loaded the Time extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Time extension.")
