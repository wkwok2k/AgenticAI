import json
import os
from pathlib import Path
from typing import Optional
from mcp_server.agents.session_types import SessionMemory

SESS_DIR = Path("logs/sessions")

def load_session(user_id: str, session_id: str) -> SessionMemory:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESS_DIR / f"{user_id}__{session_id}.json"
    if not path.exists():
        return {"user_id": user_id, "session_id": session_id, "turns": [], "last_tool_outputs": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_session(mem: SessionMemory) -> None:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESS_DIR / f"{mem['user_id']}__{mem['session_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)
