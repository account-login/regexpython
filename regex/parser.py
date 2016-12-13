

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

    def get(self) -> 'Token':
        if not self.eof:
            try:
                ret = super().get()
            except StopIteration:
                self.eof = True
            else:
                if ret.type is Token.EOF:
                    self.eof = True

        if self.eof:
            return Token.EOF()
        else:
            return ret

    def eat(self, expect: 'Token'=None):
        assert expect.type is not Token.EOF
        tok = self.get()
        if tok.type is Token.EOF:
            raise UnexpectedEOF(expect=expect)
        if expect is not None and tok != expect:
            raise UnexpectedToken(got=tok, expect=expect)


class TokenMeta(type):
    def __new__(metacls, name, bases, namespaces):
        sub_types = set()
        for attr, value in namespaces.items():
            if value == ():
                sub_types.add(attr)
        for attr in sub_types:
            del namespaces[attr]

        klass = super().__new__(metacls, name, bases, namespaces)
        for attr in sub_types:
            sub_cls = super().__new__(metacls, attr, (klass,), namespaces)
            setattr(klass, attr, sub_cls)

        return klass


class Token(metaclass=TokenMeta):
    OR = ()         # type: TokenMeta

    LPAR = ()       # type: TokenMeta
    RPAR = ()       # type: TokenMeta

    LBRACKET = ()   # type: TokenMeta
    RBRACKET = ()   # type: TokenMeta
    DASH = ()       # type: TokenMeta
    NOT = ()        # type: TokenMeta

    STAR = ()       # type: TokenMeta
    PLUS = ()       # type: TokenMeta
    QUESTION = ()   # type: TokenMeta

    DOT = ()        # type: TokenMeta
    CHAR = ()       # type: TokenMeta

    BEGIN = ()      # type: TokenMeta
    END = ()        # type: TokenMeta

    EOF = ()        # type: TokenMeta

    def __init__(self, value=None):
        self.value = value
        self.type = self.__class__

    def __eq__(self, other):
        return self.type, self.value == other.type, other.value

    def __hash__(self):
        return hash((self.type, self.value))


def read_escape(chars: BufferedGen, in_bracket: bool) -> Token:
    ascii_escpes = {
        'a': '\a',
        # 'b': '\b',
        'f': '\f',
        'n': '\n',
        'r': '\r',
        't': '\t',
        'v': '\v',
        '\\': '\\',
    }

    def check_hex_digits(digits):
        for d in digits:
            if d not in '0123456789abcdef':
                return False
        else:
            return True

    ch = chars.get()

    if ch == 'b':
        if in_bracket:
            return Token.CHAR('\b')
        else:
            raise NotImplementedError
    if ch in ascii_escpes:
        return Token.CHAR(ascii_escpes[ch])
    elif ch == 'A':
        return Token.BEGIN()
    elif ch == 'Z':
        return Token.END()
    elif ch in 'xuU':
        digits_num = {'x': 2, 'u': 4, 'U': 8}[ch]
        digits = [ chars.get().lower() for _ in range(digits_num) ]
        if not check_hex_digits(digits):
            raise IllegalEscape('\\' + ch + ''.join(digits))
        return Token.CHAR(chr(int(''.join(digits), base=16)))
    else:
        raise NotImplementedError


def tokenize(chars: BufferedGen):
    direct_yield = {
        '|': Token.OR(),
        '(': Token.LPAR(),
        ')': Token.RPAR(),
        # '[': Token.LBRACKET(),
        # ']': Token.RBRACKET(),
        '*': Token.STAR(),
        '+': Token.PLUS(),
        '?': Token.QUESTION(),
        '.': Token.DOT(),
        '^': Token.BEGIN(),
        '$': Token.END(),
    }

    in_bracket = False
    prev = None
    while True:
        try:
            ch = chars.get()
        except StopIteration:
            yield Token.EOF()
            raise

        if in_bracket:
            if ch == '\\':
                try:
                    tok = read_escape(chars, in_bracket)
                except StopIteration:
                    raise IllegalEscape
            elif ch == ']':
                if prev.type in (Token.LBRACKET, Token.NOT):
                    # empty bracket not allowed, left bracket must follow a regular char.
                    tok = Token.CHAR(ch)
                else:
                    in_bracket = False
                    tok = Token.RBRACKET()
            elif ch == '^':
                if prev.type == Token.LBRACKET:
                    tok = Token.NOT()
                else:
                    tok = Token.CHAR(ch)
            elif ch == '-':
                tok = Token.DASH()
            else:
                tok = Token.CHAR(ch)
        else:
            if ch in direct_yield:
                tok = direct_yield[ch]
            elif ch == '[':
                in_bracket = True
                tok = Token.LBRACKET()
            elif ch == '\\':
                try:
                    tok = read_escape(chars, in_bracket)
                except StopIteration:
                    raise IllegalEscape
            else:
                tok = Token.CHAR(ch)

        prev = tok
        yield tok


class ParseError(Exception):
    pass


class BadRange(ParseError):
    pass


class IllegalEscape(ParseError):
    def __init__(self, string=None):
        super().__init__(string)
        self.string = string

    def __repr__(self):
        return '<{name} {id:#x} string={string}>'.format(
            name=self.__class__.__name__, id=id(self), string=self.string
        )


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
            assert got.type is Token.EOF
        else:
            got = Token.EOF()
        super().__init__(got=got, expect=expect, msg=msg)


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

            if complement:
                return NotChars(*ors)
            else:
                if len(ors) == 1:
                    return ors[0]
                else:
                    return Or(*ors)
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
                else:
                    if isinstance(ors[-1], Char):
                        ors[-1] = CharRange(start=ors[-1].children[0], end=tokens.get().value)
                    else:
                        # TODO: possible bad range error
                        ors.append(Char('-'))
        elif tok.type is tok.CHAR:
            assert len(tok.value) == 1
            ors.append(Char(tok.value))
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
        else:
            assert tok.type in (Token.RBRACKET, Token.NOT)
            assert False, 'impossible'

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
        tok = tokens.peek()
        if tok.type is Token.EOF:
            break
        elif tok.type is Token.OR:
            tokens.eat(Token.OR())
        elif tok.type is Token.RPAR:
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
    assert tok.type is Token.EOF
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
