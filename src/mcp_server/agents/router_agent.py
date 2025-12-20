from mcp_server.llm.adapter import get_vertex_object

_vertex = get_vertex_object()

def route_question(user_question: str, recent_turns: str = "") -> dict:
    """Use router_agent.yml to decide which tool to use.
       Return a dict like ("tool_name", "get_top_breaks", "reason", "..."}"""
    resp = _vertex.generate_from_config(
        agent_config_name="router _agent",
        template_vars={
            "user _question": user_question,
            "recent_turns": recent_turns,
        },
        json_mode=True,
    )

    return resp