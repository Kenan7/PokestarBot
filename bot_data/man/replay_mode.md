Re-plays all messages in the channel that match the given prefix, and acts like they were sent again. This is useful to re-do all commands in a channel.

Arguments:
* `channel`: The channel to scan for messages. Defaults to the current channel.
* `users`: The users that the messages have to be from. Defaults to all users. Multiple users can be provided, as long as they are separated by spaces.
* `prefix`: The message prefix. Defaults to `%`.

Examples:
* `%replay_mode`
* `%replay_mode %help`
* `%replay_mode #general %help`
* `%replay_mode #general @PokestarBot#9763 %help`
* `%replay_mode #general @PokestarBot#9763 @Rythm#3722 %help`
