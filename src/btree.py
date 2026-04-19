from dataclasses import dataclass, field


@dataclass
class BTreeNode:
    is_leaf: bool = True
    keys: list[int] = field(default_factory=list)
    rids: list[int] = field(default_factory=list)
    children: list["BTreeNode"] = field(default_factory=list)


class BTree:
    # Assume d is the minimum degree.
    def __init__(self, order: int):
        if order < 2:
            raise ValueError("B-tree order must be at least 2.")

        self.order = order
        self.root = BTreeNode()
        self.split_count = 0

    def search(self, key: int, node: BTreeNode | None = None) -> int | None:
        current = node or self.root
        index = 0

        while index < len(current.keys) and key > current.keys[index]:
            index += 1

        if index < len(current.keys) and key == current.keys[index]:
            return current.rids[index]

        if current.is_leaf:
            return None

        return self.search(key, current.children[index])

    def insert(self, key: int, rid: int) -> None:
        if self.search(key) is not None:
            raise ValueError(f"Duplicate key insertion is not allowed: {key}")

        root = self.root

        if self._is_full(root):
            new_root = BTreeNode(is_leaf=False, children=[root])
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, rid)

    def delete(self, key: int) -> bool:
        if self.search(key) is None:
            return False

        self._delete(self.root, key)

        if not self.root.keys and not self.root.is_leaf:
            self.root = self.root.children[0]

        return True

    def _insert_non_full(self, node: BTreeNode, key: int, rid: int) -> None:
        index = len(node.keys) - 1

        if node.is_leaf:
            node.keys.append(0)
            node.rids.append(0)

            while index >= 0 and key < node.keys[index]:
                node.keys[index + 1] = node.keys[index]
                node.rids[index + 1] = node.rids[index]
                index -= 1

            node.keys[index + 1] = key
            node.rids[index + 1] = rid
            return

        while index >= 0 and key < node.keys[index]:
            index -= 1

        child_index = index + 1

        if self._is_full(node.children[child_index]):
            self._split_child(node, child_index)

            if key > node.keys[child_index]:
                child_index += 1

        self._insert_non_full(node.children[child_index], key, rid)

    def _split_child(self, parent: BTreeNode, child_index: int) -> None:
        full_child = parent.children[child_index]
        new_child = BTreeNode(is_leaf=full_child.is_leaf)
        middle_index = self.order - 1

        promoted_key = full_child.keys[middle_index]
        promoted_rid = full_child.rids[middle_index]

        new_child.keys = full_child.keys[middle_index + 1 :]
        new_child.rids = full_child.rids[middle_index + 1 :]
        full_child.keys = full_child.keys[:middle_index]
        full_child.rids = full_child.rids[:middle_index]

        if not full_child.is_leaf:
            new_child.children = full_child.children[self.order :]
            full_child.children = full_child.children[: self.order]

        parent.keys.insert(child_index, promoted_key)
        parent.rids.insert(child_index, promoted_rid)
        parent.children.insert(child_index + 1, new_child)
        self.split_count += 1

    def _delete(self, node: BTreeNode, key: int) -> None:
        index = self._find_key(node, key)

        if index < len(node.keys) and node.keys[index] == key:
            if node.is_leaf:
                node.keys.pop(index)
                node.rids.pop(index)
                return

            self._delete_from_internal_node(node, index)
            return

        if node.is_leaf:
            return

        child_index = index
        child_is_last = child_index == len(node.children) - 1

        if len(node.children[child_index].keys) < self.order:
            self._fill(node, child_index)

        if child_is_last and child_index >= len(node.children):
            child_index -= 1

        self._delete(node.children[child_index], key)

    def _delete_from_internal_node(self, node: BTreeNode, index: int) -> None:
        key = node.keys[index]
        left_child = node.children[index]
        right_child = node.children[index + 1]

        if len(left_child.keys) >= self.order:
            predecessor_key, predecessor_rid = self._get_predecessor(left_child)
            node.keys[index] = predecessor_key
            node.rids[index] = predecessor_rid
            self._delete(left_child, predecessor_key)
            return

        if len(right_child.keys) >= self.order:
            successor_key, successor_rid = self._get_successor(right_child)
            node.keys[index] = successor_key
            node.rids[index] = successor_rid
            self._delete(right_child, successor_key)
            return

        self._merge(node, index)
        self._delete(node.children[index], key)

    def _get_predecessor(self, node: BTreeNode) -> tuple[int, int]:
        current = node

        while not current.is_leaf:
            current = current.children[-1]

        return current.keys[-1], current.rids[-1]

    def _get_successor(self, node: BTreeNode) -> tuple[int, int]:
        current = node

        while not current.is_leaf:
            current = current.children[0]

        return current.keys[0], current.rids[0]

    def _fill(self, parent: BTreeNode, child_index: int) -> None:
        if child_index > 0 and len(parent.children[child_index - 1].keys) >= self.order:
            self._borrow_from_previous(parent, child_index)
            return

        if (
            child_index < len(parent.children) - 1
            and len(parent.children[child_index + 1].keys) >= self.order
        ):
            self._borrow_from_next(parent, child_index)
            return

        if child_index < len(parent.children) - 1:
            self._merge(parent, child_index)
        else:
            self._merge(parent, child_index - 1)

    def _borrow_from_previous(self, parent: BTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.rids.insert(0, parent.rids[child_index - 1])

        if not child.is_leaf:
            child.children.insert(0, left_sibling.children.pop())

        parent.keys[child_index - 1] = left_sibling.keys.pop()
        parent.rids[child_index - 1] = left_sibling.rids.pop()

    def _borrow_from_next(self, parent: BTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.rids.append(parent.rids[child_index])

        if not child.is_leaf:
            child.children.append(right_sibling.children.pop(0))

        parent.keys[child_index] = right_sibling.keys.pop(0)
        parent.rids[child_index] = right_sibling.rids.pop(0)

    def _merge(self, parent: BTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys.pop(child_index))
        child.rids.append(parent.rids.pop(child_index))
        child.keys.extend(right_sibling.keys)
        child.rids.extend(right_sibling.rids)

        if not child.is_leaf:
            child.children.extend(right_sibling.children)

        parent.children.pop(child_index + 1)

    def _find_key(self, node: BTreeNode, key: int) -> int:
        index = 0

        while index < len(node.keys) and node.keys[index] < key:
            index += 1

        return index

    def _is_full(self, node: BTreeNode) -> bool:
        return len(node.keys) == (2 * self.order) - 1
