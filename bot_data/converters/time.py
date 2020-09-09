import datetime
import re
from typing import Dict

import discord.ext.commands
import pytz

NY = pytz.timezone("America/New_York")


class TimeConverter(discord.ext.commands.Converter):
    DATE_REGEX = re.compile(r"^([0-9]{1,2})([/-])([0-9]{1,2})(?:[/-])([0-9]{2,4})")
    TIME_REGEX = re.compile(r"^([0-9]{1,2})([:-])([0-9]{1,2})(?:[:-])([0-9]{1,2})((?: |)[AP]M|)")
    WORD_DATA = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}

    @staticmethod
    def day_data(day) -> Dict[int, int]:
        return {day: 7, (day + 1) % 7: 6, (day + 2) % 7: 5, (day + 3) % 7: 4, (day + 4) % 7: 3, (day + 5) % 7: 2, (day + 6) % 7: 1}

    @staticmethod
    def convert_offset(dt: datetime.datetime) -> datetime.datetime:
        offset = NY.utcoffset(datetime.datetime.utcnow())
        return dt - offset

    @classmethod
    def day(cls, days: float = 0) -> datetime.datetime:
        base_dt = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC).astimezone(tz=NY)
        data = base_dt.year, base_dt.month, base_dt.day
        return cls.convert_offset(datetime.datetime(*data)) - datetime.timedelta(days=days)

    @classmethod
    def get_weekday(cls, weekday: str) -> datetime.datetime:
        val = cls.WORD_DATA[weekday]
        current_day = cls.day().weekday()
        return cls.day(cls.day_data(current_day)[val])

    async def convert(self, ctx: discord.ext.commands.Context, argument: str) -> datetime.datetime:
        if argument.lower() == "today":
            return self.day()
        elif argument.lower() == "yesterday":
            return self.day(1)
        elif argument.lower() in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            return self.get_weekday(argument.lower())
        elif argument.isdecimal():
            num = float(argument)
            return self.day(num)
        elif " " in argument:
            date, sep, time = argument.upper().partition(" ")
            if match := self.DATE_REGEX.match(argument.upper()):
                month, d_symbol, day, year = match.group(1, 2, 3, 4)
                if len(year) == 3:
                    raise discord.ext.commands.BadArgument("Year cannot be 3 digits.")
                month = month.zfill(2)
                day = day.zfill(2)
                year = year.zfill(4)
                date_format = "%m{0}%d{0}%Y".format(d_symbol)
            else:
                raise discord.ext.commands.BadArgument("Date argument is invalid.")
            if match2 := self.TIME_REGEX.match(time):
                hour, t_symbol, minute, second, am_or_pm = match2.group(1, 2, 3, 4, 5)
                hour = hour.zfill(2)
                minute = minute.zfill(0)
                second = second.zfill(0)
                if am_or_pm:
                    if " " == am_or_pm[0]:
                        time_format = "%I{0}%M{0}%S %p".format(t_symbol)
                    else:
                        time_format = "%I{0}%M{0}%S%p".format(t_symbol)
                else:
                    time_format = "%H{0}%M{0}%S".format(t_symbol)
            else:
                raise discord.ext.commands.BadArgument("Time argument is invalid.")
            combined_format = date_format + " " + time_format
            return datetime.datetime.strptime(f"{month}{d_symbol}{day}{d_symbol}{year} {hour}{t_symbol}{minute}{t_symbol}{second}{am_or_pm}",
                                              combined_format)
        elif match := self.DATE_REGEX.match(argument.upper()):
            month, d_symbol, day, year = match.group(1, 2, 3, 4)
            if len(year) == 3:
                raise discord.ext.commands.BadArgument("Year cannot be 3 digits.")
            month = month.zfill(2)
            day = day.zfill(2)
            if len(year) == 2:
                year = "20" + year
            date_format = "%m{0}%d{0}%Y".format(d_symbol)
            return datetime.datetime.strptime(f"{month}{d_symbol}{day}{d_symbol}{year}", date_format)
        elif match := self.TIME_REGEX.match(argument.upper()):
            hour, t_symbol, minute, second, am_or_pm = match.group(1, 2, 3, 4, 5)
            hour = hour.zfill(2)
            minute = minute.zfill(0)
            second = second.zfill(0)
            if am_or_pm:
                if " " == am_or_pm[0]:
                    time_format = "%I{0}%M{0}%S %p".format(t_symbol)
                else:
                    time_format = "%I{0}%M{0}%S%p".format(t_symbol)
            else:
                time_format = "%H{0}%M{0}%S".format(t_symbol)
            return datetime.datetime.strptime(f"{hour}{t_symbol}{minute}{t_symbol}{second}{am_or_pm}", time_format)
        else:
            raise discord.ext.commands.BadArgument("Date format does not match any given date format.")
