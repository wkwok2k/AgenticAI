import json
from typing import List
from mcp_server.agents.schemas import HopBreak
from mcp_server.llm.adapter import get_vertex_object

_vertex = get_vertex_object()

def explain_breaks(user_question: str, breaks: List[HopBreak]) -> str:
    """
    Use the generic VertexGenAI adapter + breaks_agent.yml
    to generate an explanation of the hop-level breaks.
    """
    breaks_json = json.dumps([vars(b) for b in breaks], indent=2, default=str)

    return _vertex.generate_from_config(
        agent_config_name="breaks_agent",
        template_vars={
            "user_question": user_question,
            "breaks_json": breaks_json
        },
        json_mode=False,
    )