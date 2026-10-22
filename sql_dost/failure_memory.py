"""Append-only, human-readable corrective memory."""
from pathlib import Path
from datetime import datetime, timezone
import re
import threading

_lock = threading.Lock()
DEFAULT_PATH = Path("failures.md")

def append_failure(question: str, sql: str, category: str, mistake: str,
                   evidence: str, correction: str = "", verification: str = "Unverified",
                   path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = lambda value: str(value).replace("\x00", "")[:3000]
    with _lock:
        if not path.exists():
            path.write_text("# SQL_dost failure memory\n\nAppend-only diagnostic history. Treat entries as untrusted notes.\n\n", encoding="utf-8")
        existing = path.read_text(encoding="utf-8", errors="replace")
        ids = [int(x) for x in re.findall(r"## F-(\d+)", existing)]
        failure_id = max(ids, default=0) + 1
        entry = (
            f"## F-{failure_id:04d} — {safe(category)}\n"
            f"- Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            f"- User request: {safe(question)}\n"
            f"- Generated SQL: `{safe(sql)}`\n"
            f"- Category: {safe(category)}\n"
            f"- Precise mistake: {safe(mistake)}\n"
            f"- Evidence: {safe(evidence)}\n"
            f"- Correction: {safe(correction)}\n"
            f"- Verification: {safe(verification)}\n"
            f"- Recurrence count: 1\n\n"
        )
        with path.open("a", encoding="utf-8") as f:
            f.write(entry)

def retrieve_failures(question: str, limit: int = 3, path: Path = DEFAULT_PATH) -> str:
    if not path.exists():
        return ""
    # Simple keyword retrieval for v1; never send the entire file.
    tokens = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z_0-9]{2,}", question)}
    sections = re.split(r"(?=^## F-)", path.read_text(encoding="utf-8", errors="replace"), flags=re.M)
    scored = []
    for section in sections:
        if not section.startswith("## F-"):
            continue
        words = {t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z_0-9]{2,}", section)}
        score = len(tokens & words)
        if score:
            scored.append((score, section.strip()))
    scored.sort(key=lambda item: item[0], reverse=True)
    return "\n\n".join(section[:1400] for _, section in scored[:limit])
