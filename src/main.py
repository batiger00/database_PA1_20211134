from pathlib import Path

from record_store import RecordStore


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "student.csv"
    store = RecordStore.from_csv(csv_path)

    first_rid = 0
    first_record = store.get_by_rid(first_rid)

    print(f"Loaded records: {len(store)}")
    print(f"RID {first_rid}: {first_record}")
    print(f"Key for RID {first_rid}: {first_record.student_id}")


if __name__ == "__main__":
    main()
