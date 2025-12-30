import time
print("\n*** INITIALIZING ***")
start_time = time.time()
import json, re
from pathlib import Path
from typing import TypedDict, List, Any, Tuple
from langgraph.graph import StateGraph, END
from mcp_server.agents.schemas import HopBreak, TraceEvent
from mcp_server.agents.breaks_agent import explain_breaks
from mcp_server.agents.lineage_agent import explain_lineage
from mcp_server.agents.router_agent import route_question
from mcp_server.agents.general_agent import answer_general_question
from mcp_server.agents.session_types import SessionMemory
from mcp_server.tools.txn_mcp_client import fetch_transactions
from app.sql_client_async import get_top_breaks_sql
from utils.sqlprocessor import build_paths_from_rows, iter_hops_from_json_file
from utils.session_store import load_session, save_session
from fastapi.encoders import jsonable_encoder
from utils.logconfig import step_log

FEEDS_DIR = Path(__file__).resolve().parents[2] / "mcp_server" / "feeds"
DEFAULT_FEED_NAME = "2052a~Loans"
DEFAULT_AS_OF_DATE = "20251015"

# --- LangGraph state definition ---
class BreaksGraphState(TypedDict, total=False):
    user_question: str
    analysis: str
    selected_tool: str
    routing_reason: str
    breaks: List[HopBreak]
    lineage_paths: List[str]
    lineage_summary: str
    trace: List[TraceEvent]
    session: SessionMemory

# --------------- Nodes ---------------
def router_node(state: BreaksGraphState) -> BreaksGraphState:
    """ First agent: decide which tool/flow to use. """
    start_time = time.time()
    step_log( "AgenticAI - router_node: Start", 0)

    user_q = (state.get("user_question") or "").strip()
    trace = state.get("trace", [])

    turns = (state.get("session", {}).get("turns", []))
    recent = turns[-6:]
    recent_text = "\n".join([f"{t.get('role','')}: {t.get('content','')}" for t in recent])

    routing = route_question(user_q, recent_turns=recent_text)
    tool_name = routing.get("tool_name", "general_qa")
    if tool_name not in {"get_top_breaks", "general_qa", "get_lineage"}:
        tool_name = "general_qa"

    reason = routing.get("reason", "")

    trace.append(
        {
            "node": "Router Agent",
            "stage": "routing",
            "message": reason,
            "extra": {"selected_tool": tool_name, "message": str(routing)},
        }
    )

    elapsed = time.time() - start_time
    step_log(f"AgenticAI - router node: Completed", elapsed)

    return {
        **state,
        "selected_tool": tool_name,
        "routing_reason": reason,
        "trace": trace,
    }

