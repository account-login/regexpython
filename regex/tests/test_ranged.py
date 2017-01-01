from itertools import permutations

from regex.ranged import RangeMap, RangeMapItem, RangeSet, MIN_CHAR, MAX_CHAR


def rm_from_pairs(pairs):
    rm = RangeMap()
    rm.sl.clear()

    start = MIN_CHAR
    for end, value in pairs:
        rm.sl.insert(RangeMapItem(start, end, value))
        start = chr(ord(end) + 1)

    rm.sl.insert(RangeMapItem(start, MAX_CHAR, set()))
    return rm


def rm_to_pairs(rm: RangeMap):
    return [ (data.end, data.value) for data in rm.sl.data_iter() ][:-1]


def check_start_end(rm: RangeMap):
    prev = None
    for data in rm.sl.data_iter():
        if prev is not None:
            assert ord(prev.end) + 1 == ord(data.start)
        else:
            assert data.start == MIN_CHAR
        prev = data

    assert data.end == MAX_CHAR


def test_get():
    def query_pairs_naive(pairs, char):
        start = MIN_CHAR
        for end, data in pairs:
            if start <= char <= end:
                return data
            start = chr(ord(end) + 1)
        assert not 'possible'

    def run(pairs):
        rm = rm_from_pairs(pairs)
        check_start_end(rm)

        for cp in range(ord(pairs[-1][0]) + 1):
            char = chr(cp)
            assert rm.get_char(char) == query_pairs_naive(pairs, char)
            assert rm.get_char(MAX_CHAR) == set()

    run([('a', {1}), ('e', {2}), ('y', {3})])


def test_query_overlap():
    def construct(ends):
        return rm_from_pairs((end, set()) for end in ends)

    assert list((item.start, item.end) for item in construct('abc').sl.data_iter()) \
        == [(MIN_CHAR, 'a'), ('b', 'b'), ('c', 'c'), ('d', MAX_CHAR)]

    def run(ends, start, end, expected):
        rm = construct(ends)
        left, middle, right = rm.query_overlap(start, end)
        el, em, er = expected
        if el is None:
            assert left is None, print(left)
        else:
            assert left.end == el
        assert [ data.end for data in middle ] == em

        if er is None:
            assert right is None, print(right)
        else:
            assert right.end == er

    run('aeg', 'a', 'b', ('a', [], 'e'))

    run('aeg', 'c', 'd', ('e', [], 'e'))
    run('aeg', 'b', 'c', (None, [], 'e'))
    run('aeg', 'c', 'e', ('e', [], None))
    run('aeg', 'c', 'f', ('e', [], 'g'))

    run('aeg', 'b', 'e', (None, ['e'], None))
    run('aeg', 'a', 'f', ('a', ['e'], 'g'))
    run('abc', 'a', 'b', ('a', ['b'], None))
    run('abc', 'a', 'c', ('a', ['b', 'c'], None))
    run('abcx', 'a', 'f', ('a', ['b', 'c'], 'x'))

    run('afy', 'd', 'f', ('f', [], None))
    run('afy', 'g', 'n', (None, [], 'y'))

    run('afy', MIN_CHAR, MAX_CHAR, (None, list('afy') + [MAX_CHAR], None))


def test_add_range():
    def check_perm_add(pairs, expected):
        triples = []
        pstart = MIN_CHAR
        for pend, pvalue in pairs:
            triples.append((pstart, pend, pvalue))
            pstart = chr(ord(pend) + 1)

        for perm_triples in permutations(triples, len(triples)):
            rm2 = RangeMap()
            for pstart, pend, pvalue in perm_triples:
                if pvalue:
                    rm2.add_range(pstart, pend, pvalue)
                    check_start_end(rm2)
            assert rm_to_pairs(rm2) == expected

    def run(pairs, start, end, value, expected):
        rm = rm_from_pairs(pairs)
        check_start_end(rm)

        check_perm_add(pairs, rm_to_pairs(rm))

        rm.add_range(start, end, value)
        check_start_end(rm)
        assert rm_to_pairs(rm) == expected

    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'd', 'g', {4},
        [('a', {1, 2}), ('c', {1}), ('e', {1, 4}), ('g', {3, 4}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        '1', 'g', {4},
        [('0', {1, 2}), ('a', {1, 2, 4}), ('e', {1, 4}), ('g', {3, 4}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'c', 'd', {4},
        [('a', {1, 2}), ('b', {1}), ('d', {1, 4}), ('e', {1}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'c', 'e', {4},
        [('a', {1, 2}), ('b', {1}), ('e', {1, 4}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'b', 'd', {4},
        [('a', {1, 2}), ('d', {1, 4}), ('e', {1}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'b', 'e', {4},
        [('a', {1, 2}), ('e', {1, 4}), ('k', {3})],
    )

    run(
        [('a', {1, 2}), ('e', {1}), ('k', {3})],
        'b', 'e', {2},
        [('e', {1, 2}), ('k', {3})],
    )
    run(
        [('a', {1, 2}), ('e', {1}), ('k', {1, 2})],
        '0', 'e', {2},
        [('k', {1, 2})],
    )

    run(
        [('a', {1}), ('f', set()), ('p', {1})],
        'b', 'f', {1},
        [('p', {1})],
    )
    run(
        [(chr(8), set()), ('\n', {1}), (chr(11), set()), ('\r', {1}), (chr(31), set()), (' ', {1})],
        chr(11), chr(11), {1},
        [(chr(8), set()), ('\r', {1}), (chr(31), set()), (' ', {1})],
    )


def test_merge_equals():
    def run(pairs, start, end, expected):
        rm = rm_from_pairs(pairs)
        rm.merge_equals(start, end)
        check_start_end(rm)
        assert rm_to_pairs(rm) == expected

    run(
        [('a', {1, 2}), ('f', {1, 2}), ('i', {1, 2}), ('p', {1, 2})],
        'g', 'i',
        [('a', {1, 2}), ('p', {1, 2})],
    )
    run(
        [('a', {1, 2}), ('f', {1, 2}), ('i', {1, 2}), ('p', {1})],
        'g', 'i',
        [('a', {1, 2}), ('i', {1, 2}), ('p', {1})],
    )
    run(
        [('a', {1, 2}), ('f', {1}), ('i', {1, 2}), ('p', {1, 2})],
        'g', 'i',
        [('a', {1, 2}), ('f', {1}), ('p', {1, 2})],
    )

    run(
        [('a', {1}), ('f', {1}), ('p', {1})],
        'b', 'f',
        [('p', {1})],
    )


def test_rangeset_complement():
    def expand(ranges):
        ans = set()
        for r in ranges:
            ans.update(chr(cp) for cp in range(ord(r.start), ord(r.end) + 1))
        return ans

    assert expand([RangeMapItem('a', 'e', set()), RangeMapItem('0', '9', set())]) \
        == set('abcde0123456789')

    def run(chars):
        rs = RangeSet()
        for ch in chars:
            rs.add_char(ch)
        assert expand(rs.get_true_ranges()) == set(chars)

        rs.complement()
        assert expand(rs.get_false_ranges()) == set(chars)

    run('123')
    run('1az-')
