"""Compatibility client for the existing Kaggle /generate server contract."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
LOCAL_SERVER_URL = os.getenv("LOCAL_SERVER_URL", "")
REMOTE_API_KEY = os.getenv("REMOTE_API_KEY", "")
REMOTE_TIMEOUT_SECONDS = float(os.getenv("REMOTE_TIMEOUT_SECONDS", "115"))
ENABLE_GEMINI_FALLBACK = os.getenv("ENABLE_GEMINI_FALLBACK", "false").lower() == "true"

def query_local_llm(prompt: str, max_tokens: int = 700, temperature: float = 0.1) -> str:
    """Call the remote server. Gemini fallback is opt-in; no local LLM is loaded."""
    if not LOCAL_SERVER_URL:
        raise RuntimeError("Set LOCAL_SERVER_URL in .env to the remote /generate endpoint.")
    headers = {}
    if REMOTE_API_KEY:
        headers["x-api-key"] = REMOTE_API_KEY
    try:
        response = requests.post(
            LOCAL_SERVER_URL,
            json={"prompt": prompt, "max_tokens": max_tokens, "temperature": temperature},
            headers=headers, timeout=REMOTE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        result = body.get("response")
        if not isinstance(result, str) or not result.strip():
            raise RuntimeError("Remote server returned no response text.")
        return result.strip()
    except requests.RequestException:
        if not ENABLE_GEMINI_FALLBACK:
            raise
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("Gemini fallback is enabled but GEMINI_API_KEY is missing.")
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        fallback = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(),
        )
        if not fallback.text:
            raise RuntimeError("Gemini fallback returned an empty response.")
        return fallback.text.strip()
