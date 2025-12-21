import asyncio
import traceback
from typing import Any, Dict, List

from mcp_server.tools.my_mcp import McpProcessor
from utils.sqlprocessor import generate_sql
from utils.yaml_loader import clean_sql, SqlCleanMode

async def get_top_breaks_sql() -> List[Dict[str, Any]]:
    YAML = "sql_mock_top_exposures"
    result = await generate_sql(YAML, {})
    query = clean_sql(result, mode=SqlCleanMode.CONDENSE)
    print(query)

    try:
        proc = McpProcessor()

        # ✅ If McpProcessor() returned a coroutine, await it
        if asyncio.iscoroutine(proc):
            proc = await proc

        resp = await proc.run_query(query)
        print(query)
        print("MCP raw response type:", type(resp))
        print("MCP raw response:", resp)
    except Exception as e:
        print(f"Error running MCP query: {e}")
        print(traceback.format_exc())
        return []

    # IMPORTANT: remove the requests.post(/sse) path.
    # Return whatever run_query gives you (normalize if needed)
    # if isinstance(resp, dict) and isinstance(resp.get("rows"), list):
    #     return resp["rows"]
    # if isinstance(resp, list):
    #     return resp
    # return []
