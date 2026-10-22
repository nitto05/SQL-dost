"""SQL policy and schema validation. Model claims are never trusted."""
import sqlite3
from pathlib import Path

class SQLValidationError(ValueError):
    def __init__(self, message: str, category: str = "Validation error"):
        super().__init__(message)
        self.category = category

def _parse_single_select(sql: str) -> str:
    sql = sql.strip()
    if not sql:
        raise SQLValidationError("Model returned an empty SQL query.", "Malformed output")
    # Prefer SQLGlot's SQLite parser when installed.
    try:
        import sqlglot
        from sqlglot import exp
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
        if len(statements) != 1:
            raise SQLValidationError("Exactly one SQL statement is allowed.", "Unsafe SQL")
        tree = statements[0]
        allowed = (exp.Select, exp.Union, exp.Intersect, exp.Except)
        if not isinstance(tree, allowed):
            raise SQLValidationError("Only read-only SELECT queries are allowed.", "Unsafe SQL")
        forbidden_nodes = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter,
                           exp.Command, exp.Transaction, exp.Pragma, exp.Attach, exp.Detach)
        if any(tree.find(node) for node in forbidden_nodes):
            raise SQLValidationError("Query contains a prohibited SQL operation.", "Unsafe SQL")
        return sql
    except ImportError:
        pass
    except SQLValidationError:
        raise
    except Exception as exc:
        raise SQLValidationError(f"SQLite SQL syntax could not be parsed: {exc}", "Syntax error") from exc

    # Conservative fallback parser when dependency is not installed.
    stripped = sql.rstrip().rstrip(";").strip()
    if ";" in stripped:
        raise SQLValidationError("Exactly one SQL statement is allowed.", "Unsafe SQL")
    first = stripped.split(None, 1)[0].upper() if stripped else ""
    if first not in {"SELECT", "WITH"}:
        raise SQLValidationError("Only SELECT queries are allowed.", "Unsafe SQL")
    blocked = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE",
               "ATTACH", "DETACH", "PRAGMA", "VACUUM", "REINDEX")
    import re
    if re.search(r"\b(" + "|".join(blocked) + r")\b", stripped, re.I):
        raise SQLValidationError("Query contains a prohibited SQL operation.", "Unsafe SQL")
    return stripped

def validate_and_execute(sql: str, database_path: str, max_rows: int = 200):
    sql = _parse_single_select(sql)
    path = Path(database_path)
    if not path.exists():
        raise SQLValidationError(f"Database not found: {database_path}", "Execution error")
    try:
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=3)
        conn.row_factory = sqlite3.Row
        # SQLite-level authorizer is defense in depth.
        denied = {
            sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_CREATE_TEMP_INDEX,
            sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
            sqlite3.SQLITE_CREATE_TEMP_VIEW, sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TEMP_INDEX,
            sqlite3.SQLITE_DROP_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_VIEW,
            sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_DROP_VIEW, sqlite3.SQLITE_ALTER_TABLE,
            sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
        }
        def authorizer(action, arg1, arg2, db_name, trigger):
            if action in denied:
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or arg1 or "").lower() in {"load_extension", "writefile", "readfile"}:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorizer)
        conn.set_progress_handler(lambda: 1, 1_000_000)
        cursor = conn.execute(sql)
        columns = [d[0] for d in (cursor.description or [])]
        rows = cursor.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        return {"columns": columns, "rows": [[row[c] for c in columns] for row in rows],
                "row_count": len(rows), "truncated": truncated}
    except sqlite3.Error as exc:
        raise SQLValidationError(f"SQLite rejected the query: {exc}", "Execution error") from exc
    finally:
        try: conn.close()
        except (UnboundLocalError, Exception): pass
