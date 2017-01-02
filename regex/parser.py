from regex.errors import ParseError, BadRange, UnexpectedToken, UnexpectedEOF
from regex.tokenizer import Token, tokenize
from regex.utils import BufferedGen, repr_range


class TokenGen(BufferedGen):
    def __init__(self, gen):
        super().__init__(gen)
        self.eof = False

    def get(self) -> Token:
        if not self.eof:
            ret = super().get()
            if ret.type is Token.EOF:
                self.eof = True

        if self.eof:
            return Token.EOF()
        else:
            return ret

    def eat(self, expect: Token=None):
        assert expect.type is not Token.EOF
        tok = self.get()
        if tok.type is Token.EOF:
            raise UnexpectedEOF(expect=expect)
        if expect is not None and tok != expect:
            raise UnexpectedToken(got=tok, expect=expect)


def parse_par(tokens: TokenGen):
    tokens.eat(Token.LPAR())
    ret = parse_exp(tokens)
    tokens.eat(Token.RPAR())
    return ret


def parser_bracket(tokens: TokenGen):
    tokens.eat(Token.LBRACKET())
    complement = tokens.peek().type is Token.NOT
    if complement:
        tokens.eat(Token.NOT())

    ors = []
    while True:
        tok = tokens.get()
        if tok.type is Token.RBRACKET:
            assert len(ors) != 0
            return Bracket(*ors, complement=complement)
        elif tok.type is Token.EOF:
            raise UnexpectedEOF()
        elif tok.type is Token.DASH:
            if len(ors) == 0:
                ors.append(Char('-'))
            else:
                next_tok = tokens.peek()
                if next_tok.type is Token.RBRACKET:
                    ors.append(Char('-'))
                elif next_tok.type is Token.EOF:
                    raise UnexpectedEOF(expect=Token.RBRACKET())
                elif next_tok.type is Token.CHAR:
                    if isinstance(ors[-1], CharRange):
                        ors.append(Char('-'))
                    elif isinstance(ors[-1], Char):
                        ors[-1] = CharRange(start=ors[-1].children[0], end=tokens.get().value)
                    else:
                        raise BadRange('not character type')
                else:
                    raise BadRange('not character type')
        elif tok.type is tok.CHAR:
            assert len(tok.value) == 1
            ors.append(Char(tok.value))
        elif tok.type is tok.ESCAPE:
            ors.append(lookup_escape(tok))
        else:
            raise NotImplementedError


def parse_cat(tokens: TokenGen):
    cats = []
    while True:
        tok = tokens.peek()
        if tok.type is Token.EOF:
            break
        elif tok.type in (Token.OR, Token.RPAR):
            break
        elif tok.type is Token.LPAR:
            cats.append(parse_par(tokens))
        elif tok.type is Token.LBRACKET:
            cats.append(parser_bracket(tokens))
        elif tok.type in (Token.STAR, Token.PLUS, Token.QUESTION):
            if not cats:
                raise ParseError('nothing to repeat')
            if isinstance(cats[-1], (Star, Plus, Question)):
                raise ParseError('multiple repeat')
            tok2node = {
                Token.STAR: Star,
                Token.PLUS: Plus,
                Token.QUESTION: Question,
            }
            cats[-1] = tok2node[tok.type](cats[-1])
            tokens.eat(tok)
        elif tok.type is Token.DOT:
            cats.append(Dot())
            tokens.eat(tok)
        elif tok.type in (Token.BEGIN, Token.END):
            cats.append(Char(tok))
            tokens.eat(tok)
        elif tok.type is Token.CHAR:
            assert isinstance(tok.value, str) and len(tok.value) == 1
            cats.append(Char(tok.value))
            tokens.eat(tok)
        elif tok.type is Token.ESCAPE:
            cats.append(lookup_escape(tok))
            tokens.eat(tok)
        else:
            assert tok.type in (Token.RBRACKET, Token.NOT)
            assert not 'possible'

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
        tok = tokens.peek()
        if tok.type is Token.EOF:
            break
        elif tok.type is Token.OR:
            tokens.eat(Token.OR())
        elif tok.type is Token.RPAR:
            break
        else:
            assert not 'possible'

    assert len(ors) != 0
    if len(ors) == 1:
        return ors[0]
    else:
        return Or(*ors)


