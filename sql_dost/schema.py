from pathlib import Path
import sqlite3

def get_schema_description(database_path: str) -> str:
    """Read actual SQLite schema metadata from the configured database."""
    if not Path(database_path).exists():
        raise FileNotFoundError(
            f"Database not found at {database_path}. Run `python scripts/init_db.py` first."
        )
    conn = sqlite3.connect(f"file:{Path(database_path).resolve()}?mode=ro", uri=True)
    try:
        tables = conn.execute("""
            SELECT name, sql FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name
        """).fetchall()
        lines = []
        for table, create_sql in tables:
            lines.append(f"Table {table}:")
            cols = conn.execute(f'PRAGMA table_info("{table.replace(chr(34), chr(34)*2)}")').fetchall()
            for col in cols:
                _, name, typ, notnull, default, pk = col
                flags = []
                if pk: flags.append("PRIMARY KEY")
                if notnull: flags.append("NOT NULL")
                suffix = f" [{' ; '.join(flags)}]" if flags else ""
                lines.append(f"  - {name} {typ or 'UNDECLARED'}{suffix}")
            fks = conn.execute(f'PRAGMA foreign_key_list("{table.replace(chr(34), chr(34)*2)}")').fetchall()
            for fk in fks:
                lines.append(f"  - FOREIGN KEY {fk[3]} REFERENCES {fk[2]}({fk[4]})")
        return "\n".join(lines)
    finally:
        conn.close()
