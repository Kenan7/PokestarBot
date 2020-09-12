Remove a role to mutliple users

Arguments:
* `role`: The role to remove
* `member_or_role`: The members or roles that should get the role. If a role is given, then all members that have the role will get the role. Multiple members and/or roles can be provided as long as they are separated by a space.

Member Format:
* Individual User: `@user` / `UserID` / `Username#XXXX` / `Nickname` / `Username` (if they do not have a nickname)
* Role: `@role` / `"Role Name"` (Quotation escape any role names with spaces)

Examples:
* `{prefix}role remove "Gamer" @PokestarBot#9763`
* `{prefix}role remove "Gamer" "Epic Gamer"`
* `{prefix}role remove "Gamer" @PokestarBot#9763 @Rythm#3722 "Epic Gamer"`
