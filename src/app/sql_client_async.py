import os, requests
from typing import Any, Dict, List
from mcp_server.tools.my_mcp import McpProcessor
from utils.sqlprocessor import generate_sql
from utils.yaml_loader import clean_sql, SqlCleanMode

MCP_SQL_URL = os.getenv("MCP_SQL_URL", "http://127.0.0.1:7000/sse")

async def get_top_breaks_sql() -> List[Dict[str, Any]]:
    YAML = "sql_mock_top_exposures"
    result = await generate_sql(YAML, {})
    query = clean_sql(result, mode=SqlCleanMode.CONDENSE)
    print(query)

    resp = ""

    try:
        proc = McpProcessor()
        resp = await proc.run_query(query)
    except Exception as e:
        print(f"Error running MCP query: {e}")
        return []

    resp = requests.post(MCP_SQL_URL, json=query, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["rows"]