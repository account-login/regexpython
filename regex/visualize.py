from itertools import chain
from graphviz import Digraph

from regex.statemachine import NfaState, NfaPair, DfaState
from regex.parser import BaseNode, Cat
from regex.utils import make_serial


def ast_to_gv(ast: BaseNode):
    g = Digraph()
    g.attr('node', width='0', height='0', shape='box', fontname='Fira Code')
    ast._add_to_gv(g, make_serial())
    return g


def add_ast_node_to_gv(node: BaseNode, graph: Digraph, serial, parent_name=None, edge_opts=None):
    name = 'N_{}'.format(serial())
    graph.node(name, node._node_label())
    if parent_name is not None:
        graph.edge(parent_name, name, **(edge_opts or {}))

    for c in node.children:
        if isinstance(c, BaseNode):
            c._add_to_gv(graph, serial, name)

    return name


def add_cat_node_to_gv(node: Cat, graph: Digraph, serial, parent_name=None, edge_opts=None):
    root_name = 'N_{}'.format(serial())
    graph.node(root_name, node._node_label())

    child_names = []
    prev_name = root_name
    for i, ch in enumerate(node.children):
        sub_edge_opts = dict(arrowhead='none') if i != 0 else {}
        name = ch._add_to_gv(graph, serial, prev_name, edge_opts=sub_edge_opts)
        child_names.append(name)
        prev_name = name

    subgraph = Digraph()
    subgraph.attr('graph', rank='same')
    for ch_name in child_names:
        subgraph.node(ch_name)
    graph.subgraph(subgraph)

    if parent_name is not None:
        graph.edge(parent_name, root_name, **(edge_opts or {}))
    return root_name


def nfa_labelize(nfa_pair: NfaPair):
    start, end = nfa_pair

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


def nfa_to_gv(nfa_pair: NfaPair, labelize=True):
    if labelize:
        nfa_labelize(nfa_pair)

    start, end = nfa_pair
    g = Digraph()
    g.attr('node', style='filled', width='0', height='0', shape='box', fontname='Fira Code')

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
            g.edge(name, sub_name, str(node.char))
        elif node.not_chars is not None:
            nonlocal has_fail_node
            if not has_fail_node:
                g.node('FAIL', color='red', fontcolor='white')
                has_fail_node = True
            g.edge(name, 'FAIL', str(node.not_chars))

        if node.other:
            sub_name = seen.get(node.other) or rec(node.other)
            g.edge(name, sub_name, 'other')

        for to in node.epsilon:
            sub_name = seen.get(to) or rec(to)
            g.edge(name, sub_name, 'ε')

        return name

    rec(start)
    return g


def dfa_to_gv(dfa_start: DfaState):
    g = Digraph()
    g.attr('node', style='filled', width='0', height='0', shape='box', fontname='Fira Code')
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
            g.edge(name, nfas2name[to], str(ch))

        for not_char in dfa.char_to_set.not_accept:
            if not has_fail_node:
                g.node('FAIL', color='red', fontcolor='white')
                has_fail_node = True
            g.edge(name, 'FAIL', not_char)

        if dfa.char_to_set.other:
            g.edge(name, nfas2name[dfa.char_to_set.other], 'other')

    return g
