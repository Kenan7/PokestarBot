Functions like `%role add` but instead of taking an existing role, takes a name for a new role and creates & uses that role instead.

Arguments:
* `role_name`: The name of the new role. If the name has spaces, it must be quotation-escaped.
* `member_or_role`: The members or roles that should get the role. If a role is given, then all members that have the role will get the role. Multiple members and/or roles can be provided as long as they are separated by a space.

Member Format:
* Individual User: `@user` / `Username#XXXX` / `Nickname` / `Username` (if they do not have a nickname)
* Role: `@role` / `"Role Name"` (Quotation escape any role names with spaces)

Examples:
* `%role create Test @PokestarBot#9763`
* `%role create Test @PokestarBot#9763 @Rythm#3722`
* `%role create Test @PokestarBot#9763 "Another Role"`
* `%role create "Test Role" @PokestarBot#9763`
