import asyncio, json
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
    params = _drop_nones({
        "hop_id": hop_id,
        "recon_run_date": recon_run_date,
        "limit_return": int(limit_return),
    })

    async with sse_client(MCP_SSE_URL) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("get_transactions", params)

            payload = extract_json_from_mcp_result(result)
            return payload

def extract_json_from_mcp_result(result) -> Dict[str, Any]:
    """
    Handles multiple MCP client versions:
    - JSON blocks: block.type == "json" and block.json exists
    - Text blocks: block.type == "text" with JSON string in block.text
    - Fallback: stringification
    """
    for block in getattr(result, "content", []) or []:
        btype = getattr(block, "type", None)

        # Case 1: proper JSON block
        if btype == "json" and hasattr(block, "json"):
            return block.json

        # Case 2: text block containing JSON
        if btype == "text":
            text = getattr(block, "text", None)
            if isinstance(text, str):
                text = text.strip()
                # try parse JSON
                if text.startswith("{") or text.startswith("["):
                    try:
                        return json.loads(text)
                    except Exception:
                        pass

        # Some variants store JSON as `data` or `value`
        for attr in ("data", "value"):
            v = getattr(block, attr, None)
            if isinstance(v, (dict, list)):
                return v
            if isinstance(v, str):
                vv = v.strip()
                if vv.startswith("{") or vv.startswith("["):
                    try:
                        return json.loads(vv)
                    except Exception:
                        pass

    return {"rows": [], "meta": {"note": "No JSON-like content returned"}, "isError": True}

async def _cli():
    # Change these to values you know exist in your CSV
    hop_id = "HOP_001"
    recon_run_date = None  # or "2024-12-31"

    resp = await fetch_transactions(
        hop_id=hop_id,
        recon_run_date=recon_run_date,
        limit_return=5,
    )

    rows = resp.get("rows", []) if isinstance(resp, dict) else []
    print("isError:", resp.get("isError"))
    print("rows_returned:", len(rows))
    print("meta:", json.dumps(resp.get("meta", {}), indent=2))

    print("\nPreview (first 5 rows):")
    print(json.dumps(rows[:5], indent=2))

if __name__ == "__main__":
    asyncio.run(_cli())