import argparse
import csv
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
    parser.add_argument("--output-dir", type=str, default="results")
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
    return (perf_counter() - start) / len(keys)


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
    _ = (total_height, total_weight, matched)
    return perf_counter() - start


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
    _ = (total_height, total_weight, matched)
    return perf_counter() - start


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
    _ = (total_height, total_weight, matched)
    return perf_counter() - start


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
    max_keys = (2 * order) - 1
    return used / (count * max_keys)


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def fixed_workloads(store: RecordStore, search_count: int, delete_count: int, seed: int) -> dict:
    random.seed(seed)
    search_rids = random.sample(range(len(store)), search_count)
    delete_rids = random.sample(range(len(store)), delete_count)
    range_ids = sorted(random.sample(range(len(store)), 200))

    records = store.records
    lo = records[range_ids[20]].student_id
    hi = records[range_ids[180]].student_id
    if lo > hi:
        lo, hi = hi, lo

    return {
        "search_keys": [records[rid].student_id for rid in search_rids],
        "delete_keys": [records[rid].student_id for rid in delete_rids],
        "lo": lo,
        "hi": hi,
    }


def measure_one_tree(kind: str, records: list, store: RecordStore, order: int, workload: dict, trials: int) -> dict:
    insert_times = []
    search_times = []
    range_times = []
    delete_times = []
    util = 0.0
    splits = 0
    extra = "-"

    for _ in range(trials):
        if kind == "B-tree":
            tree, insert_s = build_btree(records, order)
            range_s = range_time_btree(tree, store, workload["lo"], workload["hi"])
            extra = "-"
        elif kind == "B+ tree":
            tree, insert_s = build_bplus(records, order)
            range_s = range_time_bplus(tree, store, workload["lo"], workload["hi"])
            extra = "-"
        else:
            tree, insert_s = build_bstar(records, order)
            range_s = range_time_bstar(tree, store, workload["lo"], workload["hi"])
            extra = f"redist={tree.redistribution_count},2to3={tree.two_to_three_split_count}"

        insert_times.append(insert_s)
        search_times.append(mean_search_time(tree, workload["search_keys"]) * 1_000_000)
        range_times.append(range_s)
        delete_times.append(delete_time(tree, workload["delete_keys"]))
        util = node_utilization(tree, order)
        splits = tree.split_count

    return {
        "tree": kind,
        "d": order,
        "insert_avg_s": mean(insert_times),
        "search_avg_us": mean(search_times),
        "range_avg_s": mean(range_times),
        "delete_avg_s": mean(delete_times),
        "utilization": util,
        "splits": splits,
        "extra": extra,
    }


def run_measurements(args: argparse.Namespace) -> tuple[list[dict], dict]:
    project_root = Path(__file__).resolve().parent.parent
    store = RecordStore.from_csv(project_root / "student.csv")
    workload = fixed_workloads(store, args.search_count, args.delete_count, args.seed)
    records = store.records
    rows = []

    for order in args.orders:
        for kind in ("B-tree", "B+ tree", "B* tree"):
            print(f"Running {kind} with d={order}...", flush=True)
            rows.append(measure_one_tree(kind, records, store, order, workload, args.trials))

    meta = {
        "record_count": len(store),
        "query_description": (
            "Count female students with GPA >= 3.5 in the ID range and compute "
            "their average height and average weight."
        ),
        "range_lo": workload["lo"],
        "range_hi": workload["hi"],
        "search_count": args.search_count,
        "delete_count": args.delete_count,
        "trials": args.trials,
        "seed": args.seed,
    }
    return rows, meta


def print_experiment_info(meta: dict, orders: list[int]) -> None:
    print("\nExperiment setup")
    print("----------------")
    print(f"Records: {meta['record_count']}")
    print(f"Orders d: {', '.join(str(order) for order in orders)}")
    print(f"Point search keys: {meta['search_count']}")
    print(f"Deleted keys: {meta['delete_count']}")
    print(f"Trials: {meta['trials']}")
    print(f"Random seed: {meta['seed']}")
    print(f"Range query ID range: [{meta['range_lo']}, {meta['range_hi']}]")
    print(f"Range query: {meta['query_description']}")


