"""Create a small synthetic college database for local development."""
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS departments (
  department_id INTEGER PRIMARY KEY,
  department_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS students (
  student_id INTEGER PRIMARY KEY,
  student_name TEXT NOT NULL,
  department_id INTEGER NOT NULL REFERENCES departments(department_id),
  year_of_study INTEGER NOT NULL CHECK(year_of_study BETWEEN 1 AND 5),
  email TEXT
);
CREATE TABLE IF NOT EXISTS courses (
  course_id INTEGER PRIMARY KEY,
  course_name TEXT NOT NULL,
  department_id INTEGER NOT NULL REFERENCES departments(department_id),
  credits INTEGER NOT NULL DEFAULT 3
);
CREATE TABLE IF NOT EXISTS enrollments (
  enrollment_id INTEGER PRIMARY KEY,
  student_id INTEGER NOT NULL REFERENCES students(student_id),
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  semester TEXT NOT NULL,
  UNIQUE(student_id, course_id, semester)
);
CREATE TABLE IF NOT EXISTS marks (
  mark_id INTEGER PRIMARY KEY,
  student_id INTEGER NOT NULL REFERENCES students(student_id),
  course_id INTEGER NOT NULL REFERENCES courses(course_id),
  semester TEXT NOT NULL,
  score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
  UNIQUE(student_id, course_id, semester)
);
"""
def initialize_database(path="data/college.db", schema_path="schema.sql"):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT OR IGNORE INTO departments VALUES (?,?)", [
            (1, "Computer Science"), (2, "Electronics"), (3, "Mathematics")])
        conn.executemany("INSERT OR IGNORE INTO students VALUES (?,?,?,?,?)", [
            (101, "Aarav Das", 1, 2, "aarav@example.test"),
            (102, "Diya Sen", 1, 3, "diya@example.test"),
            (103, "Kabir Rao", 2, 2, "kabir@example.test"),
            (104, "Mira Patnaik", 3, 1, "mira@example.test"),
            (105, "Ishaan Roy", 1, 4, "ishaan@example.test")])
        conn.executemany("INSERT OR IGNORE INTO courses VALUES (?,?,?,?)", [
            (201, "Database Systems", 1, 4), (202, "Algorithms", 1, 4),
            (203, "Digital Electronics", 2, 3), (204, "Discrete Mathematics", 3, 3)])
        conn.executemany("INSERT OR IGNORE INTO enrollments VALUES (?,?,?,?)", [
            (1,101,201,"2026-S1"), (2,101,202,"2026-S1"), (3,102,201,"2026-S1"),
            (4,103,203,"2026-S1"), (5,104,204,"2026-S1"), (6,105,201,"2026-S1")])
        conn.executemany("INSERT OR IGNORE INTO marks VALUES (?,?,?,?,?)", [
            (1,101,201,"2026-S1",88), (2,101,202,"2026-S1",91), (3,102,201,"2026-S1",79),
            (4,103,203,"2026-S1",84), (5,104,204,"2026-S1",93), (6,105,201,"2026-S1",67)])
        conn.commit()
    finally:
        conn.close()
    Path(schema_path).write_text(SCHEMA.strip() + "\n", encoding="utf-8")
    return str(target)
