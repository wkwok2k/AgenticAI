from mcp import ClientSession
from mcp.client.sse import sse_client
from utils.logconfig import step_log

class McpProcessor:
    def __init__(self):
        pass

    @staticmethod
    async def run_query(query):
        try:
            async with sse_client(url="http://localhost:7000/query") as streams:
                try:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool("run_query", {"query": str(query)})
                        return result
                except Exception as e:
                    step_log(f"Error running query: {e}")
                    return {"error": str(e)}
        except Exception as e:
            step_log("Mcp server not reachable.  Please start the MCP server or check network issue.")
            return {"error": str(e)}