from collections import namedtuple
from itertools import chain

from regex.parser import BaseNode, Char, CharRange, NotChars, Dot, Star, Cat, Or, Empty, Token


# TODO: handle range more effectly


class NfaState:
    def __init__(self, *, char=None, not_chars=None, to=None, other=None, epsilon=None):
        # combinations:
        # char, to
        # not_chars, other
        # other
        self.char = char
        self.not_chars = not_chars
        self.to = to
        self.other = other
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


def ast_to_nfa(node: BaseNode) -> NfaPair:
    if isinstance(node, Char):
        end = NfaState()
        start = NfaState(char=node.children[0], to=end)
        return NfaPair(start, end)
    elif isinstance(node, CharRange):
        return ast_to_nfa(Or(*node))
    elif isinstance(node, NotChars):
        children_expanded = set()
        for child in node.children:
            if isinstance(child, Char):
                children_expanded.add(child.children[0])
            elif isinstance(child, CharRange):
                for char in child:
                    children_expanded.add(char.children[0])
            else:
                assert False, 'impossible'

        end = NfaState()
        start = NfaState(not_chars=children_expanded, other=end)
        return NfaPair(start, end)
    elif isinstance(node, Dot):
        end = NfaState()
        start = NfaState(other=end)
        return NfaPair(start, end)
    elif isinstance(node, Star):
        sub_start, sub_end = ast_to_nfa(node.children[0])
        sub_start.epsilon.add(sub_end)
        sub_end.epsilon.add(sub_start)

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


class CharToSet:
    def __init__(self):
        self.chars = dict()
        self.not_accept = set() # type: set
        self.other = set()

    def get(self, char):
        if char in self.chars:
            return self.chars[char]
        elif char in self.not_accept:
            return None
        else:
            return self.other

    def add_char(self, char, dest):
        if char in self.not_accept:
            assert char not in self.chars
            self.not_accept.remove(char)
            self.chars[char] = { dest }
        elif char in self.chars:
            assert char not in self.not_accept
            self.chars[char].add(dest)
        else:
            self.chars[char] = self.other.union({ dest })

    def add_not_chars(self, not_chars: set, other):
        common_with_chars = not_chars.intersection(set(self.chars.keys()))
        if self.other:
            common_with_not_accept = not_chars.intersection(self.not_accept)
        else:
            assert not self.not_accept
            common_with_not_accept = not_chars - common_with_chars

        common_with_other = not_chars - common_with_not_accept - common_with_chars
        for co in common_with_other:
            assert co not in self.chars
            self.chars[co] = set(self.other)

        for ch, sset in self.chars.items():
            if ch not in common_with_chars:
                sset.add(other)

        for na in self.not_accept - common_with_not_accept:
            assert na not in self.chars
            self.chars[na] = { other }

        self.not_accept = common_with_not_accept
        self.other.add(other)

    def add_other(self, other):
        self.other.add(other)

        for sset in self.chars.values():
            sset.add(other)

        for ch in self.not_accept:
            assert ch not in self.chars
            self.chars[ch] = { other }
        self.not_accept = set()

    def freeze(self):
        for ch, sset in self.chars.items():
            extra = {Token.END}.intersection({ch})
            self.chars[ch] = frozenset(ε_closure(sset, extra=extra))
        self.not_accept = frozenset(self.not_accept)
        self.other = frozenset(ε_closure(self.other))


class DfaState:
    def __init__(self, set_to_state, end):
        """
        :type set_to_state: dict[set[NfaState], DfaState]
        """
        self.char_to_set = CharToSet()
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

        q = [ ε_closure({start}, extra={Token.BEGIN}) ]
        while q:
            dfa_state = cls(set_to_state, end)
            dfa_state.states = q.pop()

            for nfa in dfa_state.states:    # type: NfaState
                if nfa.char is not None:
                    dfa_state.char_to_set.add_char(nfa.char, nfa.to)
                elif nfa.not_chars is not None:
                    dfa_state.char_to_set.add_not_chars(nfa.not_chars, nfa.other)
                elif nfa.other:
                    dfa_state.char_to_set.add_other(nfa.other)

            dfa_state.freeze()  # convert set to frozenset in order to work with hashtable
            set_to_state[dfa_state.states] = dfa_state

            for nfas in dfa_state.char_to_set.chars.values():
                if nfas not in set_to_state:
                    q.append(nfas)
            if dfa_state.char_to_set.other and dfa_state.char_to_set.other not in set_to_state:
                q.append(dfa_state.char_to_set.other)

            if start_dfa is None:
                start_dfa = dfa_state
                # special case for matching empty string
                # both Token.BEGIN and Token.END should be considered epsilon
                start_dfa.match_empty = end in ε_closure(
                    start_dfa.states, extra={Token.BEGIN, Token.END})

        assert start_dfa.match_empty is not None
        return start_dfa

    def follow(self, char):
        nfas = self.char_to_set.get(char)
        if nfas:
            return self.set_to_state[nfas]
        else:
            return None

    def is_end(self):
        return self.end in self.states

    def freeze(self):
        self.char_to_set.freeze()
        self.states = frozenset(self.states)
