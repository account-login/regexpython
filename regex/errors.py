

__all__ = ('ParseError', 'BadRange', 'IllegalEscape', 'UnexpectedToken', 'UnexpectedEOF')


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
        from regex.tokenizer import Token

        if got is not None:
            assert got.type is Token.EOF
        else:
            got = Token.EOF()
        super().__init__(got=got, expect=expect, msg=msg)
