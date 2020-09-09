import asyncio
import contextlib
import datetime
import io
import logging
import pprint
import subprocess
import traceback
from typing import Optional, TYPE_CHECKING

import discord.ext.commands

from . import PokestarBotCog
from ..utils import Embed, parse_discord_code_block, send_embeds_fields

if TYPE_CHECKING:
    from ..bot import PokestarBot

logger = logging.getLogger(__name__)


class Code(PokestarBotCog):

    async def python_code_base(self, ctx: discord.ext.commands.Context, code: str, is_exec: bool, block_num: Optional[int] = None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        threw_exception = False
        func = exec if is_exec else eval
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                output = func(code)
            except Exception as exc:
                threw_exception = True
                exc.__traceback__ = exc.__traceback__.tb_next
                logger.warning("%s command lead to exception:", "Exec" if is_exec else "Eval", exc_info=exc)
                traceback.print_exception(type(exc), exc, exc.__traceback__)
        stdout.seek(0)
        stderr.seek(0)
        stdout_text = stdout.read()
        stderr_text = stderr.read()
        embed = Embed(ctx, title="Python Code Execution Results", description="Code Executed:\n```python\n{}\n```".format(code),
                      color=(discord.Color.green() if not threw_exception else discord.Color.red()))
        embed.add_field(name="Mode", value="Exec" if is_exec else "Eval")
        embed.add_field(name="Code Block Number", value=str(1 if not block_num else block_num))
        fields = []
        if stdout_text:
            fields.append(("Stdout", stdout_text))
        if stderr_text:
            fields.append(("Stderr", stderr_text))
        if not is_exec and not threw_exception:
            output = pprint.pformat(output)
            fields.append(("Output", output))
        await send_embeds_fields(ctx, embed, fields, template="```py\n", ending="\n```")

    async def process_base(self, ctx: discord.ext.commands.Context, code: str, is_exec: bool, block_num: Optional[int] = None, _single: bool = True):
        num = 1
        start = datetime.datetime.now()
        if "```" not in code:
            await self.python_code_base(ctx, code, is_exec, block_num=block_num)
        else:
            try:
                items = await parse_discord_code_block(code)
            except ValueError as exc:
                return await self.bot.on_command_error(ctx, exception=exc,
                                                       custom_message="An exception occurred while trying to process the given code:\n```python\n"
                                                                      "{}\n```".format(code))
            tasks = []
            for num, item in enumerate(items, start=1):
                tasks.append(self.process_base(ctx, item, is_exec, block_num=num, _single=False))
            await asyncio.gather(*tasks)
        if _single:
            finish = datetime.datetime.now()
            embed = Embed(ctx, title="Code Execution Has Finished", description="The execution of code has finished.", color=discord.Color.green())
            embed.add_field(name="Code Blocks Processed", value=str(num))
            embed.add_field(name="Time To Run", value=str(finish - start))
            await ctx.send(embed=embed)

    async def bash_code_base(self, ctx: discord.abc.Messageable, code: str, block_num: Optional[int] = None):
        proc = await asyncio.create_subprocess_shell("/bin/bash", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_text, stderr_text = await proc.communicate(code.encode())
        stdout_text = stdout_text.decode()
        stderr_text = stderr_text.decode()
        rcode = proc.returncode or 0
        embed = Embed(ctx, title="Bash Code Execution Results", description="Code Executed:\n```bash\n{}\n```".format(code),
                      color=(discord.Color.green() if not rcode else discord.Color.red()))
        embed.add_field(name="Return Code", value=str(rcode))
        embed.add_field(name="Code Block Number", value=str(1 if not block_num else block_num))
        logger.debug("Stdout:\n%s", stdout_text)
        logger.debug("Stderr:\n%s", stderr_text)
        fields = []
        if stdout_text:
            fields.append(("Stdout", stdout_text))
        if stderr_text:
            fields.append(("Stderr", stderr_text))
        await send_embeds_fields(ctx, embed, fields, template="```bash\n", ending="\n```")

    async def bash_base(self, ctx: discord.abc.Messageable, code: str, block_num: Optional[int] = None, _single: bool = True):
        num = 1
        start = datetime.datetime.now()
        if "```" not in code:
            await self.bash_code_base(ctx, code, block_num=block_num)
        else:
            try:
                items = await parse_discord_code_block(code, languages=("bash", "sh", "shell"))
            except ValueError as exc:
                return await self.bot.on_command_error(ctx, exception=exc,
                                                       custom_message="An exception occurred while trying to process the given code:\n```bash\n"
                                                                      "{}\n```".format(code))
            tasks = []
            for num, item in enumerate(items, start=1):
                tasks.append(self.bash_base(ctx, item, block_num=num, _single=False))
            await asyncio.gather(*tasks)
            _single = True
        if _single:
            finish = datetime.datetime.now()
            embed = Embed(ctx, title="Code Execution Has Finished", description="The execution of code has finished.", color=discord.Color.green())
            embed.add_field(name="Code Blocks Processed", value=str(num))
            embed.add_field(name="Time To Run", value=str(finish - start))
            await ctx.send(embed=embed)

    @discord.ext.commands.command(name="eval", brief="Evaluate python code", usage="code")
    @discord.ext.commands.is_owner()
    async def command_eval(self, ctx: discord.ext.commands.Context, *, code: str):
        await self.process_base(ctx, code, False)

    @discord.ext.commands.command(name="exec", brief="Execute python code", usage="code")
    @discord.ext.commands.is_owner()
    async def command_exec(self, ctx: discord.ext.commands.Context, *, code: str):
        await self.process_base(ctx, code, True)

    @discord.ext.commands.command(name="bash", brief="Execute bash shell code", usage="code", aliases=["sh", "shell"])
    @discord.ext.commands.is_owner()
    async def command_bash(self, ctx: discord.ext.commands.Context, *, code: str):
        await self.bash_base(ctx, code)


def setup(bot: "PokestarBot"):
    bot.add_cog(Code(bot))
    logger.info("Loaded the Code extension.")


def teardown(_bot: "PokestarBot"):
    logger.warning("Unloading the Code extension.")
