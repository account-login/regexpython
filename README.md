# regex

Regular expression engine in Python.


## Feature implenmented

- unicode support
- dot `.`
- begin/end of string `^`, `$`
- star `x*`
- plus `x+`
- question mark `x?`
- bracket
    * enumeration `[abc]`
    * complement set `[^abc]`
    * range `[a-z0-9]`
- or `a|b`
- parentheses `(...)`
- escapes
    * begin, end `\A`, `\Z`
    * constant `\a`, `\b`, `\f`, `\n`, `\r`, `\t`, `\v`, `\\`
    * character `\xhh`, `\uhhhh`, `\Uhhhhhhhh`

### API

TBA


## Feature not implemented

- grouping by `(...)`
- non-greedy qualifier `*?`, `+?`, `??`, `x{a,b}?`
- repeat `x{a}`, `x{a,}`, `x{a,b}`
- zero length assertions
- escapes
    * group number `\1`
    * boundary `\b`
    * predifined range `\d`, `\s`, `\w`
- various compilation flags
- missing APIs
    * `search`
    * `split`
    * `findall`
    * `finditer`
    * `sub`
    * `escape`
- DFA minimization
- user friendly error message
- caching
