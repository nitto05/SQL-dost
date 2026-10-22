import pytest
from sql_dost.model_client import _extract_json, ModelError

def test_extract_json():
    obj = _extract_json('{"sql":"SELECT 1","explanation":"constant","clarification_needed":false}')
    assert obj["sql"] == "SELECT 1"
    assert obj["clarification_needed"] is False

def test_extract_json_from_wrapping_text():
    obj = _extract_json('Here you go: {"sql":"SELECT 1","explanation":"ok"}')
    assert obj["sql"] == "SELECT 1"

def test_invalid_json_rejected():
    with pytest.raises(ModelError):
        _extract_json("not json")
