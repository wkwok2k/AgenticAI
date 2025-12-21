import logging
import json
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("starburst.log"),
        logging.StreamHandler()
    ]
)

app = FastAPI()
mcp = FastMCP("starburst")
app.mount("/", mcp.sse_app())

async def invoke_api(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """ Make a request to the NWS API with proper error handling. """
    # "sqlQuery": "select • from tolvesa_managed.stream where active_flag-'y'".
    headers = {"Content-Type", "application/json"}
    logging.info("calling API tool..")
    logging.info("url: %s", url)
    logging.info("headers: %s", headers)
    logging.info("payload: %s",json.dumps(payload, indent=2))

    async with httpx.AsyncClient(verify=False) as client:   # Disable SSL verification
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=90.0)
            # This will raise 4xx/5xx error
            response.raise_for_status()
            json_response = response.json()
            logging.info("Response JSON: %s", json.dumps(json_response, indent=2))

            return json_response
        except httpx.HTTPStatusError as e:
            logging.error("HTTP error from API: status-%s, response.body=%s", e.response.status_code, e.response.text)
            raise

        except Exception as e:
            logging.info("Unexpected exception: %s",e)
            return None

@mcp.tool()
async def run_query(query: str) -> dict[str, Any]:
    url = f"https://abc/flow/api/starburst"
    payload = {
        "environment": "PROD",
        "databaseFetchSize": "50000",
        "dataSource": "starburst",
        "catalog": "openpus",
        "schema": "managed",
        "sqlQuery": query,
    }

    try:
        data = await invoke_api(url, payload)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text or ""
        snippet = body[:500]

        logging.error("API call failed with status %s and body: %s",status, body)
        return {"structuredContent": {"result": {"error": f"API call failed with status: {status}", "details": snippet}}, "meta": None, "IsError": True}
    except Exception as e:
        logging.error("Unexpected error in run_query: %s", e)
        return {"structuredContent": {"result": {"error": "Unexpected error in MCP Tool.", "details": repr(e)}}, "meta": None, "isError": True}

    logging.info("Data from tool: %s", data)

    if data in (None, [], {}):
        logging.error("No data returned from API.")
        return {"structuredContent": {"result": {"error": "No data returned from API. "}}, "meta": None, "isError": False}

    try:
        # Serialize the data to ensure its valid JSON
        valid_json = json.dumps(data)
        logging.info("Valid JSON: %s", (json.dumps(data, indent=4)))
        return json.loads(valid_json) # Convert back to a dictionary
    except (TypeError, ValueError) as e:
        logging.error("Failed to serialize data: %s",e)
        return {"structuredContent": {"result": {"error": "Data is not JSON serializable."}}, "meta": None, "isError": True}


if __name__ == "__main__":
    # uvicorn. run ("mcp_server.server:mcp.app", host="127.0.0.1", port=7000, reload-True)
    mcp.run(transport='sse')