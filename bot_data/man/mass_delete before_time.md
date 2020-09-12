Delete all messages before a specific time.

Arguments:
* `channel`: The channel to delete messages in. Defaults to the current channel.
* `users`: The users to delete messages from. Defaults to all users. Multiple users can be specified with a space.
* `time`: The time to delete before. Can be provided in multiple formats. All times are assumed to be in NYC time, so UTC-4 during Daylight Savings and UTC-5 otherwise.

Time Formats:
* Date only: `M/D/YY` / `MM/DD/YYYY` / `M-D-YY` / `MN-DD-YYYY` (Assumed to begin at midnight for that day)
* Time only: `H:M:S` / `HH:MM:SS` / `H-M-S` / `HH-MM-SS` / `H:M:S AM/PM` / `HH:MM:SS AM/PM` / `H-M-S AM/PM` / `HH-MM-SS AM/PM` / `H:M:SAM/PM` / `HH:MM:SSAM/PM` / `H-M-SAM/PM` / `HH-MM-SSAM/PM` (Assumed to be today)
Note: If AM/PM is not provided, it is assumed to be 24-hour time.
* Date and time: A combination of the Date and Time only formats, with Date before time.
* Today: `today` (Assumed to begin at midnight for that day)
* Yesterday: `yesterday`
* Day of the week: `Sunday` / `Monday` / `Tuesday` / `Wednesday` / `Thursday` / `Friday` / `Saturday` (Assumed to begin at midnight for that day)
* X days ago: `x` where x is a number. (Assumed to begin at midnight for that day)

Examples:
* `{prefix}mass_delete before_time today`
* `{prefix}mass_delete before_time #general today`
* `{prefix}mass_delete before_time #general @PokestarBot#9763 today`
* `{prefix}mass_delete before_time #general @PokestarBot#9763 @Rythm#3722 today`
* `{prefix}mass_delete before_time yesterday`
* `{prefix}mass_delete before_time sunday`
* `{prefix}mass_delete before_time 5`
* `{prefix}mass_delete before_time 9/2/20`
* `{prefix}mass_delete before_time 23:00:00`
* `{prefix}mass_delete before_time 11:00:00 PM`
* `{prefix}mass_delete before_time 9/2/20 07:00:00 PM`
