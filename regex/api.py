from regex.parser import BaseNode, Token
from regex.statemachine import regex_to_nfa, DfaState


def match_begin(re: BaseNode, s: str):
    if len(s) == 0:
        return 0

    nfa = regex_to_nfa(re)
    dfa = DfaState.from_nfa(nfa)

    ans = -1
    for i, ch in enumerate(s):
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
