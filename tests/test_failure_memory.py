from sql_dost.failure_memory import append_failure, retrieve_failures

def test_failure_append_and_retrieve(tmp_path):
    path = tmp_path / "failures.md"
    append_failure("students with high marks", "SELECT marks FROM students",
                   "Schema mismatch", "marks belongs to marks table",
                   "unknown column", path=path)
    text = path.read_text()
    assert "F-0001" in text
    assert "Schema mismatch" in retrieve_failures("students marks", path=path)
