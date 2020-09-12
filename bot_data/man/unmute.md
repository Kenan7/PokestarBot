Unmute all the users in a voice channel except for the provided exceptions.

Arguments:
* `voice_channel`: The name or channel ID of the voice channel.
* `exceptions`: The exceptions. Can be a user or a role. Different users or roles must be separated with a space.

Exception Member Format:
* Individual User: `@user` / `UserID` / `Username#XXXX` / `Nickname` / `Username` (if they do not have a nickname)
* Role: `@role` / `"Role Name"` (Quotation escape any role names with spaces)

Examples:
* `{prefix}unnmute general`
* `{prefix}unnmute general @PokestarBot#9763`
* `{prefix}unnmute general Mod`
* `{prefix}unnmute general @PokestarBot#9763 Mod`
