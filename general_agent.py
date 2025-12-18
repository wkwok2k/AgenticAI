from mcp_server.llm.adapter import get_vertex_object

_vertex = get_vertex_object()

def answer_general_question(user_question: str) -> str:
    user_question = (user_question or "").strip()
    if not user_question:
        return "I didn’t receive a question. Please type a question and try again."

    return _vertex.generate_from_config(
        agent_config_name="general_agent",
        template_vars={"user_question": user_question},
        json_mode=False,
    )
