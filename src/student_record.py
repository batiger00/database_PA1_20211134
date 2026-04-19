from dataclasses import dataclass


@dataclass(frozen=True)
class StudentRecord:
    student_id: int
    name: str
    gender: str
    gpa: float
    height: float
    weight: float
