#streamlit run app.py

import streamlit as st
import pandas as pd
from sql_dost.engine import answer_question
from sql_dost.config import settings
from sql_dost.model_client import ModelError
from sql_dost.validator import SQLValidationError

st.set_page_config(page_title="SQL_dost", page_icon="🧑‍💻", layout="wide")
st.title("SQL_dost — Natural-Language to SQL Assistant")
st.caption("Ask questions about the synthetic college database. Generated SQL is validated before read-only execution.")

with st.sidebar:
    st.subheader("Connection")
    st.write("Remote endpoint:", settings.remote_generate_url or "Not configured")
    st.write("Database:", settings.database_path)
    st.write("Inference stays remote; no local LLM is loaded.")
    st.warning("Use synthetic/demo records by default. Do not connect sensitive institutional data without a security review.")
    st.subheader("Example questions")
    for q in [
        "List all students and their department names.",
        "Show students who scored above 80, with course names and scores.",
        "What is the average score for each course?",
        "Count students in each department.",
    ]:
        st.code(q, language=None)

question = st.text_area("Your question", placeholder="e.g. Show students who scored above 80", height=100)
if st.button("Generate SQL and run safely", type="primary", disabled=not question.strip()):
    with st.spinner("Contacting the configured remote model, validating SQL, and querying SQLite…"):
        try:
            response = answer_question(question)
            if response["status"] == "clarification":
                st.info(response["question"])
                if response.get("explanation"):
                    st.write(response["explanation"])
            elif response.get("response_type") == "schema":
                if response.get("explanation"):
                    st.write(response["explanation"])
                if response.get("sql"):
                    st.subheader("SQL Query")
                    st.code(response["sql"], language="sql")
                st.subheader("Database Schema")
                st.code(response["schema"], language="text")
            elif response.get("response_type") == "policy" or response.get("status") == "rejected":
                st.warning(response.get("explanation", "Request rejected by policy."))
            elif response.get("response_type") == "message" or response.get("status") == "unsupported":
                st.info(response.get("explanation", "I can answer questions about the configured database and its records."))
            else:
                st.subheader("Generated SQL")
                st.code(response["sql"], language="sql")
                if response.get("explanation"): st.write(response["explanation"])
                for warning in response.get("warnings", []): st.warning(warning)
                result = response["result"]
                st.subheader(f"Results ({result['row_count']}{'+' if result['truncated'] else ''} rows)")
                st.dataframe(pd.DataFrame(result["rows"], columns=result["columns"]), use_container_width=True)
                st.caption("SQL passed configured policy checks and executed through a read-only SQLite connection. Semantic correctness is not guaranteed.")
                with st.expander("Was this answer correct?"):
                    feedback = st.radio("Feedback", ["Not provided", "Correct", "Incorrect"], horizontal=True, key="feedback")
                    details = st.text_area("Expected behavior / correction (optional)", key="feedback_details")
                    if st.button("Save feedback"):
                        from sql_dost.failure_memory import append_failure
                        if feedback == "Incorrect":
                            append_failure(question, response["sql"], "User-reported error",
                                           details or "User marked answer incorrect", "User feedback",
                                           verification="User-reported; not independently verified")
                            st.success("Feedback appended to failures.md as unverified user feedback.")
                        elif feedback == "Correct":
                            st.success("Thanks. This prototype does not yet maintain a separate verified-feedback database.")
                        else:
                            st.info("Choose Correct or Incorrect before saving.")
        except (ModelError, SQLValidationError, ValueError, FileNotFoundError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Unexpected application error: {type(exc).__name__}: {exc}")
            st.caption("Check the terminal logs. Secrets and private records should not be copied into diagnostics.")

st.divider()
st.caption("SQL_dost v1.0 • Streamlit • SQLite • Remote Hugging Face inference")
