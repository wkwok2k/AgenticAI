# src/mcp_server/utils/sql_client.py
import os
import requests
from typing import Any, Dict, List

MCP_SQL_URL = os.getenv("MCP_SQL_URL", "http://127.0.0.1:9000/sql")

def get_top_breaks_sql(topic: str, run_date: str, top_n: int = 5) -> List[Dict[str, Any]]:
    payload = {
        "template": "get_topx_breaks",   # name known by MCP sql server
        "params": {"topic": topic, "run_date": run_date, "top_n": top_n},
    }
    resp = requests.post(MCP_SQL_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # Expecting list[dict] rows
    return data["rows"]
