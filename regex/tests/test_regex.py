from regex.api import *
from regex.ranged import MAX_CHAR, MIN_CHAR


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
    MT(r'\w*', 'af04_b-', 6)
    MT(r'\W*', '-$#@#@.0a', 7)
    MT(r'[\W]*', '-$#@#@.0a', 7)
    MT(r'[\W\w]*', 'si3909*($%^%^.=)(*', 18)
    MT(r'\d*', '340.4', 3)
    MT(r'\s', 'a', -1)
    MT(r'\s', '　', -1)
    MT(r'\s*', ' \t\n\r　', 4)


def test_match_begin_large_range():
    max_cp = ord(MAX_CHAR)
    min_cp = ord(MIN_CHAR)
    string = ''.join(chr(cp) for cp in range(min_cp, max_cp, max_cp // 10000))
    MT(
        r'[\U{:08x}-\U{:08x}]*'.format(min_cp, max_cp - 1),
        string, len(string)
    )


def test_match_full():
    assert match_full('asdf', 'asdf')
    assert not match_full('asdf', '')
    assert match_full('.*', '')
    assert match_full('', '')
