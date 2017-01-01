import pytest

from regex.errors import ParseError
from regex.parser import ast_from_string


def expect_parser_raise(string, exception=ParseError, *, msg=None):
    with pytest.raises(exception) as exec_info:
        ast_from_string(string)
    if msg is not None:
        assert msg in repr(exec_info.value)
