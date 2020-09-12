Show a Reddit comment as well as 15 replies (including sub-replies). This will limit the length of each reply to 300 characters.

Arguments:
* `link`: The link to a comment on Reddit, or the Base36 ID of the comment. Multiple links or Base36 IDs can be supplied, as long as they are separated by spaces.

The base 36 ID can be found in the last part of the url. In this URL: `https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt`, the comment Base36 ID is `g46dndt`.

Examples:
* `{prefix}thread https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt`
* `{prefix}thread g46rltl`
* `{prefix}thread https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt g46rltl`
