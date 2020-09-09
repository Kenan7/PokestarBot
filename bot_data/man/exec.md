Execute code. No output is returned, but supports function definitions and complex imports.

Arguments:
* `code`: The code to evaluate. The code can either be one block of code, without triple backticks (\`\`\`), or one or more blocks of code, delimited with triple backticks (\`\`\`) and containing no language, `py`, or `python.`

Examples:

Note: Do not copy-paste the examples, as they are using invisible characters, and will not work.

* `%exec print(2+2)`
* ```
%exec ``​`python
def x():
    print("x", "y")

x()
``​`
```
