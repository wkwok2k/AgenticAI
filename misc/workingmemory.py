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

  if not text or not text.strip():
      raise ValueError("text must not be empty.")

  self.state.turn_counter += 1

  turn = Turn(
      turn_id=self.state.turn_counter, 
      role=role,
      text=text, 
      timestamp_utc=utcnow(),
      intent=intent, 
      response_summary=response_summary,
  )
  self.state.turns.append(turn)
  self.state.last_updated = utcnow()
  self._maybe_rollup()
  return turn

