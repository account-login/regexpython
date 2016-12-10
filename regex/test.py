from regex.parser import *


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
            Token.BEGIN,
            'a',
            'b',
            Star(
                Or('a', Empty(), 'b', Empty())
            )
        ),
        Cat(
            'c',
            Token.END,
        ),
    )

    assert ast == expected
