Get a copy of the chat log for the channel.

Arguments:
* `channel`: The channel to get a chat log of. Defaults to the current channel.
* `number`: The number of messages to get. Leave blank to get all messages.

Channel Format: `#<channel-name>` / `<channel-name>` / `channel_id`

Note: Due to the fact that channels can also be numbers (channel ID), if you want a specific number of messages, you *have to* specify the channel before the number.

Examples:
* `{prefix}chat_log`
* `{prefix}chat_log #general`
* `{prefix}chat_log #memes 50`
