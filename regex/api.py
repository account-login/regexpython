from regex.parser import Token, ast_from_string
from regex.statemachine import ast_to_nfa, DfaState


__all__ = ('Regex', 'compile', 'match_begin')


class Regex:
    def __init__(self, string: str, dfa: DfaState):
        self.string, self.dfa = string, dfa

    def match_begin(self, string: str) -> int:
        if len(string) == 0:
            return 0

        dfa = self.dfa
        ans = -1
        for i, ch in enumerate(string):
            dfa = dfa.follow(ch)
            if dfa is None:
                return ans + 1
            else:
                if dfa.is_end():
                    ans = i

        if ans == -1:
            dfa = dfa.follow(Token.END)
            if dfa is not None and dfa.is_end():
                ans = i

        return ans + 1


def compile(string: str) -> Regex:
    ast = ast_from_string(string)
    nfa = ast_to_nfa(ast)
    dfa = DfaState.from_nfa(nfa)
    return Regex(string, dfa)


def match_begin(pattern: str, string: str) -> int:
    reg = compile(pattern)
    return reg.match_begin(string)
