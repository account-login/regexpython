import pytest

from regex.api import *
from regex.parser import *
from regex.tokenizer import *
from regex.statemachine import *
from regex.utils import *
from regex.errors import *
from regex.visualize import *


def token_list_from_string(string):
    return list(tokenize(BufferedGen(iter(string))))


def simplified_tokens(string):
    def transform(tok):
        if tok.type is Token.CHAR:
            return tok.value
        elif tok.type in (Token.ESCAPE,):
            return tok
        else:
            return tok.type

    return [ transform(x) for x in token_list_from_string(string) ]


def test_tokenizer_basic():
    tokens = simplified_tokens('')
    assert tokens == [Token.EOF]

    tokens = simplified_tokens('^ab(|)[a][^c]*a+a?$')
    assert tokens == [
        Token.BEGIN, 'a', 'b', Token.LPAR, Token.OR, Token.RPAR,
        Token.LBRACKET, 'a', Token.RBRACKET, Token.LBRACKET, Token.NOT, 'c', Token.RBRACKET,
        Token.STAR, 'a', Token.PLUS, 'a', Token.QUESTION, Token.END, Token.EOF,
    ]


def test_tokenizer_right_bracket():
    assert simplified_tokens(']') == [']', Token.EOF]


def test_tokenizer_bracket_no_special():
    tokens = simplified_tokens('[^[|*+?^()]')
    assert tokens == [Token.LBRACKET, Token.NOT] + list('[|*+?^()') + [Token.RBRACKET, Token.EOF]


def test_tokenizer_bracket_non_empty():
    tokens = simplified_tokens('[]')
    assert tokens == [Token.LBRACKET, ']', Token.EOF]

    tokens = simplified_tokens('[^]')
    assert tokens == [Token.LBRACKET, Token.NOT, ']', Token.EOF]

    tokens = simplified_tokens('[]]')
    assert tokens == [Token.LBRACKET, ']', Token.RBRACKET, Token.EOF]


