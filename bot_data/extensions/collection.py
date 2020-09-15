import logging
from typing import TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Collection(PokestarBotCog):
    @discord.ext.commands.command(brief="Get Collections in the Collection archive (hard coded)", usage="[name]",
                                  aliases=["collectionarchive", "collection"], enabled=False)
    async def collection_archive(self, ctx: discord.ext.commands.Context, name: str = None):
        if name is None:
            embed = Embed(ctx, title="Archived Collections",
                          description="These Collections have been archived. Their contents can be viewed using `{}collection_archive <name>`, "
                                      "where `<name>` is the name of the Collection. The lowercase bolded word is the name, and the text underneath "
                                      "is its title.".format(
                              self.bot.command_prefix))
            embed.add_field(name="pillow", value="Mood Pillows")
            embed.add_field(name="kaguyaneko", value="Kaguya Characters With Cat Ears")
            await ctx.send(embed=embed)
        elif name not in ["pillow", "kaguyaneko"]:
            embed = Embed(ctx, title="Invalid Collection",
                          description="The specified Collection does not exist. View the Collections with `{}collection_archive`.".format(
                              self.bot.command_prefix), color=discord.Color.red())
            embed.add_field(name="Collection Name Provided", value=name)
            await ctx.send(embed=embed)
        elif name == "pillow":
            await ctx.send(embed=Embed(ctx, title="Mood Pillows", description="""1. Be that way sometimes: 
            https://cdn.discordapp.com/attachments/728757373459759237/734253669306073138/20200424_211221.jpg
2. damm: https://cdn.discordapp.com/attachments/729403691974656112/734369610190684250/damm.JPG
3. Eh: https://cdn.discordapp.com/attachments/729403691974656112/734369627169095740/eh.JPG"""))
        elif name == "kaguyaneko":
            await ctx.send(embed=Embed(ctx, title="Kaguya Characters With Cat Ears", description="""1. Kaguya and Shirogane: 
            https://www.pixiv.net/en/artworks/83088865#big_0
2. Chika: https://www.pixiv.net/en/artworks/83088865#big_1
3. Ishigami: https://www.pixiv.net/en/artworks/83088865#big_2
4. Miko: https://www.pixiv.net/en/artworks/83088865#big_3
5. Maki: https://www.pixiv.net/en/artworks/83088865#big_4
6. Kei: https://www.pixiv.net/en/artworks/83088865#big_5
7. Tsubame: https://www.pixiv.net/en/artworks/83088865#big_6
8. Kashiwagi: https://www.pixiv.net/en/artworks/83088865#big_7
9. Hayasaka: https://www.pixiv.net/en/artworks/83088865#big_8
10. Hayasaca-chan: https://www.pixiv.net/en/artworks/83088865#big_9
11. Hayasaca-kun: https://www.pixiv.net/en/artworks/83088865#big_10
12. Hayasaka (Shuchiin): https://www.pixiv.net/en/artworks/83088865#big_11"""))
        else:
            raise ValueError(name)


def setup(bot: "PokestarBot"):
    bot.add_cog(Collection(bot))
    logger.info("Loaded the Collection extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Collection extension.")
