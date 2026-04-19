import argparse
import random
from pathlib import Path

from bplustree import BPlusTree
from bstar_tree import BStarTree
from btree import BTree
from record_store import RecordStore


def build_trees(store: RecordStore, order: int) -> tuple[BTree, BPlusTree, BStarTree]:
    btree = BTree(order=order)
    bplus_tree = BPlusTree(order=order)
    bstar_tree = BStarTree(order=order)

    for rid, record in enumerate(store.records):
        key = record.student_id
        btree.insert(key, rid)
        bplus_tree.insert(key, rid)
        bstar_tree.insert(key, rid)

    return btree, bplus_tree, bstar_tree


def validate_point_searches(
    store: RecordStore,
    btree: BTree,
    bplus_tree: BPlusTree,
    bstar_tree: BStarTree,
    sample_size: int,
    seed: int,
) -> None:
    random.seed(seed)
    sample_rids = random.sample(range(len(store)), sample_size)

    for rid in sample_rids:
        key = store.get_by_rid(rid).student_id
        if btree.search(key) != rid:
            raise AssertionError(("btree_search_failed", key, rid, btree.search(key)))
        if bplus_tree.search(key) != rid:
            raise AssertionError(("bplus_search_failed", key, rid, bplus_tree.search(key)))
        if bstar_tree.search(key) != rid:
            raise AssertionError(("bstar_search_failed", key, rid, bstar_tree.search(key)))


def validate_bplus_range_query(
    store: RecordStore,
    bplus_tree: BPlusTree,
    range_sample_size: int,
    seed: int,
) -> None:
    random.seed(seed + 1)
    sample_rids = sorted(random.sample(range(len(store)), range_sample_size))
    sample_keys = sorted(store.get_by_rid(rid).student_id for rid in sample_rids)

    start_key = sample_keys[0]
    end_key = sample_keys[-1]
    expected = sorted(
        (record.student_id, rid)
        for rid, record in enumerate(store.records)
        if start_key <= record.student_id <= end_key
    )
    actual = bplus_tree.range_query(start_key, end_key)

    if actual != expected:
        raise AssertionError(("bplus_range_failed", start_key, end_key, len(expected), len(actual)))


def validate_sample_deletes(
    store: RecordStore,
    btree: BTree,
    bplus_tree: BPlusTree,
    bstar_tree: BStarTree,
    delete_sample_size: int,
    seed: int,
) -> None:
    random.seed(seed + 2)
    sample_rids = random.sample(range(len(store)), delete_sample_size)

    for rid in sample_rids:
        key = store.get_by_rid(rid).student_id

        if not btree.delete(key):
            raise AssertionError(("btree_delete_failed", key, rid))
        if btree.search(key) is not None:
            raise AssertionError(("btree_delete_visible", key, rid))

        if not bplus_tree.delete(key):
            raise AssertionError(("bplus_delete_failed", key, rid))
        if bplus_tree.search(key) is not None:
            raise AssertionError(("bplus_delete_visible", key, rid))

        if not bstar_tree.delete(key):
            raise AssertionError(("bstar_delete_failed", key, rid))
        if bstar_tree.search(key) is not None:
            raise AssertionError(("bstar_delete_visible", key, rid))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate all three trees on the full student dataset.")
    parser.add_argument("--order", type=int, default=3, help="Tree order d. Default: 3")
    parser.add_argument(
        "--search-sample-size",
        type=int,
        default=200,
        help="Number of random keys to verify with point searches. Default: 200",
    )
    parser.add_argument(
        "--range-sample-size",
        type=int,
        default=20,
        help="Number of random keys used to derive a B+ tree range query. Default: 20",
    )
    parser.add_argument(
        "--delete-sample-size",
        type=int,
        default=50,
        help="Number of random keys to delete from each tree. Default: 50",
    )
    parser.add_argument("--seed", type=int, default=321, help="Random seed. Default: 321")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "student.csv"
    store = RecordStore.from_csv(csv_path)

    print(f"Loaded records: {len(store)}")
    print(f"Building trees with order d={args.order}...")
    btree, bplus_tree, bstar_tree = build_trees(store, args.order)

    print("Validating point searches...")
    validate_point_searches(
        store,
        btree,
        bplus_tree,
        bstar_tree,
        sample_size=args.search_sample_size,
        seed=args.seed,
    )

    print("Validating B+ tree range query...")
    validate_bplus_range_query(
        store,
        bplus_tree,
        range_sample_size=args.range_sample_size,
        seed=args.seed,
    )

    print("Validating sample deletes...")
    validate_sample_deletes(
        store,
        btree,
        bplus_tree,
        bstar_tree,
        delete_sample_size=args.delete_sample_size,
        seed=args.seed,
    )

    print("Full dataset check passed.")
    print(f"B-tree splits: {btree.split_count}")
    print(f"B+ tree splits: {bplus_tree.split_count}")
    print(f"B* tree redistributions: {bstar_tree.redistribution_count}")
    print(f"B* tree 2-to-3 splits: {bstar_tree.two_to_three_split_count}")


if __name__ == "__main__":
    main()
