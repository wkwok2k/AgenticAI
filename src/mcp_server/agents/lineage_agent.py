import json
from typing import Iterable, Mapping

from mcp_server.llm.adapter import get_vertex_object

_vertex = get_vertex_object()


def explain_lineage(user_question: str, lineage_rows: Iterable[Mapping[str, str]]) -> str:
    """
    Generate a lineage diagram and commentary from hop-level lineage rows.
    lineage_rows should be an iterable of dicts containing prev_hop_id, hop_id, and next_hop_id.
    """
    lineage_json = json.dumps(list(lineage_rows), indent=2, default=str)

    return _vertex.generate_from_config(
        agent_config_name="breaks_agent_lineage",
        template_vars={
            "user_question": user_question,
            "lineage_json": lineage_json,
        },
        json_mode=False,
    )
