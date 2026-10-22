import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "data/college.db")
    schema_path: str = os.getenv("SCHEMA_PATH", "schema.sql")
    remote_generate_url: str = os.getenv("LOCAL_SERVER_URL", "")
    remote_api_key: str = os.getenv("REMOTE_API_KEY", "")
    request_timeout_seconds: float = float(os.getenv("REMOTE_TIMEOUT_SECONDS", "115"))
    max_tokens: int = int(os.getenv("MAX_NEW_TOKENS", "700"))
    temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.1"))
    max_question_chars: int = int(os.getenv("MAX_QUESTION_CHARS", "2000"))
    max_result_rows: int = int(os.getenv("MAX_RESULT_ROWS", "200"))
    max_repair_attempts: int = int(os.getenv("MAX_REPAIR_ATTEMPTS", "1"))
    enable_gemini_fallback: bool = os.getenv("ENABLE_GEMINI_FALLBACK", "false").lower() == "true"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

settings = Settings()
