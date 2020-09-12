Re-send the last image message by the user calling and mark each image as a spoiler.

Arguments:
* `spoiler_text`: Whether or not to surround the text in spoiler syntax (`||<text>||`). Defaults to False.

Boolean Values:
* Yes: `y` / `yes` / `true` / `1` / `on`
* No: `n` / `n` / `false` / `0` / `off`

Examples:
* `{prefix}spoiler_msg`
* `{prefix}spoiler_msg y`
* `{prefix}spoiler_msg no`
