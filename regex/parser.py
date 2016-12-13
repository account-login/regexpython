from regex.utils import AutoNumber


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
        assert expect is not Token.EOF
        tok = self.get()
        if tok is Token.EOF:
            raise UnexpectedEOF(expect=expect)
        if expect is not None and tok != expect:
            raise UnexpectedToken(got=tok, expect=expect)


class Token(AutoNumber):
    OR = ()

    LPAR = ()
    RPAR = ()

    LBRACKET = ()
    RBRACKET = ()
    DASH = ()
    NOT = ()

    STAR = ()
    PLUS = ()
    QUESTION = ()

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
        '+': Token.PLUS,
        '?': Token.QUESTION,
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
                if prev in (Token.LBRACKET, Token.NOT):
                    # empty bracket not allowed, left bracket must follow a regular char.
                    tok = ch
                else:
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


class ParseError(Exception):
    pass


class BadRange(ParseError):
    pass


class UnexpectedToken(ParseError):
    def __init__(self, *, got, expect=None, msg=None):
        msg = msg or ''
        super().__init__(msg, dict(got=got, expect=expect))
        self.got = got
        self.expect = expect
        self.msg = msg

    def __repr__(self):
        return '<{name} {id:#x} msg={msg} expect={expect}, got={got}>'\
            .format(name=self.__class__.__name__, id=id(self),
                    msg=self.msg, expect=self.expect, got=self.got)


class UnexpectedEOF(UnexpectedToken):
    def __init__(self, *, got=None, expect=None, msg=None):
        if got is not None:
            assert got is Token.EOF
        else:
            got = Token.EOF
        super().__init__(got=got, expect=expect, msg=msg)


def parse_par(tokens: TokenGen):
    tokens.eat(Token.LPAR)
    ret = parse_exp(tokens)
    tokens.eat(Token.RPAR)
    return ret


def parser_bracket(tokens: TokenGen):
    tokens.eat(Token.LBRACKET)
    complement = tokens.peek() is Token.NOT
    if complement:
        tokens.eat(Token.NOT)

    ors = []
    while True:
        tok = tokens.get()
        if tok is Token.RBRACKET:
            if len(ors) == 0:
                assert False, 'impossible'

            if complement:
                return NotChars(*ors)
            else:
                if len(ors) == 1:
                    return ors[0]
                else:
                    return Or(*ors)
        elif tok is Token.EOF:
            raise UnexpectedEOF()
        elif tok is Token.DASH:
            if len(ors) == 0:
                ors.append(Char('-'))
            else:
                next_tok = tokens.peek()
                if next_tok is Token.RBRACKET:
                    ors.append(Char('-'))
                elif next_tok is Token.EOF:
                    raise UnexpectedEOF(expect=Token.RBRACKET)
                else:
                    if isinstance(ors[-1], Char):
                        ors[-1] = CharRange(start=ors[-1].children[0], end=tokens.get())
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
        elif ch in (Token.STAR, Token.PLUS, Token.QUESTION):
            if not cats:
                raise ParseError('nothing to repeat')
            if isinstance(cats[-1], (Star, Plus, Question)):
                raise ParseError('multiple repeat')
            tok2node = {
                Token.STAR: Star,
                Token.PLUS: Plus,
                Token.QUESTION: Question,
            }
            cats[-1] = tok2node[ch](cats[-1])
            tokens.eat(ch)
        elif ch is Token.DOT:
            cats.append(Dot())
            tokens.eat(ch)
        elif ch in (Token.BEGIN, Token.END):
            cats.append(Char(ch))
            tokens.eat(ch)
        elif isinstance(ch, Token):
            assert ch in (Token.RBRACKET, Token.NOT)
            assert False, 'impossible'
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
            assert False, 'impossible'

    assert len(ors) != 0
    if len(ors) == 1:
        return ors[0]
    else:
        return Or(*ors)


def parse(tokens: TokenGen):
    exp = parse_exp(tokens)
    tok = tokens.peek()
    if tok is not Token.EOF:
        assert False, 'impossible'
    else:
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

    def __eq__(self, other):
        if not isinstance(other, BaseNode):
            return False
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
        return str(self.children[0])


class CharRange(BaseNode):
    def __init__(self, *args, start=None, end=None):
        assert len(args) == 0
        super().__init__(*args)
        for ch in (start, end):
            if not isinstance(ch, str) and len(ch) == 1:
                raise BadRange('not character type')
        if ord(end) < ord(start):
            raise BadRange('reversed range')
        self.start, self.end = start, end

    def __eq__(self, other):
        return self.start, self.end == other.start, other.end

    def __iter__(self):
        for codepoint in range(ord(self.start), ord(self.end) + 1):
            yield Char(chr(codepoint))


class NotChars(BaseNode):
    pass


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
