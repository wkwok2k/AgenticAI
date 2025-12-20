from typing import TypedDict, List, Dict, Any

class Turn(TypedDict):
    role: str   #"user" or "agent"
    content: str
    meta: Dict[str, Any] # Additional info about the turn ("agent, "...", "tool": "...", ...)

class SessionMemory(TypedDict, total=False):
    session_id: str
    user_id: str
    turns: List[Turn]   # Rolling conversation transcript
    last_answer: str    # Last assistant answer shown to the user
    last_agent: str     # Which agent answered last
    last_tool_outputs: Dict[str, Any]   # e.g. (breaks": [••]) from prior turns