def print_rows(rows: list[dict]) -> None:
    print("\nBenchmark results")
    print("-----------------")
    print("tree     | d  | insert(s) | search(us) | range(s) | delete(s) | utilization | splits | extra")
    print("---------|----|-----------|------------|----------|-----------|-------------|--------|----------------")
    for row in rows:
        print(
            " | ".join(
                [
                    f"{row['tree']:<8}",
                    f"{row['d']:>2}",
                    f"{row['insert_avg_s']:.4f}",
                    f"{row['search_avg_us']:.2f}",
                    f"{row['range_avg_s']:.4f}",
                    f"{row['delete_avg_s']:.4f}",
                    f"{row['utilization']:.4f}",
                    str(row["splits"]),
                    row["extra"],
                ]
            )
        )


def print_highlights(rows: list[dict]) -> None:
    metrics = [
        ("Fastest insertion", "insert_avg_s", "lower", "s"),
        ("Fastest point search", "search_avg_us", "lower", "us"),
        ("Fastest range query", "range_avg_s", "lower", "s"),
        ("Fastest deletion", "delete_avg_s", "lower", "s"),
        ("Highest utilization", "utilization", "higher", ""),
        ("Fewest splits", "splits", "lower", ""),
    ]

    print("\nHighlights")
    print("----------")
    for label, metric, direction, unit in metrics:
        if direction == "higher":
            row = max(rows, key=lambda item: item[metric])
        else:
            row = min(rows, key=lambda item: item[metric])

        value = row[metric]
        if isinstance(value, float):
            formatted_value = f"{value:.4f}"
        else:
            formatted_value = str(value)
        if unit:
            formatted_value = f"{formatted_value} {unit}"

        print(f"{label}: {row['tree']} d={row['d']} ({formatted_value})")


