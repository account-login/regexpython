from regex.parser import ast_from_string
from regex.statemachine import ast_to_nfa, DfaState


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
