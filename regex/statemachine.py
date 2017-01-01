from collections import namedtuple
from itertools import chain

from regex.parser import (
    BaseNode, Char, Bracket, CharRange, Dot,
    Star, Plus, Question, Cat, Or, Empty,
)
from regex.tokenizer import Token
from regex.ranged import RangeSet, RangeMap


class NfaState:
    def __init__(self, *, char=None, charset: RangeSet=None, to=None, epsilon=None):
        # combinations:
        # char, to
        # charset, to
        self.char = char
        self.charset = charset
        self.to = to
        self.epsilon = epsilon or set()
        self.label = 'S_{:x}'.format(id(self))

    def __repr__(self):
        return '<{}>'.format(self.label)


class NfaPair(namedtuple('NfaPair', ('start', 'end'))):
    def to_graphviz(self):
        from regex.visualize import nfa_to_gv
        return nfa_to_gv(self)

    def _repr_svg_(self):
        return self.to_graphviz()._repr_svg_()

    def to_dfa(self):
        return DfaState.from_nfa(self)


def ε_closure(nfas, extra=None):
    """
    :type nfas: set[NfaState]
    :type extra: set
    """
    extra = extra or set()

    def get_epsilons(nfa: NfaState):
        yield from nfa.epsilon
        if nfa.char in extra:
            yield nfa.to

    ans = set(nfas)
    delta = ans
    while True:
        delta = { d for d in chain.from_iterable(get_epsilons(x) for x in delta)
                  if d not in ans }
        if delta:
            ans.update(delta)
        else:
            return ans


def merge_bracket_ranges(node: Bracket) -> RangeSet:
    rs = RangeSet()
    for child in node.children:
        if isinstance(child, Char):
            rs.add_char(child.children[0])
        elif isinstance(child, CharRange):
            rs.add_range(child.start, child.end)
        elif isinstance(child, Bracket):
            subrs = merge_bracket_ranges(child)
            for r in subrs.get_true_ranges():
                rs.add_range(r.start, r.end)
        else:
            assert not 'possible'

    if node.complement:
        rs.complement()
    return rs


def ast_to_nfa(node: BaseNode) -> NfaPair:
    if isinstance(node, Char):
        end = NfaState()
        start = NfaState(char=node.children[0], to=end)
        return NfaPair(start, end)
    elif isinstance(node, Bracket):
        # merge ranges
        rs = merge_bracket_ranges(node)
        end = NfaState()
        start = NfaState(charset=rs, to=end)
        return NfaPair(start, end)
    elif isinstance(node, Dot):
        end = NfaState()
        start = NfaState(charset=RangeSet.all(), to=end)
        return NfaPair(start, end)
    elif isinstance(node, Star):
        sub_start, sub_end = ast_to_nfa(node.children[0])
        sub_start.epsilon.add(sub_end)
        sub_end.epsilon.add(sub_start)

        return NfaPair(sub_start, sub_end)
    elif isinstance(node, Plus):
        sub_start, sub_end = ast_to_nfa(node.children[0])
        sub_end.epsilon.add(sub_start)

        return NfaPair(sub_start, sub_end)
    elif isinstance(node, Question):
        sub_start, sub_end = ast_to_nfa(node.children[0])
        sub_start.epsilon.add(sub_end)

        return NfaPair(sub_start, sub_end)
    elif isinstance(node, Cat):
        assert len(node.children) > 0
        start = None
        prev_e = None
        for s, e in map(ast_to_nfa, node.children):
            if start is None:
                start = s
            if prev_e is not None:
                prev_e.epsilon.add(s)
            prev_e = e

        return NfaPair(start, e)
    elif isinstance(node, Or):
        assert len(node.children) > 0
        start = NfaState()
        end = NfaState()
        for s, e in map(ast_to_nfa, node.children):
            start.epsilon.add(s)
            e.epsilon.add(end)

        return NfaPair(start, end)
    elif isinstance(node, Empty):
        end = NfaState()
        return NfaPair(end, end)
    else:
        raise NotImplementedError


class DfaState:
    def __init__(self, set_to_state, end):
        """
        :type set_to_state: dict[set[NfaState], DfaState]
        """
        self.rangemap = RangeMap()
        self.set_to_state = set_to_state
        self.end = end
        self.states = set()
        self.match_empty = None

    def __repr__(self):
        return repr(self.states)

    def _repr_svg_(self):
        return self.to_graphviz()._repr_svg_()

    def to_graphviz(self):
        from regex.visualize import dfa_to_gv
        return dfa_to_gv(self)

    @classmethod
    def from_nfa(cls, nfa_pair: NfaPair):
        start, end = nfa_pair
        set_to_state = dict()
        start_dfa = None

        q = [ ε_closure({start}, extra={Token.BEGIN()}) ]
        while q:
            dfa_state = cls(set_to_state, end)
            dfa_state.states = q.pop()

            for nfa in dfa_state.states:    # type: NfaState
                if nfa.char is not None:
                    # nfa.char may be Token.BEGIN or Token.END
                    if isinstance(nfa.char, str):
                        dfa_state.rangemap.add_range(nfa.char, nfa.char, {nfa.to})
                elif nfa.charset is not None:
                    for r in nfa.charset.get_true_ranges():
                        dfa_state.rangemap.add_range(r.start, r.end, {nfa.to})

            dfa_state.freeze()  # convert set to frozenset in order to work with hashtable
            set_to_state[dfa_state.states] = dfa_state

            for r in dfa_state.rangemap.get_ranges():
                nfas = r.value
                if nfas and nfas not in set_to_state:
                    q.append(nfas)

            if start_dfa is None:
                start_dfa = dfa_state
                # special case for matching empty string
                # both Token.BEGIN and Token.END should be considered epsilon
                start_dfa.match_empty = end in ε_closure(
                    start_dfa.states, extra={Token.BEGIN(), Token.END()})

        assert start_dfa.match_empty is not None
        return start_dfa

    def follow(self, char):
        nfas = self.rangemap.get_char(char)
        if nfas:
            return self.set_to_state[nfas]
        else:
            return None

    def is_end(self):
        # TODO: cache this
        return self.end in self.states

    def is_dollar_end(self):
        return self.end in ε_closure(self.states, extra={Token.END()})

    def freeze(self):
        for r in self.rangemap.get_ranges():
            r.value = frozenset(ε_closure(r.value))
        self.states = frozenset(self.states)
