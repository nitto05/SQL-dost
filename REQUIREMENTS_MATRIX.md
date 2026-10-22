# SRS requirements coverage matrix

Status legend: **Implemented** = code exists; **Needs live/manual verification** = external service/model or user configuration is required.

| SRS requirement | Implementation | Test / verification | Status |
|---|---|---|---|
| FR-01 Natural-language input | `app.py`, `sql_dost/engine.py` | UI manual test | Implemented |
| FR-02 Schema context | `sql_dost/schema.py`, `sql_dost/engine.py` | `python scripts/init_db.py`; inspect prompt | Implemented |
| FR-03 Configurable HF model via remote inference | `.env`, `sql_dost/model_client.py`, Kaggle notebook | Live `/health` and `/generate` test | Needs model ID + live verification |
| FR-04 No runtime fine-tuning | No training code in app; `model_client.py` | Inspect app dependencies/flow | Implemented |
| FR-05 Structured JSON output | `sql_dost/model_client.py`, `engine.py` | `tests/test_model_client.py` | Implemented |
| FR-06 SQL validation | `sql_dost/validator.py` | `tests/test_validator.py` | Implemented |
| FR-07 Read-only execution | `sql_dost/validator.py` | write-query tests | Implemented |
| FR-08 Bounded repair | `sql_dost/engine.py`, `MAX_REPAIR_ATTEMPTS` | Manual remote malformed-SQL test | Implemented |
| FR-09 Result plausibility checks | `sql_dost/engine.py`, `app.py` | empty/truncated-result paths | Partial: heuristic warnings only |
| FR-10 Failure logging | `sql_dost/failure_memory.py`, `engine.py` | `tests/test_failure_memory.py` | Implemented |
| FR-11 Failure retrieval | `sql_dost/failure_memory.py`, `engine.py` | `tests/test_failure_memory.py` | Implemented |
| FR-12 Distinguish verified vs heuristic | failure verification labels; UI caveat | inspect `failures.md` | Implemented |
| FR-13 User feedback | `app.py`, `failure_memory.py` | manual UI test | Partial: incorrect feedback is logged; correct feedback not persisted |
| FR-14 Timeouts, correction limits, row limits | `config.py`, `model_client.py`, `validator.py` | unit tests + live timeout test | Implemented; live timeout needs verification |
| FR-15 Audit generated SQL/validation outcomes without secrets | SQL displayed; failures logged | inspect failure logs | Partial: successful audit trail not persisted separately |
| NFR-01 Performance/timeouts | `config.py`, `model_client.py`, UI spinner | live test | Needs live verification |
| NFR-02 Portability | `requirements.txt`, README | clean install | Implemented; install not run in this environment |
| NFR-03 Maintainability/configurability | `.env`, `config.py` | config inspection | Implemented |
| NFR-04 Reliability | model/client errors surfaced in UI | simulated/remote tests | Implemented |
| NFR-05 Safety | validator + read-only connection | validator tests | Implemented |
| NFR-06 Observability | user-facing errors + `failures.md` | failure-memory tests | Partial: no structured application logger |
| NFR-07 Reproducibility | configurable model and docs | manual record of model revision needed | Partial |
| NFR-08 Privacy | synthetic data, no secrets in prompts | review `.env` handling | Implemented by default |
| NFR-09 Usability | Streamlit UI with SQL/results/warnings | manual UI test | Implemented |
| NFR-10 Honest evaluation | README documents held-out evaluation limits | create held-out benchmark manually | Partial: evaluation harness not included |
| Acceptance: read-only query, results, warnings, failure memory | app + modules above | local tests and live integration | Needs live remote model test |
