from regex.parser import *
from regex.statemachine import *


def test_tokenizer():
    tokens = list(tokenize(iter('^ab(|)[][^c]*$')))
    assert tokens == [
        Token.BEGIN, 'a', 'b', Token.LPAR, Token.OR, Token.RPAR,
        Token.LBRACKET, Token.RBRACKET, Token.LBRACKET, Token.NOT, 'c', Token.RBRACKET,
        Token.STAR, Token.END, Token.EOF,
    ]


def test_paser():
    ast = regex_from_string('^ab(a||b|)*|c$')
    expected = Or(
        Cat(
            Char(Token.BEGIN),
            Char('a'),
            Char('b'),
            Star(
                Or(Char('a'), Empty(), Char('b'), Empty())
            )
        ),
        Cat(
            Char('c'),
            Char(Token.END),
        ),
    )

    assert ast == expected


def test_match_begin():
    cases = (
        ('abc',    'abcd',  3),
        ('a*',     'aaaaa', 5),
        ('a*b',    'bb',    1),
        ('a*b',    'aaabb', 4),
        ('a*b',    'aaaa',  0),
        ('.a.*',   'basdf', 5),
        ('a|cd',   'a',     1),
        ('a|cd',   'cda',   2),
        ('|a||b|', 'ab',    1),
        ('|a||b|', '',      0),
        ('|a||b|', 'ba',    1),
    )

    for pattern, string, ans in cases:
        re = regex_from_string(pattern)
        assert regex_match_begin(re, string) is ans
