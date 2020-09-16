import enum
import os
import re

# Global
bot_version = "3.2.1.1"

# help.py
help_file_dir = os.path.abspath(os.path.join(__file__, "..", "man"))
help_file_template = "* `{}{}`: **{}**"

# management.py
log_line = re.compile(r"\((DEBUG|INFO|WARNING|ERROR|CRITICAL)\):")
channel_types = {"Generic Bot Channels": ["announcements", "bot-spam"],
                 "Misc. Bot Services"  : ["anime-and-manga-updates", "message-goals", "admin-log"],
                 "Reddit Services"     : ["modqueue", "unmoderated", "modlog"]}

# reddit.py
subreddit = re.compile("r/([A-Za-z0-9_]{1,21})")
user = re.compile("(?:user|u)/([A-Za-z0-9_]{1,32})")
blockquote = re.compile(r"^>([^\s>])", re.MULTILINE | re.IGNORECASE | re.UNICODE)

# redditmod.py
submittable_actions = {"approvelink"    : "Approved Submission",
                       "approvecomment" : "Approved Comment",
                       "ignorereports"  : "Ignored Reports For Item",
                       "removelink"     : "Removed Link",
                       "removecomment"  : "Removed Comment",
                       "sticky"         : "Stickied Item",
                       "distinguish"    : "Distinguished Item",
                       "spamcomment"    : "Spam Comment",
                       "spamlink"       : "Spam Link",
                       "unsticky"       : "Unstickied Item",
                       "lock"           : "Locked Item",
                       "unlock"         : "Unlocked Item",
                       "marknsfw"       : "Marked Item as NSFW",
                       "unignorereports": "Unignored Reports For Item",
                       "spoiler"        : "Marked Item As Spoiler",
                       "unspoiler"      : "Unmarked Item As Spoiler",
                       "editflair"      : "Edit Flair Of Item"}
user_actions = {"addcontributor"       : "Add Contributor",
                "banuser"              : "Ban User",
                "muteuser"             : "Mute User",
                "removecontributor"    : "Remove Contributor",
                "acceptmoderatorinvite": "Accept Moderator Invite",
                "invitemoderator"      : "Invite Moderator",
                "unbanuser"            : "Unban User",
                "unmuteuser"           : "Unmute User",
                "setpermissions"       : "Set User Permissions"}

# role.py
user_template_role = "* {}\n"
role_template_role = "* **{}**: {} members\n"
discord_colors = {'blue'        : '#3498db',
                  'blurple'     : '#7289da',
                  'dark_blue'   : '#206694',
                  'dark_gold'   : '#c27c0e',
                  'dark_gray'   : '#607d8b',
                  'dark_green'  : '#1f8b4c',
                  'dark_grey'   : '#607d8b',
                  'dark_magenta': '#ad1457',
                  'dark_orange' : '#a84300',
                  'dark_purple' : '#71368a',
                  'dark_red'    : '#992d22',
                  'dark_teal'   : '#11806a',
                  'darker_gray' : '#546e7a',
                  'darker_grey' : '#546e7a',
                  'default'     : '#000000',
                  'gold'        : '#f1c40f',
                  'green'       : '#2ecc71',
                  'greyple'     : '#99aab5',
                  'light_gray'  : '#979c9f',
                  'light_grey'  : '#979c9f',
                  'lighter_gray': '#95a5a6',
                  'lighter_grey': '#95a5a6',
                  'magenta'     : '#e91e63',
                  'orange'      : '#e67e22',
                  'purple'      : '#9b59b6',
                  'red'         : '#e74c3c',
                  'teal'        : '#1abc9c'}