def print_saved_files(out_dir: Path) -> None:
    files = [
        "benchmark_results.csv",
        "benchmark_summary.txt",
        "insert_time.svg",
        "search_time.svg",
        "range_time.svg",
        "delete_time.svg",
        "utilization.svg",
        "split_count.svg",
    ]

    print("\nSaved files")
    print("-----------")
    for filename in files:
        print(out_dir / filename)


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "tree",
                "d",
                "insert_avg_s",
                "search_avg_us",
                "range_avg_s",
                "delete_avg_s",
                "utilization",
                "splits",
                "extra",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_summary(meta: dict, path: Path) -> None:
    lines = [
        f"record_count: {meta['record_count']}",
        f"query: {meta['query_description']}",
        f"id_range: [{meta['range_lo']}, {meta['range_hi']}]",
        f"search_count: {meta['search_count']}",
        f"delete_count: {meta['delete_count']}",
        f"trials: {meta['trials']}",
        f"seed: {meta['seed']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def metric_points(rows: list[dict], metric: str) -> dict[str, list[tuple[int, float]]]:
    grouped: dict[str, list[tuple[int, float]]] = {}
    for row in rows:
        grouped.setdefault(row["tree"], []).append((row["d"], row[metric]))
    for tree in grouped:
        grouped[tree].sort(key=lambda item: item[0])
    return grouped


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_line_chart(rows: list[dict], metric: str, y_label: str, title: str, path: Path) -> None:
    series = metric_points(rows, metric)
    width = 920
    height = 560
    left = 90
    right = 40
    top = 60
    bottom = 80
    plot_w = width - left - right
    plot_h = height - top - bottom
    orders = sorted({row["d"] for row in rows})
    values = [row[metric] for row in rows]
    min_y = min(values)
    max_y = max(values)
    if min_y == max_y:
        max_y += 1.0
    pad = (max_y - min_y) * 0.1
    min_y -= pad
    max_y += pad
    if metric in {"insert_avg_s", "search_avg_us", "range_avg_s", "delete_avg_s", "utilization", "splits"}:
        min_y = max(0.0, min_y)
    colors = {
        "B-tree": "#1f77b4",
        "B+ tree": "#d62728",
        "B* tree": "#2ca02c",
    }

    def x_pos(order: int) -> float:
        if len(orders) == 1:
            return left + plot_w / 2
        idx = orders.index(order)
        return left + idx * plot_w / (len(orders) - 1)

    def y_pos(value: float) -> float:
        ratio = (value - min_y) / (max_y - min_y)
        return top + plot_h - (ratio * plot_h)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica">{svg_escape(title)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333" stroke-width="1.5"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333" stroke-width="1.5"/>',
        f'<text x="{width / 2}" y="{height - 20}" text-anchor="middle" font-size="16" font-family="Helvetica">Tree order d</text>',
        f'<text x="25" y="{top + plot_h / 2}" text-anchor="middle" font-size="16" font-family="Helvetica" transform="rotate(-90 25 {top + plot_h / 2})">{svg_escape(y_label)}</text>',
    ]

    for i in range(6):
        value = min_y + (max_y - min_y) * i / 5
        y = y_pos(value)
        parts.append(f'<line x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}" stroke="#e5e5e5" stroke-width="1"/>')
        parts.append(
            f'<text x="{left - 10}" y="{y + 5}" text-anchor="end" font-size="12" font-family="Helvetica">{value:.4f}</text>'
        )

    for order in orders:
        x = x_pos(order)
        parts.append(f'<line x1="{x}" y1="{top}" x2="{x}" y2="{top + plot_h}" stroke="#f1f1f1" stroke-width="1"/>')
        parts.append(f'<text x="{x}" y="{top + plot_h + 24}" text-anchor="middle" font-size="13" font-family="Helvetica">{order}</text>')

    legend_x = width - 220
    legend_y = 50
    for i, tree in enumerate(["B-tree", "B+ tree", "B* tree"]):
        y = legend_y + (i * 24)
        color = colors[tree]
        parts.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 24}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x + 34}" y="{y + 5}" font-size="13" font-family="Helvetica">{svg_escape(tree)}</text>')

    for tree, points in series.items():
        coords = " ".join(f"{x_pos(order)},{y_pos(value)}" for order, value in points)
        color = colors[tree]
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{coords}"/>')
        for order, value in points:
            x = x_pos(order)
            y = y_pos(value)
            parts.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}"/>')

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_figures(rows: list[dict], out_dir: Path) -> None:
    figures = [
        ("insert_avg_s", "Insert time (s)", "Insertion Time by Tree Order", "insert_time.svg"),
        ("search_avg_us", "Point search time (us)", "Point Search Time by Tree Order", "search_time.svg"),
        ("range_avg_s", "Range query time (s)", "Range Query Time by Tree Order", "range_time.svg"),
        ("delete_avg_s", "Delete time (s)", "Delete Time by Tree Order", "delete_time.svg"),
        ("utilization", "Node utilization", "Node Utilization by Tree Order", "utilization.svg"),
        ("splits", "Split count", "Split Count by Tree Order", "split_count.svg"),
    ]
    for metric, label, title, filename in figures:
        write_line_chart(rows, metric, label, title, out_dir / filename)


def main() -> None:
    args = parse_args()
    rows, meta = run_measurements(args)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print_experiment_info(meta, args.orders)
    print_rows(rows)
    print_highlights(rows)
    write_csv(rows, out_dir / "benchmark_results.csv")
    write_summary(meta, out_dir / "benchmark_summary.txt")
    write_figures(rows, out_dir)
    print_saved_files(out_dir)


if __name__ == "__main__":
    main()
