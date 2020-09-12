Delete all messages before the provided message.

Arguments:
* `channel`: The channel to delete messages in. Defaults to the current channel. Note: If the message is not from the current channel, the bot will *still* delete messages, so double-check that you provided the right channel.
* `users`: The users to delete messages from. Defaults to all users. Multiple users can be specified with a space.
* `message`: The message to delete before.

Examples:
* `{prefix}mass_delete before https://discordapp.com/channels/728750698816340028/728756333150470195/752159027886161990`
* `{prefix}mass_delete before #general https://discordapp.com/channels/728750698816340028/728756333150470195/752159027886161990`
* `{prefix}mass_delete before #general @PokestarBot#9763 https://discordapp.com/channels/728750698816340028/728756333150470195/752159027886161990`
* `{prefix}mass_delete before #general @PokestarBot#9763 @Rythm#3722 https://discordapp.com/channels/728750698816340028/728756333150470195/752159027886161990`
