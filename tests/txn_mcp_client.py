# txn_mcp_client.py
import asyncio
from typing import Any, Dict, Optional

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Use your working SSE endpoint
MCP_SSE_URL = "http://127.0.0.1:7000/sse/sse"


def _drop_nones(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


async def fetch_transactions(
    hop_id: Optional[str] = None,
    recon_run_date: Optional[str] = None,
    limit_return: int = 50,
) -> Dict[str, Any]:
    """
    Calls MCP tool get_transactions and returns a dict like:
      {"rows": [...], "meta": {...}, "isError": False}
    """
    async with sse_client(MCP_SSE_URL) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            params = _drop_nones({
                "hop_id": hop_id,
                "recon_run_date": recon_run_date,
                "limit_return": int(limit_return),
            })

            result = await session.call_tool("get_transactions", params)

            for block in result.content:
                if getattr(block, "type", None) == "json":
                    return block.json

            # fallback: return something structured even if not json
            return {
                "rows": [],
                "meta": {"note": "No JSON content returned"},
                "isError": True,
            }

