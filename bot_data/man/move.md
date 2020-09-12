Mass-move users to a voice channel. The bot can only move users that are in voice channels. The bot can also move users to voice channels they normally would not be able to join.

Arguments:
* `channel`: The name of the voice channel to move to.
* `users`: The users to move. Multiple different users may be seperated with spaces.

User Format:
* Individual User: `@user` / `Username#XXXX` / `Nickname` / `Username` (if they do not have a nickname)
* Role: `@role` / `"Role Name"` (Quotation escape any role names with spaces)
* Voice Channel: `Voice Channel Name`
* All users in all voice channels: `all`

Examples:
* `{prefix}move general music`
* `{prefix}move general @PokestarBot#9763`
* `{prefix}move general @PokestarBot#9763 @Rythm#3722`
* `{prefix}move general "epic gamer"`
* `{prefix}move general all`
* `{prefix}move general music @PokestarBot#9763 "epic gamer"`
