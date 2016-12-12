import pytest

from regex.parser import *
from regex.statemachine import *
from regex.visualize import *


def token_list_from_string(string):
    return list(tokenize(BufferedGen(iter(string))))


def test_tokenizer_basic():
    tokens = token_list_from_string('')
    assert tokens == [Token.EOF]

    tokens = token_list_from_string('^ab(|)[a][^c]*$')
    assert tokens == [
        Token.BEGIN, 'a', 'b', Token.LPAR, Token.OR, Token.RPAR,
        Token.LBRACKET, 'a', Token.RBRACKET, Token.LBRACKET, Token.NOT, 'c', Token.RBRACKET,
        Token.STAR, Token.END, Token.EOF,
    ]


def test_tokenizer_right_bracket():
    assert token_list_from_string(']') == [']', Token.EOF]


def test_tokenizer_bracket_no_special():
    tokens = token_list_from_string('[^[|*+?^()]')
    assert tokens == [Token.LBRACKET, Token.NOT] + list('[|*+?^()') + [Token.RBRACKET, Token.EOF]


def test_tokenizer_bracket_non_empty():
    tokens = token_list_from_string('[]')
    assert tokens == [Token.LBRACKET, ']', Token.EOF]

    tokens = token_list_from_string('[^]')
    assert tokens == [Token.LBRACKET, Token.NOT, ']', Token.EOF]

    tokens = token_list_from_string('[]]')
    assert tokens == [Token.LBRACKET, ']', Token.RBRACKET, Token.EOF]


def test_tokenizer_bracket_range():
    tokens = token_list_from_string('[a-c]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[a-c-d]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.DASH, 'd', Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[a-]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, Token.RBRACKET, Token.EOF]

    tokens = token_list_from_string('[-a-]')
    assert tokens == [Token.LBRACKET, Token.DASH, 'a', Token.DASH, Token.RBRACKET, Token.EOF]


def expect_parser_raise(string, exception=ParseError, msg=None):
    with pytest.raises(exception) as exec_info:
        regex_from_string(string)
    if msg is not None:
        assert msg in repr(exec_info.value)


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


def test_parser_unexpected_repeat():
    expect_parser_raise('*', ParseError, msg='nothing to repeat')


def test_parser_bracket_basic():
    ast = regex_from_string('[abc]')
    assert ast == Or(
        Char('a'),
        Char('b'),
        Char('c'),
    )


def test_perser_bracket_empty():
    expect_parser_raise('[]', UnexpectedEOF)
    expect_parser_raise('[^]', UnexpectedEOF)


def test_parser_bracket_not_closed():
    expect_parser_raise('[', UnexpectedEOF)
    expect_parser_raise('[a-', UnexpectedEOF)


def test_parser_bracket_range():
    ast = regex_from_string('[a-c]')
    assert ast == CharRange(start='a', end='c')

    ast = regex_from_string('[a-c-d]')
    assert ast == Or(
        CharRange(start='a', end='c'),
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


def test_parser_bracket_complement():
    ast = regex_from_string('[^-ac-d-]')
    assert ast == NotChars(
        Char('-'),
        Char('a'),
        CharRange(start='c', end='d'),
        Char('-'),
    )


def test_parser_bracket_bad_range():
    expect_parser_raise('[z-a]', BadRange)


def run_match_begin_test(cases):
    for pattern, string, ans in cases:
        re = regex_from_string(pattern)
        assert regex_match_begin(re, string) is ans


def test_match_begin_literal():
    run_match_begin_test([
        ('abc', 'abcd', 3),
    ])


def test_match_begin_star():
    run_match_begin_test([
        ('a*', 'aaaaa', 5),
        ('a*b', 'bb', 1),
        ('a*b', 'aaabb', 4),
        ('a*b', 'aaaa', 0),
    ])


def test_match_begin_dot():
    run_match_begin_test([
        ('.a.*', 'basdf', 5),
    ])


def test_match_begin_or():
    run_match_begin_test([
        ('a|cd', 'a', 1),
        ('a|cd', 'cda', 2),
        ('|a||b|', 'ab', 1),
        ('|a||b|', '', 0),
        ('|a||b|', 'ba', 1),
    ])


def test_match_begin_bracket():
    run_match_begin_test([
        ('[abc]*', 'bbaacad', 6),
        ('[ab-]*', 'bbaacad', 4),
        ('[a-c]*', 'bbaacad', 6),
        ('[b-da-a]*', 'bbaacad', 7),
    ])


def test_match_begin_bracket_complement():
    run_match_begin_test([
        ('[^abc]*', '23ffsda', 6),
        ('([^a-c]|b)cd', 'acd', 0),
        ('([^a-c]|b)cd', 'bcd', 3),
        ('([^a-c]|b|[^b-z])cd', 'bcd', 3),
        ('([^a-c]*|b)z', 'z', 1),
        ('([^a-c]*|b)z', 'bz', 2),
        ('([^a-c]*|b)z', 'bbz', 0),
    ])


def test_ast_to_svg():
    ast = regex_from_string('^ab(a||b|)*|c$')
    assert ast._repr_svg_().startswith('<?xml')


def test_nfa_to_svg():
    ast = regex_from_string('ab(a||b|)*|c')
    nfa_pair = regex_to_nfa(ast)
    assert nfa_pair._repr_svg_().startswith('<?xml')


def test_dfa_to_svg():
    ast = regex_from_string('ab(a||b|)*|c')
    nfa_pair = regex_to_nfa(ast)
    dfa = DfaState.from_nfa(nfa_pair)
    assert dfa._repr_svg_().startswith('<?xml')
