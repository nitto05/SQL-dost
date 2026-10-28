from unittest.mock import patch
from sql_dost.query_understanding import _normalize, understand_query
from sql_dost.model_client import ModelError
from sql_dost.engine import answer_question
from sql_dost.demo_data import initialize_database
import pytest

def test_schema_intent_never_requires_sql():
    result = _normalize({
        "intent": "SCHEMA_OVERVIEW",
        "normalized_request": "List tables",
        "entities": [],
        "constraints": {},
        "requires_sql": True,
        "requires_clarification": False,
        "subtasks": [],
    }, "What tables exist?")
    assert result["intent"] == "SCHEMA_OVERVIEW"
    assert result["requires_sql"] is False

def test_write_request_never_requires_sql():
    result = _normalize({
        "intent": "WRITE_REQUEST",
        "normalized_request": "Add a student",
        "requires_sql": True,
    }, "Add a student")
    assert result["requires_sql"] is False

def test_unknown_intent_fails_closed():
    result = _normalize({
        "intent": "MAKE_A_SANDWICH",
        "normalized_request": "test",
    }, "test")
    assert result["intent"] == "AMBIGUOUS_REQUEST"
    assert result["requires_sql"] is False

def test_understand_query_empty_input():
    result = understand_query("   ", "CREATE TABLE dummy (id INT);")
    assert result["intent"] == "AMBIGUOUS_REQUEST"
    assert result["requires_clarification"] is True

def test_understand_query_model_failure_fails_closed():
    with patch("sql_dost.query_understanding.generate_sql", side_effect=ModelError("Server error")):
        result = understand_query("What tables exist?", "CREATE TABLE dummy (id INT);")
        assert result["intent"] == "AMBIGUOUS_REQUEST"
        assert result["requires_clarification"] is True
        assert "Query understanding failed" in result["reason"]

def test_understand_query_successful_classification():
    mock_response = {
        "sql": "",
        "intent": "SCHEMA_OVERVIEW",
        "normalized_request": "Show all tables",
        "entities": ["students"],
        "constraints": {},
        "requires_sql": False,
        "requires_clarification": False,
        "clarification_question": None,
        "subtasks": [],
        "reason": "User asked for table list",
    }
    with patch("sql_dost.query_understanding.generate_sql", return_value=mock_response):
        result = understand_query("What tables do we have?", "CREATE TABLE students (id INT);")
        assert result["intent"] == "SCHEMA_OVERVIEW"
        assert result["requires_sql"] is False
        assert result["normalized_request"] == "Show all tables"

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    import dataclasses
    from sql_dost.config import settings
    db_path = str(tmp_path / "test.db")
    initialize_database(db_path, str(tmp_path / "schema.sql"))
    new_settings = dataclasses.replace(settings, database_path=db_path)
    monkeypatch.setattr("sql_dost.engine.settings", new_settings)
    return db_path

def test_engine_schema_overview(temp_db):
    with patch("sql_dost.engine.understand_query") as mock_uq:
        mock_uq.return_value = {
            "intent": "SCHEMA_OVERVIEW",
            "normalized_request": "List tables",
            "requires_clarification": False,
        }
        res = answer_question("What tables exist?")
        assert res["status"] == "success"
        assert res["response_type"] == "schema"
        assert "sqlite_master" in res["sql"]
        assert "students" in res["schema"]
        assert res["result"] is None

def test_engine_write_request(temp_db):
    with patch("sql_dost.engine.understand_query") as mock_uq:
        mock_uq.return_value = {
            "intent": "WRITE_REQUEST",
            "normalized_request": "Delete all students",
            "requires_clarification": False,
        }
        res = answer_question("Drop the database")
        assert res["status"] == "rejected"
        assert res["response_type"] == "policy"
        assert res["result"] is None

def test_engine_unsupported_request(temp_db):
    with patch("sql_dost.engine.understand_query") as mock_uq:
        mock_uq.return_value = {
            "intent": "UNSUPPORTED_REQUEST",
            "normalized_request": "What is the weather?",
            "requires_clarification": False,
        }
        res = answer_question("What is the weather?")
        assert res["status"] == "unsupported"
        assert res["response_type"] == "message"
        assert res["result"] is None

def test_engine_clarification_request(temp_db):
    with patch("sql_dost.engine.understand_query") as mock_uq:
        mock_uq.return_value = {
            "intent": "AMBIGUOUS_REQUEST",
            "normalized_request": "Scores",
            "requires_clarification": True,
            "clarification_question": "Which semester or course?",
        }
        res = answer_question("Scores")
        assert res["status"] == "clarification"
        assert res["question"] == "Which semester or course?"

def test_engine_data_retrieval_flow(temp_db):
    with patch("sql_dost.engine.understand_query") as mock_uq, \
         patch("sql_dost.engine.generate_sql") as mock_gen:
        mock_uq.return_value = {
            "intent": "DATA_RETRIEVAL",
            "normalized_request": "SELECT student names",
            "requires_clarification": False,
        }
        mock_gen.return_value = {
            "sql": "SELECT student_name FROM students ORDER BY student_id",
            "explanation": "List of student names",
            "clarification_needed": False,
        }
        res = answer_question("Tell me student names")
        assert res["status"] == "success"
        assert res["response_type"] == "data"
        assert res["result"]["row_count"] == 5
        # Verify prompt received the normalized request
        prompt_arg = mock_gen.call_args[0][0]
        assert "SELECT student names" in prompt_arg

