import traceback
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from mcp_server.agents.graph_breaks_poc import handle_user_turn

app = FastAPI()

class AgentRequest(BaseModel):
    user_id: str
    session_id: str
    user_question: str

@app.post("/chat")
async def chat(req: AgentRequest):
    try:
        state = await handle_user_turn(req.user_id, req.session_id, req.user_question)
        return jsonable_encoder(state)
    except Exception as e:
        tb = traceback.format_exc()
        print("=== SERVER ERROR ===")
        print(tb)
        raise HTTPException(status_code=500, detail=str(e))
