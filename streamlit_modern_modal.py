"""
Streamlit UI for the Breaks Analysis Agentic POC with a canned-questions drop-down.

The drop-down sits above the text area, aligned to the right, and selecting a
question populates the text area automatically.
"""

import threading
import time
from typing import Dict, Optional

import pandas as pd
import requests
import streamlit as st

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="Breaks Analysis - Agentic POC", layout="wide")
st.markdown(
    """
<style>
div.block-container {
    padding-top: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)
st.title("Breaks Analysis - Agentic AI MCP")

CANNED_QUESTIONS = [
    "Show me the top hop-level breaks and explain what they mean.",
    "Summarize break severities by owner and priority.",
    "List the datasets impacted by the latest hop-level anomalies.",
    "What are the most recent schema changes affecting the pipeline?",
]

# --- State ---
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "selected_agent" not in st.session_state:
    st.session_state["selected_agent"] = None
if "user_question" not in st.session_state:
    st.session_state["user_question"] = CANNED_QUESTIONS[0]


def _run_request(api_url: str, payload: Dict, result_holder: Dict) -> None:
    """Execute the API request and store the response or error."""
    try:
        resp = requests.post(api_url, json=payload, timeout=120)
        resp.raise_for_status()
        result_holder["response"] = resp.json()
    except Exception as exc:  # noqa: BLE001
        result_holder["error"] = str(exc)


def handle_canned_question_selection() -> None:
    """Update the text area when the drop-down selection changes."""
    selected = st.session_state.get("selected_canned_question")
    if selected and selected != "Select a question…":
        st.session_state["user_question"] = selected


# --- Input row with right-aligned drop-down on the same line as the label ---
with st.container():
    label_col, dropdown_col = st.columns([4, 1])
    with label_col:
        st.markdown("**Question**")
    with dropdown_col:
        st.selectbox(
            "Suggested questions",
            options=["Select a question…", *CANNED_QUESTIONS],
            key="selected_canned_question",
            on_change=handle_canned_question_selection,
        )

user_question = st.text_area(
    "Question",
    height=100,
    key="user_question",
    label_visibility="collapsed",
)

# --- Actions ---
if st.button("Run analysis"):
    if not user_question.strip():
        st.warning("Please enter a question first.")
    else:
        payload = {
            "user_id": st.session_state.get("user_id", "test_user"),
            "session_id": st.session_state.get("session_id", "test_session"),
            "user_question": user_question,
        }

        result_holder: Dict[str, Optional[Dict]] = {}
        t = threading.Thread(
            target=_run_request, args=(API_URL, payload, result_holder), daemon=True
        )

        elapsed_ph = st.empty()
        start = time.perf_counter()
        t.start()

        while t.is_alive():
            elapsed = time.perf_counter() - start
            elapsed_ph.markdown(f"⏱️ Elapsed time: {elapsed:.1f}s")
            time.sleep(0.5)

        elapsed_ph.empty()

        if "error" in result_holder:
            st.error(f"Request failed: {result_holder['error']}")
        else:
            st.session_state["analysis_result"] = result_holder.get("response")

# --- Output ---
if st.session_state.get("analysis_result"):
    st.subheader("Analysis Result")
    result = st.session_state["analysis_result"]
    if isinstance(result, dict) and "data" in result:
        try:
            df = pd.DataFrame(result["data"])
            st.dataframe(df, use_container_width=True)
        except Exception:
            st.json(result)
    else:
        st.json(result)
