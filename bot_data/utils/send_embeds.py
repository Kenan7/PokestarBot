import copy
import datetime
from typing import Callable, List, Tuple, Union

import discord.ext.commands

from .embed import Embed
from .sort_long_lines import break_into_groups


async def send_embeds(ctx: discord.abc.Messageable, embed: discord.Embed, groups: List[str], *,
                      first_name: str = "\u200b",
                      timestamp: Union[datetime.datetime, type(discord.Embed.Empty)] = discord.Embed.Empty,
                      title: Union[str, type(discord.Embed.Empty)] = discord.Embed.Empty,
                      color: Union[discord.Color, type(discord.Embed.Empty)] = discord.Embed.Empty,
                      description: Union[str, type(discord.Embed.Empty)] = discord.Embed.Empty,
                      do_before_send: Callable[[discord.Embed], discord.Embed] = None):
    if not title:
        title = embed.title + " (continued)"
    first_loop = (6000 - len(embed)) // 1024
    first_groups = groups[:first_loop]
    groups = groups[first_loop:]
    messages = []
    embed.add_field(name=first_name, value=first_groups.pop(0), inline=False)
    for group in first_groups:
        embed.add_field(name="\u200b", value=group, inline=False)
    embed = do_before_send(embed) if do_before_send else embed
    messages.append(await ctx.send(embed=embed))
    while groups:
        batch = groups[:4]
        groups = groups[4:]
        embed = Embed(ctx, timestamp=timestamp, title=title, color=color, description=description)
        for group in batch:
            embed.add_field(name="\u200b", value=group, inline=False)
        embed = do_before_send(embed) if do_before_send else embed
        messages.append(await ctx.send(embed=embed))
    return messages


async def send_embeds_fields(ctx: discord.abc.Messageable, embed: discord.Embed, fields: List[Union[Tuple[str, str], str]], *,
                             field_name: str = "\u200b",
                             timestamp: Union[datetime.datetime, type(discord.Embed.Empty)] = discord.Embed.Empty,
                             title: Union[str, type(discord.Embed.Empty)] = discord.Embed.Empty,
                             color: Union[discord.Color, type(discord.Embed.Empty)] = discord.Embed.Empty,
                             description: Union[str, type(discord.Embed.Empty)] = discord.Embed.Empty,
                             heading: str = "", template: str = "", ending: str = "", line_template: str = "",
                             do_before_send: Callable[[discord.Embed], discord.Embed] = None, inline_fields: bool = True):
    for num, field in enumerate(fields.copy()):
        if not isinstance(field, tuple):
            fields[num] = (field_name, field)
    messages = []
    if not title:
        title = embed.title + " (continued)"
    if not color:
        color = embed.colour
    while fields:
        data = fields.pop(0)
        key, value = data
        key = str(key)
        value = str(value)
        groups = await break_into_groups(value, heading=heading, template=template, ending=ending, line_template=line_template)
        inline = inline_fields
        if len(groups) > 1:
            inline = False
        if (len(embed.fields) + len(groups)) <= 25:
            for num, value in enumerate(groups, start=1):
                new_embed = copy.deepcopy(embed)
                new_embed.add_field(name=key if num <= 1 else "\u200b", value=value, inline=inline)
                if len(new_embed) > 6000:
                    embed = do_before_send(embed) if do_before_send else embed
                    messages.append(await ctx.send(embed=embed))
                    embed = Embed(ctx, timestamp=timestamp, title=title, color=color, description=description)
                    embed.add_field(name=key if num <= 1 else "\u200b", value=value, inline=inline)
                else:
                    embed = new_embed
        else:
            if len(embed.fields) > 0:
                embed = do_before_send(embed) if do_before_send else embed
                messages.append(await ctx.send(embed=embed))
                embed = Embed(ctx, timestamp=timestamp, title=title, color=color, description=description)
            for num, value in enumerate(groups, start=1):
                new_embed = copy.deepcopy(embed)
                new_embed.add_field(name=key if num <= 1 else "\u200b", value=value, inline=inline)
                if len(new_embed) > 6000 or len(new_embed.fields) > 25:
                    embed = do_before_send(embed) if do_before_send else embed
                    messages.append(await ctx.send(embed=embed))
                    embed = Embed(ctx, timestamp=timestamp, title=title, color=color, description=description)
                    embed.add_field(name=key if num <= 1 else "\u200b", value=value, inline=inline)
                else:
                    embed = new_embed
    if len(embed.fields) > 0:
        embed = do_before_send(embed) if do_before_send else embed
        messages.append(await ctx.send(embed=embed))
    return messages
