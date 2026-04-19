from dataclasses import dataclass, field


@dataclass
class BStarTreeNode:
    is_leaf: bool = True
    keys: list[int] = field(default_factory=list)
    rids: list[int] = field(default_factory=list)
    children: list["BStarTreeNode"] = field(default_factory=list)


class BStarTree:
    # Assume d is the minimum degree.
    def __init__(self, order: int):
        if order < 3:
            raise ValueError("B* tree order must be at least 3.")

        self.order = order
        self.root = BStarTreeNode()
        self.split_count = 0
        self.redistribution_count = 0
        self.two_to_three_split_count = 0

    def search(self, key: int, node: BStarTreeNode | None = None) -> int | None:
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

        if self._is_full(self.root):
            new_root = BStarTreeNode(is_leaf=False, children=[self.root])
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

    def _insert_non_full(self, node: BStarTreeNode, key: int, rid: int) -> None:
        if node.is_leaf:
            self._insert_into_leaf(node, key, rid)
            return

        child_index = self._find_child_index(node, key)
        child = node.children[child_index]

        if self._is_full(child):
            if child.is_leaf:
                if (
                    child_index < len(node.children) - 1
                    and not self._is_full(node.children[child_index + 1])
                ):
                    self._redistribute_leaf_pair_with_insert(node, child_index, key, rid)
                    return

                if child_index > 0 and not self._is_full(node.children[child_index - 1]):
                    self._redistribute_leaf_pair_with_insert(node, child_index - 1, key, rid)
                    return

            self._prepare_child_for_insert(node, child_index)
            child_index = self._find_child_index(node, key)

        self._insert_non_full(node.children[child_index], key, rid)

    def _prepare_child_for_insert(self, parent: BStarTreeNode, child_index: int) -> None:
        child = parent.children[child_index]

        if not child.is_leaf:
            self._split_child(parent, child_index)
            return

        if child_index < len(parent.children) - 1 and not self._is_full(parent.children[child_index + 1]):
            self._redistribute_to_right(parent, child_index)
            return

        if child_index > 0 and not self._is_full(parent.children[child_index - 1]):
            self._redistribute_to_left(parent, child_index)
            return

        if child_index < len(parent.children) - 1:
            self._split_two_children_into_three(parent, child_index)
            return

        if child_index > 0:
            self._split_two_children_into_three(parent, child_index - 1)
            return

        self._split_child(parent, child_index)

    def _insert_into_leaf(self, node: BStarTreeNode, key: int, rid: int) -> None:
        index = 0
        while index < len(node.keys) and node.keys[index] < key:
            index += 1
        node.keys.insert(index, key)
        node.rids.insert(index, rid)

    def _split_child(self, parent: BStarTreeNode, child_index: int) -> None:
        full_child = parent.children[child_index]
        new_child = BStarTreeNode(is_leaf=full_child.is_leaf)
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

    def _redistribute_to_right(self, parent: BStarTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        right_sibling.keys.insert(0, parent.keys[child_index])
        right_sibling.rids.insert(0, parent.rids[child_index])
        parent.keys[child_index] = child.keys.pop()
        parent.rids[child_index] = child.rids.pop()

        if not child.is_leaf:
            right_sibling.children.insert(0, child.children.pop())

        self.redistribution_count += 1

    def _redistribute_to_left(self, parent: BStarTreeNode, child_index: int) -> None:
        left_sibling = parent.children[child_index - 1]
        child = parent.children[child_index]

        left_sibling.keys.append(parent.keys[child_index - 1])
        left_sibling.rids.append(parent.rids[child_index - 1])
        parent.keys[child_index - 1] = child.keys.pop(0)
        parent.rids[child_index - 1] = child.rids.pop(0)

        if not child.is_leaf:
            left_sibling.children.append(child.children.pop(0))

        self.redistribution_count += 1

    def _redistribute_leaf_pair_with_insert(
        self,
        parent: BStarTreeNode,
        left_index: int,
        key: int,
        rid: int,
    ) -> None:
        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]

        combined = list(
            zip(
                left_child.keys + [parent.keys[left_index]] + right_child.keys + [key],
                left_child.rids + [parent.rids[left_index]] + right_child.rids + [rid],
                strict=True,
            )
        )
        combined.sort(key=lambda item: item[0])

        parent_index = len(combined) // 2
        left_items = combined[:parent_index]
        parent_item = combined[parent_index]
        right_items = combined[parent_index + 1 :]

        left_child.keys = [current_key for current_key, _ in left_items]
        left_child.rids = [current_rid for _, current_rid in left_items]
        parent.keys[left_index] = parent_item[0]
        parent.rids[left_index] = parent_item[1]
        right_child.keys = [current_key for current_key, _ in right_items]
        right_child.rids = [current_rid for _, current_rid in right_items]

        self.redistribution_count += 1

    def _split_two_children_into_three(self, parent: BStarTreeNode, left_index: int) -> None:
        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]
        new_child = BStarTreeNode(is_leaf=left_child.is_leaf)

        combined_keys = left_child.keys + [parent.keys[left_index]] + right_child.keys
        combined_rids = left_child.rids + [parent.rids[left_index]] + right_child.rids

        remaining_key_count = len(combined_keys) - 2
        base_size = remaining_key_count // 3
        remainder = remaining_key_count % 3
        left_size = base_size + (1 if remainder > 0 else 0)
        middle_size = base_size + (1 if remainder > 1 else 0)
        right_size = remaining_key_count - left_size - middle_size

        first_parent_index = left_size
        second_parent_index = left_size + 1 + middle_size

        promoted_key_1 = combined_keys[first_parent_index]
        promoted_rid_1 = combined_rids[first_parent_index]
        promoted_key_2 = combined_keys[second_parent_index]
        promoted_rid_2 = combined_rids[second_parent_index]

        middle_child_keys = combined_keys[first_parent_index + 1 : second_parent_index]
        middle_child_rids = combined_rids[first_parent_index + 1 : second_parent_index]
        right_child_keys = combined_keys[second_parent_index + 1 :]
        right_child_rids = combined_rids[second_parent_index + 1 :]

        left_child.keys = combined_keys[:left_size]
        left_child.rids = combined_rids[:left_size]
        new_child.keys = middle_child_keys
        new_child.rids = middle_child_rids
        right_child.keys = right_child_keys
        right_child.rids = right_child_rids

        if not left_child.is_leaf:
            combined_children = left_child.children + right_child.children
            left_child.children = combined_children[: left_size + 1]
            new_child.children = combined_children[left_size + 1 : left_size + middle_size + 2]
            right_child.children = combined_children[left_size + middle_size + 2 :]

        parent.keys[left_index] = promoted_key_1
        parent.rids[left_index] = promoted_rid_1
        parent.keys.insert(left_index + 1, promoted_key_2)
        parent.rids.insert(left_index + 1, promoted_rid_2)
        parent.children.insert(left_index + 1, new_child)

        self.two_to_three_split_count += 1

    def _delete(self, node: BStarTreeNode, key: int) -> None:
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

    def _delete_from_internal_node(self, node: BStarTreeNode, index: int) -> None:
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

    def _get_predecessor(self, node: BStarTreeNode) -> tuple[int, int]:
        current = node

        while not current.is_leaf:
            current = current.children[-1]

        return current.keys[-1], current.rids[-1]

    def _get_successor(self, node: BStarTreeNode) -> tuple[int, int]:
        current = node

        while not current.is_leaf:
            current = current.children[0]

        return current.keys[0], current.rids[0]

    def _fill(self, parent: BStarTreeNode, child_index: int) -> None:
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

    def _borrow_from_previous(self, parent: BStarTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.rids.insert(0, parent.rids[child_index - 1])

        if not child.is_leaf:
            child.children.insert(0, left_sibling.children.pop())

        parent.keys[child_index - 1] = left_sibling.keys.pop()
        parent.rids[child_index - 1] = left_sibling.rids.pop()

    def _borrow_from_next(self, parent: BStarTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.rids.append(parent.rids[child_index])

        if not child.is_leaf:
            child.children.append(right_sibling.children.pop(0))

        parent.keys[child_index] = right_sibling.keys.pop(0)
        parent.rids[child_index] = right_sibling.rids.pop(0)

    def _merge(self, parent: BStarTreeNode, child_index: int) -> None:
        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys.pop(child_index))
        child.rids.append(parent.rids.pop(child_index))
        child.keys.extend(right_sibling.keys)
        child.rids.extend(right_sibling.rids)

        if not child.is_leaf:
            child.children.extend(right_sibling.children)

        parent.children.pop(child_index + 1)

    def _find_key(self, node: BStarTreeNode, key: int) -> int:
        index = 0

        while index < len(node.keys) and node.keys[index] < key:
            index += 1

        return index

    def _find_child_index(self, node: BStarTreeNode, key: int) -> int:
        index = 0

        while index < len(node.keys) and key > node.keys[index]:
            index += 1

        return index

    def _is_full(self, node: BStarTreeNode) -> bool:
        return len(node.keys) == (2 * self.order) - 1
