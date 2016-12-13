import itertools


def make_serial():
    gen = itertools.count()
    return lambda: next(gen)


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
