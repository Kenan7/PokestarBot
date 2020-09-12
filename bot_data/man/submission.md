Get information on a submission from Reddit.

Arguments:
* `link` The link or Base36 ID of a Reddit submission. Multiple links or Base36 IDs can be supplied, as long as they are separated by spaces.

The base 36 ID can be found in the second-to-last part of the url. In this URL: `https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more`, the submission Base36 ID is `in8x2j`.

Note: Using a comment link will only show the submission data.

Note: Images for NSFW submissions will not be shown if the channel is not NSFW.

Examples:
* `{prefix}submission https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more`
* `{prefix}submission https://www.reddit.com/r/Catswithjobs/comments/in8x2j/never_wears_a_mask_always_demanding_more_and_more https://www.reddit.com/r/mildlyinteresting/comments/ink6nn/the_wick_of_my_candle_looks_like_a_mushroomtree/`
