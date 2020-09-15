import asyncio
import datetime
import html
import inspect
import logging
import re
import sqlite3
from typing import Optional, TYPE_CHECKING, Union

import bbcode
import bs4
import discord.ext.commands
import discord.ext.tasks
import feedparser
import pytz

from . import PokestarBotCog
from ..utils import CustomContext, Embed, send_embeds_fields
from ..const import mangadex, guyamoe, nyaasi, horriblesubs

if TYPE_CHECKING:
    from ..bot import PokestarBot

NY = pytz.timezone("America/New_York")


class Updates(PokestarBotCog):
    GUYAMOE_URL = guyamoe
    MANGADEX_URL = mangadex
    NYAASI_URL = nyaasi
    HORRIBLESUBS_TORRENT = horriblesubs

    @property
    def conn(self):
        return self.bot.conn

    def __init__(self, bot: "PokestarBot"):
        super().__init__(bot)
        self.parser = self.set_up_parser()
        self.checked_for = []
        self.check_for_updates.start()
        check = self.bot.has_channel("anime-and-manga-updates")
        self.bot.add_check_recursive(self.updates, check)
        self.bot.add_check_recursive(self.loop, check)

    def cog_unload(self):
        self.check_for_updates.stop()

    @staticmethod
    def render_url(name, value, options, parent, context):
        if options and "url" in options:
            href = options["url"]
        else:
            href = value
        return "[{text}]({href})".format(href=href, text=html.unescape(value))

    def set_up_parser(self):
        parser = bbcode.Parser(newline="\n", install_defaults=False, escape_html=False, url_template="[{text}({href})", replace_cosmetic=False)
        parser.add_simple_formatter("b", "**%(value)s**", render_embedded=True)
        parser.add_simple_formatter("i", "*%(value)s*", render_embedded=True)
        parser.add_simple_formatter("u", "__%(value)s__", render_embedded=True)
        parser.add_simple_formatter("hr", "\n\n", standalone=True, render_embedded=False)
        parser.add_simple_formatter("spoiler", "||%(value)s||")
        parser.add_simple_formatter("*", "", standalone=True)
        parser.add_simple_formatter("img", "")
        parser.add_simple_formatter("quote", "```\n%(value)s\n```")
        parser.add_simple_formatter("code", "`%(value)s`")
        parser.add_formatter("url", self.render_url, replace_links=False, replace_cosmetic=False)
        return parser

    async def pre_create(self):
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS GUYAMOE(ID INTEGER PRIMARY KEY, SLUG TEXT, NAME TEXT NOT NULL, USER_ID UNSIGNED BIGINT NOT NULL, 
                COMPLETED BOOLEAN NOT NULL DEFAULT FALSE, GUILD_ID BIGINT NOT NULL, UNIQUE (SLUG, NAME, USER_ID, GUILD_ID))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS MANGADEX(ID INTEGER PRIMARY KEY, MANGA_ID INTEGER NOT NULL, NAME TEXT NOT NULL, USER_ID UNSIGNED 
                BIGINT NOT NULL, COMPLETED BOOLEAN NOT NULL DEFAULT FALSE, GUILD_ID BIGINT NOT NULL, UNIQUE (MANGA_ID, NAME, USER_ID, GUILD_ID))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS NYAASI(ID INTEGER PRIMARY KEY, NAME TEXT NOT NULL, USER_ID UNSIGNED BIGINT NOT NULL, 
                COMPLETED BOOLEAN NOT NULL DEFAULT FALSE, GUILD_ID BIGINT NOT NULL, UNIQUE(NAME, USER_ID, GUILD_ID))"""):
            pass
        async with self.conn.execute(
                """CREATE TABLE IF NOT EXISTS SEEN(ID INTEGER PRIMARY KEY, SERVICE TEXT NOT NULL, ITEM TEXT NOT NULL, CHAPTER TEXT NOT NULL, 
                UNIQUE (SERVICE, ITEM, CHAPTER))"""):
            pass

    async def get_conn(self):
        await self.pre_create()
        return self.conn

    async def guyamoe_info(self, ctx: discord.ext.commands.Context, slug: str, _info_only: bool = False):
        url = f"https://guya.moe/api/series/{slug}/"
        async with self.bot.session.get(url) as request:
            if request.status != 200:
                embed = Embed(ctx, title="Non-200 status code", description="The web request returned a non-200 status code",
                              color=discord.Color.red())
                embed.add_field(name="URL", value=url)
                embed.add_field(name="Status Code", value=str(request.status))
                return await ctx.send(embed=embed)
            json = await request.json()
        title = json['title']
        description = json["description"]
        author = json["author"]
        artist = json["artist"]
        image_url = "https://guya.moe" + json["cover"]
        next_release = datetime.datetime.utcfromtimestamp(json["next_release_time"]).replace(tzinfo=pytz.UTC).astimezone(NY).strftime(
            "%A, %B %d, %Y at %I:%M:%S %p")
        chaps = [float(key) for key in json["chapters"].keys()]
        latest_chapter = max(chaps)
        if int(latest_chapter) == latest_chapter:
            latest_chapter = int(latest_chapter)
        embed = Embed(ctx, title=title, description=description)
        embed.set_image(url=image_url)
        if not _info_only:
            embed.add_field(name="For User", value=ctx.author.mention)
            embed.add_field(name="Service", value="Guya.moe")
        embed.add_field(name="Link", value=f"https://guya.moe/read/manga/{slug}")
        embed.add_field(name="Author", value=author or None)
        embed.add_field(name="Artist", value=artist or None)
        embed.add_field(name="Latest Chapter", value=str(latest_chapter))
        embed.add_field(name="Next Chapter Published In", value=next_release)
        msg = await ctx.send(embed=embed)
        if _info_only:
            return
        await msg.add_reaction("✅")
        try:
            async with self.conn.execute("""INSERT INTO GUYAMOE(SLUG, NAME, USER_ID, GUILD_ID) VALUES (?, ?, ?, ?)""",
                                         [slug, title, ctx.author.id, ctx.guild.id]):
                pass
        except sqlite3.IntegrityError:
            logger.warning("", exc_info=True)
            embed = Embed(ctx, title="Manga Exists", description="The manga has been already added.", color=discord.Color.red())
            embed.add_field(name="Service", value="Guya.moe")
            embed.add_field(name="Slug", value=str(slug))
            return await ctx.send(embed=embed)
        async with self.conn.executemany("""INSERT OR IGNORE INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES ('Guyamoe', ?, ?)""",
                                         [(slug, str(chap)) for chap in chaps]):
            pass

    async def mangadex_info(self, ctx: discord.ext.commands.Context, manga_id: int, _info_only: bool = False):
        url = f"https://mangadex.org/api/manga/{manga_id}"
        async with self.bot.session.get(url) as request:
            if request.status != 200:
                embed = Embed(ctx, title="Non-200 status code", description="The web request returned a non-200 status code",
                              color=discord.Color.red())
                embed.add_field(name="URL", value=url)
                embed.add_field(name="Status Code", value=str(request.status))
                return await ctx.send(embed=embed)
            json = await request.json()
        manga = json["manga"]
        completed = manga["status"] == 1
        description = self.parser.format(html.unescape(manga["description"]))
        if len(description) > 2048:
            description = description[:2045] + "..."
        author = html.unescape(manga["author"])
        artist = html.unescape(manga["artist"])
        alt_names = "\n".join(html.unescape(name) for name in manga["alt_names"])
        r18 = bool(manga["hentai"])
        rating = manga["rating"]["bayesian"]
        title = html.unescape(manga['title'])
        image_url = f"https://www.mangadex.org{manga['cover_url']}"
        latest_chapter = None
        processed_chapters = []
        for chapter_data in json["chapter"].values():
            chap = chapter_data["chapter"] + ": " + chapter_data["title"]
            if chapter_data["lang_code"] == "gb" and chap not in processed_chapters:
                processed_chapters.append(chap)
                if latest_chapter is None:
                    latest_chapter = chap
        embed = Embed(ctx, title=title, description=description)
        embed.set_image(url=image_url)
        if not _info_only:
            embed.add_field(name="For User", value=ctx.author.mention)
            embed.add_field(name="Service", value="MangaDex")
        embed.add_field(name="Link", value=f"https://mangadex.org/title/{manga_id}")
        embed.add_field(name="Completed", value=str(completed))
        embed.add_field(name="Author", value=author or "None")
        embed.add_field(name="Artist", value=artist or "None")
        embed.add_field(name="Alternate Names", value=alt_names or "None")
        embed.add_field(name="R18", value=str(r18))
        embed.add_field(name="Rating", value=str(rating))
        embed.add_field(name="Latest Chapter", value=str(latest_chapter))
        msg = await ctx.send(embed=embed)
        if _info_only:
            return
        await msg.add_reaction("✅")
        try:
            async with self.conn.execute("""INSERT INTO MANGADEX(MANGA_ID, NAME, USER_ID, GUILD_ID) VALUES (?, ?, ?, ?)""",
                                         [manga_id, title, ctx.author.id, ctx.guild.id]):
                pass
        except sqlite3.IntegrityError:
            logger.warning("", exc_info=True)
            embed = Embed(ctx, title="Manga Exists", description="The manga has been already added.", color=discord.Color.red())
            embed.add_field(name="Service", value="MangaDex")
            embed.add_field(name="Manga ID", value=str(manga_id))
            return await ctx.send(embed=embed)
        async with self.conn.executemany("""INSERT OR IGNORE INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES ('MangaDex', ?, ?)""",
                                         [(str(manga_id), str(chap)) for chap in processed_chapters]):
            pass

    async def nyaasi_info(self, ctx: discord.ext.commands.Context, torrent_id: int, _get_name: bool = False, _info_only: bool = False):
        url = f"https://nyaa.si/view/{torrent_id}"
        async with self.bot.session.get(url) as request:
            if request.status != 200:
                embed = Embed(ctx, title="Non-200 status code", description="The web request returned a non-200 status code",
                              color=discord.Color.red())
                embed.add_field(name="URL", value=url)
                embed.add_field(name="Status Code", value=str(request.status))
                return await ctx.send(embed=embed)
            text = await request.text()
        soup = bs4.BeautifulSoup(text, features="lxml")
        full_title = next(filter(lambda tag: self.HORRIBLESUBS_TORRENT.search(tag.text), soup.find_all(class_="panel-title")))
        anime_name = self.HORRIBLESUBS_TORRENT.search(full_title.text).group(1)
        if _get_name:
            return anime_name
        rss_link = f"https://nyaa.si/?page=rss&q={anime_name.replace(' ', '+')}&c=0_0&f=0&u=HorribleSubs"
        async with self.bot.session.get(rss_link) as request:
            if request.status != 200:
                embed = Embed(ctx, title="Non-200 status code", description="The web request returned a non-200 status code",
                              color=discord.Color.red())
                embed.add_field(name="URL", value=url)
                embed.add_field(name="Status Code", value=str(request.status))
                return await ctx.send(embed=embed)
            text = await request.text()
        data = feedparser.parse(text)
        episodes = {int(self.HORRIBLESUBS_TORRENT.search(entry["title"]).group(2)) for entry in data["entries"]}
        latest_episode = max(episodes)
        embed = Embed(ctx, title=anime_name)
        if not _info_only:
            embed.add_field(name="For User", value=ctx.author.mention)
            embed.add_field(name="Service", value="Nyaa.si")
            embed.add_field(name="Initial Torrent Link (for adding)", value=url)
        embed.add_field(name="Latest Episode", value=str(latest_episode))
        msg = await ctx.send(embed=embed)
        if _info_only:
            return
        await msg.add_reaction("✅")
        try:
            async with self.conn.execute("INSERT INTO NYAASI(NAME, USER_ID, GUILD_ID) VALUES (?, ?, ?)", [anime_name, ctx.author.id, ctx.guild.id]):
                pass
        except sqlite3.IntegrityError:
            logger.warning("", exc_info=True)
            embed = Embed(ctx, title="Anime Exists", description="The anime has been already added.", color=discord.Color.red())
            embed.add_field(name="Service", value="Nyaa.si")
            embed.add_field(name="Anime Name", value=anime_name)
            return await ctx.send(embed=embed)
        async with self.conn.executemany("""INSERT OR IGNORE INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES ('Nyaasi', ?, ?)""",
                                         [(anime_name, str(episode)) for episode in episodes]):
            pass

    @discord.ext.commands.group(brief="Manage the manga updates system.", invoke_without_command=True, usage="subcommand", aliases=["update"])
    async def updates(self, ctx: discord.ext.commands.Context):
        await self.bot.generic_help(ctx)

    @updates.command(brief="Add a manga to the updates", usage="url [url] [...]")
    async def add(self, ctx: discord.ext.commands.Context, *urls: str):
        await self.get_conn()
        if len(urls) == 0:
            embed = Embed(ctx, title="No URLs Specified",
                          description="You need to specify a valid URL. The different valid types of URLs are specified.", color=discord.Color.red())
            embed.add_field(name="Guya.moe", value="https://guya.moe/read/manga/<manga-name>")
            embed.add_field(name="MangaDex", value="https://mangadex.org/title/<manga-id>")
            embed.add_field(name="Nyaa.si", value="https://nyaa.si/view/<torrent-id>")
            return await ctx.send(embed=embed)
        for url in urls:
            if match := self.GUYAMOE_URL.match(url):
                slug = match.group(1)
                await self.guyamoe_info(ctx, slug)
            elif match := self.MANGADEX_URL.match(url):
                manga_id = int(match.group(1))
                await self.mangadex_info(ctx, manga_id)
            elif match := self.NYAASI_URL.match(url):
                torrent_id = int(match.group(1))
                await self.nyaasi_info(ctx, torrent_id)
            else:
                embed = Embed(ctx, title="Invalid URL",
                              description="The given URL is not recognized by the bot. Look at the supported services that are attached on this "
                                          "Embed.",
                              color=discord.Color.red())
                embed.add_field(name="Guya.moe", value="https://guya.moe/read/manga/<manga-name>")
                embed.add_field(name="MangaDex", value="https://mangadex.org/title/<manga-id>")
                embed.add_field(name="Nyaa.si", value="https://nyaa.si/view/<torrent-id>")
                await ctx.send(embed=embed)

    @updates.command(brief="Remove a manga from the updates", usage="url [url] [...]")
    async def remove(self, ctx: discord.ext.commands.Context, *urls: str):
        await self.get_conn()
        if len(urls) == 0:
            embed = Embed(ctx, title="No URLs Specified",
                          description="You need to specify a valid URL. The different valid types of URLs are specified.", color=discord.Color.red())
            embed.add_field(name="Guya.moe", value="https://guya.moe/read/manga/<manga-name>")
            embed.add_field(name="MangaDex", value="https://mangadex.org/title/<manga-id>")
            embed.add_field(name="Nyaa.si", value="https://nyaa.si/view/<torrent-id>")
            return await ctx.send(embed=embed)
        for url in urls:
            if match := self.GUYAMOE_URL.match(url):
                slug = match.group(1)
                async with self.conn.execute("""DELETE FROM GUYAMOE WHERE SLUG==? AND USER_ID==? AND GUILD_ID==?""",
                                             [slug, ctx.author.id, ctx.guild.id]):
                    pass
                # async with self.conn.execute("""DELETE FROM SEEN WHERE SERVICE=='Guyamoe' AND ITEM==?""", [slug]):
                # pass
                embed = Embed(ctx, color=discord.Color.green(), title="Manga Removed")
                embed.add_field(name="Service", value="Guya.moe")
                embed.add_field(name="Slug", value=slug)
                await ctx.send(embed=embed)
            elif match := self.MANGADEX_URL.match(url):
                manga_id = int(match.group(1))
                async with self.conn.execute("""DELETE FROM MANGADEX WHERE MANGA_ID==? AND USER_ID==? AND GUILD_ID==?""",
                                             [manga_id, ctx.author.id, ctx.guild.id]):
                    pass
                embed = Embed(ctx, color=discord.Color.green(), title="Manga Removed")
                embed.add_field(name="Service", value="MangaDex")
                embed.add_field(name="Manga ID", value=str(manga_id))
                await ctx.send(embed=embed)
            elif match := self.NYAASI_URL.match(url):
                torrent_id = int(match.group(1))
                name = await self.nyaasi_info(ctx, torrent_id, _get_name=True)
                async with self.conn.execute("""DELETE FROM NYAASI WHERE NAME==? AND USER_ID==? AND GUILD_ID==?""",
                                             [name, ctx.author.id, ctx.guild.id]):
                    pass
                embed = Embed(ctx, color=discord.Color.green(), title="Manga Removed")
                embed.add_field(name="Service", value="Nyaa.si")
                embed.add_field(name="Anime Name", value=name)
                await ctx.send(embed=embed)
            else:
                embed = Embed(ctx, title="Invalid URL",
                              description="The given URL is not recognized by the bot. Look at the supported services that are attached on this "
                                          "Embed.",
                              color=discord.Color.red())
                embed.add_field(name="Guya.moe", value="https://guya.moe/read/manga/<manga-name>")
                embed.add_field(name="MangaDex", value="https://mangadex.org/title/<manga-id>")
                embed.add_field(name="Nyaa.si", value="https://nyaa.si/view/<torrent-id>")
                await ctx.send(embed=embed)

    @updates.command(brief="List the current mangas that will give notifications", usage="[user]")
    async def list(self, ctx: discord.ext.commands.Context, user: Optional[discord.Member] = None):
        await self.get_conn()
        user_data = {}
        slug_data = {}
        embed = Embed(ctx, title="Mangas in Update List")
        fields = []
        async with self.conn.execute("""SELECT SLUG, NAME, USER_ID FROM GUYAMOE WHERE GUILD_ID==?""", [ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        for slug, name, user_id in data:
            member: discord.Member = ctx.guild.get_member(user_id)
            slug_data.setdefault(slug, name)
            members = user_data.setdefault(slug, [])
            members.append(member.mention)
        for slug in sorted(set(slug_data.keys())):
            if not user or user.mention in user_data[slug]:
                fields.append((slug_data[slug] + " [Guya.moe]", "\n".join((f"Link: https://guya.moe/read/manga/{slug}", ", ".join(user_data[slug])))))
        user_data = {}
        slug_data = {}
        async with self.conn.execute("""SELECT MANGA_ID, NAME, USER_ID FROM MANGADEX WHERE GUILD_ID==?""", [ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        for slug, name, user_id in data:
            member: discord.Member = ctx.guild.get_member(user_id)
            slug_data.setdefault(slug, name)
            members = user_data.setdefault(slug, [])
            members.append(member.mention)
        for slug in sorted(set(slug_data.keys())):
            if not user or user.mention in user_data[slug]:
                fields.append((slug_data[slug] + " [MangaDex]", "\n".join((f"Link: https://mangadex.org/title/{slug}", ", ".join(user_data[slug])))))
        async with self.conn.execute("""SELECT NAME, USER_ID FROM NYAASI WHERE GUILD_ID==?""", [ctx.guild.id]) as cursor:
            data = await cursor.fetchall()
        user_data = {}
        for name, user_id in data:
            member: discord.Member = ctx.guild.get_member(user_id)
            members = user_data.setdefault(name, [])
            members.append(member.mention)
        for name in sorted(user_data.keys()):
            if not user or user.mention in user_data[name]:
                fields.append((name + " [Nyaa.i]", ", ".join(user_data[name])))
        await send_embeds_fields(ctx, embed, fields)

    async def guyamoe_update(self, slug: str, name: str):
        url = f"https://guya.moe/api/series/{slug}/"
        async with self.bot.session.get(url) as request:
            request.raise_for_status()
            json = await request.json()
        chaps = {str(float(key)) for key in json["chapters"].keys()}
        async with self.conn.execute("""SELECT CHAPTER FROM SEEN WHERE SERVICE==? AND ITEM==?""", ["Guyamoe", slug]) as cursor:
            data = await cursor.fetchall()
        seen_chaps = {chap for chap, in data}
        new_chaps = chaps - seen_chaps
        if len(new_chaps) > 0:
            logger.debug(str(new_chaps))
        async with self.conn.execute("""SELECT USER_ID, GUILD_ID FROM GUYAMOE WHERE SLUG==?""", [slug]) as cursor:
            data = await cursor.fetchall()
        for chap in sorted(new_chaps):
            num_chap = float(chap)
            int_chap = int(num_chap)
            if int_chap == num_chap:
                num_chap = int_chap
            logger.info("New Chapter: %s chapter %s", name, num_chap)
            link = f"https://guya.moe/read/manga/{slug}/{str(num_chap).replace('.', '-')}"
            embed = discord.Embed(color=discord.Color.green(), title="New Chapter")
            embed.add_field(name="Service", value="Guya.moe")
            embed.add_field(name="Manga", value=name)
            embed.add_field(name="Chapter", value=str(num_chap))
            embed.add_field(name="Link", value=link)
            for user_id, guild_id in data:
                dest = self.bot.get_channel_data(guild_id, "anime-and-manga-updates")
                if dest is None:
                    continue
                user = dest.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                await dest.send(user.mention, embed=embed)
        async with self.conn.executemany("""INSERT INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES('Guyamoe', ?, ?)""",
                                         [(slug, chap) for chap in new_chaps]):
            pass

    async def mangadex_update(self, manga_id: int, name: str):
        url = f"https://mangadex.org/api/manga/{manga_id}"
        async with self.bot.session.get(url) as request:
            request.raise_for_status()
            json = await request.json()
        processed_chapters = {}
        for chap_key, chapter_data in json["chapter"].items():
            chap = chapter_data["chapter"] + ": " + chapter_data["title"]
            if chapter_data["lang_code"] == "gb" and chap not in processed_chapters:
                processed_chapters[chap] = chap_key
        chaps = set(processed_chapters.keys())
        nums = [chap.partition(":")[0] for chap in chaps]
        if json["manga"]["last_chapter"] in nums and str(json["manga"]["last_chapter"]) != "0":
            async with self.conn.execute("""UPDATE MANGADEX SET COMPLETED=TRUE WHERE MANGA_ID==?""", [manga_id]):
                pass
        async with self.conn.execute("""SELECT CHAPTER FROM SEEN WHERE SERVICE==? AND ITEM==?""", ["MangaDex", str(manga_id)]) as cursor:
            data = await cursor.fetchall()
        seen_chaps = {chap for chap, in data}
        new_chaps = chaps - seen_chaps
        if len(new_chaps) > 0:
            logger.debug(str(new_chaps))
        async with self.conn.execute("""SELECT USER_ID, GUILD_ID FROM MANGADEX WHERE MANGA_ID==?""", [manga_id]) as cursor:
            data = await cursor.fetchall()
        for chap in sorted(new_chaps):
            logger.info("New Chapter: %s chapter %s", name, chap)
            chap_id = processed_chapters[chap]
            link = f"https://mangadex.org/chapter/{chap_id}/"
            embed = discord.Embed(color=discord.Color.green(), title="New Chapter")
            embed.add_field(name="Service", value="MangaDex")
            embed.add_field(name="Manga", value=name)
            embed.add_field(name="Chapter", value=chap)
            embed.add_field(name="Link", value=link)
            for user_id, guild_id in data:
                dest = self.bot.get_channel_data(guild_id, "anime-and-manga-updates")
                if dest is None:
                    continue
                user = dest.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                await dest.send(user.mention, embed=embed)
        async with self.conn.executemany("""INSERT INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES('MangaDex', ?, ?)""",
                                         [(str(manga_id), chap) for chap in new_chaps]):
            pass

    async def nyaasi_update(self, anime_name: str):
        rss_link = f"https://nyaa.si/?page=rss&q={anime_name.replace(' ', '+')}&c=0_0&f=0&u=HorribleSubs"
        async with self.bot.session.get(rss_link) as request:
            request.raise_for_status()
            text = await request.text()
        data = feedparser.parse(text)
        episodes = {}
        for entry in data["entries"]:
            search = self.HORRIBLESUBS_TORRENT.search(entry["title"])
            number, resolution = search.group(2, 3)
            if int(resolution) != 1080:
                continue
            episodes[int(number)] = entry["link"]
        async with self.conn.execute("""SELECT CHAPTER FROM SEEN WHERE SERVICE==? AND ITEM==?""", ["Nyaasi", anime_name]) as cursor:
            data = await cursor.fetchall()
        seen_eps = {int(ep) for ep, in data}
        new_eps = set(episodes.keys()) - seen_eps
        if len(new_eps) > 0:
            logger.debug(str(new_eps))
        async with self.conn.execute("""SELECT USER_ID, GUILD_ID FROM NYAASI WHERE NAME==?""", [anime_name]) as cursor:
            data = await cursor.fetchall()
        for ep in sorted(new_eps):
            logger.info("New Episode: %s episode %s", anime_name, ep)
            embed = discord.Embed(color=discord.Color.green(), title="New Episode")
            embed.add_field(name="Service", value="Nyaa.si")
            embed.add_field(name="Anime", value=anime_name)
            embed.add_field(name="Episode #", value=ep)
            embed.add_field(name="Link", value=episodes[ep])
            embed.add_field(name="Search Page", value=f"https://nyaa.si/user/HorribleSubs?q={anime_name.replace(' ', '+')}&c=0_0&f=0")
            for user_id, guild_id in data:
                dest = self.bot.get_channel_data(guild_id, "anime-and-manga-updates")
                if dest is None:
                    continue
                user = dest.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
                await dest.send(user.mention, embed=embed)
        async with self.conn.executemany("""INSERT OR IGNORE INTO SEEN(SERVICE, ITEM, CHAPTER) VALUES ('Nyaasi', ?, ?)""",
                                         [(anime_name, str(episode)) for episode in episodes.keys()]):
            pass

    @updates.group(brief="Get the update loop statistics", aliases=["updateloop", "update_loop"], invoke_without_command=True)
    async def loop(self, ctx: discord.ext.commands.Context):
        await self.bot.loop_stats(ctx, self.check_for_updates, "Check For Updates")

    @loop.command(brief="Start the loop")
    @discord.ext.commands.is_owner()
    async def start(self, ctx: discord.ext.commands.Context):
        self.check_for_updates.start()
        await ctx.send(embed=Embed(ctx, title="Loop Started", description="The loop has been started.", color=discord.Color.green()))

    @loop.command(brief="Stop the loop")
    @discord.ext.commands.is_owner()
    async def stop(self, ctx: discord.ext.commands.Context):
        self.check_for_updates.stop()
        await ctx.send(embed=Embed(ctx, title="Loop Stopped", description="The loop has been stopped.", color=discord.Color.green()))

    @loop.command(brief="Restart the loop")
    @discord.ext.commands.is_owner()
    async def restart(self, ctx: discord.ext.commands.Context):
        self.check_for_updates.restart()
        await ctx.send(embed=Embed(ctx, title="Loop Restarted", description="The loop has been restarted.", color=discord.Color.green()))

    @discord.ext.commands.command(brief="Get information on a manga on Guya.moe", usage="url [url] [...]", aliases=["guya.moe"])
    async def guyamoe(self, ctx: discord.ext.commands.Context, *urls: str):
        if len(urls) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("url", inspect.Parameter.POSITIONAL_ONLY))
        for url in urls:
            if match := self.GUYAMOE_URL.match(url):
                slug = match.group(1)
                await self.guyamoe_info(ctx, slug, _info_only=True)
            else:
                embed = Embed(ctx, title="Invalid URL", description="The provided URL is invalid.", color=discord.Color.red())
                embed.add_field(name="Provided URL", value=url)
                embed.add_field(name="Valid URL", value="https://guya.moe/read/manga/<manga-name>")
                await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Get information on a manga on MangaDex", usage="url [url] [...]")
    async def mangadex(self, ctx: discord.ext.commands.Context, *urls: str):
        if len(urls) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("url", inspect.Parameter.POSITIONAL_ONLY))
        for url in urls:
            if match := self.MANGADEX_URL.match(url):
                manga_id = int(match.group(1))
                await self.mangadex_info(ctx, manga_id, _info_only=True)
            else:
                embed = Embed(ctx, title="Invalid URL", description="The provided URL is invalid.", color=discord.Color.red())
                embed.add_field(name="Provided URL", value=url)
                embed.add_field(name="Valid URL", value="https://mangadex.org/title/<manga-id>")
                await ctx.send(embed=embed)

    @discord.ext.commands.command(brief="Get information on an anime provided by HorribleSubs on nyaa.si", usage="url [url] [...]",
                                  aliases=["nyaa.si"])
    async def nyaasi(self, ctx: discord.ext.commands.Context, *urls: str):
        if len(urls) == 0:
            raise discord.ext.commands.MissingRequiredArgument(inspect.Parameter("url", inspect.Parameter.POSITIONAL_ONLY))
        for url in urls:
            if match := self.NYAASI_URL.match(url):
                torrent_id = int(match.group(1))
                await self.nyaasi_info(ctx, torrent_id, _info_only=True)
            else:
                embed = Embed(ctx, title="Invalid URL", description="The provided URL is invalid.", color=discord.Color.red())
                embed.add_field(name="Provided URL", value=url)
                embed.add_field(name="Valid URL", value="https://nyaa.si/view/<torrent-id>")
                await ctx.send(embed=embed)

    @discord.ext.tasks.loop(minutes=5)
    async def check_for_updates(self):
        await self.get_conn()
        await self.bot.load_session()
        async with self.conn.execute("""SELECT DISTINCT SLUG, NAME FROM GUYAMOE WHERE COMPLETED==?""", [False]) as cursor:
            guyamoe = await cursor.fetchall()
        for slug, name in guyamoe:
            if "GUYAMOE" + slug in self.checked_for:
                continue
            try:
                await self.guyamoe_update(slug, name)
            except:
                raise
            else:
                self.checked_for.append("GUYAMOE" + slug)
        async with self.conn.execute("""SELECT DISTINCT MANGA_ID, NAME FROM MANGADEX WHERE COMPLETED==?""", [False]) as cursor:
            mangadex = await cursor.fetchall()
        for manga_id, name in mangadex:
            if "MANGADEX" + str(manga_id) in self.checked_for:
                continue
            try:
                await self.mangadex_update(manga_id, name)
            except:
                raise
            else:
                self.checked_for.append("MANGADEX" + str(manga_id))
        async with self.conn.execute("""SELECT DISTINCT NAME FROM NYAASI WHERE COMPLETED==?""", [False]) as cursor:
            nyaasi = await cursor.fetchall()
        for anime_name, in nyaasi:
            if "NYAASI" + anime_name in self.checked_for:
                continue
            try:
                await self.nyaasi_update(anime_name)
            except:
                raise
            else:
                self.checked_for.append("NYAASI" + anime_name)
        self.checked_for = []

    @check_for_updates.before_loop
    async def before_check_for_updates(self):
        await self.bot.wait_until_ready()

    @check_for_updates.error
    async def on_check_for_updates_error(self, exception: BaseException):
        logger.exception("Exception occured inside the check_for_updates task: %s", exception, exc_info=exception)

    async def on_reaction(self, msg: discord.Message, emoji: Union[discord.PartialEmoji, discord.Emoji], user: discord.Member):
        if user.id == self.bot.user.id or user.bot or msg.author.id != self.bot.user.id:
            return
        embed: discord.Embed = msg.embeds[0]
        ctx: CustomContext = await self.bot.get_context(msg, cls=CustomContext)
        ctx.author = user
        if len(embed.fields) > 1:
            val = embed.fields[1].value
            if val == "Guya.moe":
                if embed.title == "Manga Removed":
                    if "✅" in str(emoji):
                        pass
                    elif "🚫" in str(emoji):
                        pass
                else:
                    if "✅" in str(emoji):
                        link = embed.fields[2].value
                        await self.add(ctx, link)
                    elif "🚫" in str(emoji):
                        pass
            elif val == "MangaDex":
                if embed.title == "Manga Removed":
                    if "✅" in str(emoji):
                        pass
                    elif "🚫" in str(emoji):
                        pass
                else:
                    if "✅" in str(emoji):
                        link = embed.fields[2].value
                        await self.add(ctx, link)
                    elif "🚫" in str(emoji):
                        pass
            elif val == "Nyaa.si":
                if embed.title == "Manga Removed":
                    if "✅" in str(emoji):
                        pass
                    elif "🚫" in str(emoji):
                        pass
                else:
                    if "✅" in str(emoji):
                        link = embed.fields[2].value
                        await self.add(ctx, link)
                    elif "🚫" in str(emoji):
                        pass

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


logger = logging.getLogger(__name__)


def setup(bot: "PokestarBot"):
    bot.add_cog(Updates(bot))
    logger.info("Loaded the Updates extension.")


def teardown(bot: "PokestarBot"):
    cog: Updates = bot.cogs["Updates"]
    asyncio.gather(cog.conn.close())
    logger.warning("Unloading the Updates extension.")
