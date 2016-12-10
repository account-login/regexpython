from enum import Enum


class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class Token(AutoNumber):
    OR = ()

    LPAR = ()
    RPAR = ()

    LBRACKET = ()
    RBRACKET = ()

    STAR = ()
    NOT = ()

    DOT = ()

    BEGIN = ()
    END = ()


def read_escape(chars):
    return next(chars)


def tokenizer(chars):
    direct_yield = {
        '|': Token.OR,
        '(': Token.LPAR,
        ')': Token.RPAR,
        '[': Token.LBRACKET,
        ']': Token.RBRACKET,
        '*': Token.STAR,
        '.': Token.DOT,
        # '^': Token.BEGIN,
        '$': Token.END,
    }

    prev = None
    while True:
        try:
            ch = next(chars)
        except StopIteration:
            raise

        if ch in direct_yield:
            tok = direct_yield[ch]
        elif ch == '^':
            if prev == Token.LBRACKET:
                tok = Token.NOT
            else:
                tok = Token.BEGIN
        elif ch == '\\':
            tok = read_escape(chars)
        else:
            tok = ch

        prev = tok
        yield tok