def parse(tokens: TokenGen):
    exp = parse_exp(tokens)
    assert tokens.peek().type is Token.EOF
    return exp


def ast_from_string(string):
    tokens = TokenGen(tokenize(BufferedGen(iter(string))))
    return parse(tokens)


class BaseNode:
    def __init__(self, *children, **kwargs):
        """
        :type children: tuple[BaseNode|Token|str]
        """
        self.children = children

    def __eq__(self, other: 'BaseNode'):
        if not isinstance(other, BaseNode):
            raise TypeError('uncomparable types: BaseNode vs {}'.format(other.__class__.__name__))
        else:
            return (self.__class__ is other.__class__
                    and self.children == other.children)

    def _repr_svg_(self):
        return self.to_graphiviz()._repr_svg_()

    def to_graphiviz(self):
        from regex.visualize import ast_to_gv
        return ast_to_gv(self)

    def _node_label(self):
        return self.__class__.__name__

    def _add_to_gv(self, graph, serial, parent_name=None, edge_opts=None):
        from regex.visualize import add_ast_node_to_gv
        return add_ast_node_to_gv(self, graph, serial, parent_name, edge_opts)


class Empty(BaseNode):
    def _node_label(self):
        return 'NIL'


class Char(BaseNode):
    def _node_label(self):
        assert len(self.children) == 1
        assert isinstance(self.children[0], (str, Token))
        if isinstance(self.children[0], str):
            return repr_range(self.children[0], self.children[0])
        elif isinstance(self.children[0], Token):
            return self.children[0].type.__name__
        else:
            assert not 'possible'


class CharRange(BaseNode):
    def __init__(self, *, start=None, end=None):
        for ch in (start, end):
            assert isinstance(ch, str) and len(ch) == 1
        if ord(end) < ord(start):
            raise BadRange('reversed range')

        super().__init__()
        self.start, self.end = start, end

    def __eq__(self, other):
        return self.start, self.end == other.start, other.end

    def _node_label(self):
        return '{cls}: {range}'.format(
            cls=self.__class__.__name__,
            range=repr_range(self.start, self.end),
        )


class Bracket(BaseNode):
    def __init__(self, *children, complement: bool):
        super().__init__(*children)
        self.complement = complement

    def _node_label(self):
        ret = self.__class__.__name__
        if self.complement:
            ret += '^'
        return ret

    def __eq__(self, other):
        return super().__eq__(other) and self.complement is other.complement


class Dot(BaseNode):
    pass


class Star(BaseNode):
    pass


class Plus(BaseNode):
    pass


class Question(BaseNode):
    pass


class Cat(BaseNode):
    def _add_to_gv(self, graph, serial, parent_name=None, edge_opts=None):
        from regex.visualize import add_cat_node_to_gv
        return add_cat_node_to_gv(self, graph, serial, parent_name, edge_opts)


class Or(BaseNode):
    pass


def lookup_escape(tok: Token) -> BaseNode:
    if tok.value in PREDEFINED_RANGE:
        return PREDEFINED_RANGE[tok.value]
    elif tok.value in 'bB':
        raise NotImplementedError
    else:
        assert not 'possible'


# TODO: unicode mode
PREDEFINED_RANGE = {
    'w': ast_from_string('[a-zA-Z0-9_]'),
    'W': ast_from_string('[^a-zA-Z0-9_]'),
    's': ast_from_string('[ \\t\\n\\r\\f\\v]'),
    'S': ast_from_string('[^ \\t\\n\\r\\f\\v]'),
    'd': ast_from_string('[0-9]'),
    'D': ast_from_string('[^0-9]'),
}
