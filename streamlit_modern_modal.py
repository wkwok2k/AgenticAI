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

AGENT_META = {
    "router agent": {"label": "Router Agent", "icon": "🧭"},
    "breaks analysis agent": {"label": "Breaks Analysis Agent", "icon": "📊"},
    "breaks node": {"label": "Breaks Node", "icon": "🛠️"},
    "general question agent": {"label": "General Question Agent", "icon": "💡"},
}

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


def normalize_agent_key(key: str | None) -> str:
    """Normalize agent identifiers for consistent display."""
    return (key or "").strip().lower()


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
    col_main, col_side = st.columns([3, 1])

    with col_main:
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

    data = st.session_state.get("analysis_result", {}) or {}

    with col_side:
        st.subheader("Agents Reasoning Trace")
        trace = data.get("trace", []) or []

        if not trace:
            st.caption("No trace available.")
        else:
            # Identify agents from trace in order of appearance
            agents_in_order: list[str] = []
            seen = set()
            for ev in trace:
                k = normalize_agent_key(ev.get("node", ""))
                if k and k not in seen:
                    seen.add(k)
                    agents_in_order.append(k)

            if agents_in_order:
                # Initialize selection once, then let the widget own it
                if "selected_agent" not in st.session_state or st.session_state["selected_agent"] not in agents_in_order:
                    st.session_state["selected_agent"] = agents_in_order[0]

                def agent_label(agent_key: str) -> str:
                    meta = AGENT_META.get(agent_key, {"label": agent_key, "icon": "•"})
                    return f"{meta['icon']} {meta['label']}"

                # IMPORTANT: stable key + no forced index
                selected_agent = st.radio(
                    "Select Agent",
                    options=agents_in_order,
                    format_func=agent_label,
                    key="selected_agent_radio",  # stable widget identity
                )

                # sync selection into your canonical state
                st.session_state["selected_agent"] = selected_agent

                st.markdown("---")

                # Selected agent detail panel
                sel_agent = selected_agent
                if sel_agent:
                    meta = AGENT_META.get(sel_agent, {"label": sel_agent, "icon": "•"})
                    st.markdown(f"**{meta['icon']} {meta['label']} - reasoning trace**")

                    agent_events = [
                        ev for ev in trace
                        if normalize_agent_key(ev.get("node", "")) == sel_agent
                    ]

                    if not agent_events:
                        st.caption("No events for this agent.")
                    else:
                        for i, ev in enumerate(agent_events, start=1):
                            st.markdown(
                                f"""
                            <div style="
                                background-color: #FAFAFA;
                                border-radius: 8px;
                                padding: 8px 10px;
                                margin-bottom: 6px;
                                border: 1px solid #E0E0E0;">
                                <div style="font-size:0.8rem;color:#666;">
                                    Step {i} • Stage: {ev.get('stage', '')}
                                </div>
                                <div style="margin-top:4px;">
                                    {ev.get('message', '')}
                                </div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )
                else:
                    st.caption("Select an agent to see its reasoning.")
