from typing import List
from langgraph.graph import StateGraph, END

from .schemas import BreaksGraphState, HopBreak, TraceEvent
from .tools import mock_top2_hop_breaks
from .router_agent import route_question
from .breaks_agent import explain_breaks
from .general_agent import answer_general_question


def router_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = (state.get("user_question") or "").strip()
    trace: List[TraceEvent] = state.get("trace", [])

    if not user_q:
        # If user sends empty input, route to general_qa (which will respond politely)
        tool_name = "general_qa"
        reason = "No question text detected; handing to GeneralQAgent."
    else:
        routing = route_question(user_q)
        tool_name = routing.get("tool_name") or "general_qa"
        reason = routing.get("reason") or ""

    trace.append(
        {
            "node": "router",
            "stage": "routing",
            "message": reason or f"Routing to {tool_name}.",
            "extra": {"selected_tool": tool_name},
        }
    )

    return {
        **state,
        "user_question": user_q,     # ensure stripped
        "selected_tool": tool_name,
        "routing_reason": reason,
        "trace": trace,
    }


def breaks_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = state["user_question"]
    trace: List[TraceEvent] = state.get("trace", [])

    breaks: List[HopBreak] = mock_top2_hop_breaks()
    trace.append(
        {
            "node": "breaks_analysis",
            "stage": "tool_call",
            "message": "Fetched top 2 mocked hop-level breaks.",
            "extra": {"hop_ids": [b["hop_id"] for b in breaks]},
        }
    )

    analysis = explain_breaks(user_q, breaks)
    trace.append(
        {
            "node": "breaks_analysis",
            "stage": "llm_analysis",
            "message": "I analyzed the hop-level breaks and summarized the main drivers.",
            "extra": {"preview": analysis[:200] + ("..." if len(analysis) > 200 else "")},
        }
    )

    return {**state, "breaks": breaks, "analysis": analysis, "trace": trace}


def general_qa_node(state: BreaksGraphState) -> BreaksGraphState:
    user_q = (state.get("user_question") or "").strip()
    trace: List[TraceEvent] = state.get("trace", [])

    answer = answer_general_question(user_q)
    trace.append(
        {
            "node": "general_qa",
            "stage": "llm_analysis",
            "message": "I answered a general question directly (no breaks tool needed).",
            "extra": {"preview": answer[:200] + ("..." if len(answer) > 200 else "")},
        }
    )
    return {**state, "analysis": answer, "trace": trace}


def _route_next(state: BreaksGraphState) -> str:
    # Conditional router
    return "breaks_analysis" if state.get("selected_tool") == "get_top_breaks" else "general_qa"


def build_breaks_poc_graph():
    g = StateGraph(BreaksGraphState)
    g.add_node("router", router_node)
    g.add_node("breaks_analysis", breaks_node)
    g.add_node("general_qa", general_qa_node)

    g.set_entry_point("router")

    # ✅ This is the important part: only ONE branch runs
    g.add_conditional_edges("router", _route_next, {
        "breaks_analysis": "breaks_analysis",
        "general_qa": "general_qa",
    })

    g.add_edge("breaks_analysis", END)
    g.add_edge("general_qa", END)

    return g.compile()


def run_breaks_poc(user_question: str) -> BreaksGraphState:
    app = build_breaks_poc_graph()
    return app.invoke({"user_question": user_question, "trace": []})