css_colors = {'aliceblue'           : '#f0f8ff',
              'antiquewhite'        : '#faebd7',
              'aqua'                : '#00ffff',
              'aquamarine'          : '#7fffd4',
              'azure'               : '#f0ffff',
              'beige'               : '#f5f5dc',
              'bisque'              : '#ffe4c4',
              'black'               : '#000000',
              'blanchedalmond'      : '#ffebcd',
              'blueviolet'          : '#8a2be2',
              'brown'               : '#a52a2a',
              'burlywood'           : '#deb887',
              'cadetblue'           : '#5f9ea0',
              'chartreuse'          : '#7fff00',
              'chocolate'           : '#d2691e',
              'coral'               : '#ff7f50',
              'cornflowerblue'      : '#6495ed',
              'cornsilk'            : '#fff8dc',
              'crimson'             : '#dc143c',
              'cyan'                : '#00ffff',
              'darkblue'            : '#00008b',
              'darkcyan'            : '#008b8b',
              'darkgoldenrod'       : '#b8860b',
              'darkgray'            : '#a9a9a9',
              'darkgrey'            : '#a9a9a9',
              'darkgreen'           : '#006400',
              'darkkhaki'           : '#bdb76b',
              'darkmagenta'         : '#8b008b',
              'darkolivegreen'      : '#556b2f',
              'darkorange'          : '#ff8c00',
              'darkorchid'          : '#9932cc',
              'darkred'             : '#8b0000',
              'darksalmon'          : '#e9967a',
              'darkseagreen'        : '#8fbc8f',
              'darkslateblue'       : '#483d8b',
              'darkslategray'       : '#2f4f4f',
              'darkslategrey'       : '#2f4f4f',
              'darkturquoise'       : '#00ced1',
              'darkviolet'          : '#9400d3',
              'deeppink'            : '#ff1493',
              'deepskyblue'         : '#00bfff',
              'dimgray'             : '#696969',
              'dimgrey'             : '#696969',
              'dodgerblue'          : '#1e90ff',
              'firebrick'           : '#b22222',
              'floralwhite'         : '#fffaf0',
              'forestgreen'         : '#228b22',
              'fuchsia'             : '#ff00ff',
              'gainsboro'           : '#dcdcdc',
              'ghostwhite'          : '#f8f8ff',
              'goldenrod'           : '#daa520',
              'gray'                : '#808080',
              'grey'                : '#808080',
              'greenyellow'         : '#adff2f',
              'honeydew'            : '#f0fff0',
              'hotpink'             : '#ff69b4',
              'indianred'           : '#cd5c5c',
              'indigo'              : '#4b0082',
              'ivory'               : '#fffff0',
              'khaki'               : '#f0e68c',
              'lavender'            : '#e6e6fa',
              'lavenderblush'       : '#fff0f5',
              'lawngreen'           : '#7cfc00',
              'lemonchiffon'        : '#fffacd',
              'lightblue'           : '#add8e6',
              'lightcoral'          : '#f08080',
              'lightcyan'           : '#e0ffff',
              'lightgoldenrodyellow': '#fafad2',
              'lightgray'           : '#d3d3d3',
              'lightgrey'           : '#d3d3d3',
              'lightgreen'          : '#90ee90',
              'lightpink'           : '#ffb6c1',
              'lightsalmon'         : '#ffa07a',
              'lightseagreen'       : '#20b2aa',
              'lightskyblue'        : '#87cefa',
              'lightslategray'      : '#778899',
              'lightslategrey'      : '#778899',
              'lightsteelblue'      : '#b0c4de',
              'lightyellow'         : '#ffffe0',
              'lime'                : '#00ff00',
              'limegreen'           : '#32cd32',
              'linen'               : '#faf0e6',
              'maroon'              : '#800000',
              'mediumaquamarine'    : '#66cdaa',
              'mediumblue'          : '#0000cd',
              'mediumorchid'        : '#ba55d3',
              'mediumpurple'        : '#9370db',
              'mediumseagreen'      : '#3cb371',
              'mediumslateblue'     : '#7b68ee',
              'mediumspringgreen'   : '#00fa9a',
              'mediumturquoise'     : '#48d1cc',
              'mediumvioletred'     : '#c71585',
              'midnightblue'        : '#191970',
              'mintcream'           : '#f5fffa',
              'mistyrose'           : '#ffe4e1',
              'moccasin'            : '#ffe4b5',
              'navajowhite'         : '#ffdead',
              'navy'                : '#000080',
              'oldlace'             : '#fdf5e6',
              'olive'               : '#808000',
              'olivedrab'           : '#6b8e23',
              'orangered'           : '#ff4500',
              'orchid'              : '#da70d6',
              'palegoldenrod'       : '#eee8aa',
              'palegreen'           : '#98fb98',
              'paleturquoise'       : '#afeeee',
              'palevioletred'       : '#db7093',
              'papayawhip'          : '#ffefd5',
              'peachpuff'           : '#ffdab9',
              'peru'                : '#cd853f',
              'pink'                : '#ffc0cb',
              'plum'                : '#dda0dd',
              'powderblue'          : '#b0e0e6',
              'rebeccapurple'       : '#663399',
              'rosybrown'           : '#bc8f8f',
              'royalblue'           : '#4169e1',
              'saddlebrown'         : '#8b4513',
              'salmon'              : '#fa8072',
              'sandybrown'          : '#f4a460',
              'seagreen'            : '#2e8b57',
              'seashell'            : '#fff5ee',
              'sienna'              : '#a0522d',
              'silver'              : '#c0c0c0',
              'skyblue'             : '#87ceeb',
              'slateblue'           : '#6a5acd',
              'slategray'           : '#708090',
              'slategrey'           : '#708090',
              'snow'                : '#fffafa',
              'springgreen'         : '#00ff7f',
              'steelblue'           : '#4682b4',
              'tan'                 : '#d2b48c',
              'thistle'             : '#d8bfd8',
              'tomato'              : '#ff6347',
              'turquoise'           : '#40e0d0',
              'violet'              : '#ee82ee',
              'wheat'               : '#f5deb3',
              'white'               : '#ffffff',
              'whitesmoke'          : '#f5f5f5',
              'yellow'              : '#ffff00',
              'yellowgreen'         : '#9acd32'}
color_str_set = set("#0123456789abcdef")


# stats.py
stats_template = "* **{}**{}: **{}** messages (max **{}** messages)"

# time.py
strftime_format = "%A, %B %d, %Y @ %I:%M:%S %p"

# updates.py
guyamoe = re.compile(r"https://(?:www\.|)guya\.moe/read/manga/([^/\s]+)")
mangadex = re.compile(r"https://(?:www\.|)mangadex\.org/(?:title|manga)/([0-9]+)")
nyaasi = re.compile(r"https://nyaa.si/view/([0-9]+)")
horriblesubs = re.compile(r"\[HorribleSubs\] ([\S ]+) - ([0-9]+) \[([0-9]+)p\].mkv")


# waifu.py
class Status(enum.IntEnum):
    ALL = 0
    OPEN = 1
    VOTABLE = 2
    LOCKED = 4
    CLOSED = 3
