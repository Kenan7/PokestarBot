Get stats for the entire Guild. This requires the Guild to have a message-goals channel defined under the guild-channel database (`%channel add`).

Arguments:
* `min_messages`: The minimum amount of messages a user or channel has to have in order to show up on the list. Defaults to 5.
* `limit`: The maximum number of users to show. Defaults to no limit.

Note: Due to discord.py limitations, you *need* to specify `min_messages` before `limit`. In this case, you can provide 0 for `min_messages`.

Examples:
* `%stats global`
* `%stats global 20`
* `%stats global 0 20`
