import itertools
from collections import deque
from itertools import chain
import graphviz


def make_serial():
    gen = itertools.count()
    return lambda: next(gen)


class BaseNode:
    def __init__(self, *children):
        """
        :type children: tuple[BaseNode|str]
        """
        self.children = children

    def _repr_svg_(self):
        return self.to_graphiviz()._repr_svg_()

    def to_graphiviz(self):
        g = graphviz.Digraph()
        g.attr('node', width='0', height='0', shape='box', fontname='fira')
        self._add_to_gv(g, make_serial())
        return g

    def _node_label(self):
        return self.__class__.__name__

    def _add_to_gv(self, graph: graphviz.Digraph, serial, parent_name=None, edge_opts=None):
        name = 'N_{}'.format(serial())
        graph.node(name, self._node_label())
        if parent_name is not None:
            graph.edge(parent_name, name, **(edge_opts or {}))

        for c in self.children:
            if isinstance(c, BaseNode):
                c._add_to_gv(graph, serial, name)

        return name


class Char(BaseNode):
    def _node_label(self):
        return self.children[0]


class NotChar(BaseNode):
    def _node_label(self):
        return '^%c' % self.children[0]


class Dot(BaseNode):
    pass


class Star(BaseNode):
    pass


class Cat(BaseNode):
    def _add_to_gv(self, graph: graphviz.Digraph, serial, parent_name=None, edge_opts=None):
        root_name = 'N_{}'.format(serial())
        graph.node(root_name, self._node_label())

        child_names = []
        prev_name = root_name
        for i, ch in enumerate(self.children):
            sub_edge_opts = dict(arrowhead='none') if i != 0 else {}
            name = ch._add_to_gv(graph, serial, prev_name, edge_opts=sub_edge_opts)
            child_names.append(name)
            prev_name = name

        subgraph = graphviz.Digraph()
        subgraph.attr('graph', rank='same')
        for ch_name in child_names:
            subgraph.node(ch_name)
        graph.subgraph(subgraph)

        if parent_name is not None:
            graph.edge(parent_name, root_name, **(edge_opts or {}))
        return root_name


class Or(BaseNode):
    pass


def nfa_to_gv(nfa, labelize=True):
    """
    :type nfa: (NfaState, NfaState)
    """

    if labelize:
        nfa_labelize(nfa)

    start, end = nfa
    g = graphviz.Digraph()
    g.attr('node', style='filled', width='0', height='0', shape='box', fontname='fira')

    if start is end:
        g.node(start.label, 'START & END', color='gray')
    else:
        g.node(start.label, 'START', color='black', fontcolor='white')
        g.node(end.label, 'END', color='green', fontcolor='white')
    has_fail_node = False

    seen = dict()

    def rec(node: NfaState):
        name = node.label
        seen[node] = name

        if node.char is not None:
            sub_name = seen.get(node.to) or rec(node.to)
            g.edge(name, sub_name, node.char)
        elif node.not_char is not None:
            nonlocal has_fail_node
            if not has_fail_node:
                g.node('FAIL', color='red', fontcolor='white')
                has_fail_node = True
            g.edge(name, 'FAIL', str(node.not_char))

        if node.other:
            sub_name = seen.get(node.other) or rec(node.other)
            g.edge(name, sub_name, 'other')

        for to in node.epsilon:
            sub_name = seen.get(to) or rec(to)
            g.edge(name, sub_name, 'ε')

        return name

    rec(start)
    return g


class NfaState:
    def __init__(self, char=None, not_char=None, to=None, other=None, epsilon=None):
        self.char = char
        self.not_char = not_char
        self.to = to
        self.other = other
        self.epsilon = epsilon or set()
        self.label = 'S_{:x}'.format(id(self))

    def __repr__(self):
        return '<{}>'.format(self.label)


def ε_closure(nfas):
    """
    :type nfas: set[NfaState]
    """
    ans = set(nfas)
    delta = ans
    while True:
        delta = { d for d in chain.from_iterable(x.epsilon for x in delta)
                  if d not in ans }
        if delta:
            ans.update(delta)
        else:
            return ans


