from functools import total_ordering
from itertools import islice

from regex.skiplist import SkipList
from regex.utils import repr_range


MIN_CHAR = '\0'
MAX_CHAR = '\U0010ffff'


@total_ordering
class RangeMapItem:
    def __init__(self, start: str, end: str, value):
        self.start = start
        self.end = end
        self.value = set(value)

    def __eq__(self, other):
        return self.end == other.end

    def __lt__(self, other):
        return self.end < other.end

    def __repr__(self):
        return '<{cls} range={range} value={value}>'.format(
            cls=self.__class__.__name__,
            range=repr_range(self.start, self.end),
            value=self.value,
        )


class RangeMap:
    def __init__(self):
        self.sl = SkipList()
        self.sl.insert(RangeMapItem(MIN_CHAR, MAX_CHAR, set()))

    def get_char(self, char: str) -> set():
        found = next(self.sl.lower_bound(RangeMapItem(MIN_CHAR, char, set())))
        assert found.start <= char
        return found.value

    def get_ranges(self):
        yield from self.sl.data_iter()

    def query_overlap(self, start: str, end: str):
        left, middle, right = None, [], None

        for node in self.sl.lower_bound_nodes(RangeMapItem(MIN_CHAR, start, set())):
            data = node.data    # type: RangeMapItem
            if data.start < start and data.end <= end:
                assert left is None
                left = data
            elif data.start >= start and data.end > end:
                if data.start <= end:
                    right = data
                break
            elif data.start >= start and data.end <= end:
                middle.append(data)
            elif data.start < start and data.end > end:
                assert left is right is None and middle == []
                left = right = data
                break
            else:
                assert not 'possible'

        return left, middle, right

    def add_range(self, start: str, end: str, value: set):
        left, middle, right = self.query_overlap(start, end)
        if left is right is not None:
            assert left.start < start and right.end > end
            mid_data = RangeMapItem(start, end, left.value.union(value))
            right_data = RangeMapItem(chr(ord(end) + 1), right.end, set(right.value))
            left.end = chr(ord(start) - 1)
            self.sl.insert(mid_data)
            self.sl.insert(right_data)
        else:
            if left is not None:
                assert left.end >= start
                new_data = RangeMapItem(start, left.end, left.value.union(value))
                left.end = chr(ord(start) - 1)
                self.sl.insert(new_data)
            if right is not None:
                assert right.start <= end
                new_data = RangeMapItem(right.start, end, right.value.union(value))
                right.start = chr(ord(end) + 1)
                self.sl.insert(new_data)

            for data in middle:
                data.value.update(value)

        self.merge_equals(start, end)

    def prev_value(self, data):
        return next(islice(self.sl.upper_bound(data), 1, 2), None)

    def next_value(self, data):
        return next(islice(self.sl.lower_bound(data), 1, 2), None)

    def merge_equals(self, start: str, end: str):
        left, middle, right = self.query_overlap(start, end)
        assert left is right is None
        assert middle

        prec = self.prev_value(middle[0])
        if prec is not None:
            middle.insert(0, prec)
        succ = self.next_value(middle[-1])
        if succ is not None:
            middle.append(succ)

        prev = None
        for data in middle:
            if prev is not None and prev.value == data.value:
                self.sl.remove(data)
                prev.end = data.end
            else:
                prev = data


class RangeSet(RangeMap):
    TRUE = frozenset({1})
    FALSE = frozenset()

    def __str__(self):
        return ','.join(repr_range(r.start, r.end) for r in self.get_true_ranges())

    def add_range(self, start: str, end: str, value=None):
        super().add_range(start, end, self.TRUE)

    def get_true_ranges(self):
        return filter(lambda data: data.value == self.TRUE, self.get_ranges())

    def get_false_ranges(self):
        return filter(lambda data: data.value == self.FALSE, self.get_ranges())

    def add_char(self, char: str):
        self.add_range(char, char)

    def complement(self):
        for data in self.get_ranges():  # type: RangeMapItem
            if data.value == self.TRUE:
                data.value = set(self.FALSE)
            else:
                data.value = set(self.TRUE)

    @classmethod
    def all(cls):
        rs = cls()
        rs.add_range(MIN_CHAR, MAX_CHAR)
        return rs
