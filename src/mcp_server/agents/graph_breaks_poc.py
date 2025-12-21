import time
print("\n*** INITIALIZING ***")
start_time = time.time()

from typing import TypedDict, List, Any
from langgraph.graph import StateGraph, END
from mcp_server.agents.schemas import HopBreak, TraceEvent
from mcp_server.agents.breaks_agent import explain_breaks
from mcp_server.agents.router_agent import route_question
from mcp_server.agents.general_agent import answer_general_question
from mcp_server.agents.session_types import SessionMemory
from app.sql_client_async import get_top_breaks_sql
from utils.session_store import load_session, save_session
from fastapi.encoders import jsonable_encoder
from utils.logconfig import step_log

# --- LangGraph state definition ---
class BreaksGraphState(TypedDict, total=False):
    user_question: str
    analysis: str
    selected_tool: str
    routing_reason: str
    breaks: List[HopBreak]
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
    tool_name = routing.get ("tool _name", "general_qa")
    reason = routing.get ("reason", "")

    trace.append(
        {
            "node": "Router Agent",
            "stage": "routing",
            "message": reason,
            "extra": {"selected_tool": tool_name},
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
    session = state.get("session", ())

    breaks: List[HopBreak] = await get_top_breaks_sql()  # ✅ await the async function
    print(breaks)

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
    session.setdefault("last_tool_outputs", {})
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

def general_qa_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = state["user_question"]
    trace: List[TraceEvent] = state.get("trace", [])
    session = state.get("session", ())

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
    mem.setdefault("last_tool_output", {})

    mem["turns"].append(
        {
            "role": "assistant",
            "content": assistant_answer,
            "meta": {"agent": state.get("selected_tool", "")},
        }
    )
    mem["last_answer"] = assistant_answer
    mem["last_agent"] = state.get("selected_tool") or mem.get("last_agent", "")

    # If you store anything else later (lineage diagrams, exposures, etc...), run it through _to_jsonable as well.
    # Save session (must be JSON serializable)
    save_session(_to_jsonable(mem))

    # Return updated state - keep session json-safe too
    state["session"] = mem

    # If your FastAPI endpoint returns state directly, this prevents serialization issues:
    return _to_jsonable(state)

def _split_explanation_and_commentary(text: str) -> tuple[str, str]:
    explanation = text
    commentary = ""
    if "AgentCommentary:" in text:
        head, _, tail = text.partition("AgentCommentary:")
        explanation = head.replace("Explanation", "").strip()
        commentary = tail.strip()
    return explanation, commentary

def _route_next(state: BreaksGraphState) -> str:
    return "breaks_analysis" if state.get("selected_tool") == "get_top_breaks" else "general_qa"

def _to_jsonable(obj: Any) -> Any:
    return jsonable_encoder(obj)

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
