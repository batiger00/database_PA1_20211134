import csv
from pathlib import Path

from student_record import StudentRecord


class RecordStore:
    def __init__(self, records: list[StudentRecord]):
        self.records = records

    @classmethod
    def from_csv(cls, csv_path: str | Path) -> "RecordStore":
        path = Path(csv_path)
        records: list[StudentRecord] = []

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = StudentRecord(
                    student_id=int(row["Student ID"]),
                    name=row["Name"],
                    gender=row["Gender"],
                    gpa=float(row["GPA"]),
                    height=float(row["Height"]),
                    weight=float(row["Weight"]),
                )
                records.append(record)

        return cls(records)

    def __len__(self) -> int:
        return len(self.records)

    def get_by_rid(self, rid: int) -> StudentRecord:
        return self.records[rid]

    def get_rid_by_index(self, index: int) -> int:
        return index
