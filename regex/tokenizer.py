from regex.utils import BufferedGen
from regex.errors import IllegalEscape


class TokenMeta(type):
    def __new__(metacls, name, bases, namespaces):
        sub_types = set()
        for attr, value in namespaces.items():
            if value == ():
                sub_types.add(attr)
        for attr in sub_types:
            del namespaces[attr]

        klass = super().__new__(metacls, name, bases, namespaces)
        for attr in sub_types:
            sub_cls = super().__new__(metacls, attr, (klass,), namespaces)
            setattr(klass, attr, sub_cls)

        return klass


class Token(metaclass=TokenMeta):
    OR = ()         # type: TokenMeta

    LPAR = ()       # type: TokenMeta
    RPAR = ()       # type: TokenMeta

    LBRACKET = ()   # type: TokenMeta
    RBRACKET = ()   # type: TokenMeta
    DASH = ()       # type: TokenMeta
    NOT = ()        # type: TokenMeta

    STAR = ()       # type: TokenMeta
    PLUS = ()       # type: TokenMeta
    QUESTION = ()   # type: TokenMeta

    DOT = ()        # type: TokenMeta
    CHAR = ()       # type: TokenMeta
    ESCAPE = ()     # type: TokenMeta

    BEGIN = ()      # type: TokenMeta
    END = ()        # type: TokenMeta

    EOF = ()        # type: TokenMeta

    def __init__(self, value=None):
        self.value = value
        self.type = self.__class__

    def __eq__(self, other):
        return self.type, self.value == other.type, other.value

    def __hash__(self):
        return hash((self.type, self.value))


def read_escape(chars: BufferedGen, in_bracket: bool) -> Token:
    ascii_escpes = {
        'a': '\a',
        # 'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t',
        'v': '\v',
        '\\': '\\',
    }

    def check_hex_digits(digits):
        for d in digits:
            if d not in '0123456789abcdef':
                return False
        else:
            return True

    ch = chars.get()

    if ch == 'b':
        if in_bracket:
            return Token.CHAR('\b')
        else:
            return Token.ESCAPE(ch)
    elif ch == 'B':
        if in_bracket:
            return Token.CHAR(ch)
        else:
            return Token.ESCAPE(ch)
    if ch in ascii_escpes:
        return Token.CHAR(ascii_escpes[ch])
    elif ch == 'A':
        return Token.BEGIN()
    elif ch == 'Z':
        return Token.END()
    elif ch in 'xuU':
        digits_num = {'x': 2, 'u': 4, 'U': 8}[ch]
        digits = [ chars.get().lower() for _ in range(digits_num) ]
        if not check_hex_digits(digits):
            raise IllegalEscape('\\' + ch + ''.join(digits))
        return Token.CHAR(chr(int(''.join(digits), base=16)))
    elif ch in 'wWsSdD':
        return Token.ESCAPE(ch)
    elif ch.isdecimal():
        raise NotImplementedError
    else:
        return Token.CHAR(ch)


def tokenize(chars: BufferedGen):
    direct_yield = {
        '|': Token.OR(),
        '(': Token.LPAR(),
        ')': Token.RPAR(),
        # '[': Token.LBRACKET(),
        # ']': Token.RBRACKET(),
        '*': Token.STAR(),
        '+': Token.PLUS(),
        '?': Token.QUESTION(),
        '.': Token.DOT(),
        '^': Token.BEGIN(),
        '$': Token.END(),
    }

    in_bracket = False
    prev = None
    while True:
        try:
            ch = chars.get()
        except StopIteration:
            yield Token.EOF()
            raise

        if in_bracket:
            if ch == '\\':
                try:
                    tok = read_escape(chars, in_bracket)
                except StopIteration:
                    raise IllegalEscape
            elif ch == ']':
                if prev.type in (Token.LBRACKET, Token.NOT):
                    # empty bracket not allowed, left bracket must follow a regular char.
                    tok = Token.CHAR(ch)
                else:
                    in_bracket = False
                    tok = Token.RBRACKET()
            elif ch == '^':
                if prev.type == Token.LBRACKET:
                    tok = Token.NOT()
                else:
                    tok = Token.CHAR(ch)
            elif ch == '-':
                tok = Token.DASH()
            else:
                tok = Token.CHAR(ch)
        else:
            if ch in direct_yield:
                tok = direct_yield[ch]
            elif ch == '[':
                in_bracket = True
                tok = Token.LBRACKET()
            elif ch == '\\':
                try:
                    tok = read_escape(chars, in_bracket)
                except StopIteration:
                    raise IllegalEscape
            else:
                tok = Token.CHAR(ch)

        prev = tok
        yield tok
