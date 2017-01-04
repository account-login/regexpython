from regex.tokenizer import *
from regex.errors import *
from regex.utils import BufferedGen
from regex.tests.utils import expect_parser_raise


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

    ret = [ transform(x) for x in token_list_from_string(string) ]
    assert ret[-1] is Token.EOF
    return ret[:-1]


def test_tokenizer_basic():
    tokens = simplified_tokens('')
    assert tokens == []

    tokens = simplified_tokens('^ab(|)[a][^c]*a+a?$')
    assert tokens == [
        Token.BEGIN, 'a', 'b', Token.LPAR, Token.OR, Token.RPAR,
        Token.LBRACKET, 'a', Token.RBRACKET, Token.LBRACKET, Token.NOT, 'c', Token.RBRACKET,
        Token.STAR, 'a', Token.PLUS, 'a', Token.QUESTION, Token.END,
    ]


def test_tokenizer_right_bracket():
    assert simplified_tokens(']') == [']']


def test_tokenizer_bracket_no_special():
    tokens = simplified_tokens('[^[|*+?^()]')
    assert tokens == [Token.LBRACKET, Token.NOT] + list('[|*+?^()') + [Token.RBRACKET]


def test_tokenizer_bracket_non_empty():
    tokens = simplified_tokens('[]')
    assert tokens == [Token.LBRACKET, ']']

    tokens = simplified_tokens('[^]')
    assert tokens == [Token.LBRACKET, Token.NOT, ']']

    tokens = simplified_tokens('[]]')
    assert tokens == [Token.LBRACKET, ']', Token.RBRACKET]


def test_tokenizer_bracket_range():
    tokens = simplified_tokens('[a-c]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.RBRACKET]

    tokens = simplified_tokens('[a-c-d]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, 'c', Token.DASH, 'd', Token.RBRACKET]

    tokens = simplified_tokens('[a-]')
    assert tokens == [Token.LBRACKET, 'a', Token.DASH, Token.RBRACKET]

    tokens = simplified_tokens('[-a-]')
    assert tokens == [Token.LBRACKET, Token.DASH, 'a', Token.DASH, Token.RBRACKET]


def test_tokenizer_escape_constant():
    tokens = simplified_tokens('\\a\\f\\n\\r\\t\\v\\\\')
    assert tokens == list('\a\f\n\r\t\v\\')


def test_tokenizer_escape_hex():
    tokens = simplified_tokens('\\x11\\u1234\\U00004321')
    assert tokens == list('\x11\u1234\U00004321')


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
        Token.LBRACKET, '\b', 'B', Token.RBRACKET
    ]


def test_tokenizer_escape_AZ():
    tokens = simplified_tokens('\\A\\Z')
    assert tokens == [Token.BEGIN, Token.END]


def test_tokenizer_escape_wsd():
    tokens = simplified_tokens('\\w\\W\\s\\S\\d\\D')
    assert tokens == list(map(Token.ESCAPE , 'wWsSdD'))

    tokens = simplified_tokens('[\\w\\W\\s\\S\\d\\D]')
    assert tokens == (
        [Token.LBRACKET] + list(map(Token.ESCAPE , 'wWsSdD')) + [Token.RBRACKET])


def test_tokenizer_escape_undefined():
    tokens = simplified_tokens('\\q\\e\\y\\i')
    assert tokens == list('qeyi')
