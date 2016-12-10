import itertools
from enum import Enum

import graphviz


class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class Token(AutoNumber):
    OR = ()

    LPAR = ()
    RPAR = ()

    LBRACKET = ()
    RBRACKET = ()

    STAR = ()
    NOT = ()

    DOT = ()

    BEGIN = ()
    END = ()


def read_escape(chars):
    return next(chars)


def tokenizer(chars):
    direct_yield = {
        '|': Token.OR,
        '(': Token.LPAR,
        ')': Token.RPAR,
        '[': Token.LBRACKET,
        ']': Token.RBRACKET,
        '*': Token.STAR,
        '.': Token.DOT,
        # '^': Token.BEGIN,
        '$': Token.END,
    }

    prev = None
    while True:
        try:
            ch = next(chars)
        except StopIteration:
            raise

        if ch in direct_yield:
            tok = direct_yield[ch]
        elif ch == '^':
            if prev == Token.LBRACKET:
                tok = Token.NOT
            else:
                tok = Token.BEGIN
        elif ch == '\\':
            tok = read_escape(chars)
        else:
            tok = ch

        prev = tok
        yield tok


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
        g.attr('node', width='0', height='0', shape='box', fontname='Fira Code')
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
