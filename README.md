
# SQL_dost — Natural-Language to SQL Assistant

SQL_dost accepts plain-English questions about a configured college-records SQLite database, asks a **remote** model to produce structured SQL, validates the SQL, executes only approved read-only queries, and displays results and warnings. It keeps an append-only `failures.md` diagnostic history and retrieves relevant prior notes for subsequent prompts.

> **Important:** The uploaded model server currently points to `unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit`. That is a base/instruct repository, not evidence of the user's separately fine-tuned SQL_dost model. The application does not silently claim or select a fine-tuned checkpoint. Configure the intended fine-tuned model or adapter in the server notebook before using it for evaluation.

## Architecture

`Streamlit UI → request orchestrator → schema + failure retrieval → remote /generate → JSON parser → SQL policy/syntax checks → read-only SQLite executor → result/warnings`

- **No local model inference:** the desktop runs only the app and SQLite. It does not load Transformers or GPU models.
- **Remote client:** `sql_dost/model_client.py` is used by the app; `local_llm_client.py` preserves the old `query_local_llm()`-style contract for other integrations.
- **Remote contract:** POST `{"prompt": "...", "max_tokens": 700, "temperature": 0.1}` to `/generate`; expected response is `{"response": "<model text>"}`.
- **Model output contract:** the text inside `response` must be a JSON object containing `sql`, `explanation`, `clarification_needed`, and `clarification_question`.
- **Failure memory:** `failures.md` is append-only retrieval-based corrective memory, not fine-tuning. Entries from failed validation/model calls are logged automatically. User-reported incorrect feedback is explicitly marked unverified.
- **Safety:** SQLGlot parses SQLite SQL when installed; only one SELECT-family query is allowed. A read-only SQLite URI, SQLite authorizer, progress handler, timeout, and row cap provide defense in depth. Syntax/execution success cannot prove semantic correctness.

## Project layout

```text
SQL_dost/
├── app.py
├── local_llm_client.py  # compatibility wrapper for existing /generate contract
├── schema.sql
├── requirements.txt
├── .env.example
├── .gitignore
├── sql_dost/
│   ├── config.py
│   ├── model_client.py
│   ├── schema.py
│   ├── engine.py
│   ├── validator.py
│   ├── failure_memory.py
│   └── demo_data.py
├── scripts/init_db.py
└── tests/
```

## 1. Local setup (Windows PowerShell)

Use Python 3.11 or another version supported by the dependencies.

```powershell
cd SQL_dost
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/init_db.py
```

Open `.env` and set `LOCAL_SERVER_URL` to the **current** remote URL ending in `/generate`. The ephemeral `trycloudflare.com` URL changes when the Kaggle session restarts. If authentication is enabled on Kaggle, set `REMOTE_API_KEY` to the same secret. Never commit `.env`.

Start the UI:

```powershell
streamlit run app.py
```

Streamlit prints a local browser URL. The model inference still happens on the remote server.

## 2. Kaggle server setup

1. Open the supplied notebook in Kaggle and enable a GPU accelerator.
2. Ensure the selected model repository is the intended model. The current notebook hard-codes an Unsloth Qwen instruct model; update it for the fine-tuned model if needed.
3. For a merged fine-tuned model, set Kaggle environment variable `SQL_DOST_MODEL_ID` to its repository/path and leave `SQL_DOST_ADAPTER_ID` empty. For LoRA, set `SQL_DOST_MODEL_ID` to the compatible base model and `SQL_DOST_ADAPTER_ID` to the adapter repository/path; the adapted notebook applies `PeftModel.from_pretrained`. Do not point `AutoModelForCausalLM` at an adapter folder as if it were a merged model.
4. Set `API_KEY` as a Kaggle secret/environment variable (recommended), and configure the server's `API_KEY` from `os.environ`. Do not expose the tunnel publicly without authentication.
5. Run the install, GPU check, model loading, and server cells. Copy the printed public `/generate` URL to local `.env`.
6. Check `/health` in a browser or call it with `requests.get(base_url + "/health")`.
7. Test `/generate` with a simple prompt before using the UI.

**Important existing notebook observations:** it currently hard-codes the model ID twice, has inconsistent system prompt branding (SHARQO in one cell and GateSter in the server cell), allows up to 4096 output tokens, and uses a 105-second generation ceiling. The app uses a 115-second HTTP timeout and defaults to 700 tokens; lower output tokens further if the remote tunnel is timing out. The server's Cloudflare reader uses blocking `stdout.readline()`, so tunnel startup can wait longer than intended if no output arrives. Kaggle sessions may disconnect; this is a prototype, not persistent hosting.

## 3. Remote model output prompt

The app asks for exactly this JSON shape:

```json
{
  "sql": "SELECT s.student_name FROM students AS s",
  "explanation": "Lists student names.",
  "clarification_needed": false,
  "clarification_question": null
}
```

The model should not wrap the JSON in Markdown fences. The client tolerates surrounding text only as a best-effort parser, not as the preferred contract.

## 4. Database

The demo database contains synthetic records in `departments`, `students`, `courses`, `enrollments`, and `marks`. Rebuild it with:

```powershell
python scripts/init_db.py
```

The database is opened read-only for query execution. If changing the schema, update `schema.sql`, initialize or migrate the database, and test the schema-aware prompts. Do not use real student information without a separate privacy/security review.

## 5. Tests

```powershell
pytest -q
```

The tests cover SELECT execution, blocked writes and multiple statements, unknown tables, row caps, failure-memory retrieval, and JSON parsing. Run them after dependency installation. Remote integration tests require a live Kaggle tunnel and the intended model configured.

## 6. Optional Gemini fallback

By default, fallback is **disabled** so an unavailable configured model is surfaced clearly and does not silently change model behavior. To explicitly enable it, set `ENABLE_GEMINI_FALLBACK=true`, add `GEMINI_API_KEY`, and install the `google-genai` dependency. Gemini is a cloud fallback, not local inference, but output quality and evaluation results may differ from the configured Hugging Face model.

## Troubleshooting

- **`LOCAL_SERVER_URL is not configured`:** set it in `.env` and restart Streamlit.
- **Remote model unavailable / timeout:** verify Kaggle is still running, the URL is current, `/health` responds, and API keys match. Lower `MAX_NEW_TOKENS` on both sides if needed.
- **JSON parse error:** check that the model follows the response contract and doesn't emit reasoning or prose around the JSON.
- **Unknown table/column:** verify schema and database agree; inspect `failures.md` for the exact diagnostic.
- **`Database not found`:** run `python scripts/init_db.py`.
- **Cloudflare 524 / tunnel timeout:** Kaggle may be cold or generating too long. Try shorter questions and smaller output limits; use persistent remote GPU hosting for stable use.
- **Semantic uncertainty:** a query can execute successfully and still answer the wrong question. Verify against known answers and use held-out tests; the app deliberately does not claim perfect semantic validation.

## Security notes

- Use synthetic data by default.
- Never put API keys in source control or prompts.
- Remote endpoint authentication is strongly recommended.
- The tunnel URL is publicly reachable unless protected by the configured API key or other access controls.
- SQL checks are defense in depth, not a substitute for reviewing the model, schema, and data handling.
