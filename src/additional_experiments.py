import argparse
import csv
import random
from pathlib import Path
from time import perf_counter

from bplustree import BPlusTree, BPlusTreeNode
from bstar_tree import BStarTree, BStarTreeNode
from btree import BTree, BTreeNode
from record_store import RecordStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run additional PA1 experiments.")
    parser.add_argument("--orders", type=int, nargs="+", default=[3, 5, 10])
    parser.add_argument("--range-order", type=int, default=10)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--range-trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=321)
    parser.add_argument(
        "--selectivities",
        type=float,
        nargs="+",
        default=[0.001, 0.01, 0.05, 0.10, 0.50],
        help="Fractions of the full dataset used for range query widths.",
    )
    parser.add_argument("--output-dir", type=str, default="results")
    return parser.parse_args()


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def tree_height(root) -> int:
    height = 0
    node = root
    while not node.is_leaf:
        height += 1
        node = node.children[0]
    return height


def utilization(node) -> tuple[int, int]:
    used = len(node.keys)
    count = 1
    for child in node.children:
        child_used, child_count = utilization(child)
        used += child_used
        count += child_count
    return used, count


def node_utilization(tree, order: int) -> float:
    used, count = utilization(tree.root)
    return used / (count * ((2 * order) - 1))


def insertion_workloads(store: RecordStore, seed: int) -> dict[str, list[tuple[int, object]]]:
    items = list(enumerate(store.records))
    rng = random.Random(seed)
    random_items = items[:]
    rng.shuffle(random_items)
    ascending_items = sorted(items, key=lambda item: item[1].student_id)
    descending_items = list(reversed(ascending_items))

    return {
        "random": random_items,
        "ascending": ascending_items,
        "descending": descending_items,
    }


def build_tree(kind: str, order: int):
    if kind == "B-tree":
        return BTree(order)
    if kind == "B+ tree":
        return BPlusTree(order)
    return BStarTree(order)


def build_from_items(kind: str, order: int, items: list[tuple[int, object]]) -> tuple[object, float]:
    tree = build_tree(kind, order)
    start = perf_counter()
    for rid, record in items:
        tree.insert(record.student_id, rid)
    return tree, perf_counter() - start


def run_insertion_order_experiment(
    store: RecordStore,
    orders: list[int],
    trials: int,
    seed: int,
) -> list[dict]:
    workloads = insertion_workloads(store, seed)
    rows = []

    print("\nAdditional Experiment 1: Insertion order sensitivity")
    print("----------------------------------------------------")
    for order in orders:
        for order_name, items in workloads.items():
            for kind in ("B-tree", "B+ tree", "B* tree"):
                print(f"Running {kind}, d={order}, order={order_name}...", flush=True)
                insert_times = []
                tree = None
                for _ in range(trials):
                    tree, elapsed = build_from_items(kind, order, items)
                    insert_times.append(elapsed)

                assert tree is not None
                rows.append(
                    {
                        "tree": kind,
                        "d": order,
                        "insertion_order": order_name,
                        "insert_avg_s": mean(insert_times),
                        "height": tree_height(tree.root),
                        "utilization": node_utilization(tree, order),
                        "splits": tree.split_count,
                        "redistributions": getattr(tree, "redistribution_count", 0),
                        "two_to_three_splits": getattr(tree, "two_to_three_split_count", 0),
                    }
                )

    return rows


def analytical_update(store: RecordStore, rid: int, stats: dict) -> None:
    record = store.get_by_rid(rid)
    stats["range_record_count"] += 1
    if record.gender != "Female" or record.gpa < 3.5:
        return
    stats["matched_record_count"] += 1
    stats["total_height"] += record.height
    stats["total_weight"] += record.weight


def finalize_stats(stats: dict) -> dict:
    matched = stats["matched_record_count"]
    avg_height = stats["total_height"] / matched if matched else 0.0
    avg_weight = stats["total_weight"] / matched if matched else 0.0
    return {
        "range_record_count": stats["range_record_count"],
        "matched_record_count": matched,
        "avg_height": avg_height,
        "avg_weight": avg_weight,
        "visited_internal_nodes": stats["visited_internal_nodes"],
        "visited_leaf_nodes": stats["visited_leaf_nodes"],
    }


