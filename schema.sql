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
