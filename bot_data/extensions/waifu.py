import asyncio
import enum
import logging
import random
import sqlite3
import string
from typing import Callable, Iterable, Literal, Optional, TYPE_CHECKING, Tuple, Union

import aiosqlite
import discord.ext.commands

from . import PokestarBotCog
from ..utils import ConformingIterator, CustomContext, Embed, StopCommand, send_embeds_fields
from ..const import Status

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Waifu(PokestarBotCog):
    @property
    def conn(self):
        return self.bot.conn

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        self.guide_data = {}
        self.embed.add_check(self.bot.has_channel("bot-spam"))

    def log_and_run(self, /, sql: str, arguments: Optional[Iterable[Union[str, int, float, bool, None]]] = None, *,
                    method: Literal["execute", "executemany", "executescript", "execute_insert", "execute_fetchall"] = "execute"):
        meth: Callable[[str, Optional[Iterable[Union[str, int, float, bool, None]]]], aiosqlite.Cursor] = getattr(self.conn, method)
        logger.debug("Running %s query:\n%s\nArguments: %s", method, sql, arguments)
        return meth(sql, arguments)

    async def pre_create(self):
        async with self.log_and_run(
                """CREATE TABLE IF NOT EXISTS BRACKETS(ID INTEGER PRIMARY KEY AUTOINCREMENT, NAME TEXT NOT NULL UNIQUE, STATUS TINYINT DEFAULT %s, 
                GUILD_ID BIGINT NOT NULL )""" % int(
                    Status.OPEN)):
            pass
        async with self.log_and_run(
                """CREATE TABLE IF NOT EXISTS ALIASES(ALIAS TEXT PRIMARY KEY UNIQUE, NAME TEXT NOT NULL, unique(ALIAS, NAME))"""):
            pass
        async with self.log_and_run("""CREATE TABLE IF NOT EXISTS WAIFUS(ID INTEGER PRIMARY KEY AUTOINCREMENT, NAME TEXT NOT NULL UNIQUE, 
            DESCRIPTION TEXT NOT NULL, ANIME TEXT NOT NULL COLLATE NOCASE, IMAGE TEXT NOT NULL)"""):
            pass
        async with self.log_and_run(
                """CREATE TABLE IF NOT EXISTS VOTES(ID INTEGER PRIMARY KEY AUTOINCREMENT, USER_ID UNSIGNED BIG INT NOT NULL, BRACKET INTEGER NOT 
                NULL, 
                DIVISION INTEGER NOT NULL, CHOICE BOOLEAN NOT NULL, UNIQUE(USER_ID, BRACKET, DIVISION))"""):
            pass

    async def get_conn(self):
        await self.pre_create()
        return self.conn

    async def get_voting(self, guild_id: int):
        await self.get_conn()
        async with self.log_and_run("""SELECT ID FROM BRACKETS WHERE STATUS==? AND GUILD_ID==?""", [Status.VOTABLE, guild_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return None
        else:
            return data[0][0]

    @discord.ext.commands.group(brief="Main group for the Waifu Wars command", invoke_without_command=True, aliases=["ww", "waifuwar"],
                                usage="subcommand", significant=True)
    async def waifu_war(self, ctx: discord.ext.commands.Context):
        await self.bot.generic_help(ctx)

    @waifu_war.command(brief="Create a new bracket", usage="bracket_name", aliases=["createbracket", "cb"])
    @discord.ext.commands.is_owner()
    async def create_bracket(self, ctx: discord.ext.commands.Context, *, name: str):
        await self.get_conn()
        try:
            async with self.log_and_run("""INSERT INTO BRACKETS(NAME, GUILD_ID) VALUES (?, ?)""", [name, ctx.guild.id]) as cursor:
                cursor: aiosqlite.Cursor
                await cursor.execute("""SELECT ID FROM BRACKETS WHERE ID == (SELECT MAX(ID)  FROM BRACKETS);""")
                data = await cursor.fetchone()
                bracket_id = data[0]
        except sqlite3.IntegrityError:
            embed = Embed(ctx, title="Bracket Exists", color=discord.Color.red(), description="The bracket already exists.")
            async with self.log_and_run("""SELECT ID FROM BRACKETS WHERE NAME==?""", [name]) as cursor:
                data = await cursor.fetchone()
                bracket_id = data[0]
            fields = [("Existing Bracket ID", str(bracket_id))]
            await send_embeds_fields(ctx, embed, fields)
        else:
            async with self.log_and_run(
                    """CREATE TABLE IF NOT EXISTS BRACKET_%s(ID INTEGER PRIMARY KEY AUTOINCREMENT, NAME TEXT NOT NULL UNIQUE)""" % bracket_id):
                pass
            embed = Embed(ctx, title="Bracket Created", description="The bracket has been created.", color=discord.Color.green())
            fields = [("ID", str(bracket_id)), ("Name", name)]
            await send_embeds_fields(ctx, embed, fields)
            return bracket_id

    async def id_does_not_exist(self, ctx: discord.ext.commands.Context, bracket_id: int):
        embed = Embed(ctx, title="Bracket Does Not Exist",
                      description="The provided bracket does not exist. Use `{}waifu_war brackets` to view the existing brackets.".format(
                          self.bot.command_prefix), color=discord.Color.red())
        embed.add_field(name="Bracket ID", value=str(bracket_id))
        await ctx.send(embed=embed)

    async def needs_bracket(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int]):
        if bracket_id is None:
            await ctx.send(embed=Embed(ctx, title="Bracket ID needed", description="A bracket ID needs to be specified.", color=discord.Color.red()))
            raise StopCommand

    @waifu_war.command(brief="Get information on a bracket.", usage="bracket_id", aliases=["getbracket", "gb", "b", "get_bracket"], significant=True)
    async def bracket(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int] = None):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        await self.needs_bracket(ctx, bracket_id)
        async with self.log_and_run("""SELECT NAME, STATUS FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return await self.id_does_not_exist(ctx, bracket_id)
        name, status = data[0]
        embed = Embed(ctx, title=name)
        embed.add_field(name="Bracket ID", value=str(bracket_id))
        embed.add_field(name="Status", value=Status(status).name.title())
        async with self.log_and_run(
                """SELECT BRACKET_{0}.ID, WAIFUS.NAME, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = WAIFUS.NAME""".format(
                    bracket_id)) as cursor:
            data = await cursor.fetchall()
        lines = []
        for waifu_id, name, anime, image in data:
            lines.append(f"**{waifu_id}**: [{name} (*{anime}*)]({image})")
        await send_embeds_fields(ctx, embed, [("Waifus", "\n".join(lines) or "None")])

    async def no_brackets_exist(self, ctx: discord.ext.commands.Context, state: int):
        embed = Embed(ctx, title="No Brackets", description="No brackets exist for the given state.", color=discord.Color.red())
        embed.add_field(name="State", value=str(Status(state)))
        return await ctx.send(embed=embed)



    @waifu_war.command(brief="Get information on all brackets.", usage="[state]", aliases=["getbrackets", "gbs", "bs", "get_brackets"], enabled=False)
    async def brackets(self, ctx: discord.ext.commands.Context, state: int = 2):
        await self.get_conn()
        try:
            Status(state)
        except ValueError:
            embed = Embed(ctx, title="Invalid State", description="The provided state was invalid.", color=discord.Color.red())
            embed.add_field(name="State", value=str(state))
            embed.add_field(name="Valid States", value="\n".join(f"{enum_state.name}: **{enum_state.value}**" for enum_state in Status))
            await ctx.send(embed=embed)
        else:
            if state == Status.ALL:
                async with self.log_and_run("SELECT ID, NAME, STATUS FROM BRACKETS WHERE GUILD_ID==?", [ctx.guild.id]) as cursor:
                    data = await cursor.fetchall()
                if len(data) == 0:
                    return await self.no_brackets_exist(ctx, 0)
                embed = Embed(ctx, title="Brackets", description="Here are the brackets for the given state.")
                fields = []
                for bracket_id, name, status in data:
                    fields.append((f"{name} (**{Status(status).title()}**)", f"Bracket ID **{bracket_id}**"))
                await send_embeds_fields(ctx, embed, fields)
            else:
                async with self.log_and_run("SELECT ID, NAME FROM BRACKETS WHERE STATUS == ? AND GUILD_ID==?", [state, ctx.guild.id]) as cursor:
                    data = await cursor.fetchall()
                if len(data) == 0:
                    return await self.no_brackets_exist(ctx, state)
                else:
                    embed = Embed(ctx, title="Brackets", description="Here are the brackets for the given state.")
                    embed.add_field(name="State", value=str(Status(state)))
                    fields = []
                    for bracket_id, name in data:
                        fields.append((name, f"Bracket ID **{bracket_id}**"))
                    await send_embeds_fields(ctx, embed, fields)

    async def bracket_exists(self, ctx: discord.ext.commands.Context, bracket_id: int):
        async with self.log_and_run("""SELECT NAME, STATUS FROM BRACKETS WHERE ID==? AND GUILD_ID==?""", [bracket_id, ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            await self.id_does_not_exist(ctx, bracket_id)
            raise StopCommand
        else:
            return data

    @waifu_war.command(brief="Get the different animes in the bracket", usage="bracket_id", aliases=["getanimes", "get_animes", "as"], enabled=False)
    async def animes(self, ctx: discord.ext.commands.Context, bracket_id: int):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        await self.bracket_exists(ctx, bracket_id)
        data = self.bracket_exists(ctx, bracket_id)
        name, status = data[0]
        embed = Embed(ctx, title=name)
        embed.add_field(name="Bracket ID", value=str(bracket_id))
        embed.add_field(name="Status", value=Status(status).name.title())
        try:
            async with self.log_and_run(
                    "SELECT ANIME FROM WAIFUS INNER JOIN BRACKET_{0} ON BRACKET_{0}.NAME = WAIFUS.NAME".format(bracket_id)) as cursor:
                data = await cursor.fetchall()
        except sqlite3.OperationalError:
            logger.warning("", exc_info=True)
            return await self.id_does_not_exist(ctx, bracket_id)
        lines = []
        for anime in sorted({item for item, in data}):
            lines.append(f"*{anime}*")
        await send_embeds_fields(ctx, embed, [("Animes", "\n".join(lines) or "None")])

    @waifu_war.command(brief="Get the a division in the bracket", usage="[bracket_id] division_id",
                       aliases=["getdivision", "get_division", "gd", "d"], significant=True)
    async def division(self, ctx: discord.ext.commands.Context, id1: int, id2: Optional[int] = None, *_, _continue=False, _send=True):
        await self.get_conn()
        if id2 is not None:
            bracket_id = id1
            division_id = id2
        else:
            bracket_id = await self.get_voting(ctx.guild.id)
            await self.needs_bracket(ctx, bracket_id)
            division_id = id1
        try:
            async with self.log_and_run("""SELECT COUNT(*) FROM BRACKET_{0}""".format(bracket_id)) as cursor:
                data = await cursor.fetchone()
        except sqlite3.OperationalError:
            logger.warning("", exc_info=True)
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            divisions = data[0] // 2
            if division_id == (divisions + 1):
                return await ctx.send(
                    embed=Embed(ctx, title="Waifu War is complete!", description="You have completed the waifu war bracket! You can now stop voting.",
                                color=discord.Color.green()))
            elif division_id > divisions:
                embed = Embed(ctx, title="Divsion too high",
                              description="The specified division is higher than the highest possibile division. Use `{}waifu_war divisions {}` to "
                                          "check the divisions.".format(
                                  self.bot.command_prefix, bracket_id), color=discord.Color.red())
                embed.add_field(name="Highest Division", value=str(divisions))
                embed.add_field(name="Requested Division", value=str(division_id))
                return await ctx.send(embed=embed)
            else:
                async with self.log_and_run("""SELECT COUNT(*) FROM VOTES WHERE USER_ID==?""", [ctx.author.id]) as cursor:
                    data = (await cursor.fetchone())[0]
                if data == 0 and not _continue and ctx.author.id not in self.guide_data:
                    embed = Embed(ctx, title="Start Guide",
                                  description="You have never voted using the waifu war system. It is recommended that you start the guide. Click "
                                              "the **:white_check_mark:** to begin. However, if you know what you're doing, "
                                              "click the **:no_entry_sign:** to continue.")
                    fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division_id))]
                    messages = await send_embeds_fields(ctx, embed, fields)
                    msg = messages[0]
                    await msg.add_reaction("✅")
                    await msg.add_reaction("🚫")
                    return
                async with self.log_and_run("""SELECT A.ID,A.NAME, 
                        C.ANIME,C.DESCRIPTION,C.IMAGE,B.ID,B.NAME,D.ANIME, D.DESCRIPTION,D.IMAGE FROM (SELECT A.ID, A.NAME FROM BRACKET_{0} A WHERE 
                        A.ID % 2 == 1) AS A JOIN (SELECT B.ID, B.NAME FROM BRACKET_{0} B WHERE B.ID % 2 == 0) AS B ON (CAST((A.ID - 1) / 2 AS 
                        INTEGER) == CAST((B.ID - 1) / 2 AS INTEGER)) JOIN WAIFUS C ON A.NAME == C.NAME JOIN WAIFUS D ON B.NAME == D.NAME WHERE 
                        CAST((B.ID + 1) / 2 AS INTEGER) == ?""".format(bracket_id), [division_id]) as cursor:
                    data = await cursor.fetchone()
                async with self.log_and_run("""SELECT COUNT(*) FROM VOTES WHERE BRACKET==? AND DIVISION==? AND CHOICE==1""",
                                            [bracket_id, division_id]) as cursor:
                    data_left = (await cursor.fetchone())[0]
                async with self.log_and_run("""SELECT COUNT(*) FROM VOTES WHERE BRACKET==? AND DIVISION==? AND CHOICE==0""",
                                            [bracket_id, division_id]) as cursor:
                    data_right = (await cursor.fetchone())[0]
                embed = Embed(ctx, title=f"Division **{division_id}**")
                l_id, l_name, l_anime, l_description, l_image_link, r_id, r_name, r_anime, r_description, r_image_link = data
                fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division_id)),
                          ("Contenders",
                           f"[{l_name} (*{l_anime}*)]({l_image_link}) (Waifu ID **{l_id}**)\n[{r_name} (*{r_anime}*)]({r_image_link}) (Waifu ID **"
                           f"{r_id}**)"),
                          (f"Votes for {l_name}", str(data_left)), (f"Votes for {r_name}", str(data_right))]
                if not _send:
                    return l_name, l_anime, l_description, l_image_link, int(data_left), r_name, r_anime, r_description, r_image_link, int(data_right)
                messages = await send_embeds_fields(ctx, embed, fields)
                msg = messages[0]
                await msg.add_reaction("⬅️")
                await msg.add_reaction("ℹ️")
                await msg.add_reaction("🚫")
                await msg.add_reaction("🇮")
                await msg.add_reaction("➡️")
                guide_val = self.guide_data.get(ctx.author.id, 0)
                if guide_val == 1:
                    await self.guide_step_2(ctx)
                elif guide_val == 4:
                    await self.guide_step_5(ctx)
                return l_name, int(data_left), r_name, int(data_right)

    @waifu_war.command(brief="Get the different divisions in the bracket", usage="[bracket_id]",
                       aliases=["getdivisions", "get_divisions", "gds", "ds"])
    async def divisions(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int] = None):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        await self.needs_bracket(ctx, bracket_id)
        try:
            async with self.log_and_run("""SELECT 
                    A.NAME,C.ANIME,C.DESCRIPTION,C.IMAGE,B.NAME,D.ANIME, D.DESCRIPTION,D.IMAGE FROM (SELECT A.ID, A.NAME FROM BRACKET_{0} A WHERE 
                    A.ID % 2 == 1) AS A JOIN (SELECT B.ID, B.NAME FROM BRACKET_{0} B WHERE B.ID % 2 == 0) AS B ON (CAST((A.ID - 1) / 2 AS INTEGER) == 
                    CAST((B.ID - 1) / 2 AS INTEGER)) JOIN WAIFUS C ON A.NAME == C.NAME JOIN WAIFUS D ON B.NAME == D.NAME""".format(
                bracket_id)) as cursor:
                data = await cursor.fetchall()
        except sqlite3.OperationalError:
            logger.warning("", exc_info=True)
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            embed = Embed(ctx, title="Bracket Divisions",
                          description="A division is a matchup between two waifus. The waifu with more votes will move on while the waifu with less "
                                      "votes will lose.")
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            lines = []
            for division, item in enumerate(data, start=1):
                l_name, l_anime, l_description, l_image_link, r_name, r_anime, r_description, r_image_link = item
                lines.append(f"Division **{division}**: [{l_name} (*{l_anime}*)]({l_image_link}) ***v.*** [{r_name} (*{r_anime}*)]({r_image_link})")
            await send_embeds_fields(ctx, embed, [("Divisions", "\n".join(lines) or "None")])

    @waifu_war.command(brief="Get the characters of an anime in the bracket", usage="[bracket_id] anime_name",
                       aliases=["getanime", "get_anime", "a", "ga"], enabled=False)
    async def anime(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int] = None, *, anime_name: str):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        if bracket_id is not None:
            try:
                async with self.log_and_run(
                        "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = "
                        "WAIFUS.NAME WHERE ANIME LIKE '%'||?||'%'".format(bracket_id), [anime_name]) as cursor:
                    data = await cursor.fetchall()
            except sqlite3.OperationalError:
                logger.warning("", exc_info=True)
                return await self.id_does_not_exist(ctx, bracket_id)
            else:
                async with self.log_and_run(
                        """SELECT BRACKET_{0}.ID, BRACKET_{0}.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON 
                        BRACKET_{0}.NAME = WAIFUS.NAME INNER JOIN ALIASES on ALIASES.NAME = WAIFUS.ANIME WHERE ALIAS LIKE '%'||?||'%'""".format(
                            bracket_id), [anime_name]) as cursor:
                    data2 = await cursor.fetchall()
                    data.extend(data2)
                seen = []
                for item in data.copy():
                    waifu_id, name, description, anime, image_link = item
                    if waifu_id in seen:
                        data.remove(item)
                    else:
                        seen.append(waifu_id)
            animes = {anime for waifu_id, name, description, anime, image_link in data}
            if len(animes) < 1:
                embed = Embed(ctx, title="Anime Does Not Exist", description="The provided anime does not exist for the bracket.",
                              color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                embed.add_field(name="Anime Name", value=anime_name)
                return await ctx.send(embed=embed)
            elif len(animes) > 1:
                embed = Embed(ctx, title="Duplicate Animes", description="More than one anime matched the provided name.", color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                await send_embeds_fields(ctx, embed, [("Animes", "\n".join(f"*{anime}*" for anime in animes))])
            else:
                ids = [f"**{waifu_id}**: [{name}]({image_link})" for waifu_id, name, description, anime, image_link in data]
                awaifu_id, name, description, anime, image_link = data[0]
                async with self.log_and_run("""SELECT ALIAS FROM ALIASES WHERE NAME = ?""", [anime]) as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title=f"*{anime}*")
                fields = [("Waifu Bracket", str(bracket_id)), ("Aliases", "\n".join(f"*{alias}*" for alias, in data) or "None"),
                          ("Number of Waifus", str(len(ids))), ("Waifus", "\n".join(ids))]
                await send_embeds_fields(ctx, embed, fields)
        else:
            async with self.log_and_run("SELECT ID, NAME, DESCRIPTION, ANIME, IMAGE FROM WAIFUS  WHERE ANIME LIKE '%'||?||'%'",
                                        [anime_name]) as cursor:
                data = await cursor.fetchall()
            async with self.log_and_run(
                    """SELECT ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM WAIFUS INNER JOIN ALIASES on ALIASES.NAME = WAIFUS.ANIME WHERE ALIAS 
                    LIKE '%'||?||'%'""",
                    [anime_name]) as cursor:
                data2 = await cursor.fetchall()
                data.extend(data2)
            seen = []
            for item in data.copy():
                waifu_id, name, description, anime, image_link = item
                if waifu_id in seen:
                    data.remove(item)
                else:
                    seen.append(waifu_id)
            animes = {anime for waifu_id, name, description, anime, image_link in data}
            if len(animes) < 1:
                embed = Embed(ctx, title="Anime Does Not Exist", description="The provided anime does not exist.",
                              color=discord.Color.red())
                embed.add_field(name="Anime Name", value=anime_name)
                return await ctx.send(embed=embed)
            elif len(animes) > 1:
                embed = Embed(ctx, title="Duplicate Animes", description="More than one anime matched the provided name.", color=discord.Color.red())
                await send_embeds_fields(ctx, embed, [("Animes", "\n".join(f"*{anime}*" for anime in animes))])
            else:
                ids = [f"Global ID **{waifu_id}**: [{name}]({image_link})" for waifu_id, name, description, anime, image_link in data]
                awaifu_id, name, description, anime, image_link = data[0]
                async with self.log_and_run("""SELECT ALIAS FROM ALIASES WHERE NAME = ?""", [anime]) as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title=f"*{anime}*")
                fields = [("Aliases", "\n".join(f"*{alias}*" for alias, in data) or "None"), ("Number of Waifus", str(len(ids))),
                          ("Waifus", "\n".join(ids))]
                await send_embeds_fields(ctx, embed, fields)

    @staticmethod
    def score_word(phrase: str) -> int:
        count = 0
        for char in phrase:
            if char in string.ascii_uppercase:
                count += 1
        return count

    @waifu_war.command(brief="Normalize cases on the Anime field", aliases=["normalizecases", "normalizeanime", "normalize_cases", "na", "nc"], enabled=False)
    @discord.ext.commands.is_owner()
    async def normalize_anime(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        async with self.log_and_run("""SELECT ID, ANIME FROM WAIFUS ORDER BY ID""") as cursor:
            data = await cursor.fetchall()
        count_dict = {}
        for waifu_id, anime in data:
            anime: str
            score = self.score_word(anime)
            if anime in count_dict and self.score_word(count_dict[anime.lower()]) < score:
                count_dict[anime.lower()] = anime
            elif anime not in count_dict:
                count_dict[anime.lower()] = anime
        for anime_name in count_dict.values():
            async with self.log_and_run("""UPDATE WAIFUS SET ANIME=? WHERE ANIME=?""", [anime_name] * 2):
                pass
        await ctx.send(embed=Embed(ctx, title="Anime Names Normalized", description="Anime Names have been normalized.", color=discord.Color.green()))

    @waifu_war.command(brief="Get information on a waifu", usage="bracket_id waifu_id or waifu_name", aliases=["getwaifu", "w", "get_waifu"], significant=True)
    async def waifu(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int] = None, *, id_or_name: Union[int, str]):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        if bracket_id is not None:
            if isinstance(id_or_name, str):
                query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                        "WAIFUS.NAME WHERE WAIFUS.NAME LIKE '%'||?||'%'".format(bracket_id)
            else:
                query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                        "WAIFUS.NAME WHERE BRACKET_{0}.ID==?".format(bracket_id)
            try:
                async with self.log_and_run(query, [id_or_name]) as cursor:
                    data = await cursor.fetchall()
            except sqlite3.OperationalError:
                logger.warning("", exc_info=True)
                return await self.id_does_not_exist(ctx, bracket_id)
            if isinstance(id_or_name, str):
                async with self.log_and_run(
                        """SELECT BRACKET_{0}.ID, ALIASES.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN ALIASES on BRACKET_{0}.NAME = 
                        ALIASES.NAME INNER JOIN WAIFUS ON BRACKET_{0}.NAME = WAIFUS.NAME WHERE ALIAS LIKE '%'||?||'%'""".format(bracket_id),
                        [id_or_name]) as cursor:
                    data2 = await cursor.fetchall()
                data.extend(data2)
            seen = []
            for item in data.copy():
                waifu_id, name, description, anime, image_link = item
                if waifu_id in seen:
                    data.remove(item)
                else:
                    seen.append(waifu_id)
            if len(data) < 1:
                embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                              color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                if isinstance(id_or_name, str):
                    embed.add_field(name="Waifu Name", value=id_or_name)
                else:
                    embed.add_field(name="Bracket Waifu ID", value=str(id_or_name))
                return await ctx.send(embed=embed)
            elif len(data) > 1:
                ids = [f"**{waifu_id}**: [{name} (*{anime}*)]({image_link})" for waifu_id, name, description, anime, image_link in data]
                embed = Embed(ctx, title="Duplicate Named Waifus",
                              description="There are multiple waifus with the same name. Use an ID instead of a name to search for them. The "
                                          "bracket waifu IDs that share the same name have been provided.")
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                await send_embeds_fields(ctx, embed, [("IDs", "\n".join(str(id) for id in ids))])
            else:
                waifu_id, name, description, anime, image_link = data[0]
                async with self.log_and_run("""SELECT ALIAS FROM ALIASES WHERE NAME = ?""", [name]) as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title=name, description=description)
                embed.set_image(url=image_link)
                fields = [("Anime", anime), ("Bracket Waifu ID", str(waifu_id)), ("Waifu Bracket", str(bracket_id)),
                          ("Aliases", "\n".join(alias for alias, in data) or "None")]
                await send_embeds_fields(ctx, embed, fields)
        else:
            if isinstance(id_or_name, str):
                query = "SELECT ID, NAME, DESCRIPTION, ANIME, IMAGE FROM WAIFUS WHERE NAME LIKE '%'||?||'%'".format(bracket_id)
            else:
                query = "SELECT ID, NAME, DESCRIPTION, ANIME, IMAGE FROM WAIFUS WHERE ID==?".format(bracket_id)
            async with self.log_and_run(query, [id_or_name]) as cursor:
                data = await cursor.fetchall()
            if isinstance(id_or_name, str):
                async with self.log_and_run(
                        """SELECT ID, ALIASES.NAME, DESCRIPTION, ANIME, IMAGE FROM WAIFUS INNER JOIN ALIASES on ALIASES.NAME = WAIFUS.NAME WHERE 
                        ALIAS LIKE '%'||?||'%'""", [id_or_name]) as cursor:
                    data2 = await cursor.fetchall()
                data.extend(data2)
            seen = []
            for item in data.copy():
                waifu_id, name, description, anime, image_link = item
                if waifu_id in seen:
                    data.remove(item)
                else:
                    seen.append(waifu_id)
            if len(data) < 1:
                embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                              color=discord.Color.red())
                if isinstance(id_or_name, str):
                    embed.add_field(name="Waifu Name", value=id_or_name)
                else:
                    embed.add_field(name="Global Waifu ID", value=str(id_or_name))
                return await ctx.send(embed=embed)
            elif len(data) > 1:
                ids = [f"**{waifu_id}**: [{name} (*{anime}*)]({image_link})" for waifu_id, name, description, anime, image_link in data]
                embed = Embed(ctx, title="Duplicate Named Waifus",
                              description="There are multiple waifus with the same name. Use an ID instead of a name to search for them. The global "
                                          "waifu IDs that share the same name have been provided.")
                await send_embeds_fields(ctx, embed, [("IDs", "\n".join(str(id) for id in ids))])
            else:
                waifu_id, name, description, anime, image_link = data[0]
                async with self.log_and_run("""SELECT ALIAS FROM ALIASES WHERE NAME = ?""", [name]) as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title=name, description=description)
                embed.set_image(url=image_link)
                fields = [("Anime", anime), ("Global Waifu ID", str(waifu_id)), ("Aliases", "\n".join(alias for alias, in data) or "None")]
                await send_embeds_fields(ctx, embed, fields)

    @waifu_war.command(brief="Add a waifu to the global waifu table", usage="name image_link [description]", aliases=["addwaifu", "aw"])
    @discord.ext.commands.is_owner()
    async def add_waifu(self, ctx: discord.ext.commands.Context, name: str, image_link: str, anime: str, *, description: str):
        await self.get_conn()
        async with self.log_and_run("""INSERT INTO WAIFUS(NAME, DESCRIPTION, ANIME, IMAGE) VALUES (?, ?, ?, ?)""",
                                    [name, description, anime, image_link]) as cursor:
            await cursor.execute("""SELECT ID FROM WAIFUS WHERE ID = (SELECT MAX(ID) FROM WAIFUS)""")
            data = await cursor.fetchone()
            item_id = data[0]
        await self.waifu(ctx, id_or_name=item_id)

    @waifu_war.command(brief="Add a waifu to a bracket", usage="bracket_id name",
                       aliases=["addtobracket", "atb", "add_waifu_bracket", "awb", "addwaifubracket"])
    @discord.ext.commands.is_owner()
    async def add_to_bracket(self, ctx: discord.ext.commands.Context, bracket_id: int, *, name: str):
        await self.get_conn()
        async with self.log_and_run("""SELECT STATUS FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            logger.debug("Data: %s", data)
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            status = data[0][0]
            if status != Status.OPEN:
                embed = Embed(ctx, title="Bracket Not Open",
                              description="The given Bracket is not open. A Bracket has to be Open in order to add characters to it.",
                              color=discord.Color.red())
                embed.add_field(name="Bracket ID", value=str(bracket_id))
                embed.add_field(name="Status", value=Status(status).name.title())
                return await ctx.send(embed=embed)
        async with self.log_and_run("""INSERT INTO BRACKET_{0}(NAME) VALUES (?)""".format(bracket_id), [name]) as cursor:
            await cursor.execute("""SELECT ID FROM BRACKET_{0} WHERE ID = (SELECT MAX(ID) FROM BRACKET_{0})""".format(bracket_id))
            data = await cursor.fetchone()
            item_id = data[0]
        await self.waifu(ctx, bracket_id, id_or_name=item_id)

    @waifu_war.command(brief="Lock a bracket", usage="bracket_id", aliases=["lockbracket", "lb"], enabled=False)
    @discord.ext.commands.is_owner()
    async def lock_bracket(self, ctx: discord.ext.commands.Context, bracket_id: Optional[int] = None):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        await self.needs_bracket(ctx, bracket_id)
        async with self.log_and_run("""SELECT STATUS FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            async with self.log_and_run("""UPDATE BRACKETS SET STATUS=? WHERE ID==?""", [Status.LOCKED, bracket_id]):
                pass
            embed = Embed(ctx, title="Closed Bracket", description="Bracket has been locked.", color=discord.Color.green())
            embed.add_field(name="Bracket ID", value=str(bracket_id))
            await ctx.send(embed=embed)

    @waifu_war.command(brief="Delete a waifu", usage="bracket_id waifu_id", aliases=["deletewaifu", "dw"])
    @discord.ext.commands.is_owner()
    async def delete_waifu(self, ctx: discord.ext.commands.Context, bracket_id: int, waifu_id: int):
        await self.get_conn()
        async with self.log_and_run("""SELECT STATUS FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            if data[0][0] != Status.OPEN:
                raise
            async with self.log_and_run("""SELECT * FROM BRACKET_%s WHERE ID==?""" % bracket_id, [waifu_id]) as cursor:
                data = await cursor.fetchall()
            if len(data) != 1:
                embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                              color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                embed.add_field(name="Waifu ID", value=str(waifu_id))
                await ctx.send(embed=embed)
            else:
                async with self.log_and_run("""DELETE FROM BRACKET_%s WHERE ID==?""" % bracket_id, [waifu_id]):
                    pass
                embed = Embed(ctx, title="Deleted Waifu", description="Waifu has been deleted.", color=discord.Color.green())
                embed.add_field(name="Bracket ID", value=str(bracket_id))
                embed.add_field(name="Waifu ID", value=str(waifu_id))
                await ctx.send(embed=embed)

    @waifu_war.command(brief="Duplicate a bracket", usage="bracket_id [name]", aliases=["dup"])
    @discord.ext.commands.is_owner()
    async def duplicate(self, ctx: discord.ext.commands.Context, /, bracket_id: Optional[int] = None, *, name: Optional[str] = None):
        await self.get_conn()
        bracket_id = bracket_id or await self.get_voting(ctx.guild.id)
        await self.needs_bracket(ctx, bracket_id)
        async with self.log_and_run("""SELECT NAME FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            original_name = data[0][0]
            new_bracket_id = await self.create_bracket(name)
            async with self.log_and_run("""INSERT INTO BRACKET_{} SELECT * FROM BRACKET_{}""".format(new_bracket_id, bracket_id)):
                pass
            embed = Embed(ctx, title="Bracket Duplicated", description="The Bracket has been successfully duplicated!", color=discord.Color.green())
            embed.add_field(name="Original Bracket ID", value=str(bracket_id))
            embed.add_field(name="Original Name", value=original_name)
            embed.add_field(name="New Bracket ID", value=str(new_bracket_id))
            embed.add_field(name="New Name", value=name)
            await ctx.send(embed=embed)

    @waifu_war.command(brief="Add an alias to the Waifu system.", usage="character_name character_alias [character_alias] [...]",
                       aliases=["addalias", "aa"])
    @discord.ext.commands.is_owner()
    async def add_alias(self, ctx: discord.ext.commands.Context, character_name: str, *aliases: str):
        await self.get_conn()
        if len(aliases) < 1:
            await ctx.send(embed=Embed(ctx, title="No Aliases Specified", description="An alias needs to be specified.", color=discord.Color.red()))
        for alias in aliases:
            try:
                async with self.log_and_run("""INSERT INTO ALIASES(NAME, ALIAS) VALUES (?, ?)""", [character_name, alias]):
                    pass
            except sqlite3.IntegrityError:
                embed = Embed(ctx, title="Alias Already Exists", description="The given alias already exists.", color=discord.Color.red())
                async with self.log_and_run("""SELECT NAME FROM ALIASES WHERE ALIAS = ?""", [aliases]) as cursor:
                    data = await cursor.fetchone()
                name = data[0]
                embed.add_field(name="Name", value=name)
                embed.add_field(name="Alias", value=alias)
                await ctx.send(embed=embed)
            else:
                embed = Embed(ctx, title="Alias Added", description="The alias was successfully added.", color=discord.Color.green())
                embed.add_field(name="Name", value=character_name)
                embed.add_field(name="Alias", value=alias)
                await ctx.send(embed=embed)

    @staticmethod
    def get_power_of_two(x: int):
        count = 0
        while x > 2:
            x /= 2
            count += 1
        return count, count + 1

    @waifu_war.command(brief="Start voting on a bracket", usage="bracket_id", aliases=["sv", "startvote"])
    @discord.ext.commands.is_owner()
    async def start_vote(self, ctx: discord.ext.commands.Context, bracket_id: int):
        await self.get_conn()
        async with self.log_and_run("""SELECT STATUS FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
            data = await cursor.fetchall()
        if len(data) != 1:
            return await self.id_does_not_exist(ctx, bracket_id)
        else:
            val = await self.get_voting(ctx.guild.id)
            if val is not None:
                embed = Embed(ctx, title="Another Bracket Already In Voting",
                              description="Another bracket is already going through a vote. Wait for that bracket to finish.",
                              color=discord.Color.red())
                embed.add_field(name="Other Waifu Bracket", value=str(val))
                embed.add_field(name="Specified Waifu Bracket", value=str(bracket_id))
                return await ctx.send(embed=embed)
            status = data[0][0]
            if status != Status.OPEN:
                embed = Embed(ctx, title="Cannot Start Voting on Non-Open Bracket",
                              description="A bracket must be open to start voting on it. Use `{}waifu_war duplicate {} name` to obtain a new "
                                          "bracket.".format(self.bot.command_prefix, bracket_id), color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                return await ctx.send(embed=embed)
            else:
                async with self.log_and_run("""SELECT NAME FROM BRACKET_{0}""".format(bracket_id)) as cursor:
                    data = await cursor.fetchall()
                x = len(data)
                if (x & (x - 1)) != 0:
                    bound_low, bound_high = self.get_power_of_two(x)
                    embed = Embed(ctx, title="Not a Power of Two",
                                  description="A bracket must be a power of two before starting voting. Add or delete enough waifus to get the "
                                              "minimum or maximum you need to start.")
                    fields = [("Number of Waifus", str(x)), ("Minimum", str(bound_low)), ("Maximum", str(bound_high))]
                    return await send_embeds_fields(ctx, embed, fields)
                else:
                    choices = [name for name, in data]
                    random.shuffle(choices)
                    new_choices = [[name] for name in choices]
                    async with self.log_and_run("""DROP TABLE BRACKET_{0}""".format(bracket_id)):
                        pass
                    async with self.log_and_run(
                            """CREATE TABLE IF NOT EXISTS BRACKET_%s(ID INTEGER PRIMARY KEY AUTOINCREMENT, NAME TEXT NOT NULL UNIQUE)""" %
                            bracket_id):
                        pass
                    async with self.conn.executemany("""INSERT INTO BRACKET_{0}(NAME) VALUES(?)""".format(bracket_id), new_choices):
                        pass
                    async with self.log_and_run("""UPDATE BRACKETS SET STATUS=? WHERE ID==?""", [Status.VOTABLE, bracket_id]):
                        pass
                    embed = Embed(ctx, title="Vote Started", description="Voting has now started", color=discord.Color.green())
                    embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                    await ctx.send(embed=embed)
                    await self.bracket(ctx)

    @waifu_war.command(brief="Vote on a division", usage="waifu_id", alias=["v"], significant=True)
    async def vote(self, ctx: discord.ext.commands.Context, *, id_or_name: Union[int, str]):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            async with self.conn.execute("""SELECT GUILD_ID FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
                data = await cursor.fetchone()
            if data is None or data[0] != ctx.guild.id:
                embed = Embed(ctx, title="Can Only Vote on Brackets in the Guild",
                              description="This bracket was not made in the current Guild. To ensure that brackets are fair, you cannot vote on "
                                          "this bracket from any guild except where it was created.",
                              color=discord.Color.red())
                embed.add_field(name="Bracket ID", value=bracket_id)
                embed.add_field(name="Current Guild ID", value=str(ctx.guild.id))
                embed.add_field(name="Bracket Guild ID", value=str(data[0]))
                return await ctx.send(embed=embed)
        if isinstance(id_or_name, str):
            query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                    "WAIFUS.NAME WHERE WAIFUS.NAME LIKE '%'||?||'%'".format(bracket_id)
        else:
            query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                    "WAIFUS.NAME WHERE BRACKET_{0}.ID==?".format(bracket_id)
        try:
            async with self.log_and_run(query, [id_or_name]) as cursor:
                data = await cursor.fetchall()
        except sqlite3.OperationalError:
            logger.warning("", exc_info=True)
            return await self.id_does_not_exist(ctx, bracket_id)
        if isinstance(id_or_name, str):
            async with self.log_and_run(
                    """SELECT BRACKET_{0}.ID, ALIASES.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN ALIASES on BRACKET_{0}.NAME = 
                    ALIASES.NAME INNER JOIN WAIFUS ON BRACKET_{0}.NAME = WAIFUS.NAME WHERE ALIAS LIKE '%'||?||'%'""".format(bracket_id),
                    [id_or_name]) as cursor:
                data2 = await cursor.fetchall()
            data.extend(data2)
        seen = []
        for item in data.copy():
            waifu_id, name, description, anime, image_link = item
            if waifu_id in seen:
                data.remove(item)
            else:
                seen.append(waifu_id)
        if len(data) < 1:
            embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                          color=discord.Color.red())
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            if isinstance(id_or_name, str):
                embed.add_field(name="Waifu Name", value=id_or_name)
            else:
                embed.add_field(name="Bracket Waifu ID", value=str(id_or_name))
            return await ctx.send(embed=embed)
        elif len(data) > 1:
            ids = [f"**{waifu_id}**: [{name} (*{anime}*)]({image_link})" for waifu_id, name, description, anime, image_link in data]
            embed = Embed(ctx, title="Duplicate Named Waifus",
                          description="There are multiple waifus with the same name. Use an ID instead of a name to vote. The "
                                      "bracket waifu IDs that share the same name have been provided.")
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            await send_embeds_fields(ctx, embed, [("IDs", "\n".join(str(id) for id in ids))])
        else:
            waifu_id, name, description, anime, image_link = data[0]
            division = (waifu_id + 1) // 2
            try:
                async with self.log_and_run("""INSERT INTO VOTES(USER_ID, BRACKET, DIVISION, CHOICE) VALUES(?, ?, ?, ?)""",
                                            [ctx.author.id, bracket_id, division, bool(waifu_id % 2)]):
                    pass
            except sqlite3.IntegrityError:
                logger.warning("", exc_info=True)
                async with self.log_and_run("""SELECT CHOICE FROM VOTES WHERE USER_ID==? AND BRACKET==? AND DIVISION==?""",
                                            [ctx.author.id, bracket_id, division]) as cursor:
                    previous_choice = division * 2 - int((await cursor.fetchone())[0])
                embed = Embed(ctx, title="Already Voted", description="You have already voted for this division. Specify another waifu ID.",
                              color=discord.Color.red())
                fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division)), ("Intended Waifu ID", str(waifu_id)),
                          ("Existing Choice", str(previous_choice))]
                messages = await send_embeds_fields(ctx, embed, fields)
                msg = messages[0]
                await msg.add_reaction("🚫")
            else:
                embed = Embed(ctx, title="Voted", description="You have successfully voted in the waifu war!", color=discord.Color.green())
                fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division)), ("Waifu ID", str(waifu_id)), ("Waifu Name", name),
                          ("Waifu Anime", anime), ("Waifu Description", description)]
                embed.set_image(url=image_link)
                messages = await send_embeds_fields(ctx, embed, fields)
                msg = messages[0]
                await msg.add_reaction("✅")
                await msg.add_reaction("🚫")
                if self.guide_data.get(ctx.author.id, 0) == 2:
                    await self.guide_step_3(ctx)

    @waifu_war.command(brief="Undo your vote", usage="waifu_id_or_name",
                       alias=["uv", "undo_vote", "undovote", "undo", "revert", "revert_vote", "rv", "revertvote", "unvote"], significant=True)
    async def un_vote(self, ctx: discord.ext.commands.Context, *, id_or_name: Union[int, str]):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        if isinstance(id_or_name, str):
            query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                    "WAIFUS.NAME WHERE WAIFUS.NAME LIKE '%'||?||'%'".format(bracket_id)
        else:
            query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                    "WAIFUS.NAME WHERE BRACKET_{0}.ID==?".format(bracket_id)
        try:
            async with self.log_and_run(query, [id_or_name]) as cursor:
                data = await cursor.fetchall()
        except sqlite3.OperationalError:
            logger.warning("", exc_info=True)
            return await self.id_does_not_exist(ctx, bracket_id)
        if isinstance(id_or_name, str):
            async with self.log_and_run(
                    """SELECT BRACKET_{0}.ID, ALIASES.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN ALIASES on BRACKET_{0}.NAME = 
                    ALIASES.NAME INNER JOIN WAIFUS ON BRACKET_{0}.NAME = WAIFUS.NAME WHERE ALIAS LIKE '%'||?||'%'""".format(bracket_id),
                    [id_or_name]) as cursor:
                data2 = await cursor.fetchall()
            data.extend(data2)
        seen = []
        for item in data.copy():
            waifu_id, name, description, anime, image_link = item
            if waifu_id in seen:
                data.remove(item)
            else:
                seen.append(waifu_id)
        if len(data) < 1:
            embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                          color=discord.Color.red())
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            if isinstance(id_or_name, str):
                embed.add_field(name="Waifu Name", value=id_or_name)
            else:
                embed.add_field(name="Bracket Waifu ID", value=str(id_or_name))
            return await ctx.send(embed=embed)
        elif len(data) > 1:
            ids = [f"**{waifu_id}**: [{name} (*{anime}*)]({image_link})" for waifu_id, name, description, anime, image_link in data]
            embed = Embed(ctx, title="Duplicate Named Waifus",
                          description="There are multiple waifus with the same name. Use an ID instead of a name to unvote. The "
                                      "bracket waifu IDs that share the same name have been provided.")
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            await send_embeds_fields(ctx, embed, [("IDs", "\n".join(str(id) for id in ids))])
        else:
            waifu_id, name, description, anime, image_link = data[0]
            division = (waifu_id + 1) // 2
            async with self.log_and_run("""DELETE FROM VOTES WHERE USER_ID==? AND BRACKET==? AND DIVISION==? AND CHOICE==?""",
                                        [ctx.author.id, bracket_id, division, bool(waifu_id % 2)]):
                pass
            embed = Embed(ctx, title="Vote Removed", description="Your vote has been removed.", color=discord.Color.green())
            fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division)), ("Waifu ID", str(waifu_id)), ("Waifu Name", name)]
            messages = await send_embeds_fields(ctx, embed, fields)
            msg = messages[0]
            await msg.add_reaction("✅")
            if self.guide_data.get(ctx.author.id, 0) == 3:
                await self.guide_step_4(ctx)

    @waifu_war.command(brief="Get the votes of a user or the users that voted on a waifu", usage="user / waifu_id_or_name", aliases=["gv", "getvote"])
    async def get_vote(self, ctx: discord.ext.commands.Context, *, id_or_name: Union[discord.Member, int, str]):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        if isinstance(id_or_name, discord.Member):
            async with self.log_and_run(
                    """SELECT DIVISION, BRACKET_{0}.ID, WAIFUS.NAME, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = 
                    WAIFUS.NAME INNER JOIN (SELECT * FROM VOTES WHERE USER_ID==? AND BRACKET==?) ON BRACKET_{0}.ID = ((DIVISION * 2)- 
                    CHOICE)""".format(
                        bracket_id), [id_or_name.id, bracket_id]) as cursor:
                data = await cursor.fetchall()
            embed = Embed(ctx, title="User Votes")
            embed.add_field(name="User", value=id_or_name.mention)
            embed.add_field(name="Waifu Bracket", value=str(bracket_id))
            lines = []
            for divison, waifu_id, name, anime, image in data:
                lines.append(f"Division **{divison}** / Waifu ID **{waifu_id}**: [{name} (*{anime}*)]({image})")
            await send_embeds_fields(ctx, embed, [("Waifus", "\n".join(lines) or "None")])
        else:
            if isinstance(id_or_name, str):
                query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                        "WAIFUS.NAME WHERE WAIFUS.NAME LIKE '%'||?||'%'".format(bracket_id)
            else:
                query = "SELECT BRACKET_{0}.ID, WAIFUS.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN WAIFUS ON BRACKET_{0}.NAME = " \
                        "WAIFUS.NAME WHERE BRACKET_{0}.ID==?".format(bracket_id)
            try:
                async with self.log_and_run(query, [id_or_name]) as cursor:
                    data = await cursor.fetchall()
            except sqlite3.OperationalError:
                logger.warning("", exc_info=True)
                return await self.id_does_not_exist(ctx, bracket_id)
            if isinstance(id_or_name, str):
                async with self.log_and_run(
                        """SELECT BRACKET_{0}.ID, ALIASES.NAME, DESCRIPTION, ANIME, IMAGE FROM BRACKET_{0} INNER JOIN ALIASES on BRACKET_{0}.NAME = 
                        ALIASES.NAME INNER JOIN WAIFUS ON BRACKET_{0}.NAME = WAIFUS.NAME WHERE ALIAS LIKE '%'||?||'%'""".format(bracket_id),
                        [id_or_name]) as cursor:
                    data2 = await cursor.fetchall()
                data.extend(data2)
            seen = []
            for item in data.copy():
                waifu_id, name, description, anime, image_link = item
                if waifu_id in seen:
                    data.remove(item)
                else:
                    seen.append(waifu_id)
            if len(data) < 1:
                embed = Embed(ctx, title="Waifu Does Not Exist", description="The provided waifu does not exist for the bracket.",
                              color=discord.Color.red())
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                if isinstance(id_or_name, str):
                    embed.add_field(name="Waifu Name", value=id_or_name)
                else:
                    embed.add_field(name="Bracket Waifu ID", value=str(id_or_name))
                return await ctx.send(embed=embed)
            elif len(data) > 1:
                ids = [f"**{waifu_id}**: [{name} (*{anime}*)]({image_link})" for waifu_id, name, description, anime, image_link in data]
                embed = Embed(ctx, title="Duplicate Named Waifus",
                              description="There are multiple waifus with the same name. Use an ID instead of a name to view votes. The "
                                          "bracket waifu IDs that share the same name have been provided.")
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                await send_embeds_fields(ctx, embed, [("IDs", "\n".join(str(id) for id in ids))])
            else:
                waifu_id, name, description, anime, image_link = data[0]
                division = (waifu_id + 1) // 2
                choice = waifu_id % 2
                async with self.log_and_run("""SELECT USER_ID FROM VOTES WHERE BRACKET==? AND DIVISION==? AND CHOICE==?""",
                                            [bracket_id, division, choice]) as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title="Votes", description="These are the people who voted for a specific character.")
                fields = [("Waifu Bracket", str(bracket_id)), ("Bracket Division", str(division)), ("Waifu ID", str(waifu_id)), ("Waifu Name", name),
                          ("Voters", "\n".join(ctx.guild.get_member(user_id).mention for user_id, in data) or "None")]
                return await send_embeds_fields(ctx, embed, fields)

    @waifu_war.command(brief="Get the last division you voted for.", aliases=["lastdivision", "ld"], significant=True)
    async def last_division(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            async with self.log_and_run("""SELECT MAX(DIVISION) FROM VOTES WHERE USER_ID==?""", [ctx.author.id]) as cursor:
                data = (await cursor.fetchone())[0]
            if data is None:
                msg = await ctx.send(embed=Embed(ctx, title="Never Participated",
                                                 description="You have never participated in the waifu war. Click the emoji below to get started on "
                                                             "the guide.",
                                                 color=discord.Color.red()))
                await msg.add_reaction("✅")
            else:
                embed = Embed(ctx, title="Previous Division")
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                embed.add_field(name="Waifu Division", value=str(data))
                msg = await ctx.send(embed=embed)
                await msg.add_reaction("✅")

    @waifu_war.command(brief="Start the next bracket", usage="additional", aliases=["start_next", "startnext", "sn", "finishbracket", "fb"])
    @discord.ext.commands.is_owner()
    async def finish_bracket(self, ctx: discord.ext.commands.Context, *, additional: str):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            async with self.log_and_run("""SELECT MAX(ID) FROM BRACKET_{0}""".format(bracket_id)) as cursor:
                data = (await cursor.fetchone())[0]
            max_division = data // 2
            async with self.log_and_run("""SELECT NAME FROM BRACKETS WHERE ID==?""", [bracket_id]) as cursor:
                name = (await cursor.fetchone())[0]
            name = name.partition("(")[0].strip()
            if max_division == 1:
                channel = self.bot.get_channel_data(ctx.guild, "announcements") or ctx
                l_name, l_anime, l_description, l_image_link, l_votes, r_name, r_anime, r_description, r_image_link, r_votes = await self.division(ctx, 1, _send=False)
                embed = Embed(ctx, title=f"Winner for *{name}*")
                if l_votes > r_votes:
                    name, anime, description, image_link, votes = l_name, l_anime, l_description, l_image_link, l_votes
                    embed.add_field(name="Status", value="Clear Winner")
                elif l_votes > r_votes:
                    name, anime, description, image_link, votes = r_name, r_anime, r_description, r_image_link, r_votes
                    embed.add_field(name="Status", value="Clear Winner")
                elif l_votes == r_votes:  # We use random number generation.
                    waifu_id = 2 - random.randint(0, 1)
                    embed.add_field(name="Status", value="Tie")
                    embed.description = "The two winning sides have the same amount of votes. A random number generation sequence has been used to determine the winner."
                    if waifu_id % 2 == 0:  # Right
                        name, anime, description, image_link, votes = l_name, l_anime, l_description, l_image_link, l_votes
                    else:
                        name, anime, description, image_link, votes = r_name, r_anime, r_description, r_image_link, r_votes
                else:
                    raise ValueError("Values do not make sense", l_name, l_votes, r_name, r_votes)
                fields = [("Waifu Name", name), ("Waifu Anime", anime), ("Waifu Description", description), ("Votes", votes)]
                embed.set_image(url=image_link)
                return await send_embeds_fields(channel, embed, fields)
            else:
                new_bracket_id = int(await self.create_bracket(ctx, name=name + f" ({additional})"))
                for i in range(1, max_division + 1):
                    l_name, l_votes, r_name, r_votes = await self.division(ctx, bracket_id, i)
                    if l_votes > r_votes:
                        waifu_id = (i * 2) - 1
                        await self.waifu(ctx, bracket_id=bracket_id, id_or_name=waifu_id)
                        winner = l_name
                    elif l_votes < r_votes:
                        waifu_id = (i * 2)
                        await self.waifu(ctx, bracket_id=bracket_id, id_or_name=waifu_id)
                        winner = r_name
                    elif l_votes == r_votes:  # We use random number generation.
                        waifu_id = (i * 2) - (random.randint(0, 1))
                        await ctx.send(embed=Embed(ctx, title="Tie",
                                                   description=f"The waifus **{l_name}** and **{r_name}** are tired, so a random number was used to "
                                                               f"determine the winner."))
                        await self.waifu(ctx, bracket_id=bracket_id, id_or_name=waifu_id)
                        if waifu_id % 2 == 0:  # Right
                            winner = r_name
                        else:
                            winner = l_name
                    else:
                        raise ValueError("Values do not make sense", l_name, l_votes, r_name, r_votes)
                    async with self.log_and_run("""INSERT INTO BRACKET_{0}(NAME) VALUES (?)""".format(new_bracket_id), [winner]):
                        pass
                embed = Embed(ctx, title="Finalizing", description="The brackets are being finalized.", color=discord.Color.green())
                embed.add_field(name="Old Bracket ID", value=str(bracket_id))
                embed.add_field(name="New Bracket ID", value=str(new_bracket_id))
                await ctx.send(embed=embed)
                async with self.log_and_run("""UPDATE BRACKETS SET STATUS=? WHERE ID==?""", [Status.VOTABLE, new_bracket_id]):
                    pass
            async with self.log_and_run("""UPDATE BRACKETS SET STATUS=? WHERE ID==?""", [Status.CLOSED, bracket_id]):
                pass

    @waifu_war.command(brief="Start the guide that shows how to use the bot.", aliases=["start", "g", "s"])
    async def guide(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            embed = Embed(ctx, title="Guide",
                          description="Welcome to the interactive Waifu War guide. This will show you how the various reactions work, "
                                      "allowing you to use the Waifu War system to it's fullest potential. Click the check mark below to start.")
            embed.add_field(name="Note",
                            value="If you have previously used the Waifu War system, the guide *will* delete the entry for the first division.")
            msg = await ctx.send(embed=embed)
            await msg.add_reaction("✅")

    @waifu_war.command(brief="See which divisions a person did not vote for.", usage="user", aliases=["misseddivisions", "md"], significant=True)
    async def missed_division(self, ctx: discord.ext.commands.Context, user: discord.Member = None):
        if user is None:
            user = ctx.author
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            async with self.log_and_run("""SELECT MAX(ID) FROM BRACKET_{0}""".format(bracket_id)) as cursor:
                data = (await cursor.fetchone())[0]
            max_division = data // 2
            async with self.log_and_run("""SELECT DIVISION FROM VOTES WHERE USER_ID==? AND BRACKET==?""", [user.id, bracket_id]) as cursor:
                data = await cursor.fetchall()
            missed = set(range(1, max_division + 1)) - {division for division, in data}
            if len(missed) > 0:
                async with self.log_and_run(
                        """SELECT A.ID,A.NAME, C.ANIME,C.DESCRIPTION,C.IMAGE,B.ID,B.NAME,D.ANIME, D.DESCRIPTION,D.IMAGE FROM (SELECT A.ID, 
                        A.NAME FROM BRACKET_{0} A WHERE A.ID % 2 == 1) AS A JOIN (SELECT B.ID, B.NAME FROM BRACKET_{0} B WHERE B.ID % 2 == 0) AS B 
                        ON (CAST((A.ID - 1) / 2 AS INTEGER) == CAST((B.ID - 1) / 2 AS INTEGER)) JOIN WAIFUS C ON A.NAME == C.NAME JOIN WAIFUS D ON 
                        B.NAME == D.NAME WHERE ((CAST((B.ID + 1) / 2 AS INTEGER)) IN {1})""".format(bracket_id,
                                                                                                    str(ConformingIterator(missed))).replace(",)",
                                                                                                                                             ")")) \
                        as cursor:
                    data = await cursor.fetchall()
                embed = Embed(ctx, title="Missed Divisions", description="The given user has not voted in all divisions.", color=discord.Color.red())
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                lines = []
                for division, item in zip(sorted(missed), data):
                    l_id, l_name, l_anime, l_description, l_image_link, r_id, r_name, r_anime, r_description, r_image_link = item
                    lines.append(
                        f"Division **{division}**: [{l_name} (*{l_anime}*) (Waifu ID **{l_id}**)]({l_image_link}) ***v.*** [{r_name} (*{r_anime}*) "
                        f"(Waifu ID **{r_id}**)]({r_image_link})")
                await send_embeds_fields(ctx, embed, [("Divisions", "\n".join(lines) or "None")])
            else:
                embed = Embed(ctx, title="No Missed Divisions", description="The given user has voted in all divisions.", color=discord.Color.green())
                embed.add_field(name="User", value=user.mention)
                embed.add_field(name="Waifu Bracket", value=str(bracket_id))
                await ctx.send(embed=embed)

    @waifu_war.command(brief="Get a convenient Embed that lets people start voting.")
    async def embed(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        chan = self.bot.get_channel_data(ctx.guild.id, "bot-spam")
        bracket_id = await self.get_voting(ctx.guild.id)
        if bracket_id is None:
            return await ctx.send(embed=Embed(ctx, title="No Voting Bracket Yet",
                                              description="No brackets are marked as Votable. Wait for a bracket to be marked as votable.",
                                              color=discord.Color.red()))
        else:
            msg = await ctx.send(embed=Embed(ctx, title="Start Voting",
                                             description=f"In order to vote, type `%ww d 1` in the {chan.mention} channel. Or, click the check mark "
                                                         f"below this item, and then go to {chan.mention}."))
            await msg.add_reaction("✅")

    @waifu_war.command(brief="See all waifus in the global list of waifus.",
                       aliases=["ws", "all_waifu", "all_waifus", "aws", "allwaifu", "allwaifus", "globalwaifus", "gws", "g_ws", "global_waifu", "globalwaifu"])
    async def global_waifus(self, ctx: discord.ext.commands.Context):
        embed = Embed(ctx, title="Global Waifu List")
        async with self.log_and_run("""SELECT ID, NAME, ANIME, IMAGE FROM WAIFUS""") as cursor:
            data = await cursor.fetchall()
        lines = []
        for waifu_id, name, anime, image in data:
            lines.append(f"**{waifu_id}**: [{name} (*{anime}*)]({image})")
        await send_embeds_fields(ctx, embed, [("Waifus", "\n".join(lines) or "None")])

    @waifu_war.command(brief="See all animes in the global list of waifus.", aliases=["globalanimes", "gas", "g_as"])
    async def global_animes(self, ctx: discord.ext.commands.Context):
        embed = Embed(ctx, title="Global Animes")
        async with self.log_and_run("SELECT ANIME FROM WAIFUS") as cursor:
            data = await cursor.fetchall()
        lines = []
        for anime in sorted({item for item, in data}):
            lines.append(f"*{anime}*")
        await send_embeds_fields(ctx, embed, [("Animes", "\n".join(lines) or "None")])

    async def guide_step_1(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        bracket_id = await self.get_voting(ctx.guild.id)
        async with self.log_and_run("""DELETE FROM VOTES WHERE USER_ID==? AND BRACKET==? AND DIVISION==1""", [ctx.author.id, bracket_id]):
            pass
        self.guide_data[ctx.author.id] = 1
        embed = Embed(ctx, title="Step 1: Summoning a Division",
                      description="To get the information for a division, you need to type `%ww d <number>` in order to access information. To "
                                  "bring up the first division, try typing `%ww d 1`.")
        embed.add_field(name="Note", value="For the purposes of the guide, clicking the check mark below will do the same thing as typing `%ww d 1`.")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")

    async def guide_step_2(self, ctx: discord.ext.commands.Context):
        await self.get_conn()
        self.guide_data[ctx.author.id] = 2
        embed = Embed(ctx, title="Step 2: Using a Division",
                      description="The division data will contain 5 emojis. Read how each emoji works. Note that you can click a button more than "
                                  "once, and have the same action repeat. When you're done reading, please vote on a waifu to continue. If you "
                                  "would rather not vote in this division, use the *skip* button (mentioned at the bottom) and find a division "
                                  "where you would like to vote.")
        embed.add_field(name="⬅️",
                        value="This button will cause you to vote for the left waifu. The left waifu is the waifu with the **odd** Waifu ID, "
                              "the first contender, or the waifu whose votes are listed to the left.")
        embed.add_field(name="➡️",
                        value="This button will cause you to vote for the right waifu. The right waifu is the waifu with the **even** Waifu ID, "
                              "the second contender, or the waifu whose votes are listed to the right.")
        embed.add_field(name="ℹ", value="The left information button. Gets the waifu Embed of the left waifu.")
        embed.add_field(name="🇮", value="The right information button. Gets the waifu Embed of the right waifu.")
        embed.add_field(name="🚫",
                        value="The division skip button. Allows you to get the information for the next division without voting for the given "
                              "division. Note, that if you click this button, you can still go back and vote on the previous division.")
        await ctx.send(embed=embed)

    async def guide_step_3(self, ctx: discord.ext.commands.Context):
        self.guide_data[ctx.author.id] = 3
        embed = Embed(ctx, title="Step 3: Using a Vote Result",
                      description="The vote result will contain two emojis. Read how each emoji works. Note that you can click a button more than "
                                  "once, and have the same action repeat. For the purposes of this guide, please click the **🚫** emoji.")
        embed.add_field(name="✅", value="The continue button. Brings up the next division, where you can get info and vote again.")
        embed.add_field(name="🚫",
                        value="The undo vote button. If you accidentally voted for the wrong character, click this button to undo your vote.")
        await ctx.send(embed=embed)

    async def guide_step_4(self, ctx: discord.ext.commands.Context):
        self.guide_data[ctx.author.id] = 4
        embed = Embed(ctx, title="Step 4: Using an Undo Vote Result",
                      description="The unvote result will contain one emoji. Read how it works and then click it to continue the guide. You're "
                                  "almost done -- one more step to go!")
        embed.add_field(name="✅",
                        value="The continue button. Brings up the division of the waifu that you removed your vote for, where you can get info and "
                              "vote again.")
        await ctx.send(embed=embed)

    async def guide_step_5(self, ctx: discord.ext.commands.Context):
        await ctx.send(embed=Embed(ctx, title="Final Step: Resuming the War",
                                   description="If for whatever reason, you are unable to complete the entire Waifu War in a single session, "
                                               "you can type `%ww ld` to bring up the last division you voted for. This Embed will contain a single "
                                               "check mark, which will open up the next division. Now go out there and vote for your waifu!"))
        del self.guide_data[ctx.author.id]

    async def on_reaction(self, msg: discord.Message, emoji: Union[discord.PartialEmoji, discord.Emoji], user: discord.Member):
        if user.id == self.bot.user.id or user.bot or msg.author.id != self.bot.user.id:
            return
        embed: discord.Embed = msg.embeds[0]
        ctx: CustomContext = await self.bot.get_context(msg, cls=CustomContext)
        ctx.author = user
        if embed.title == "Voted":
            if "✅" in str(emoji):
                bracket_id = int(embed.fields[0].value)
                division_id = int(embed.fields[1].value)
                return await self.division(ctx, bracket_id, division_id + 1)
            elif "🚫" in str(emoji):
                waifu_id = int(embed.fields[2].value)
                return await self.un_vote(ctx, id_or_name=waifu_id)
        elif embed.title.startswith("Division "):
            bracket_id = int(embed.fields[0].value)
            division_id = int(embed.fields[1].value)
            right_id = division_id * 2
            left_id = right_id - 1
            if "⬅️" in str(emoji):
                return await self.vote(ctx, id_or_name=left_id)
            elif "➡️" in str(emoji):
                return await self.vote(ctx, id_or_name=right_id)
            elif "ℹ" in str(emoji):
                return await self.waifu(ctx, bracket_id, id_or_name=left_id)
            elif "🇮" in str(emoji):
                return await self.waifu(ctx, bracket_id, id_or_name=right_id)
            elif "🚫" in str(emoji):
                return await self.division(ctx, bracket_id, division_id + 1)
        elif embed.title == "Vote Removed":
            if "✅" in str(emoji):
                bracket_id = int(embed.fields[0].value)
                division_id = int(embed.fields[1].value)
                return await self.division(ctx, bracket_id, division_id)
        elif embed.title == "Already Voted":
            if "🚫" in str(emoji):
                waifu_id = int(embed.fields[3].value)
                return await self.un_vote(ctx, id_or_name=waifu_id)
        elif embed.title == "Never Participated":
            if "✅" in str(emoji):
                return await self.guide(ctx)
        elif embed.title == "Previous Division":
            if "✅" in str(emoji):
                bracket_id = int(embed.fields[0].value)
                division_id = int(embed.fields[1].value)
                return await self.division(ctx, bracket_id, division_id + 1)
        elif embed.title == "Guide":
            if "✅" in str(emoji):
                return await self.guide_step_1(ctx)
        elif embed.title == "Step 1: Summoning a Division":
            if "✅" in str(emoji):
                return await self.division(ctx, 1)
        elif embed.title == "Start Guide":
            if "✅" in str(emoji):
                return await self.guide(ctx)
            elif "🚫" in str(emoji):
                bracket_id = int(embed.fields[0].value)
                division_id = int(embed.fields[1].value)
                return await self.division(ctx, bracket_id, division_id, _continue=True)
        elif embed.title == "Start Voting":
            if "✅" in str(emoji):
                chan = self.bot.get_channel_data(ctx.guild, "bot-spam")
                ctx.channel = chan
                return await self.division(ctx, 1)

    @discord.ext.commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        message: discord.Message = await channel.fetch_message(payload.message_id)
        guild: discord.Guild = self.bot.get_guild(payload.guild_id)
        user: discord.Member = guild.get_member(payload.user_id)
        emoji = payload.emoji
        await self.on_reaction(message, emoji, user)


def setup(bot: "PokestarBot"):
    cog = Waifu(bot)
    bot.add_cog(cog)
    if hasattr(bot, "_guide_data"):
        cog.guide_data = bot._guide_data
        del bot._guide_data
    logger.info("Loaded the Waifu extension.")


def teardown(bot: "PokestarBot"):
    cog: Waifu = bot.cogs["Waifu"]
    bot._guide_data = cog.guide_data
    asyncio.gather(cog.conn.close())
    logger.warning("Unloading the Waifu extension.")
