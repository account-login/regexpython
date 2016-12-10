import itertools
from enum import Enum


def make_serial():
    gen = itertools.count()
    return lambda: next(gen)


class AutoNumber(Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