def search_btree_like_with_stats(node, key: int, stats: dict) -> int | None:
    if node.is_leaf:
        stats["visited_leaf_nodes"] += 1
    else:
        stats["visited_internal_nodes"] += 1

    index = 0
    while index < len(node.keys) and key > node.keys[index]:
        index += 1

    if index < len(node.keys) and key == node.keys[index]:
        return node.rids[index]

    if node.is_leaf:
        return None

    return search_btree_like_with_stats(node.children[index], key, stats)


def measure_range_btree_like(tree, store: RecordStore, lo: int, hi: int) -> tuple[float, dict]:
    stats = {
        "range_record_count": 0,
        "matched_record_count": 0,
        "total_height": 0.0,
        "total_weight": 0.0,
        "visited_internal_nodes": 0,
        "visited_leaf_nodes": 0,
    }
    start = perf_counter()
    for key in range(lo, hi + 1):
        rid = search_btree_like_with_stats(tree.root, key, stats)
        if rid is not None:
            analytical_update(store, rid, stats)
    elapsed = perf_counter() - start
    return elapsed, finalize_stats(stats)


def find_bplus_start_leaf(tree: BPlusTree, key: int, stats: dict) -> BPlusTreeNode:
    node = tree.root
    while not node.is_leaf:
        stats["visited_internal_nodes"] += 1
        index = 0
        while index < len(node.keys) and key >= node.keys[index]:
            index += 1
        node = node.children[index]
    return node


def measure_range_bplus(tree: BPlusTree, store: RecordStore, lo: int, hi: int) -> tuple[float, dict]:
    stats = {
        "range_record_count": 0,
        "matched_record_count": 0,
        "total_height": 0.0,
        "total_weight": 0.0,
        "visited_internal_nodes": 0,
        "visited_leaf_nodes": 0,
    }
    start = perf_counter()
    node = find_bplus_start_leaf(tree, lo, stats)

    while node is not None:
        stats["visited_leaf_nodes"] += 1
        for key, rid in zip(node.keys, node.rids):
            if key < lo:
                continue
            if key > hi:
                elapsed = perf_counter() - start
                return elapsed, finalize_stats(stats)
            analytical_update(store, rid, stats)
        node = node.next_leaf

    elapsed = perf_counter() - start
    return elapsed, finalize_stats(stats)


