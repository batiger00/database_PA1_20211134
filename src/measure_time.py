import argparse
import random
from pathlib import Path
from time import perf_counter

from bplustree import BPlusTree
from bstar_tree import BStarTree
from btree import BTree
from record_store import RecordStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure tree operation times.")
    parser.add_argument("--orders", type=int, nargs="+", default=[3, 5, 10])
    parser.add_argument("--search-count", type=int, default=10000)
    parser.add_argument("--delete-count", type=int, default=2000)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--seed", type=int, default=321)
    return parser.parse_args()


def build_btree(records: list, order: int) -> tuple[BTree, float]:
    tree = BTree(order)
    start = perf_counter()
    for rid, record in enumerate(records):
        tree.insert(record.student_id, rid)
    return tree, perf_counter() - start


def build_bplus(records: list, order: int) -> tuple[BPlusTree, float]:
    tree = BPlusTree(order)
    start = perf_counter()
    for rid, record in enumerate(records):
        tree.insert(record.student_id, rid)
    return tree, perf_counter() - start


def build_bstar(records: list, order: int) -> tuple[BStarTree, float]:
    tree = BStarTree(order)
    start = perf_counter()
    for rid, record in enumerate(records):
        tree.insert(record.student_id, rid)
    return tree, perf_counter() - start


def mean_search_time(tree, keys: list[int]) -> float:
    start = perf_counter()
    for key in keys:
        tree.search(key)
    elapsed = perf_counter() - start
    return elapsed / len(keys)


def delete_time(tree, keys: list[int]) -> float:
    start = perf_counter()
    for key in keys:
        tree.delete(key)
    return perf_counter() - start


def range_time_btree(tree: BTree, store: RecordStore, lo: int, hi: int) -> float:
    start = perf_counter()
    total_height = 0.0
    total_weight = 0.0
    matched = 0
    for key in range(lo, hi + 1):
        rid = tree.search(key)
        if rid is None:
            continue
        record = store.get_by_rid(rid)
        if record.gender != "Female" or record.gpa < 3.5:
            continue
        total_height += record.height
        total_weight += record.weight
        matched += 1
    elapsed = perf_counter() - start
    return elapsed


def range_time_bplus(tree: BPlusTree, store: RecordStore, lo: int, hi: int) -> float:
    start = perf_counter()
    total_height = 0.0
    total_weight = 0.0
    matched = 0
    for _, rid in tree.range_query(lo, hi):
        record = store.get_by_rid(rid)
        if record.gender != "Female" or record.gpa < 3.5:
            continue
        total_height += record.height
        total_weight += record.weight
        matched += 1
    elapsed = perf_counter() - start
    return elapsed


def range_time_bstar(tree: BStarTree, store: RecordStore, lo: int, hi: int) -> float:
    start = perf_counter()
    total_height = 0.0
    total_weight = 0.0
    matched = 0
    for key in range(lo, hi + 1):
        rid = tree.search(key)
        if rid is None:
            continue
        record = store.get_by_rid(rid)
        if record.gender != "Female" or record.gpa < 3.5:
            continue
        total_height += record.height
        total_weight += record.weight
        matched += 1
    elapsed = perf_counter() - start
    return elapsed


def utilization_btree(node) -> tuple[int, int]:
    used = len(node.keys)
    count = 1
    for child in node.children:
        child_used, child_count = utilization_btree(child)
        used += child_used
        count += child_count
    return used, count


def utilization_bplus(node) -> tuple[int, int]:
    used = len(node.keys)
    count = 1
    for child in node.children:
        child_used, child_count = utilization_bplus(child)
        used += child_used
        count += child_count
    return used, count


def utilization_bstar(node) -> tuple[int, int]:
    used = len(node.keys)
    count = 1
    for child in node.children:
        child_used, child_count = utilization_bstar(child)
        used += child_used
        count += child_count
    return used, count