async def breaks_node(state: BreaksGraphState) -> BreaksGraphState:
    """ Second agent: if tool is get_top_breaks, run the breaks analysis. """
    start_time = time.time()
    step_log("AgenticAI - breaks_node: Start", 0)

    user_q = state["user_question"]
    trace: List[TraceEvent] = state.get("trace", [])
    selected_tool = state.get("selected_tool", "get_top_breaks")

    session = state.get("session", {}) or {}
    session.setdefault("last_tool_outputs", {})

    lineage_paths: List[str] = []
    lineage_summary: str | None = None

    if selected_tool == "get_lineage":
        feed_name, as_of_date = _resolve_lineage_source(state, session)
        lineage_rows = _load_lineage_rows(feed_name, as_of_date)
        lineage_paths = [" >>> ".join(p) for p in build_paths_from_rows(lineage_rows)] if lineage_rows else []

        trace.append(
            {
                "node": "Breaks Analysis Agent",
                "stage": "tool_call",
                "message": "Fetched hop lineage rows for diagramming.",
                "extra": {
                    "feed_name": feed_name,
                    "as_of_date": as_of_date,
                    "row_count": len(lineage_rows),
                    "path_examples": lineage_paths[:3],
                },
            }
        )

        if lineage_rows:
            lineage_summary = explain_lineage(user_q, lineage_rows)
            trace.append(
                {
                    "node": "Breaks analysis agent",
                    "stage": "llm_analysis",
                    "message": "Generated lineage diagram and commentary.",
                    "extra": {
                        "preview": lineage_summary[:500] + ("..." if len(lineage_summary) > 500 else ""),
                        "path_examples": lineage_paths[:3],
                    },
                }
            )
        else:
            lineage_summary = "No lineage data was found for the requested feed/date."

        session["last_tool_outputs"]["lineage"] = {
            "paths": lineage_paths,
            "summary": lineage_summary,
        }

        elapsed = time.time() - start_time
        step_log(f"AgenticAI - breaks_node: Completed", elapsed)

        return {
            **state,
            "analysis": lineage_summary or "",
            "lineage_paths": lineage_paths,
            "lineage_summary": lineage_summary or "",
            "trace": trace,
            "session": session,
        }

    breaks: List[HopBreak] = await get_top_breaks_sql() or []  # ✅ await the async function

    hop_ids = [
        b.get("hop_id")
        for b in (breaks or [])
        if isinstance(b, dict) and b.get("hop_id")
    ]

    trace.append({
        "node": "breaks_node",
        "event": "fetched_breaks",
        "extra": {"hop_ids": hop_ids, "row_count": len(breaks or [])},
    })

    # (optional) store in session so you can see it in your logs
    session["last_tool_outputs"]["breaks"] = breaks

    # Debug trace entry so you can see what tool we think we have
    trace.append(
        {
            "node": "Breaks Analysis Agent",
            "stage": "tool_call",
            "message": "Fetch top breaks from MCP server.",
            "extra": {"hop_ids": hop_ids, "row_count": len(breaks or [])},
        }
    )

    if not breaks:
        analysis = "Connectivity to data store was successful, but no breaks data was returned."
        return {
            **state,
            "breaks": [],
            "analysis": analysis,
            "trace": trace,
            "session": session
        }

    # LLM explanation
    full_text = explain_breaks(user_q, breaks)
    explanation, commentary = _split_explanation_and_commentary(full_text)
    trace.append(
        {
            "node": "Breaks analysis agent",
            "stage": "llm_analysis",
            "message": commentary or "Generated natural-language explanation of hop-level breaks and highlights the drivers.",
            "extra": {
                "preview": explanation[:500] + ("..." if len(explanation) > 500 else "")
            },
        }
    )

    elapsed = time.time() - start_time
    step_log(f"AgenticAI - breaks_node: Completed", elapsed)

    return {
        **state,
        "breaks": breaks,
        "analysis": explanation,
        "trace": trace
    }

async def investigator_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = state.get("user_question", "")
    hop_id = extract_hop_id(user_q) or "16"  # fallback for test

    resp = await fetch_transactions(hop_id=hop_id, limit_return=20)
    rows = resp.get("rows", []) if isinstance(resp, dict) else []

    state["analysis"] = (
        f"MCP test OK\n"
        f"hop_id={hop_id}\n"
        f"rows_returned={len(rows)}"
    )

    session = state.get("session", {}) or {}
    session.setdefault("last_tool_outputs", {})
    session["last_tool_outputs"]["txn_details_test"] = resp
    state["session"] = session

    return state

def general_qa_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = state["user_question"]
    trace: List[TraceEvent] = state.get("trace", [])
    session = state.get("session", {}) or {}

    turns = session.get("turns", [])
    recent = turns[-6:]
    recent_text = "\n".join(
        [f"{t.get('role','')}: {t.get('content','')}"
         for t in recent if isinstance(t, dict)]
    ).strip()

    last_answer = session.get("last_answer", "")
    answer = answer_general_question(
        user_question=user_q,
        recent_turns=recent_text,
        last_answer=last_answer,
    )

    trace.append(
        {
            "node": "General Question Agent",
            "stage": "llm_analysis",
            "message": "I answered a general question directly.",
            "extra": {
                "last_answer_preview": last_answer[:500] + ("..." if len(last_answer) > 500 else ""),
                "recent_turns_preview": recent_text[:500] + ("..." if len(recent_text) > 500 else ""),
                "my_answer_preview": answer[:500] + ("..." if len(answer) > 500 else "")
            },
        }
    )

    return {
        **state,
        "analysis": answer,
        "trace": trace,
        "session": session,
    }

# ------------- Graph Wiring --------------
def build_breaks_poc_graph():
    graph = StateGraph(BreaksGraphState)

    graph.add_node("router", router_node)
    graph.add_node("breaks_analysis", breaks_node)
    graph.add_node("general_qa", general_qa_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", _route_next, {
        "breaks_analysis": "breaks_analysis",
        "general_qa": "general_qa",
    })

    graph.add_edge("breaks_analysis", END)
    graph.add_edge("general_qa", END)

    return graph.compile()

