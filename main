import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from mcp_server.agents.handle_turn import handle_user_turn  # wherever yours is

app = FastAPI()

class AgentRequest(BaseModel):
    user_id: str
    session_id: str
    user_question: str

@app.post("/chat")
def chat(req: AgentRequest):
    try:
        state = handle_user_turn(req.user_id, req.session_id, req.user_question)
        return state
    except Exception as e:
        tb = traceback.format_exc()
        print("=== SERVER ERROR ===")
        print(tb)
        # return a readable error to the client while you debug
        raise HTTPException(status_code=500, detail=str(e))
