import regex.parser
import regex.statemachine
import regex.api

__all__ = tuple(regex.api.__all__)

for attr in regex.api.__all__:
    globals()[attr] = getattr(regex.api, attr)