# ---------------- Helper -----------------
async def handle_user_turn(user_id: str, session_id: str, user_question: str) -> BreaksGraphState:
    mem = load_session(user_id, session_id)

    # Safeguards for brand-new / older sessions missing keys
    mem.setdefault("turns", [])
    mem.setdefault("last_tool_outputs", {})
    mem.setdefault("last_answer", "")
    mem.setdefault("last_agent", "")
    user_question = (user_question or "").strip()

    # Add new user turn
    mem["turns"].append({"role": "user", "content": user_question, "meta": {}})

    # Run graph with session injected
    app = build_breaks_poc_graph()
    state: BreaksGraphState = await app.ainvoke({"user_question": user_question, "trace": [], "session": mem})

    # Persist assistant answer to memory
    assistant_answer = (state.get("analysis") or "").strip()

    # Allow nodes to modify memory; still ensure required keys exist
    state_session = state.get("session") or {}
    mem.update(state_session)
    mem.setdefault("turns", [])
    mem.setdefault("last_tool_outputs", {})

    mem["turns"].append(
        {
            "role": "assistant",
            "content": assistant_answer,
            "meta": {"agent": state.get("selected_tool", "")},
        }
    )
    mem["last_answer"] = assistant_answer
    mem["last_agent"] = state.get("selected_tool") or mem.get("last_agent", "")
    if "breaks" in state and state["breaks"] is not None:
        mem["last_tool_outputs"]["breaks"] = _to_jsonable(state["breaks"])
    if "lineage_paths" in state and state["lineage_paths"] is not None:
        mem["last_tool_outputs"]["lineage_paths"] = _to_jsonable(state["lineage_paths"])
    if "lineage_summary" in state and state["lineage_summary"]:
        mem["last_tool_outputs"]["lineage_summary"] = state["lineage_summary"]

    # If you store anything else later (lineage diagrams, exposures, etc...), run it through _to_jsonable as well.
    # Save session (must be JSON serializable)
    save_session(_to_jsonable(mem))

    # Return updated state - keep session json-safe too
    state["session"] = mem

    # If your FastAPI endpoint returns state directly, this prevents serialization issues:
    return _to_jsonable(state)

def extract_hop_id(text: str) -> str | None:
    # very simple heuristic; adjust as needed
    m = re.search(r"\bHOP[_-]?\w+\b", text.upper())
    return m.group(0) if m else None

def _split_explanation_and_commentary(text: str) -> tuple[str, str]:
    explanation = text
    commentary = ""
    if "AgentCommentary:" in text:
        head, _, tail = text.partition("AgentCommentary:")
        explanation = head.replace("Explanation", "").strip()
        commentary = tail.strip()
    return explanation, commentary

def _route_next(state: BreaksGraphState) -> str:
    return "breaks_analysis" if state.get("selected_tool") in {"get_top_breaks", "get_lineage"} else "general_qa"

def _to_jsonable(obj: Any) -> Any:
    return jsonable_encoder(obj)

def _resolve_lineage_source(state: BreaksGraphState, session: SessionMemory) -> Tuple[str, str]:
    """
    Determine which feed/as_of_date to use for lineage. Defaults fall back to a sample feed file.
    """
    feed_name = state.get("feed_name") or session.get("feed_name") or DEFAULT_FEED_NAME
    as_of_date = state.get("recon_run_date") or session.get("recon_run_date") or DEFAULT_AS_OF_DATE
    return str(feed_name), str(as_of_date)

def _load_lineage_rows(feed_name: str, as_of_date: str) -> List[dict]:
    file_path = FEEDS_DIR / f"hops_{feed_name}_{as_of_date}.json"
    if not file_path.exists():
        step_log(f"Lineage file not found: {file_path}", 0)
        return []

    try:
        return list(iter_hops_from_json_file(str(file_path)))
    except Exception as exc:  # noqa: BLE001
        step_log(f"Failed to read lineage file {file_path}: {exc}", 0)
        return []

# ----------- Non-streaming runner (optional) ----------
def run_breaks_poc(user_question: str) -> BreaksGraphState:
    app = build_breaks_poc_graph()
    final_state = app.invoke({"user_question": user_question, "trace": []})
    return final_state

async def run_breaks_poc_async(user_question: str) -> BreaksGraphState:
    app = build_breaks_poc_graph()
    final_state = await app.ainvoke({"user_question": user_question, "trace": []})
    return final_state

# --------------- CLI ---------------
if __name__ == "__main__":
    q = "Show me the top 2 hop-level breaks and explain what the stats are telling us."
    elapsed = time.time() - start_time
    step_log("AgenticAI INIT: Start", 0)
    step_log("AgenticAI - INIT: Completed", elapsed)

    import asyncio
    result = asyncio.run(run_breaks_poc_async(q))

    print("\n=== ANALYSIS (FINAL) ===")
    print(result.get("analysis", "[no analysis produced]"))
    print("=== ANALYSIS (COMPLETED) ===")
