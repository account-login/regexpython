import itertools


def make_serial():
    gen = itertools.count()
    return lambda: next(gen)


def repr_range(start, end):
    if start == end:
        return repr(start)[1:-1]
    else:
        return '{}-{}'.format(*map(lambda x: repr(x)[1:-1], (start, end)))


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
