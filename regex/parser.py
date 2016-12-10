import itertools
from enum import Enum

import graphviz


class TokenGen:
    NONE = object()

    def __init__(self, gen):
        self.gen = gen
        self.buffer = []
        self.eof = False

    def peek(self):
        ret = self.get()
        self.unget(ret)
        return ret

    def get(self):
        if not self.eof:
            ret = self._get()
            if ret is Token.EOF:
                self.eof = True

        if self.eof:
            return Token.EOF
        else:
            return ret

    def _get(self):
        if self.buffer:
            return self.buffer.pop()
        else:
            return next(self.gen)

    def unget(self, item):
        self.buffer.append(item)


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

    EOF = ()


def read_escape(chars):
    return next(chars)


def tokenize(chars):
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
            yield Token.EOF
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


class ParseError(Exception):
    pass


class UnexpectedEOF(ParseError):
    pass


class UnexpectedToken(ParseError):
    def __init__(self, got, expect=None):
        super().__init__(got, expect)
        self.got = got
        self.expect = expect

    def __repr__(self):
        return '<{name} {id:#x} expect={expect}, got={got}>'\
            .format(name=self.__class__.__name__, id=id(self),
                    expect=self.expect, got=self.got)


def eat_token(tokens: TokenGen, expect=None):
    tok = tokens.get()
    if expect is not None and tok != expect:
        raise UnexpectedToken(expect, tok)
    if tok is Token.EOF:
        raise UnexpectedEOF


def parse_par(tokens: TokenGen):
    eat_token(tokens, Token.LPAR)
    ret = parse_exp(tokens)
    eat_token(tokens, Token.RPAR)
    return ret


def parse_bra(tokens: TokenGen):
    pass


def parse_cat(tokens: TokenGen):
    cats = []
    while True:
        ch = tokens.peek()
        if ch is Token.EOF:
            break
        elif ch in (Token.OR, Token.RPAR):
            break
        elif ch is Token.LPAR:
            cats.append(parse_par(tokens))
        elif ch is Token.LBRACKET:
            cats.append(parse_bra(tokens))
        elif ch is Token.STAR:
            if not cats:
                raise UnexpectedToken(ch)
            if isinstance(cats[-1], Star):
                raise ParseError('mutiple repeat')
            cats[-1] = Star(cats[-1])
            eat_token(tokens, ch)
        elif ch is Token.DOT:
            cats.append(Dot())
            eat_token(tokens, ch)
        elif ch in (Token.BEGIN, Token.END):
            cats.append(Char(ch))
            eat_token(tokens, ch)
        elif isinstance(ch, Token):
            assert ch in (Token.RBRACKET, Token.NOT)
            raise UnexpectedToken(ch)
        else:
            assert isinstance(ch, str) and len(ch) == 1
            cats.append(Char(ch))
            eat_token(tokens, ch)

    if len(cats) == 0:
        return Empty()
    elif len(cats) == 1:
        return cats[0]
    else:
        return Cat(*cats)


def parse_exp(tokens: TokenGen):
    ors = []
    while True:
        cat = parse_cat(tokens)
        ors.append(cat)
        ch = tokens.peek()
        if ch is Token.EOF:
            break
        elif ch is Token.OR:
            eat_token(tokens, Token.OR)
        elif ch is Token.RPAR:
            break
        else:
            pass

    if len(ors) == 0:
        return Empty()
    elif len(ors) == 1:
        return ors[0]
    else:
        return Or(*ors)


def parse(tokens: TokenGen):
    exp = parse_exp(tokens)
    tok = tokens.peek()
    if tok is not Token.EOF:
        raise UnexpectedToken(tok)
    else:
        return exp


def regex_from_string(string):
    tokens = TokenGen(tokenize(iter(string)))
    return parse(tokens)


def make_serial():
    gen = itertools.count()
    return lambda: next(gen)


class BaseNode:
    def __init__(self, *children):
        """
        :type children: tuple[BaseNode|Token|str]
        """
        self.children = children

    def __eq__(self, other):
        if not isinstance(other, BaseNode):
            return False
        else:
            return (self.__class__ is other.__class__
                    and self.children == other.children)

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


class Empty(BaseNode):
    def _node_label(self):
        return 'NIL'


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
