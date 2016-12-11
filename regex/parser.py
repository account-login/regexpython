import graphviz

from regex.utils import make_serial, AutoNumber


class BufferedGen:
    def __init__(self, gen):
        self.gen = gen
        self.buffer = []

    def peek(self):
        ret = self.get()
        self.unget(ret)
        return ret

    def get(self):
        if self.buffer:
            return self.buffer.pop()
        else:
            return next(self.gen)

    def unget(self, item):
        self.buffer.append(item)


class TokenGen(BufferedGen):
    def __init__(self, gen):
        super().__init__(gen)
        self.eof = False

    def get(self):
        if not self.eof:
            try:
                ret = super().get()
            except StopIteration:
                self.eof = True
            else:
                if ret is Token.EOF:
                    self.eof = True

        if self.eof:
            return Token.EOF
        else:
            return ret

    def eat(self, expect=None):
        tok = self.get()
        if expect is not None and tok != expect:
            raise UnexpectedToken(got=tok, expect=expect)
        if tok is Token.EOF:
            raise UnexpectedEOF


class Token(AutoNumber):
    OR = ()

    LPAR = ()
    RPAR = ()

    LBRACKET = ()
    RBRACKET = ()
    DASH = ()

    STAR = ()
    NOT = ()

    DOT = ()

    BEGIN = ()
    END = ()

    EOF = ()


def read_escape(chars: BufferedGen):
    # TODO:
    return chars.get()


def tokenize(chars: BufferedGen):
    direct_yield = {
        '|': Token.OR,
        '(': Token.LPAR,
        ')': Token.RPAR,
        # '[': Token.LBRACKET,
        # ']': Token.RBRACKET,
        '*': Token.STAR,
        '.': Token.DOT,
        '^': Token.BEGIN,
        '$': Token.END,
    }

    in_bracket = False
    prev = None
    while True:
        try:
            ch = chars.get()
        except StopIteration:
            yield Token.EOF
            raise

        if in_bracket:
            if ch == '\\':
                tok = read_escape(chars)
            elif ch == ']':
                in_bracket = False
                tok = Token.RBRACKET
            elif ch == '^':
                if prev == Token.LBRACKET:
                    tok = Token.NOT
                else:
                    tok = ch
            elif ch == '-':
                tok = Token.DASH
            else:
                tok = ch
        else:
            if ch in direct_yield:
                tok = direct_yield[ch]
            elif ch == '[':
                in_bracket = True
                tok = Token.LBRACKET
            elif ch == '\\':
                tok = read_escape(chars)
            else:
                tok = ch

        prev = tok
        yield tok


class CharRange:
    def __init__(self, start, end):
        for ch in (start, end):
            if not isinstance(ch, str) and len(ch) == 1:
                raise ParseError('bad range')
        if ord(end) < ord(start):
            raise ParseError('bad range')
        self.start, self.end = start, end

    def __eq__(self, other):
        return self.start, self.end == other.start, other.end

    def __iter__(self):
        for codepoint in range(ord(self.start), ord(self.end) + 1):
            yield Char(chr(codepoint))


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


def parse_par(tokens: TokenGen):
    tokens.eat(Token.LPAR)
    ret = parse_exp(tokens)
    tokens.eat(Token.RPAR)
    return ret


def parser_bracket(tokens: TokenGen):
    tokens.eat(Token.LBRACKET)
    tok = tokens.peek()
    if tok is Token.NOT:
        # TODO:
        raise NotImplementedError
    else:
        ors = []
        while True:
            tok = tokens.get()
            if tok is Token.RBRACKET:
                if len(ors) == 0:
                    return Empty
                elif len(ors) == 1:
                    return ors[0]
                else:
                    return Or(*ors)
            elif tok is Token.EOF:
                raise UnexpectedToken(got=tok, expect=Token.RBRACKET)
            elif tok is Token.DASH:
                if len(ors) == 0:
                    ors.append(Char('-'))
                else:
                    next_tok = tokens.peek()
                    if next_tok is Token.RBRACKET:
                        ors.append(Char('-'))
                    elif next_tok is Token.EOF:
                        raise UnexpectedToken(got=tok, expect=Token.RBRACKET)
                    else:
                        if isinstance(ors[-1], Char):
                            ors[-1] = CharRange(ors[-1].children[0], tokens.get())
                        else:
                            # TODO: possible bad range error
                            ors.append(Char('-'))
            elif isinstance(tok, str):
                assert len(tok) == 1
                ors.append(Char(tok))
            else:
                raise NotImplementedError


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
            cats.append(parser_bracket(tokens))
        elif ch is Token.STAR:
            if not cats:
                raise UnexpectedToken(got=ch)
            if isinstance(cats[-1], Star):
                raise ParseError('mutiple repeat')
            cats[-1] = Star(cats[-1])
            tokens.eat(ch)
        elif ch is Token.DOT:
            cats.append(Dot())
            tokens.eat(ch)
        elif ch in (Token.BEGIN, Token.END):
            cats.append(Char(ch))
            tokens.eat(ch)
        elif isinstance(ch, Token):
            assert ch in (Token.RBRACKET, Token.NOT)
            raise UnexpectedToken(got=ch)
        else:
            assert isinstance(ch, str) and len(ch) == 1
            cats.append(Char(ch))
            tokens.eat(ch)

    if len(cats) == 0:
        return Empty()
    elif len(cats) == 1:
        # unnecessary optimization
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
            tokens.eat(Token.OR)
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
        raise UnexpectedToken(got=tok)
    else:
        return exp


def regex_from_string(string):
    tokens = TokenGen(tokenize(BufferedGen(iter(string))))
    return parse(tokens)


class BaseNode:
    def __init__(self, *children):
        """
        :type children: tuple[BaseNode|Token|CharRange|str]
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
