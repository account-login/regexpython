from regex.parser import *
from regex.tokenizer import *
from regex.errors import *
from regex.tests.utils import expect_parser_raise


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
    assert ast == Bracket(
        Char('a'),
        Char('b'),
        Char('c'),
        complement=False,
    )


def test_perser_bracket_empty():
    expect_parser_raise('[]', UnexpectedEOF)
    expect_parser_raise('[^]', UnexpectedEOF)


def test_parser_bracket_not_closed():
    expect_parser_raise('[', UnexpectedEOF)
    expect_parser_raise('[a-', UnexpectedEOF)


def test_parser_bracket_range():
    ast = ast_from_string('[a-c]')
    assert ast == Bracket(CharRange(start='a', end='c'), complement=False)

    ast = ast_from_string('[a-c-d]')
    assert ast == Bracket(
        CharRange(start='a', end='c'),
        Char('-'),
        Char('d'),
        complement=False,
    )

    ast = ast_from_string('[a-]')
    assert ast == Bracket(
        Char('a'),
        Char('-'),
        complement=False,
    )

    ast = ast_from_string('[-a-]')
    assert ast == Bracket(
        Char('-'),
        Char('a'),
        Char('-'),
        complement=False,
    )


def test_parser_bracket_complement():
    ast = ast_from_string('[^-ac-d-]')
    assert ast == Bracket(
        Char('-'),
        Char('a'),
        CharRange(start='c', end='d'),
        Char('-'),
        complement=True,
    )


def test_parser_bracket_bad_range():
    expect_parser_raise('[z-a]', BadRange, msg='reversed range')
    expect_parser_raise('[\w-a]', BadRange, msg='not character type')
    expect_parser_raise('[a-\w]', BadRange, msg='not character type')
    expect_parser_raise('[\s-\w]', BadRange, msg='not character type')


def test_parser_predefined_range():
    assert ast_from_string('\\w\\d') == ast_from_string('[a-zA-Z0-9_][0-9]')
