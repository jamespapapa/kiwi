from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from .qwen_client import QwenClient

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - requirements include langgraph.
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]


AgentAction = Literal["answer", "interview", "code", "docs", "review"]


class AgentState(TypedDict, total=False):
    user_message: str
    project_context: str
    history: list[dict[str, str]]
    dangerous_mode: bool
    decision: dict[str, Any]
    response: str
    pending_coder_prompt: str | None
    approval_required: bool


class KiwiAgentRuntime:
    def __init__(self, qwen: QwenClient):
        self.qwen = qwen
        self.graph = self._build_graph()

    async def run(
        self,
        user_message: str,
        project_context: str,
        history: list[dict[str, str]],
        dangerous_mode: bool,
    ) -> AgentState:
        state: AgentState = {
            "user_message": user_message,
            "project_context": project_context,
            "history": history,
            "dangerous_mode": dangerous_mode,
        }
        if self.graph is None:
            state = await self._pm_node(state)
            route = self._route_after_pm(state)
            if route == "architect":
                return await self._architect_node(state)
            if route == "planner":
                return await self._planner_node(state)
            return await self._answer_node(state)
        return await self.graph.ainvoke(state)

    def _build_graph(self) -> Any:
        if StateGraph is None:
            return None
        graph = StateGraph(AgentState)
        graph.add_node("pm", self._pm_node)
        graph.add_node("architect", self._architect_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("answer", self._answer_node)
        graph.set_entry_point("pm")
        graph.add_conditional_edges(
            "pm",
            self._route_after_pm,
            {
                "architect": "architect",
                "planner": "planner",
                "answer": "answer",
            },
        )
        graph.add_edge("architect", END)
        graph.add_edge("planner", END)
        graph.add_edge("answer", END)
        return graph.compile()

    async def _pm_node(self, state: AgentState) -> AgentState:
        content = await self.qwen.chat(
            [
                {"role": "system", "content": PM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _compose_context_prompt(
                        state["project_context"],
                        state["history"],
                        state["user_message"],
                    ),
                },
            ],
            temperature=0.1,
        )
        decision = _parse_json_object(content)
        if not decision:
            decision = {
                "action": "answer",
                "assistant_message": content.strip(),
                "reason": "non_json_response",
            }
        action = str(decision.get("action", "answer"))
        if action not in {"answer", "interview", "code", "docs", "review"}:
            decision["action"] = "answer"
        state["decision"] = decision
        return state

    def _route_after_pm(self, state: AgentState) -> str:
        action = state.get("decision", {}).get("action")
        if action in {"code", "review"}:
            return "architect"
        if action in {"interview", "docs"}:
            return "planner"
        return "answer"

    async def _architect_node(self, state: AgentState) -> AgentState:
        decision = state.get("decision", {})
        content = await self.qwen.chat(
            [
                {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _compose_context_prompt(
                        state["project_context"],
                        state["history"],
                        state["user_message"],
                        decision,
                    ),
                },
            ],
            temperature=0.1,
        )
        refined = _parse_json_object(content)
        if not refined:
            refined = {
                "assistant_message": content.strip(),
                "coder_prompt": "",
                "ready": False,
            }

        coder_prompt = str(refined.get("coder_prompt", "")).strip()
        ready = bool(refined.get("ready")) and bool(coder_prompt)
        state["pending_coder_prompt"] = coder_prompt if ready else None
        state["approval_required"] = ready and not state.get("dangerous_mode", False)
        if ready:
            if state.get("dangerous_mode", False):
                suffix = "\n\n`dangerous` 모드가 켜져 있어 바로 qwencode 실행을 준비합니다."
            else:
                suffix = "\n\n승인하면 이 프롬프트로 qwencode를 실행합니다."
        else:
            suffix = ""
        state["response"] = str(refined.get("assistant_message", "")).strip() + suffix
        return state

    async def _planner_node(self, state: AgentState) -> AgentState:
        decision = state.get("decision", {})
        content = await self.qwen.chat(
            [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _compose_context_prompt(
                        state["project_context"],
                        state["history"],
                        state["user_message"],
                        decision,
                    ),
                },
            ],
            temperature=0.2,
        )
        state["response"] = content.strip()
        state["pending_coder_prompt"] = None
        state["approval_required"] = False
        return state

    async def _answer_node(self, state: AgentState) -> AgentState:
        decision = state.get("decision", {})
        message = str(decision.get("assistant_message", "")).strip()
        if message:
            state["response"] = message
            state["pending_coder_prompt"] = None
            state["approval_required"] = False
            return state
        content = await self.qwen.chat(
            [
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _compose_context_prompt(
                        state["project_context"],
                        state["history"],
                        state["user_message"],
                    ),
                },
            ],
            temperature=0.2,
        )
        state["response"] = content.strip()
        state["pending_coder_prompt"] = None
        state["approval_required"] = False
        return state


def _compose_context_prompt(
    project_context: str,
    history: list[dict[str, str]],
    user_message: str,
    decision: dict[str, Any] | None = None,
) -> str:
    history_text = "\n".join(f"{item['role']}: {item['content']}" for item in history[-24:])
    decision_text = f"\n\nPM decision:\n{json.dumps(decision, ensure_ascii=False)}" if decision else ""
    return (
        "Project long-term memory (KIWI.md):\n"
        f"{project_context}\n\n"
        "Recent chat history:\n"
        f"{history_text or '(none)'}\n\n"
        "Latest user request:\n"
        f"{user_message}"
        f"{decision_text}"
    )


def _parse_json_object(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


PM_SYSTEM_PROMPT = """
You are Kiwi PM, the main orchestrator for a controlled local vibe-coding workflow.
Use Korean for user-facing text.
Read KIWI.md as long-term project memory.
Decide whether the latest user request needs more interview, can be answered, needs docs, or is ready for coding.
Do not start coding unless the requirement is specific enough to hand to a terminal coding agent.
Return only JSON:
{
  "action": "answer" | "interview" | "code" | "docs" | "review",
  "assistant_message": "short user-facing Korean message",
  "reason": "brief reason",
  "missing_information": ["..."]
}
""".strip()

ARCHITECT_SYSTEM_PROMPT = """
You are Kiwi Architect. Convert an approved coding intent into a precise qwencode prompt.
Use Korean for user-facing text. The coder will run inside the selected project root only.
The prompt must be concrete: objective, files/areas to inspect, implementation constraints, verification commands, and expected final report.
For unsafe or vague requests, set ready=false and ask focused questions instead.
Return only JSON:
{
  "ready": true,
  "assistant_message": "Korean summary of the implementation plan",
  "coder_prompt": "full prompt for qwencode"
}
or:
{
  "ready": false,
  "assistant_message": "questions or blockers in Korean",
  "coder_prompt": ""
}
""".strip()

PLANNER_SYSTEM_PROMPT = """
You are Kiwi Planner. Interview the user and sharpen requirements.
Ask only the questions needed to remove ambiguity. Keep it concise and actionable.
Use Korean.
""".strip()

ANSWER_SYSTEM_PROMPT = """
You are Kiwi, a pragmatic local coding assistant. Answer using KIWI.md context.
Use Korean. Be concise and concrete.
""".strip()
