from typing import Optional, Tuple

import discord.ext.commands

from ..const import css_colors, discord_colors
from ..utils import get_key


class ColorConverter(discord.ext.commands.Converter):
    async def convert(self, ctx: discord.ext.commands.Converter, argument: str) -> Tuple[Optional[str], int]:
        argument = argument.lower()
        if argument.isnumeric():  # RGB color without the #
            argument = "#" + argument
        if argument.startswith("#"):  # RGB color
            if key := get_key(discord_colors, argument):
                return key, int(argument[1:], base=16)
            elif key := get_key(css_colors, argument):
                return key, int(argument[1:], base=16)
            else:
                return None, int(argument[1:], base=16)
        else:
            if argument in discord_colors:
                return argument, int(discord_colors[argument][1:], base=16)
            elif argument in css_colors:
                return argument, int(css_colors[argument][1:], base=16)
            else:
                raise discord.ext.commands.BadArgument(f"The color `{argument}` is not an RGB code nor a valid name for a color.")
