from regex.parser import *
from regex.statemachine import *


def token_list_from_string(string):
    return list(tokenize(BufferedGen(iter(string))))


def test_tokenizer_basic():
    tokens = token_list_from_string('')
    assert tokens == [Token.EOF]

    tokens = token_list_from_string('^ab(|)[][^c]*$')
    assert tokens == [
        Token.BEGIN, 'a', 'b', Token.LPAR, Token.OR, Token.RPAR,
        Token.LBRACKET, Token.RBRACKET, Token.LBRACKET, Token.NOT, 'c', Token.RBRACKET,
        Token.STAR, Token.END, Token.EOF,
    ]


def test_tokenizer_right_bracket():
    assert token_list_from_string(']') == [']', Token.EOF]


def test_tokenizer_bracket_no_special():
    tokens = token_list_from_string('[^[|*+?^()]')
    assert tokens == [Token.LBRACKET, Token.NOT] + list('[|*+?^()') + [Token.RBRACKET, Token.EOF]


def test_tokenizer_bracket_range():
    tokens = token_list_from_string('[a-c]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[a-c-d]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.DASH, 'd', Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[a-]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[-a-]')
    assert tokens == [Token.LBRACKET, Token.DASH, 'a', Token.DASH, Token.RBRACKET, Token.EOF]


def test_paser_basic():
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


def test_parser_bracket_basic():
    ast = regex_from_string('[]')
    assert ast == Empty
    ast = regex_from_string('[abc]')
    assert ast == Or(
        Char('a'),
        Char('b'),
        Char('c'),
    )


def test_parser_bracket_range():
    ast = regex_from_string('[a-c]')
    assert ast == CharRange('a', 'c')

    ast = regex_from_string('[a-c-d]')
    assert ast == Or(
        CharRange('a', 'c'),
        Char('-'),
        Char('d'),
    )

    ast = regex_from_string('[a-]')
    assert ast == Or(
        Char('a'),
        Char('-'),
    )

    ast = regex_from_string('[-a-]')
    assert ast == Or(
        Char('-'),
        Char('a'),
        Char('-'),
    )


def test_match_begin():
    cases = (
        ('abc',         'abcd',     3),
        ('a*',          'aaaaa',    5),
        ('a*b',         'bb',       1),
        ('a*b',         'aaabb',    4),
        ('a*b',         'aaaa',     0),
        ('.a.*',        'basdf',    5),
        ('a|cd',        'a',        1),
        ('a|cd',        'cda',      2),
        ('|a||b|',      'ab',       1),
        ('|a||b|',      '',         0),
        ('|a||b|',      'ba',       1),
        ('[abc]*',      'bbaacad',  6),
        ('[ab-]*',      'bbaacad',  4),
        ('[a-c]*',      'bbaacad',  6),
        ('[b-da-a]*',   'bbaacad',  7),
    )

    for pattern, string, ans in cases:
        re = regex_from_string(pattern)
        assert regex_match_begin(re, string) is ans
