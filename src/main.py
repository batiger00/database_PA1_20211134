from pathlib import Path

from bstar_tree import BStarTree
from btree import BTree
from bplustree import BPlusTree
from record_store import RecordStore


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "student.csv"
    store = RecordStore.from_csv(csv_path)
    tree = BTree(order=3)
    bplus_tree = BPlusTree(order=3)
    bstar_tree = BStarTree(order=3)

    first_rid = 0
    first_record = store.get_by_rid(first_rid)

    for rid in range(20):
        record = store.get_by_rid(rid)
        tree.insert(record.student_id, rid)
        bplus_tree.insert(record.student_id, rid)
        bstar_tree.insert(record.student_id, rid)

    searched_rid = tree.search(first_record.student_id)
    deleted = tree.delete(first_record.student_id)
    search_after_delete = tree.search(first_record.student_id)
    bplus_search_result = bplus_tree.search(first_record.student_id)
    range_start = min(first_record.student_id, store.get_by_rid(5).student_id)
    range_end = max(first_record.student_id, store.get_by_rid(5).student_id)
    range_results = bplus_tree.range_query(range_start, range_end)
    bplus_deleted = bplus_tree.delete(first_record.student_id)
    bplus_search_after_delete = bplus_tree.search(first_record.student_id)
    bstar_search_result = bstar_tree.search(first_record.student_id)
    bstar_deleted = bstar_tree.delete(first_record.student_id)
    bstar_search_after_delete = bstar_tree.search(first_record.student_id)

    print(f"Loaded records: {len(store)}")
    print(f"RID {first_rid}: {first_record}")
    print(f"Key for RID {first_rid}: {first_record.student_id}")
    print(f"Search result for key {first_record.student_id}: {searched_rid}")
    print(f"Deleted key {first_record.student_id}: {deleted}")
    print(f"Search after delete: {search_after_delete}")
    print(f"Split count after sample inserts: {tree.split_count}")
    print(f"B+ tree search result: {bplus_search_result}")
    print(f"B+ tree deleted key {first_record.student_id}: {bplus_deleted}")
    print(f"B+ tree search after delete: {bplus_search_after_delete}")
    print(f"B+ tree range query result count: {len(range_results)}")
    print(f"B* tree search result: {bstar_search_result}")
    print(f"B* tree deleted key {first_record.student_id}: {bstar_deleted}")
    print(f"B* tree search after delete: {bstar_search_after_delete}")
    print(f"B* tree redistribution count: {bstar_tree.redistribution_count}")
    print(f"B* tree 2-to-3 split count: {bstar_tree.two_to_three_split_count}")


if __name__ == "__main__":
    main()
