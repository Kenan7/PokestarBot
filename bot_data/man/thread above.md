Similar to `%thread`, but it only shows the comments above the provided comment, not any replies. Also will not cut comments to 300 characters.

Arguments:
* `link`: The link to a comment on Reddit, or the Base36 ID of the comment. Multiple links or Base36 IDs can be supplied, as long as they are separated by spaces.

The base 36 ID can be found in the last part of the url. In this URL: `https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt`, the comment Base36 ID is `g46dndt`.

Examples:
* `%thread above https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt`
* `%thread above g46rltl`
* `%thread above https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more/g46dndt g46rltl`
