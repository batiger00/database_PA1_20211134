from dataclasses import dataclass, field


@dataclass
class BPlusTreeNode:
    is_leaf: bool = True
    keys: list[int] = field(default_factory=list)
    rids: list[int] = field(default_factory=list)
    children: list["BPlusTreeNode"] = field(default_factory=list)
    next_leaf: "BPlusTreeNode | None" = None


class BPlusTree:
    # Assume d is the minimum degree.
    def __init__(self, order: int):
        if order < 2:
            raise ValueError("B+ tree order must be at least 2.")

        self.order = order
        self.root = BPlusTreeNode()
        self.split_count = 0

    def search(self, key: int) -> int | None:
        leaf = self._find_leaf(key)

        for i, k in enumerate(leaf.keys):
            if k == key:
                return leaf.rids[i]

        return None

    def insert(self, key: int, rid: int) -> None:
        if self.search(key) is not None:
            raise ValueError(f"Duplicate key insertion is not allowed: {key}")

        root = self.root
        if self._is_full(root):
            new_root = BPlusTreeNode(is_leaf=False, children=[root])
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, rid)

    def delete(self, key: int) -> bool:
        path: list[tuple[BPlusTreeNode, int]] = []
        leaf = self._find_leaf(key, path)

        if key not in leaf.keys:
            return False

        key_index = leaf.keys.index(key)
        leaf.keys.pop(key_index)
        leaf.rids.pop(key_index)

        self._rebalance_after_delete(leaf, path)

        if not self.root.is_leaf and len(self.root.children) == 1:
            self.root = self.root.children[0]

        return True

    def range_query(self, start_key: int, end_key: int) -> list[tuple[int, int]]:
        if start_key > end_key:
            return []

        results: list[tuple[int, int]] = []
        node = self._find_leaf(start_key)

        while node is not None:
            for key, rid in zip(node.keys, node.rids):
                if key < start_key:
                    continue
                if key > end_key:
                    return results
                results.append((key, rid))

            node = node.next_leaf

        return results

    def _find_leaf(
        self,
        key: int,
        path: list[tuple[BPlusTreeNode, int]] | None = None,
    ) -> BPlusTreeNode:
        node = self.root

        while not node.is_leaf:
            idx = 0
            while idx < len(node.keys) and key >= node.keys[idx]:
                idx += 1
            if path is not None:
                path.append((node, idx))
            node = node.children[idx]

        return node

    def _insert_non_full(self, node: BPlusTreeNode, key: int, rid: int) -> None:
        if node.is_leaf:
            index = 0
            while index < len(node.keys) and node.keys[index] < key:
                index += 1
            node.keys.insert(index, key)
            node.rids.insert(index, rid)
            return

        idx = 0
        while idx < len(node.keys) and key >= node.keys[idx]:
            idx += 1

        if self._is_full(node.children[idx]):
            self._split_child(node, idx)

            if key >= node.keys[idx]:
                idx += 1

        self._insert_non_full(node.children[idx], key, rid)

    def _split_child(self, parent: BPlusTreeNode, child_index: int) -> None:
        full_child = parent.children[child_index]
        new_child = BPlusTreeNode(is_leaf=full_child.is_leaf)

        if full_child.is_leaf:
            split_index = self.order
            new_child.keys = full_child.keys[split_index:]
            new_child.rids = full_child.rids[split_index:]
            full_child.keys = full_child.keys[:split_index]
            full_child.rids = full_child.rids[:split_index]

            new_child.next_leaf = full_child.next_leaf
            full_child.next_leaf = new_child

            promoted_key = new_child.keys[0]
            parent.keys.insert(child_index, promoted_key)
            parent.children.insert(child_index + 1, new_child)
            self.split_count += 1
            return

        middle_index = self.order - 1
        promoted_key = full_child.keys[middle_index]

        new_child.keys = full_child.keys[middle_index + 1 :]
        new_child.children = full_child.children[self.order :]
        full_child.keys = full_child.keys[:middle_index]
        full_child.children = full_child.children[: self.order]

        parent.keys.insert(child_index, promoted_key)
        parent.children.insert(child_index + 1, new_child)
        self.split_count += 1

    def _rebalance_after_delete(
        self,
        node: BPlusTreeNode,
        path: list[tuple[BPlusTreeNode, int]],
    ) -> None:
        node = node

        while True:
            if not node.is_leaf:
                self._sync_keys(node)

            if node is self.root:
                if not node.is_leaf and len(node.children) == 1:
                    self.root = node.children[0]
                elif not node.is_leaf:
                    self._sync_keys(node)
                return

            parent, idx = path.pop()
            min_keys = self.order - 1

            if len(node.keys) < min_keys:
                if idx > 0 and len(parent.children[idx - 1].keys) > min_keys:
                    self._borrow_from_left(parent, idx)
                elif idx + 1 < len(parent.children) and len(parent.children[idx + 1].keys) > min_keys:
                    self._borrow_from_right(parent, idx)
                elif idx > 0:
                    self._merge_children(parent, idx - 1)
                else:
                    self._merge_children(parent, idx)

            self._sync_keys(parent)
            node = parent

    def _borrow_from_left(self, parent: BPlusTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        if child.is_leaf:
            child.keys.insert(0, left_sibling.keys.pop())
            child.rids.insert(0, left_sibling.rids.pop())
        else:
            child.children.insert(0, left_sibling.children.pop())
            self._sync_keys(left_sibling)
            self._sync_keys(child)

        self._sync_keys(parent)

    def _borrow_from_right(self, parent: BPlusTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        if child.is_leaf:
            child.keys.append(right_sibling.keys.pop(0))
            child.rids.append(right_sibling.rids.pop(0))
        else:
            child.children.append(right_sibling.children.pop(0))
            self._sync_keys(right_sibling)
            self._sync_keys(child)

        self._sync_keys(parent)

    def _merge_children(self, parent: BPlusTreeNode, child_index: int) -> None:
        left_child = parent.children[child_index]
        right_child = parent.children[child_index + 1]

        if left_child.is_leaf:
            left_child.keys.extend(right_child.keys)
            left_child.rids.extend(right_child.rids)
            left_child.next_leaf = right_child.next_leaf
        else:
            left_child.children.extend(right_child.children)
            self._sync_keys(left_child)

        parent.children.pop(child_index + 1)
        self._sync_keys(parent)

    def _sync_keys(self, node: BPlusTreeNode) -> None:
        if node.is_leaf:
            return

        node.keys = [self._first_key(child) for child in node.children[1:]]

    def _first_key(self, node: BPlusTreeNode) -> int:
        node = node

        while not node.is_leaf:
            node = node.children[0]

        return node.keys[0]

    def _is_full(self, node: BPlusTreeNode) -> bool:
        return len(node.keys) == (2 * self.order) - 1
