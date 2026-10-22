import sqlite3
import pytest
from sql_dost.validator import validate_and_execute, SQLValidationError
from sql_dost.demo_data import initialize_database

@pytest.fixture
def db(tmp_path):
    path = tmp_path / "test.db"
    initialize_database(str(path), str(tmp_path / "schema.sql"))
    return str(path)

def test_select_works(db):
    result = validate_and_execute("SELECT student_name FROM students ORDER BY student_id", db)
    assert result["row_count"] == 5
    assert result["rows"][0][0] == "Aarav Das"

def test_write_query_rejected(db):
    with pytest.raises(SQLValidationError):
        validate_and_execute("DELETE FROM students", db)

def test_multiple_statements_rejected(db):
    with pytest.raises(SQLValidationError):
        validate_and_execute("SELECT 1; DROP TABLE students", db)

def test_unknown_table_rejected_at_execution(db):
    with pytest.raises(SQLValidationError):
        validate_and_execute("SELECT * FROM not_a_table", db)

def test_row_cap(db):
    result = validate_and_execute("SELECT * FROM students", db, max_rows=2)
    assert result["row_count"] == 2
    assert result["truncated"] is True
