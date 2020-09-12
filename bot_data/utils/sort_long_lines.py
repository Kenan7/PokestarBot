import logging
import textwrap
from typing import List, Optional

logger = logging.getLogger(__name__)


async def break_into_groups(text: Optional[str] = None, heading: str = "", template: str = "```python\n",
                            ending: str = "\n```", line_template: str = "", lines: Optional[List[str]] = None) -> List[str]:
    if text is None:
        text = ""
    lines = [line.replace("```", "``​`") for line in (text.splitlines(False) if not lines else lines)]
    return_lines = []
    msg = "{}{}".format(heading, template)
    allocation = 1024 - len(template + ending)
    while lines:
        line = lines.pop(0)
        if len(line) > allocation:  # Special case
            extra_lines = textwrap.wrap(line, width=(allocation - len(msg) - len(line_template) - 2), break_on_hyphens=True, replace_whitespace=False)
            lines = extra_lines + lines
            continue
        newmsg = msg + (line if not line_template else line_template.format(line)) + "\n"
        if len(newmsg.rstrip()) > allocation:
            return_lines.append(msg.rstrip() + ending)
            msg = template + (line if not line_template else line_template.format(line)) + "\n"
        else:
            msg = newmsg
    if msg:
        return_lines.append(msg.rstrip() + ending)
    return return_lines
