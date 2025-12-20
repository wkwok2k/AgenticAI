from typing import Any
from fastapi.encoders import jsonable_encoder

from mcp_server.utils.session_store import load_session, save_session
from mcp_server.agents.graph_breaks_poc import build_breaks_poc_graph
from mcp_server.agents.schemas import BreaksGraphState


def _to_jsonable(obj: Any) -> Any:
    """
    Converts dataclasses / Pydantic models / custom objects into JSON-safe
    dict/list/primitive structures.
    """
    return jsonable_encoder(obj)


def handle_user_turn(user_id: str, session_id: str, user_question: str) -> BreaksGraphState:
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
    state: BreaksGraphState = app.invoke({"user_question": user_question, "trace": [], "session": mem})

    # Persist assistant answer to memory
    assistant_answer = (state.get("analysis") or "").strip()

    # Allow nodes to modify memory; still ensure required keys exist
    mem = state.get("session") or mem
    mem.setdefault("turns", [])
    mem.setdefault("last_tool_outputs", {})

    mem["turns"].append({
        "role": "assistant",
        "content": assistant_answer,
        "meta": {"agent": state.get("selected_tool", "")},
    })
    mem["last_answer"] = assistant_answer
    mem["last_agent"] = state.get("selected_tool") or mem.get("last_agent", "")

    # Persist tool outputs (optional) — MUST be JSON-safe
    if "breaks" in state and state["breaks"] is not None:
        mem["last_tool_outputs"]["breaks"] = _to_jsonable(state["breaks"])

    # If you store anything else later (lineage diagrams, exposures, etc.),
    # run it through _to_jsonable as well.

    # Save session (must be JSON serializable)
    save_session(_to_jsonable(mem))

    # Return updated state — keep session json-safe too
    state["session"] = mem

    # If your FastAPI endpoint returns state directly, this prevents serialization issues:
    return _to_jsonable(state)
