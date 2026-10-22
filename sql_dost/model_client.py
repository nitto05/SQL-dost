"""Remote model client. Inference is remote; no local model is loaded."""
import json
import requests
from .config import settings

class ModelError(RuntimeError):
    pass

def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ModelError("Remote model did not return a JSON object.")
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ModelError("Remote model returned malformed JSON.") from exc
    if not isinstance(data, dict):
        raise ModelError("Model response must be a JSON object.")
    if not isinstance(data.get("sql"), str):
        raise ModelError("Model JSON must contain a string field named 'sql'.")
    data.setdefault("explanation", "")
    data.setdefault("clarification_needed", False)
    data.setdefault("clarification_question", None)
    return data

def generate_sql(prompt: str) -> dict:
    """Call configured remote /generate endpoint and parse its response."""
    if not settings.remote_generate_url:
        raise ModelError(
            "LOCAL_SERVER_URL is not configured. Set it to your remote server's /generate URL."
        )
    headers = {"Content-Type": "application/json"}
    if settings.remote_api_key:
        headers["x-api-key"] = settings.remote_api_key
    try:
        response = requests.post(
            settings.remote_generate_url,
            json={"prompt": prompt, "max_tokens": settings.max_tokens,
                  "temperature": settings.temperature},
            headers=headers, timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("response")
        if not isinstance(raw, str) or not raw.strip():
            raise ModelError("Remote server response did not contain a non-empty 'response' string.")
        return _extract_json(raw)
    except ModelError:
        raise
    except requests.Timeout as exc:
        raise ModelError("Remote model request timed out. Check generation limits and server status.") from exc
    except requests.RequestException as exc:
        if settings.enable_gemini_fallback:
            return _generate_with_gemini(prompt)
        raise ModelError(f"Remote model is unavailable: {exc}") from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise ModelError("Remote server returned invalid JSON.") from exc

def _generate_with_gemini(prompt: str) -> dict:
    """Optional explicit fallback; disabled by default and never uses local inference."""
    if not settings.gemini_api_key:
        raise ModelError("Gemini fallback is enabled but GEMINI_API_KEY is not configured.")
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _extract_json(response.text or "")
    except Exception as exc:
        raise ModelError(f"Optional Gemini fallback failed: {exc}") from exc