def test_tokenizer_bracket_range():
    tokens = simplified_tokens('[a-c]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.RBRACKET, Token.EOF]

    tokens = simplified_tokens('[a-c-d]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.DASH, 'd', Token.RBRACKET, Token.EOF]

    tokens = simplified_tokens('[a-]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, Token.RBRACKET, Token.EOF]

    tokens = simplified_tokens('[-a-]')
    assert tokens == [Token.LBRACKET, Token.DASH, 'a', Token.DASH, Token.RBRACKET, Token.EOF]


def test_tokenizer_escape_constant():
    tokens = simplified_tokens('\\a\\f\\n\\r\\t\\v\\\\')
    assert tokens == list('\a\f\n\r\t\v\\') + [Token.EOF]


def test_tokenizer_escape_hex():
    tokens = simplified_tokens('\\x11\\u1234\\U00004321')
    assert tokens == list('\x11\u1234\U00004321') + [Token.EOF]


def test_tokenizer_escape_bad_hex():
    # actually raised from tokenizer
    expect_parser_raise('\\x1', IllegalEscape)
    expect_parser_raise('\\xfg', IllegalEscape)
    expect_parser_raise('\\uff0', IllegalEscape)
    expect_parser_raise('\\Uff00ff0g', IllegalEscape)
    expect_parser_raise('[\\x1]', IllegalEscape)
    expect_parser_raise('[\\x1', IllegalEscape)


def test_tokenizer_escape_bB():
    tokens = simplified_tokens('\\b\\B[\\b\\B]')
    assert tokens == [
        Token.ESCAPE('b'), Token.ESCAPE('B'),
        Token.LBRACKET, '\b', 'B', Token.RBRACKET, Token.EOF,
    ]


def test_tokenizer_escape_AZ():
    tokens = simplified_tokens('\\A\\Z')
    assert tokens == [Token.BEGIN, Token.END, Token.EOF]


def test_tokenizer_escape_wsd():
    tokens = simplified_tokens('\\w\\W\\s\\S\\d\\D')
    assert tokens == list(map(Token.ESCAPE , 'wWsSdD')) + [Token.EOF]

    tokens = simplified_tokens('[\\w\\W\\s\\S\\d\\D]')
    assert tokens == (
        [Token.LBRACKET] + list(map(Token.ESCAPE , 'wWsSdD')) + [Token.RBRACKET, Token.EOF])


def test_tokenizer_escape_undefined():
    tokens = simplified_tokens('\\q\\e\\y\\i')
    assert tokens == list('qeyi') + [Token.EOF]


def expect_parser_raise(string, exception=ParseError, *, msg=None):
    with pytest.raises(exception) as exec_info:
        ast_from_string(string)
    if msg is not None:
        assert msg in repr(exec_info.value)


def test_paser_basic():
    ast = ast_from_string('^ab(a||b|)*|c$')
    assert ast == Or(
        Cat(
            Char(Token.BEGIN()),
            Char('a'),
            Char('b'),
            Star(
                Or(Char('a'), Empty(), Char('b'), Empty())
            )
        ),
        Cat(
            Char('c'),
            Char(Token.END()),
        ),
    )


def test_parser_repeat():
    ast = ast_from_string('a*a+a?')
    assert ast == Cat(
        Star(Char('a')),
        Plus(Char('a')),
        Question(Char('a')),
    )


def test_parser_empty():
    ast = ast_from_string('')
    assert ast == Empty()


def test_parser_unexpected_repeat():
    expect_parser_raise('*', ParseError, msg='nothing to repeat')
    expect_parser_raise('+', ParseError, msg='nothing to repeat')
    expect_parser_raise('?', ParseError, msg='nothing to repeat')


def test_perser_multiple_repeat():
    for r1 in '*+?':
        for r2 in '*+':
            expect_parser_raise('.' + r1 + r2, ParseError, msg='multiple repeat')


def test_parser_bracket_basic():
    ast = ast_from_string('[abc]')
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
    ast = ast_from_string('[a-c]')
    assert ast == CharRange(start='a', end='c')

    ast = ast_from_string('[a-c-d]')
    assert ast == Or(
        CharRange(start='a', end='c'),
        Char('-'),
        Char('d'),
    )

    ast = ast_from_string('[a-]')
    assert ast == Or(
        Char('a'),
        Char('-'),
    )

    ast = ast_from_string('[-a-]')
    assert ast == Or(
        Char('-'),
        Char('a'),
        Char('-'),
    )


def test_parser_bracket_complement():
    ast = ast_from_string('[^-ac-d-]')
    assert ast == NotChars(
        Char('-'),
        Char('a'),
        CharRange(start='c', end='d'),
        Char('-'),
    )


def test_parser_bracket_bad_range():
    expect_parser_raise('[z-a]', BadRange, msg='reversed range')
    expect_parser_raise('[\w-a]', BadRange, msg='not character type')
    expect_parser_raise('[a-\w]', BadRange, msg='not character type')
    expect_parser_raise('[\s-\w]', BadRange, msg='not character type')


def test_parser_predefined_range():
    assert ast_from_string('\\w\\d') == ast_from_string('[a-zA-Z0-9_][0-9]')


def run_match_begin_test(pattern, string, ans):
    assert match_begin(pattern, string) == ans

MT = run_match_begin_test


def test_match_begin_literal():
    MT('abc', 'abcd', 3)
    MT('abc', 'axc', -1)


def test_match_begin_empty_re_empty_string():
    MT('', '', 0)
    MT('^', '', 0)
    MT('$', '', 0)
    MT('^$', '', 0)
    MT('$^', '', 0)
    MT('$^$^$^', '', 0)
    MT('$.*^', '', 0)


def test_match_begin_empty_re():
    MT('', 'asdf', 0)
    MT('^', 'asdf', 0)
    MT('$', 'asdf', -1)
    MT('^$', 'asdf', -1)
    MT('$^', 'asdf', -1)


def test_match_begin_empty_string():
    MT('asdf', '', -1)


def test_match_begin_star():
    MT('a*', 'aaaaa', 5)
    MT('a*b', 'bb', 1)
    MT('a*b', 'aaabb', 4)
    MT('a*b', 'aaaa', -1)


def test_match_begin_plus():
    MT('a+', 'a', 1)
    MT('a+', 'aa', 2)
    MT('a+', '', -1)
    MT('a+', 'ab', 1)


def test_match_begin_question():
    MT('a?', 'a', 1)
    MT('a?', '', 0)
    MT('a?', 'aa', 1)


def test_match_begin_dot():
    MT('.a.*', 'basdf', 5)
    MT('.|[^a]|.|[^a]|.', 'aa', 1)
    MT('aa|.|aa|.|aa|.', 'aa', 2)


def test_match_begin_or():
    MT('a|cd', 'a', 1)
    MT('a|cd', 'cda', 2)
    MT('|a||b|', 'ab', 1)
    MT('|a||b|', '', 0)
    MT('|a||b|', 'ba', 1)
    MT('|b|a|b|', 'ba', 1)


def test_match_begin_bracket():
    MT('[abc]*', 'bbaacad', 6)
    MT('[ab-]*', 'bbaacad', 4)
    MT('[a-c]*', 'bbaacad', 6)
    MT('[b-da-a]*', 'bbaacad', 7)


def test_match_begin_bracket_complement():
    MT('[^abc]*', '23ffsda', 6)
    MT('([^a-c]|b)cd', 'acd', -1)
    MT('([^a-c]|b)cd', 'bcd', 3)
    MT('([^a-c]|b|[^b-z])cd', 'bcd', 3)
    MT('([^a-c]|[^b-z]|b)cd', 'bcd', 3)
    MT('(b|[^a-c]|[^b-z])cd', 'bcd', 3)
    MT('([^b-z]|[^a-c]|b)cd', 'bcd', 3)
    MT('([^a-c]*|b)z', 'z', 1)
    MT('([^a-c]*|b)z', 'bz', 2)
    MT('([^a-c]*|b)z', 'bbz', -1)


def test_match_begin_end_dollar():
    MT('a$', 'ad', -1)
    MT('a$', 'a', 1)
    MT('a$$', 'a', 1)
    MT('a(b|$)$', 'a', 1)
    MT('a(b|$)$', 'ab', 2)
    MT('a(b|$)$', 'ac', -1)
    MT('a(b|$)c$', 'a', -1)
    MT('a$c', 'ac', -1)
    MT('a($|b)c*', 'ac', -1)
    MT('a($|b)c', 'ac', -1)
    MT('a($|b)c*', 'abc', 3)
    MT('a($|b)c*', 'a', 1)


def test_match_begin_begin_caret():
    MT('^a', 'a', 1)
    MT('^^a', 'a', 1)
    MT('^(b|^a)', 'a', 1)
    MT('c*^a', 'a', 1)
    MT('c*^a', 'ca', -1)
    MT('c^a', 'ca', -1)
    MT('b*(^ba|bb)c', 'bbac', -1)
    MT('b*(^ba|bb)c', 'bac', 3)
    MT('b*(^ba|bb)c', 'bbc', 3)


def test_match_begin_constant():
    MT('[\\a\\b\\f\\n\\r\\t\\v\\\\]*', ''.join(reversed('\a\b\f\n\r\t\v\\' * 2)), 16)


def test_match_begin_predefined_range():
    # MT('\w*', 'af04_b-', 6)   # FIXME: it takes 10s to compile!!!
    MT('\w', 'a', 1)
    MT('\s*', ' \t\n\r　', 4)


def test_match_full():
    assert match_full('asdf', 'asdf')
    assert not match_full('asdf', '')
    assert match_full('.*', '')
    assert match_full('', '')


def test_ast_to_svg():
    ast = ast_from_string('^ab(a||b|[^a-c]|)*|c$')
    assert ast._repr_svg_().startswith('<?xml')


def test_nfa_to_svg():
    for string in ('ab(a||b|[^a-c]|)*|c', ''):
        ast = ast_from_string(string)
        nfa_pair = ast_to_nfa(ast)
        assert nfa_pair._repr_svg_().startswith('<?xml')


def test_dfa_to_svg():
    ast = ast_from_string('ab(a||b|[^a-c]|)*|c')
    nfa_pair = ast_to_nfa(ast)
    dfa = DfaState.from_nfa(nfa_pair)
    assert dfa._repr_svg_().startswith('<?xml')
