from pathlib import Path

from btree import BTree
from record_store import RecordStore


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "student.csv"
    store = RecordStore.from_csv(csv_path)
    tree = BTree(order=3)

    first_rid = 0
    first_record = store.get_by_rid(first_rid)

    for rid in range(20):
        record = store.get_by_rid(rid)
        tree.insert(record.student_id, rid)

    searched_rid = tree.search(first_record.student_id)
    deleted = tree.delete(first_record.student_id)
    search_after_delete = tree.search(first_record.student_id)

    print(f"Loaded records: {len(store)}")
    print(f"RID {first_rid}: {first_record}")
    print(f"Key for RID {first_rid}: {first_record.student_id}")
    print(f"Search result for key {first_record.student_id}: {searched_rid}")
    print(f"Deleted key {first_record.student_id}: {deleted}")
    print(f"Search after delete: {search_after_delete}")
    print(f"Split count after sample inserts: {tree.split_count}")


if __name__ == "__main__":
    main()