def selectivity_ranges(store: RecordStore, selectivities: list[float]) -> list[tuple[float, int, int, int]]:
    sorted_keys = sorted(record.student_id for record in store.records)
    count = len(sorted_keys)
    ranges = []

    for selectivity in selectivities:
        width = max(1, min(count, round(count * selectivity)))
        start_index = max(0, (count - width) // 2)
        end_index = start_index + width - 1
        ranges.append((selectivity, sorted_keys[start_index], sorted_keys[end_index], width))

    return ranges


def run_range_selectivity_experiment(
    store: RecordStore,
    order: int,
    selectivities: list[float],
    trials: int,
) -> list[dict]:
    print("\nAdditional Experiment 2: Range query selectivity")
    print("------------------------------------------------")
    print(f"Building trees once with d={order}...", flush=True)

    items = list(enumerate(store.records))
    btree, _ = build_from_items("B-tree", order, items)
    bplus_tree, _ = build_from_items("B+ tree", order, items)
    bstar_tree, _ = build_from_items("B* tree", order, items)
    trees = {
        "B-tree": btree,
        "B+ tree": bplus_tree,
        "B* tree": bstar_tree,
    }

    rows = []
    for selectivity, lo, hi, expected_width in selectivity_ranges(store, selectivities):
        for kind, tree in trees.items():
            print(f"Running {kind}, selectivity={selectivity:.1%}...", flush=True)
            elapsed_values = []
            stats = None
            for _ in range(trials):
                if kind == "B+ tree":
                    elapsed, stats = measure_range_bplus(tree, store, lo, hi)
                else:
                    elapsed, stats = measure_range_btree_like(tree, store, lo, hi)
                elapsed_values.append(elapsed)

            assert stats is not None
            rows.append(
                {
                    "tree": kind,
                    "d": order,
                    "selectivity": selectivity,
                    "expected_key_count": expected_width,
                    "lo": lo,
                    "hi": hi,
                    "range_avg_s": mean(elapsed_values),
                    **stats,
                }
            )

    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_insertion_rows(rows: list[dict]) -> None:
    print("\nInsertion order results")
    print("-----------------------")
    print("tree     | d  | order      | insert(s) | height | utilization | splits | redist | 2-to-3")
    print("---------|----|------------|-----------|--------|-------------|--------|--------|-------")
    for row in rows:
        print(
            f"{row['tree']:<8} | {row['d']:>2} | {row['insertion_order']:<10} | "
            f"{row['insert_avg_s']:.4f} | {row['height']:>6} | {row['utilization']:.4f} | "
            f"{row['splits']:>6} | {row['redistributions']:>6} | {row['two_to_three_splits']:>6}"
        )


def print_range_rows(rows: list[dict]) -> None:
    print("\nRange selectivity results")
    print("-------------------------")
    print("tree     | d  | sel    | keys  | range(s) | internal | leaf  | matched | avg_h | avg_w")
    print("---------|----|--------|-------|----------|----------|-------|---------|-------|------")
    for row in rows:
        print(
            f"{row['tree']:<8} | {row['d']:>2} | {row['selectivity']:>5.1%} | "
            f"{row['range_record_count']:>5} | {row['range_avg_s']:.5f} | "
            f"{row['visited_internal_nodes']:>8} | {row['visited_leaf_nodes']:>5} | "
            f"{row['matched_record_count']:>7} | {row['avg_height']:.2f} | {row['avg_weight']:.2f}"
        )


def print_highlights(insertion_rows: list[dict], range_rows: list[dict]) -> None:
    print("\nAdditional experiment highlights")
    print("--------------------------------")
    for order_name in ("random", "ascending", "descending"):
        subset = [row for row in insertion_rows if row["insertion_order"] == order_name]
        best_util = max(subset, key=lambda row: row["utilization"])
        fewest_splits = min(subset, key=lambda row: row["splits"])
        print(
            f"{order_name}: highest utilization = {best_util['tree']} d={best_util['d']} "
            f"({best_util['utilization']:.4f}), fewest splits = {fewest_splits['tree']} "
            f"d={fewest_splits['d']} ({fewest_splits['splits']})"
        )

    for selectivity in sorted({row["selectivity"] for row in range_rows}):
        subset = [row for row in range_rows if row["selectivity"] == selectivity]
        fastest = min(subset, key=lambda row: row["range_avg_s"])
        print(f"range {selectivity:.1%}: fastest = {fastest['tree']} ({fastest['range_avg_s']:.5f}s)")


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    store = RecordStore.from_csv(project_root / "student.csv")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Additional PA1 experiments")
    print("==========================")
    print(f"Records: {len(store)}")
    print(f"Insertion orders d: {', '.join(str(order) for order in args.orders)}")
    print(f"Insertion trials: {args.trials}")
    print(f"Range query d: {args.range_order}")
    print(f"Range trials: {args.range_trials}")
    print(f"Seed: {args.seed}")

    insertion_rows = run_insertion_order_experiment(store, args.orders, args.trials, args.seed)
    range_rows = run_range_selectivity_experiment(
        store,
        args.range_order,
        args.selectivities,
        args.range_trials,
    )

    insertion_path = out_dir / "additional_insertion_order.csv"
    range_path = out_dir / "additional_range_selectivity.csv"
    write_csv(insertion_rows, insertion_path)
    write_csv(range_rows, range_path)

    print_insertion_rows(insertion_rows)
    print_range_rows(range_rows)
    print_highlights(insertion_rows, range_rows)

    print("\nSaved files")
    print("-----------")
    print(insertion_path)
    print(range_path)


if __name__ == "__main__":
    main()
