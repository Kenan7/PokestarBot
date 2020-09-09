import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Union

import discord.ext.commands

from bot_data.converters import MemberConverter
from . import PokestarBotCog
from ..utils import Embed

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Templates(PokestarBotCog):

    @discord.ext.commands.command(brief="Add text to a image of a girl getting bad grades", usage="text",
                                  aliases=["badgrade", "badgrades", "bad_grade"])
    async def bad_grades(self, ctx: discord.ext.commands.Context, *, message: str = None):
        """Add text to a image of a cheerful anime girl about to go get a bad grade."""
        await self.reaction_base("https://i.imgur.com/Eunb07U.jpg", ctx, message)

    async def bad_collegeboard(self, ctx: discord.ext.commands.Context, test_type: str, name: Union[str, discord.Member]):
        msg = "{} logging into CollegeBoard to see his {} Scores, {} Colorized".format(name.mention if isinstance(name, discord.Member) else name,
                                                                                       test_type, datetime.now().year)
        await self.bad_grades(ctx, message=msg)

    @discord.ext.commands.command(brief="Pre-filled bad_grades command for the AP tests.", usage="name_or_username", aliases=["badap"])
    async def bad_ap(self, ctx: discord.ext.commands.Context, *, name: MemberConverter):
        await self.bad_collegeboard(ctx, "AP", name)

    @discord.ext.commands.command(brief="Pre-filled bad_grades command for the SAT test.", usage="name_or_username", aliases=["badsat"])
    async def bad_sat(self, ctx: discord.ext.commands.Context, *, name: MemberConverter):
        await self.bad_collegeboard(ctx, "SAT", name)

    @staticmethod
    async def reaction_base(url: str, ctx: discord.abc.Messageable, text: Optional[str] = None):
        await ctx.trigger_typing()
        embed = Embed(ctx, description=text or discord.Embed.Empty)
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Share the image of a pillow captioned \"damm\"", usage="[text]", enabled=False)
    async def damm(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/pRy0S6D.jpg", ctx, text)

    @discord.ext.commands.command(brief="Share the image of a pillow captioned \"eh\"", usage="[text]", enabled=False)
    async def eh(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/nOgTAwx.jpg", ctx, text)

    @discord.ext.commands.command(brief="Share the image of a pillow captioned \"let my soul frickin ascend\"", usage="[text]", enabled=False)
    async def ascend(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/jpFC9bu.jpg", ctx, text)

    @discord.ext.commands.command(brief="Share the image of a pillow captioned \"yeah, it be that way sometimes\"", usage="[text]",
                                  aliases=["bethatway"], enabled=False)
    async def be_that_way(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/Zm3KCeW.jpg", ctx, text)

    @discord.ext.commands.command(brief="Share the image of a pillow captioned \"I'm listening...\"", usage="[text]", enabled=False)
    async def listening(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/IC6QXLo.jpg", ctx, text)

    @discord.ext.commands.command(brief="Share the image of an anime girl holding a sign saying \"lol wut\"", usage="[text]", aliases=["lolwut"],
                                  enabled=False)
    async def lol_wut(self, ctx: discord.ext.commands.Context, *, text: str = None):
        await self.reaction_base("https://i.imgur.com/TMe7rXT.jpg", ctx, text)


def setup(bot: "PokestarBot"):
    bot.add_cog(Templates(bot))
    logger.info("Loaded the Templates extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Templates extension.")
