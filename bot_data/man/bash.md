Execute the given bash code. Tools that are available depend on the system that the bot is running on. The command acts like a shell, but no command that takes user input will work.

Code can be given two ways:

1. Anything after the command and a space will be part of the bash script, if it does not contain triple backticks (\`\`\`).
2. Triple backticks can be used to show a code block. This way, multiple blocks can be run with one command. The language can be omitted, or if included, must be either "bash" or "shell".

Examples:
* `{prefix}bash echo 5`
* ```shell
%bash ``​`echo 5``​` `​``shell
echo 5``​`
```
