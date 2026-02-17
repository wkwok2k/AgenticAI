import json, logging, time
from dataclasses import dataclass, field, asdict from datetime import datetime, timezone from typing import List, Optional, Dict, Any from enum import Enum
from uuid import uuid4
from pathlib import Path

@dataclass
class WorkingMemory:
  def__init__(self, state: GraphState):
    self.state = state

  def append_turn_text(
    self, 
    role: Role,
    *,
    intent: str | None = None,
    text: str | None = None,
    response_summary str | None = None
  ) -> Turn:


