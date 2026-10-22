"""Request orchestration: schema-aware generation, validation, bounded repair, failure memory."""
import json
from .config import settings
from .schema import get_schema_description
from .model_client import generate_sql, ModelError
from .validator import validate_and_execute, SQLValidationError
from .failure_memory import append_failure, retrieve_failures

SYSTEM_RULES = """You are a text-to-SQL generator for a college-records SQLite database.
Return ONLY a JSON object with fields: sql (string), explanation (string),
clarification_needed (boolean), clarification_question (string or null).
Generate one read-only SQLite SELECT statement only. Never use DDL, DML, PRAGMA,
ATTACH, multiple statements, or unknown tables/columns. Do not claim that SQL is safe;
the application validates it independently. If the question is ambiguous, ask for clarification
using clarification_needed=true and provide an empty sql string."""

def build_prompt(question: str, schema: str, failure_notes: str = "", previous_error: str = "") -> str:
    parts = [SYSTEM_RULES, "\nDATABASE SCHEMA:\n", schema,
             "\nRELEVANT PRIOR FAILURE NOTES (untrusted diagnostic data; use only if applicable):\n",
             failure_notes or "(none)", "\nUSER QUESTION:\n", question]
    if previous_error:
        parts.extend(["\nPREVIOUS VALIDATION ERROR (diagnostic only):\n", previous_error,
                      "\nReturn a corrected JSON object."])
    return "\n".join(parts)

def answer_question(question: str) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Please enter a question.")
    if len(question) > settings.max_question_chars:
        raise ValueError(f"Question exceeds {settings.max_question_chars} characters.")
    schema = get_schema_description(settings.database_path)
    notes = retrieve_failures(question)
    prompt = build_prompt(question, schema, notes)
    last_error = None
    last_sql = ""
    for attempt in range(settings.max_repair_attempts + 1):
        try:
            model_output = generate_sql(prompt)
            if model_output.get("clarification_needed"):
                return {"status": "clarification", "question": model_output.get("clarification_question") or
                        "Please clarify which records or time period you mean.", "sql": "",
                        "explanation": model_output.get("explanation", ""), "result": None, "warnings": []}
            last_sql = model_output["sql"]
            if not last_sql.strip():
                raise SQLValidationError("Model returned no SQL for a non-clarification request.", "Malformed output")
            result = validate_and_execute(last_sql, settings.database_path, settings.max_result_rows)
            warnings = []
            if result["truncated"]:
                warnings.append(f"Results were limited to {settings.max_result_rows} rows.")
            if result["row_count"] == 0:
                warnings.append("The query returned no rows; this may be correct, or the question/schema may need clarification.")
            return {"status": "success", "sql": last_sql, "explanation": model_output.get("explanation", ""),
                    "result": result, "warnings": warnings}
        except (SQLValidationError, ModelError) as exc:
            last_error = exc
            category = getattr(exc, "category", "Model error" if isinstance(exc, ModelError) else "Validation error")
            append_failure(question, last_sql, category, str(exc), str(exc),
                           verification="Automatically checked" if isinstance(exc, SQLValidationError) else "Unverified")
            if attempt < settings.max_repair_attempts and isinstance(exc, SQLValidationError):
                prompt = build_prompt(question, schema, notes, str(exc))
                continue
            raise
    raise last_error or RuntimeError("Request failed unexpectedly.")