def regex_to_nfa(re):
    """
    :type re: BaseNode
    :rtype: (NfaState, NfaState)
    """
    if isinstance(re, Char):
        end = NfaState()
        start = NfaState(char=re.children[0], to=end)
        return start, end
    elif isinstance(re, NotChar):
        end = NfaState()
        start = NfaState(not_char=re.children[0], other=end)
        return start, end
    elif isinstance(re, Dot):
        end = NfaState()
        start = NfaState(other=end)
        return start, end
    elif isinstance(re, Star):
        sub_start, sub_end = regex_to_nfa(re.children[0])
        sub_start.epsilon.add(sub_end)
        sub_end.epsilon.add(sub_start)

        return sub_start, sub_end
    elif isinstance(re, Cat):
        s1, e1 = regex_to_nfa(re.children[0])
        s2, e2 = regex_to_nfa(re.children[1])
        e1.epsilon.add(s2)

        return s1, e2
    elif isinstance(re, Or):
        s1, e1 = regex_to_nfa(re.children[0])
        s2, e2 = regex_to_nfa(re.children[1])
        start = NfaState(epsilon={ s1, s2 })
        end = NfaState()
        for e in (e1, e2):
            e.epsilon.add(end)

        return start, end
    else:
        raise NotImplementedError


def nfa_labelize(nfa):
    """
    :type nfa: (NfaState, NfaState)
    """
    start, end = nfa

    if start is end:
        start.label = 'START & END'
    else:
        start.label = 'START'
        end.label = 'END'

    seen = set()
    serial = make_serial()

    def rec(node: NfaState):
        if node is not start and node is not end:
            node.label = 'S{}'.format(serial())

        seen.add(node)
        for child in chain(node.epsilon, (node.to, node.other)):
            if child and child not in seen:
                rec(child)

    rec(start)


class CharToSet:
    def __init__(self):
        self.chars = dict()
        self.not_accept = set()
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

    def add_not_char(self, not_char, other):
        for ch, sset in self.chars.items():
            if ch != not_char:
                sset.add(other)

        for ch in self.not_accept:
            if ch != not_char:
                self.chars[ch] = { other }

        if not_char in self.chars:
            assert not_char not in self.not_accept
            self.not_accept = set()
        elif not_char in self.not_accept:
            assert not_char not in self.chars
            self.not_accept = { not_char }
        else:
            if self.other:
                self.chars[not_char] = set(self.other)
            else:
                assert not self.not_accept
                self.not_accept = { not_char }

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
            self.chars[ch] = frozenset(ε_closure(sset))
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

    def __repr__(self):
        return repr(self.states)

    def to_graphviz(self):
        return dfa_to_gv(self)

    @classmethod
    def from_nfa(cls, nfa):
        """
        :type nfa: (NfaState, NfaState)
        """
        start, end = nfa
        set_to_state = dict()
        start_dfa = None

        q = deque([ ε_closure({ start }) ])
        while q:
            dfa_state = cls(set_to_state, end)
            dfa_state.states = q.popleft()
            start_dfa = start_dfa or dfa_state

            for nfa in dfa_state.states:    # type: NfaState
                if nfa.char is not None:
                    dfa_state.char_to_set.add_char(nfa.char, nfa.to)
                elif nfa.not_char is not None:
                    dfa_state.char_to_set.add_not_char(nfa.not_char, nfa.other)
                elif nfa.other:
                    dfa_state.char_to_set.add_other(nfa.other)

            dfa_state.freeze()
            set_to_state[dfa_state.states] = dfa_state

            for nfas in dfa_state.char_to_set.chars.values():
                if nfas not in set_to_state:
                    q.append(nfas)
            if dfa_state.char_to_set.other and dfa_state.char_to_set.other not in set_to_state:
                q.append(dfa_state.char_to_set.other)

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


def dfa_to_gv(dfa_start: DfaState):
    g = graphviz.Digraph()
    g.attr('node', style='filled', width='0', height='0', shape='box', fontname='fira')
    has_fail_node = False

    nfas2name = dict()
    for nfas, dfa in dfa_start.set_to_state.items():
        labels = sorted(nfa.label for nfa in nfas)
        name = ''.join(labels)
        if dfa is dfa_start:
            node_opts = dict(color='black', fontcolor='white')
        elif dfa.is_end():
            node_opts = dict(color='green', fontcolor='white')
        else:
            node_opts = dict()
        g.node(name, ','.join(labels), **node_opts)
        assert name not in nfas2name.values()
        nfas2name[dfa.states] = name

    for dfa in dfa_start.set_to_state.values():
        name = nfas2name[dfa.states]
        for ch, to in dfa.char_to_set.chars.items():
            g.edge(name, nfas2name[to], ch)

        for not_char in dfa.char_to_set.not_accept:
            if not has_fail_node:
                g.node('FAIL', color='red', fontcolor='white')
                has_fail_node = True
            g.edge(name, 'FAIL', not_char)

        if dfa.char_to_set.other:
            g.edge(name, nfas2name[dfa.char_to_set.other], 'other')

    return g


def regex_match_begin(re: BaseNode, s: str):
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

    return ans + 1
