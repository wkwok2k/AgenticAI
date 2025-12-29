import os 
import csv 
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional 
from fastapi import FastAPI 
from mcp.server.Fastmcp import FastMCP 
logging.basicConfig(level=logging.INFO)

# Config
BASE_DIR = Path(__file__).parent
CSV_PATH_DEFAULT = str (BASE_DIR / "feeds" / "transactions. csv")
MAX_ROWS_DEFAULT = int(os.getenv("TXN_MAX_ROWS", "509")) # rows read from file
MAX_RETURN_DEFAULT = int(os.getenv("TXN_MAX_RETURN", "200")) # rows returned

print (CSV_PATH_DEFAULT)

app = FastAPI()
mcp = FastMCP("txn_csv_mcp")
mcp_app = mcp.sse_app()

print("MCP SSE app type:", type(mcp_app))
routes = getattr(mcp_app, "routes", None)
print("Has routes:", bool(routes))

if routes:
    for r in routes:
        print("MCP ROUTE:", getattr(r, "path", None), getattr(r, "methods", None), type(r).__name__)

app = FastAPI(redirect_slashes=False)
app.mount("/sse", mcp_app)