def node_utilization(tree, kind: str, order: int) -> float:
    max_keys = (2 * order) - 1
    if kind == "btree":
        used, count = utilization_btree(tree.root)
    elif kind == "bplus":
        used, count = utilization_bplus(tree.root)
    else:
        used, count = utilization_bstar(tree.root)
    return used / (count * max_keys)


def print_row(values: list[str]) -> None:
    print(" | ".join(values))


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    store = RecordStore.from_csv(project_root / "student.csv")
    records = store.records

    random.seed(args.seed)
    search_rids = random.sample(range(len(store)), args.search_count)
    search_keys = [records[rid].student_id for rid in search_rids]

    delete_rids = random.sample(range(len(store)), args.delete_count)
    delete_keys = [records[rid].student_id for rid in delete_rids]

    range_ids = sorted(random.sample(range(len(store)), 200))
    lo = records[range_ids[20]].student_id
    hi = records[range_ids[180]].student_id
    if lo > hi:
        lo, hi = hi, lo

    print_row(
        [
            "tree",
            "d",
            "insert_avg_s",
            "search_avg_us",
            "range_avg_s",
            "delete_avg_s",
            "utilization",
            "splits",
            "extra",
        ]
    )

    for order in args.orders:
        btree_insert = []
        btree_search = []
        btree_range = []
        btree_delete = []
        util = 0.0
        splits = 0

        for _ in range(args.trials):
            btree, insert_s = build_btree(records, order)
            btree_insert.append(insert_s)
            btree_search.append(mean_search_time(btree, search_keys) * 1_000_000)
            btree_range.append(range_time_btree(btree, store, lo, hi))
            btree_delete.append(delete_time(btree, delete_keys))
            util = node_utilization(btree, "btree", order)
            splits = btree.split_count

        print_row(
            [
                "B-tree",
                str(order),
                f"{mean(btree_insert):.4f}",
                f"{mean(btree_search):.2f}",
                f"{mean(btree_range):.4f}",
                f"{mean(btree_delete):.4f}",
                f"{util:.4f}",
                str(splits),
                "-",
            ]
        )

        bplus_insert = []
        bplus_search = []
        bplus_range = []
        bplus_delete = []
        util = 0.0
        splits = 0

        for _ in range(args.trials):
            bplus, insert_s = build_bplus(records, order)
            bplus_insert.append(insert_s)
            bplus_search.append(mean_search_time(bplus, search_keys) * 1_000_000)
            bplus_range.append(range_time_bplus(bplus, store, lo, hi))
            bplus_delete.append(delete_time(bplus, delete_keys))
            util = node_utilization(bplus, "bplus", order)
            splits = bplus.split_count

        print_row(
            [
                "B+ tree",
                str(order),
                f"{mean(bplus_insert):.4f}",
                f"{mean(bplus_search):.2f}",
                f"{mean(bplus_range):.4f}",
                f"{mean(bplus_delete):.4f}",
                f"{util:.4f}",
                str(splits),
                "-",
            ]
        )

        bstar_insert = []
        bstar_search = []
        bstar_range = []
        bstar_delete = []
        util = 0.0
        splits = 0
        redist = 0
        two_to_three = 0

        for _ in range(args.trials):
            bstar, insert_s = build_bstar(records, order)
            bstar_insert.append(insert_s)
            bstar_search.append(mean_search_time(bstar, search_keys) * 1_000_000)
            bstar_range.append(range_time_bstar(bstar, store, lo, hi))
            bstar_delete.append(delete_time(bstar, delete_keys))
            util = node_utilization(bstar, "bstar", order)
            splits = bstar.split_count
            redist = bstar.redistribution_count
            two_to_three = bstar.two_to_three_split_count

        extra = f"redist={redist},2to3={two_to_three}"
        print_row(
            [
                "B* tree",
                str(order),
                f"{mean(bstar_insert):.4f}",
                f"{mean(bstar_search):.2f}",
                f"{mean(bstar_range):.4f}",
                f"{mean(bstar_delete):.4f}",
                f"{util:.4f}",
                str(splits),
                extra,
            ]
        )


if __name__ == "__main__":
    main()
