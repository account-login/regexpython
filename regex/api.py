from regex.parser import Token, ast_from_string
from regex.statemachine import ast_to_nfa, DfaState


__all__ = ('Regex', 'compile', 'match_begin', 'match_full')


class Regex:
    def __init__(self, pattern: str, dfa: DfaState):
        self.pattern, self.dfa = pattern, dfa

    def match_begin(self, string: str) -> int:
        dfa = self.dfa
        if dfa.is_end():
            last_match = -1
        else:
            last_match = -2

        i = -1
        for i, ch in enumerate(string):
            dfa = dfa.follow(ch)
            if dfa is None:
                return last_match + 1
            else:
                if dfa.is_end():
                    last_match = i

        assert dfa is not None
        if not dfa.is_end():
            dfa = dfa.follow(Token.END)
            if dfa is not None and dfa.is_end():
                last_match = i

        return last_match + 1

    def match_full(self, string: str) -> bool:
        return self.match_begin(string) == len(string)


def compile(pattern: str) -> Regex:
    ast = ast_from_string(pattern)
    nfa = ast_to_nfa(ast)
    dfa = DfaState.from_nfa(nfa)
    return Regex(pattern, dfa)


def match_begin(pattern: str, string: str) -> int:
    reg = compile(pattern)
    return reg.match_begin(string)


def match_full(pattern: str, string: str) -> bool:
    reg = compile(pattern)
    return reg.match_full(string)
