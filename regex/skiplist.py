import random


class SLNode:
    __slots__ = ('tower', 'data')

    def __init__(self, data, height=1):
        self.tower = [None] * height
        self.data = data


def sl_height(p=0.5, _max_height=32):
    ans = 1
    rand = random.random()
    threshold = p
    while rand < threshold and ans < _max_height:
        ans += 1
        threshold *= p

    return ans


def sl_insert_node(node: SLNode, new_node: SLNode):
    for next_node in reversed(node.tower):
        if next_node is not None and next_node.data <= new_node.data:
            sl_insert_node(next_node, new_node)
            # link node to new_node
            for i in range(len(next_node.tower), min(len(new_node.tower), len(node.tower))):
                new_node.tower[i] = node.tower[i]
                node.tower[i] = new_node
            return
    # insert new_node here

    # do not compare with head.data since new_node.data may be wrapped
    # assert node.data <= new_node.data
    assert node.tower[0] is None or node.tower[0].data > new_node.data

    # link node to new_node
    for i in range(min(len(new_node.tower), len(node.tower))):
        new_node.tower[i] = node.tower[i]
        node.tower[i] = new_node


def sl_remove(node: SLNode, data) -> SLNode:
    for next_node in reversed(node.tower):
        if next_node is not None and next_node.data < data:
            removed = sl_remove(next_node, data)
            if removed is not None:
                assert removed is not next_node
                for i in range(len(next_node.tower), min(len(removed.tower), len(node.tower))):
                    node.tower[i] = removed.tower[i]

            return removed

    assert node.tower[0] is None or node.tower[0].data >= data

    if node.tower[0] is not None and node.tower[0].data == data:
        removed = node.tower[0]
        for i in range(min(len(node.tower), len(removed.tower))):
            node.tower[i] = removed.tower[i]
        return removed
    else:
        return None


class SkipList:
    def __init__(self, *, prob=0.5):
        self.head = SLNode(None, height=1)
        assert 0 < prob < 1
        self.prob = prob

    def node_iter(self):
        cur = self.head
        while cur.tower[0] is not None:
            cur = cur.tower[0]
            yield cur

    def data_iter(self):
        for node in self.node_iter():
            yield node.data

    def lower_bound_nodes(self, data):
        node = self.head
        while True:
            next_node = None
            for candidate in reversed(node.tower):
                if candidate is not None and candidate.data < data:
                    next_node = candidate
                    break

            if next_node is None:
                # all next_node.data is >= data
                next_node = node.tower[0]
                break
            else:
                assert next_node.data < data
                node = next_node

        while next_node is not None:
            assert next_node.data >= data
            yield next_node
            next_node = next_node.tower[0]

    def lower_bound(self, data):
        for node in self.lower_bound_nodes(data):
            yield node.data

    def upper_bound_nodes(self, data):
        def g(node):
            prev_next_node = None
            for next_node in reversed(node.tower):
                if (
                    next_node is not prev_next_node
                    and len(next_node.tower) <= len(node.tower)
                    and next_node.data <= data
                ):
                    yield from g(next_node)

                prev_next_node = next_node

            if node.data is not None and node.data <= data:
                yield node

        yield from g(self.head)

    def upper_bound(self, data):
        for node in self.upper_bound_nodes(data):
            yield node.data

    def insert(self, data):
        new_node = SLNode(data, height=sl_height(self.prob))
        sl_insert_node(self.head, new_node)
        extended = len(new_node.tower) - len(self.head.tower)
        if extended > 0:
            # increase height of head
            self.head.tower.extend([new_node] * extended)
        return new_node

    def remove(self, data):
        removed = sl_remove(self.head, data)
        while len(self.head.tower) > 1 and self.head.tower[-1] is None:
            # decrease height of head
            self.head.tower.pop()
        return removed

    def clear(self):
        self.head = SLNode(float('-inf'), height=1)
