from dataclasses import dataclass, field
from typing import Any, Literal, Optional, TypedDict, Dict

EventType = Literal["user_message", "assistant_message", "tool_call", "tool_result"]
Actor = Literal["user", "assistant", "tool"]

@dataclass
class Event:
    event_id: str
    event_seq: int
    turn_index: int
    actor: Actor
    type: EventType
    content_type: str = "text/plain"
    content: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass
class RunningSummary:
    text: str = ""
    derived_from_seq: int = 0  # last event_seq included

PointerKind = Literal["doc", "url", "commit", "ticket"]

@dataclass
class Pointer:
    pointer_id: str
    kind: PointerKind
    # store IDs/URLs/hashes instead of full text
    ref: dict[str, str]  # e.g. {"url": "..."} or {"repo": "...", "commit": "...", "path": "..."}
    anchor: dict[str, str] = field(default_factory=dict)  # e.g. {"section": "..."} or {"lines": "120-180"}
    content_hash: Optional[str] = None  # helps detect staleness/changes

ArtifactType = Literal["policy", "decision", "runbook"]
ArtifactStatus = Literal["draft", "active", "deprecated"]

@dataclass
class Artifact:
    artifact_id: str
    type: ArtifactType
    title: str
    status: ArtifactStatus = "draft"
    version: int = 1

    summary: str = ""
    details: list[str] = field(default_factory=list)

    pointer_ids: list[str] = field(default_factory=list)       # cite sources-of-record
    evidence_event_ids: list[str] = field(default_factory=list) # provenance
    tags: list[str] = field(default_factory=list)
    owner: Optional[str] = None

IndexType = Literal["lexical", "semantic"]

@dataclass
class IndexDescriptor:
    index_id: str
    type: IndexType
    corpus: str                # "artifacts", "pointer_anchors", etc.
    backend: str               # "bm25", "hnsw", etc.
    embedding_model_id: Optional[str] = None  # only for semantic
    built_at: Optional[str] = None
    status: str = "ready"      # "building", "ready", "stale"

@dataclass
class InstitutionalMemory:
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    pointers: dict[str, Pointer] = field(default_factory=dict)
    indexes: list[IndexDescriptor] = field(default_factory=list)

@dataclass
class GraphState:
    # existing
    user_question: str
    selected_tool: str
    breaks: list["HopBreak"] = field(default_factory=list)
    analysis: Optional[str] = None
    trace: list["TraceEvent"] = field(default_factory=list)

    # v2
    turn_index: int = 0
    last_event_seq: int = 0
    events: list[Event] = field(default_factory=list)
    running_summary: RunningSummary = field(default_factory=RunningSummary)

    # institutional
    institution: InstitutionalMemory = field(default_factory=InstitutionalMemory)

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