from dataclasses import dataclass, field
from typing import List, Dict, Any, TypedDict

@dataclass
class HopBreak:
    entity_name: str
    recon_run_date: str
    hierarchy_path: str
    hop_id: str
    hop_description: str
    eval_asof_date: str
    required_cde: int
    total_anchor_count: int
    break_anchor_count: int
    break_anchor_pct: float
    break_null_count: int
    break_empty_count: int
    break_valid_count: int
    break_valid_pct: float
    break_distinct_count: int
    exposure_amt: float
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TraceEvent(TypedDict, total=False):
    node: str               # e.g. "breaks_analys1s"
    stage: str              # e.g. "11m_analysis", "tool_call"
    message: str            # human-readable message
    extra: Dict[str, Any]   # optional structured payload

# State for LangGraph POC
@dataclass
class BreakState:
    user_question: str
    selected_tool: str
    breaks: List[HopBreak] = field(default_factory=list)
    analysis: str | None = None
    trace: List[TraceEvent] = field(default_factory=list)
