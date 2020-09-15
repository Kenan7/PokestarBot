import discord.ext.commands


class SignificantCommand(discord.ext.commands.Command):
    def __init__(self, func, significant: bool = False, **kwargs):
        self.significant = significant
        super().__init__(func, **kwargs)


class SignificantGroup(discord.ext.commands.Group):
    def __init__(self, func, significant: bool = False, **kwargs):
        self.significant = significant
        super().__init__(func, **kwargs)


def patch():
    """Patch the discord.ext.commands.command() and discord.ext.commands.group() decorators to use the classes defined above"""
    import functools
    if not isinstance(discord.ext.commands.command, functools.partial):  # Prevent double-partial-ing
        command = functools.partial(discord.ext.commands.command, cls=SignificantCommand)
        discord.ext.commands.command = command
    if not isinstance(discord.ext.commands.group, functools.partial):  # Prevent double-partial-ing
        group = functools.partial(discord.ext.commands.group, cls=SignificantGroup)
        discord.ext.commands.group = group
