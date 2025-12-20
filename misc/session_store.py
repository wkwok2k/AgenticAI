import json
import os
from pathlib import Path
from typing import Optional
from mcp_server.agents.session_types import SessionMemory

SESS_DIR = Path("logs/sessions")

import json
from pathlib import Path
from typing import Any

SESS_DIR = Path("logs/sessions")

def load_session(user_id: str, session_id: str) -> dict[str, Any]:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESS_DIR / f"{user_id}__{session_id}.json"

    # Default fresh session
    fresh_session = {
        "user_id": user_id,
        "session_id": session_id,
        "turns": [],
        "last_tool_outputs": {},
        "last_answer": "",
        "last_agent": "",
    }

    if not path.exists():
        return fresh_session

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return fresh_session
            # Ensure required keys always exist
            data.setdefault("turns", [])
            data.setdefault("last_tool_outputs", {})
            data.setdefault("last_answer", "")
            data.setdefault("last_agent", "")
            return data

    except json.JSONDecodeError:
        # Corrupted session file — recover gracefully
        print(f"[SessionStore] Corrupted session file detected: {path}. Resetting session.")
        return fresh_session

    except Exception as e:
        # Any other unexpected issue
        print(f"[SessionStore] Failed to load session {path}: {e}")
        return fresh_session

def save_session(mem: SessionMemory) -> None:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESS_DIR / f"{mem['user_id']}__{mem['session_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2, ensure_ascii=False)
