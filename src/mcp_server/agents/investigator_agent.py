import json
from typing import Any, Dict, List

from mcp_server.llm.adapter import get_vertex_object

_vertex = get_vertex_object()

def format_transactions_markdown_table(
    user_question: str,
    hop_id: str,
    rows: List[Dict[str, Any]],
    max_rows: int = 5,
) -> str:
    """
    Use investigator_agent.yml to convert transaction rows into a Markdown table for Streamlit.
    """
    user_question = (user_question or "").strip()
    hop_id = (hop_id or "").strip()

    # Keep payload small for context limits
    slim_rows = rows[:max_rows]
    rows_json = json.dumps(slim_rows, indent=2, default=str)

    return _vertex.generate_from_config(
        agent_config_name="investigator_agent",
        template_vars={
            "user_question": user_question,
            "hop_id": hop_id,
            "rows_json": rows_json,
            "rows_returned": str(len(rows)),
            "rows_shown": str(len(slim_rows)),
        },
        json_mode=False,
    )
