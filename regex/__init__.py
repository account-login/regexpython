import regex.parser
import regex.tokenizer
import regex.statemachine
import regex.errors
import regex.api

__all__ = ()


def _grab_all_from(module):
    global __all__
    for attr in module.__all__:
        globals()[attr] = getattr(module, attr)

    __all__ += module.__all__


_grab_all_from(regex.errors)
_grab_all_from(regex.api)

del _grab_all_from
