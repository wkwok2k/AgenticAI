from mcp_server.utils.session_store import load_session, save_session

def handle_user_turn(user_id: str, session_id: str, user_question: str) -> BreaksGraphState:
    mem = load_session(user_id, session_id)

    # Add new user turn
    mem["turns"].append({"role": "user", "content": user_question, "meta": {}})

    # Run graph with session injected
    app = build_breaks_poc_graph()
    state = app.invoke({"user_question": user_question, "trace": [], "session": mem})

    # Persist assistant answer to memory
    assistant_answer = state.get("analysis", "")
    mem = state.get("session", mem)  # allow nodes to modify memory
    mem["turns"].append({"role": "assistant", "content": assistant_answer, "meta": {
        "agent": state.get("selected_tool", ""),
    }})
    mem["last_answer"] = assistant_answer
    mem["last_agent"] = state.get("selected_tool", mem.get("last_agent"))

    # Persist tool outputs (optional)
    if "breaks" in state:
        mem.setdefault("last_tool_outputs", {})["breaks"] = state["breaks"]

    save_session(mem)

    # Return updated state
    state["session"] = mem
    return state
