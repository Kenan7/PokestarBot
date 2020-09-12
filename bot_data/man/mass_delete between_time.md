Delete all messages between two times.

Arguments:
* `channel`: The channel to delete messages in. Defaults to the current channel.
* `users`: The users to delete messages from. Defaults to all users. Multiple users can be specified with a space.
* `after_time`: All messages after this time will be deleted.
* `before_time`: All messages before this time will be deleted.

Note: Any arguments that have spaces need to be quoted (surrounded in quotations) due to how discord.py deals with arguments. View the examples for an example.

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
* `{prefix}mass_delete after_time yesterday today`
* `{prefix}mass_delete after_time #general yesterday today`
* `{prefix}mass_delete after_time #general @PokestarBot#9763 yesterday today`
* `{prefix}mass_delete after_time #general @PokestarBot#9763 @Rythm#3722 yesterday today`
* `{prefix}mass_delete after_time sunday tuesday`
* `{prefix}mass_delete after_time 5 2`
* `{prefix}mass_delete after_time 9/2/20 9/5/20`
* `{prefix}mass_delete after_time 23:00:00 23:30:00`
* `{prefix}mass_delete after_time "11:00:00 PM" "11:30:00 PM"`
* `{prefix}mass_delete after_time "9/2/20 11:00:00 PM" "9/5/20 11:30:00 PM"`
