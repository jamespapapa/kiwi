from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Literal, TypedDict

from .config import get_internal_settings
from .db import APP_ROOT, now_iso
from .fast_system_prompts import load_fast_system_prompt, render_fast_runtime_injection
from .kk_mcp import KkMcpClient
from .project_analyzer import load_project_context
from .project_info import PROJECT_INFO_CONTEXT_MAX_CHARS, describe_project_info_status, load_project_info_context
from .qwen_client import QwenClient
from .ultrawork_policy import (
    TASK_SIZES,
    build_ultrawork_policy,
    render_qwencode_tool_cheatsheet,
    render_subagent_contract,
    render_tshirt_section,
)
from .work_modes import DEFAULT_TASK_SIZE, WorkMode, normalize_work_mode, render_work_mode_lock_lines, work_mode_definition

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - requirements include langgraph.
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]


PromptBuildStatus = Literal["running", "succeeded", "failed"]
BuilderMode = Literal["analysis", "implement", "review"]

BUILDER_LOG_DIR = APP_ROOT / "data" / "prompt-builder"
PROMPT_GUIDE_PATH = APP_ROOT / "docs" / "ultrawork-prompt-template.md"
FAST_SYSTEM_PROMPT_DOCS = "docs/fast-system-prompts"
FAST_PROMPT_GUIDE = """
FAST/lightwork Prompt Builder Guide

목표:
- Kiwi가 직접 계획, 실행, 검증할 수 있는 짧고 명확한 지시문을 만든다.
- 범위가 좁고 현재 파일 근거로 바로 확인 가능한 작업에 맞춘다.
- 작업이 넓어지거나 위험해지면 현재 세션에서 계속 키우지 말고 더 강한 work mode의 새 콘솔이 필요하다고 보고하게 한다.

필수 섹션:
1. KIWI work mode lock
2. 작업 목표
3. 사용자 확인 답변
4. 프로젝트 지식 베이스 우선 참고
5. KK docs MCP 참고 근거
6. 필수 읽기 파일
7. 필수 검색
8. 구현 규칙
9. 영향도 지도 작성
10. FAST/lightwork 직접 실행 계약
11. qwencode 직접 tool 사용법 초간단 참조
12. 검증 계획
13. 완료 보고 형식
14. 중단 조건
15. 진행 방식

작성 규칙:
- `lightwork` prefix는 KIWI UI가 전송 시 붙이므로 최종 프롬프트 본문에는 넣지 않는다.
- 실행 전 요구사항을 한 문장으로 재정의하고 짧은 계획을 세우게 한다.
- 현재 파일을 읽고 가장 작은 직접 변경만 수행하게 한다.
- 검증 명령 또는 대체 확인 방법을 반드시 적는다.
- read_file/edit/write_file/run_shell_command/ask_user_question의 실제 파라미터명을 얇게 적는다.
""".strip()


class PromptBuilderState(TypedDict, total=False):
    project: dict[str, Any]
    user_message: str
    work_mode: WorkMode
    history: list[dict[str, str]]
    project_context: str
    project_info_context: str
    project_info: dict[str, Any]
    fast_system_prompt: str
    fast_system_prompt_runtime: str
    fast_system_prompt_source: str
    prompt_guide: str
    intent: dict[str, Any]
    kk_docs_results: list[dict[str, Any]]
    ultrawork_policy: dict[str, Any]
    selected_task_size: str
    result: dict[str, Any]
    final_prompt: str
    prompt_lint: dict[str, Any]
    prompt_evaluation: dict[str, Any]


class PromptBuilderManager:
    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def start_run(
        self,
        project: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
        work_mode: WorkMode = "ultrawork",
        task_size: str | None = None,
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        normalized_work_mode = normalize_work_mode(work_mode)
        selected_task_size = _require_selected_task_size(normalized_work_mode, task_size)
        BUILDER_LOG_DIR.mkdir(parents=True, exist_ok=True)
        run = {
            "id": run_id,
            "project_id": project["id"],
            "project_name": project["name"],
            "work_mode": normalized_work_mode,
            "work_mode_label": work_mode_definition(normalized_work_mode).label,
            "status": "running",
            "created_at": now_iso(),
            "completed_at": None,
            "message": message,
            "assistant_message": "",
            "questions": [],
            "interview_questions": [],
            "final_prompt": "",
            "task_size": selected_task_size or None,
            "task_size_reason": "",
            "task_size_source": "user" if selected_task_size else "",
            "selected_task_size": selected_task_size or None,
            "recommended_task_size": None,
            "recommended_task_size_reason": "",
            "ultrawork_mode": "",
            "project_info": {},
            "events": [],
            "log_path": str(BUILDER_LOG_DIR / f"{run_id}.jsonl"),
        }
        self._runs[run_id] = run
        asyncio.create_task(self._execute(run_id, project, message, history, normalized_work_mode, selected_task_size))
        return self._public_run(run)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._runs.get(run_id)
        return self._public_run(run) if run else None

    async def stream_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        run = self._runs.get(run_id)
        if not run:
            return

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.setdefault(run_id, set()).add(queue)
        try:
            yield {"type": "snapshot", "run": self._public_run(run), "events": run["events"][-200:]}
            if run["status"] != "running":
                yield {"type": "done", "run": self._public_run(run)}
                return
            while True:
                event = await queue.get()
                yield event
                if event.get("type") in {"done", "error"}:
                    break
        finally:
            self._queues.get(run_id, set()).discard(queue)

    async def _execute(
        self,
        run_id: str,
        project: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
        work_mode: WorkMode,
        selected_task_size: str,
    ) -> None:
        settings = get_internal_settings()
        runtime = PromptBuilderRuntime(QwenClient(settings), lambda event: self._emit(run_id, event), settings)
        try:
            await self._emit(
                run_id,
                {
                    "type": "step",
                    "step": "start",
                    "title": "프롬프트 빌더 시작",
                    "message": f"{project['name']} 기준으로 요구사항을 분석합니다.",
                },
            )
            state = await runtime.run(project, message, history, settings.max_context_chars, work_mode, selected_task_size)
            run = self._runs[run_id]
            result = state.get("result", {})
            run["assistant_message"] = str(result.get("assistant_message", "")).strip()
            run["questions"] = [str(item) for item in result.get("questions", []) if str(item).strip()]
            run["interview_questions"] = _normalize_interview_questions(result)
            run["final_prompt"] = state.get("final_prompt", "")
            run["prompt_lint"] = state.get("prompt_lint", {})
            run["prompt_evaluation"] = state.get("prompt_evaluation", {})
            run["project_info"] = state.get("project_info", {})
            policy = state.get("ultrawork_policy", {})
            if work_mode == "fast":
                run["task_size"] = None
                run["task_size_reason"] = ""
                run["task_size_source"] = ""
                run["selected_task_size"] = None
                run["recommended_task_size"] = None
                run["recommended_task_size_reason"] = ""
                run["ultrawork_mode"] = ""
            else:
                run["task_size"] = policy.get("task_size")
                run["task_size_reason"] = policy.get("task_size_reason", "")
                run["task_size_source"] = policy.get("task_size_source", "")
                run["selected_task_size"] = policy.get("selected_task_size") or selected_task_size or policy.get("task_size")
                run["recommended_task_size"] = None
                run["recommended_task_size_reason"] = ""
                run["ultrawork_mode"] = policy.get("mode", "")
            run["status"] = "succeeded"
            run["completed_at"] = now_iso()
            await self._emit(run_id, {"type": "done", "run": self._public_run(run)})
        except Exception as exc:  # pragma: no cover - runtime guard.
            run = self._runs[run_id]
            run["status"] = "failed"
            run["completed_at"] = now_iso()
            run["assistant_message"] = f"프롬프트 빌더 실패: {exc}"
            await self._emit(
                run_id,
                {
                    "type": "error",
                    "error": str(exc),
                    "run": self._public_run(run),
                },
            )

    async def _emit(self, run_id: str, event: dict[str, Any]) -> None:
        run = self._runs.get(run_id)
        if not run:
            return
        payload = {"timestamp": now_iso(), **event}
        run["events"].append(payload)
        run["events"] = run["events"][-300:]
        _append_jsonl(Path(run["log_path"]), payload)
        for queue in self._queues.get(run_id, set()).copy():
            await queue.put(payload)

    @staticmethod
    def _public_run(run: dict[str, Any] | None) -> dict[str, Any]:
        if not run:
            return {}
        return {
            "id": run["id"],
            "project_id": run["project_id"],
            "project_name": run["project_name"],
            "work_mode": run.get("work_mode", "ultrawork"),
            "work_mode_label": run.get("work_mode_label", "ultrawork"),
            "status": run["status"],
            "created_at": run["created_at"],
            "completed_at": run["completed_at"],
            "message": run["message"],
            "assistant_message": run["assistant_message"],
            "questions": run["questions"],
            "interview_questions": run.get("interview_questions", []),
            "final_prompt": run["final_prompt"],
            "task_size": run.get("task_size"),
            "task_size_reason": run.get("task_size_reason", ""),
            "task_size_source": run.get("task_size_source", ""),
            "selected_task_size": run.get("selected_task_size"),
            "recommended_task_size": run.get("recommended_task_size"),
            "recommended_task_size_reason": run.get("recommended_task_size_reason", ""),
            "ultrawork_mode": run.get("ultrawork_mode", ""),
            "prompt_lint": run.get("prompt_lint", {}),
            "prompt_evaluation": run.get("prompt_evaluation", {}),
            "project_info": run.get("project_info", {}),
            "log_path": run["log_path"],
        }


class PromptBuilderRuntime:
    def __init__(self, qwen: QwenClient, emit: Any, settings: Any):
        self.qwen = qwen
        self.emit = emit
        self.settings = settings
        self.graph = self._build_graph()

    async def run(
        self,
        project: dict[str, Any],
        message: str,
        history: list[dict[str, str]],
        max_context_chars: int,
        work_mode: WorkMode = "ultrawork",
        selected_task_size: str = "",
    ) -> PromptBuilderState:
        root = Path(project["root_path"])
        normalized_work_mode = normalize_work_mode(work_mode)
        state: PromptBuilderState = {
            "project": project,
            "user_message": message,
            "work_mode": normalized_work_mode,
            "history": history[-12:],
            "project_context": load_project_context(root, min(max_context_chars, 80_000)),
            "project_info_context": load_project_info_context(
                root,
                normalized_work_mode,
                min(max_context_chars, PROJECT_INFO_CONTEXT_MAX_CHARS),
            ),
            "project_info": describe_project_info_status(root, normalized_work_mode),
            "prompt_guide": _load_prompt_guide(),
        }
        if normalized_work_mode == "fast":
            fast_prompt = load_fast_system_prompt(root)
            state["fast_system_prompt"] = fast_prompt.full_text
            state["fast_system_prompt_runtime"] = render_fast_runtime_injection(root, max_chars=10_000)
            state["fast_system_prompt_source"] = fast_prompt.source_relpath
        await self.emit(
            {
                "type": "project_info",
                "step": "start",
                "title": "Project Info Layer",
                "message": _project_info_event_message(state["project_info"]),
                "project_info": state["project_info"],
            }
        )
        if normalized_work_mode != "fast":
            state["selected_task_size"] = _require_selected_task_size(normalized_work_mode, selected_task_size)
        if self.graph is None:
            state = await self._intent_node(state)
            state = await self._kk_docs_node(state)
            state = await self._compose_node(state)
            return await self._lint_node(state)
        return await self.graph.ainvoke(state)

    def _build_graph(self) -> Any:
        if StateGraph is None:
            return None
        graph = StateGraph(PromptBuilderState)
        graph.add_node("intent", self._intent_node)
        graph.add_node("kk_docs", self._kk_docs_node)
        graph.add_node("compose", self._compose_node)
        graph.add_node("lint", self._lint_node)
        graph.set_entry_point("intent")
        graph.add_edge("intent", "kk_docs")
        graph.add_edge("kk_docs", "compose")
        graph.add_edge("compose", "lint")
        graph.add_edge("lint", END)
        return graph.compile()

    async def _intent_node(self, state: PromptBuilderState) -> PromptBuilderState:
        await self.emit(
            {
                "type": "step",
                "step": "intent",
                "title": "의도 분석",
                "message": "Qwen3.5로 작업 유형, 모호성, 필요한 검색어를 정리합니다.",
            }
        )
        content = await self.qwen.chat(
            [
                {"role": "system", "content": _intent_system_prompt(state.get("work_mode", "ultrawork"))},
                {"role": "user", "content": _compose_intent_prompt(state)},
            ],
            temperature=0,
            max_tokens=4096,
        )
        work_mode = normalize_work_mode(state.get("work_mode", "ultrawork"))
        intent = _parse_json_object(content)
        if not intent:
            intent = {
                "task_summary": state["user_message"],
                "task_type": "unknown",
                "mode": "analysis",
                "search_queries": _fallback_queries(state["user_message"]),
                "target_files": [],
                "missing_information": [],
                "questions": [],
                "risk_flags": ["intent_json_parse_failed"],
            }
            if work_mode != "fast":
                intent["task_size"] = ""
                intent["task_size_reason"] = ""
        if work_mode == "fast":
            intent.pop("task_size", None)
            intent.pop("task_size_reason", None)
            intent.pop("tshirt_size", None)
            intent.pop("sizing_reason", None)
            policy: dict[str, Any] = {}
        else:
            selected_task_size = _require_selected_task_size(work_mode, state.get("selected_task_size"))
            policy = build_ultrawork_policy(
                state["project"],
                intent,
                selected_task_size=selected_task_size,
                selected_task_size_reason=f"사용자가 `{selected_task_size}`를 선택했다.",
            )
            intent["task_size"] = policy["task_size"]
            intent["task_size_reason"] = policy["task_size_reason"]
            intent["task_size_source"] = policy["task_size_source"]
            state["selected_task_size"] = selected_task_size
            state["ultrawork_policy"] = policy
        state["intent"] = intent
        await self.emit(
            {
                "type": "intent",
                "step": "intent",
                "title": "의도 분석 완료",
                "intent": intent,
            }
        )
        if work_mode == "fast":
            await self.emit(
                {
                    "type": "fast_policy",
                    "step": "intent",
                    "title": "FAST 경량 정책",
                    "message": "FAST/lightwork는 Kiwi 단독 계획/실행/검증 프롬프트로 구성합니다.",
                    "policy": _fast_policy_context({}),
                }
            )
        else:
            await self.emit(
                {
                    "type": "task_size",
                    "step": "intent",
                    "title": "티셔츠 사이징",
                    "message": (
                        f"사용자 선택 {policy['task_size']} 기준으로 "
                        f"{work_mode_definition(work_mode).label} 프롬프트를 구성합니다."
                    ),
                    "policy": policy,
                }
            )
        return state

    async def _kk_docs_node(self, state: PromptBuilderState) -> PromptBuilderState:
        if not getattr(self.settings, "kk_docs_mcp_enabled", False) or not getattr(self.settings, "kk_docs_mcp_url", ""):
            state["kk_docs_results"] = []
            await self.emit(
                {
                    "type": "step",
                    "step": "kk_docs",
                    "title": "KK 문서 검색 생략",
                    "message": "docs MCP가 비활성화되어 문서 근거 없이 프롬프트를 조립합니다.",
                }
            )
            return state

        intent = state.get("intent", {})
        queries = _clean_string_list(intent.get("search_queries"), limit=5, max_len=120)
        if not queries:
            queries = _fallback_queries(state["user_message"])[:5]

        await self.emit(
            {
                "type": "step",
                "step": "kk_docs",
                "title": "KK docs MCP 검색",
                "message": f"{len(queries)}개 질의로 KK 문서 지식베이스를 확인합니다.",
                "endpoint": self.settings.kk_docs_mcp_url,
                "queries": queries,
            }
        )
        kk_docs_results = await KkMcpClient(self.settings).search_documents(queries, limit=5)
        state["kk_docs_results"] = kk_docs_results
        await self.emit(
            {
                "type": "kk_docs_search",
                "step": "kk_docs",
                "title": "KK 문서 검색 완료",
                "result_count": sum(len(item.get("results", [])) for item in kk_docs_results),
                "results": kk_docs_results,
            }
        )
        return state

    async def _compose_node(self, state: PromptBuilderState) -> PromptBuilderState:
        await self.emit(
            {
                "type": "step",
                "step": "compose",
                "title": "표준 프롬프트 조립",
                "message": "KK 문서 근거, 프로젝트 기억, 대화 이력, 선택 work mode 정책을 합쳐 지시문을 만듭니다.",
            }
        )
        content = await self.qwen.chat(
            [
                {"role": "system", "content": _compose_system_prompt(state.get("work_mode", "ultrawork"))},
                {"role": "user", "content": _compose_builder_prompt(state)},
            ],
            temperature=0.1,
            max_tokens=8192,
        )
        result = _parse_json_object(content) or {
            "status": "ready",
            "mode": "analysis",
            "assistant_message": "모델 응답이 JSON이 아니어서 원문을 분석 지시문으로 감쌉니다.",
            "questions": [],
            "prompt_parts": {
                "title": "사용자 요청 분석",
                "task": content.strip() or state["user_message"],
            },
        }
        state["result"] = result
        if str(result.get("status")) == "needs_input":
            questions = _clean_string_list(result.get("questions"), limit=5, max_len=260)
            interview_questions = _normalize_interview_questions(result)
            await self.emit(
                {
                    "type": "interview",
                    "step": "compose",
                    "title": "사용자 인터뷰 필요",
                    "message": str(result.get("assistant_message", "")).strip(),
                    "questions": questions,
                    "interview_questions": interview_questions,
                }
            )
            state["final_prompt"] = ""
            return state

        final_prompt = _render_ultrawork_prompt(state, result)
        if normalize_work_mode(state.get("work_mode", "ultrawork")) != "fast":
            final_prompt = _enforce_tshirt_policy_section(
                final_prompt,
                {
                    **state.get("ultrawork_policy", {}),
                    "work_mode": normalize_work_mode(state.get("work_mode", "ultrawork")),
                },
            )
        state["final_prompt"] = final_prompt
        await self.emit(
            {
                "type": "final_prompt",
                "step": "compose",
                "title": "프롬프트 생성 완료",
                "message": str(result.get("assistant_message", "")).strip(),
                "prompt": final_prompt,
            }
        )
        return state

    async def _lint_node(self, state: PromptBuilderState) -> PromptBuilderState:
        prompt = state.get("final_prompt", "")
        if not prompt:
            return state
        await self.emit(
            {
                "type": "step",
                "step": "lint",
                "title": "프롬프트 린트",
                "message": "최종 프롬프트가 선택 work mode 실행 계약과 필수 섹션을 만족하는지 확인합니다.",
            }
        )
        work_mode = normalize_work_mode(state.get("work_mode", "ultrawork"))
        if work_mode != "fast":
            prompt = _enforce_tshirt_policy_section(
                prompt,
                {**state.get("ultrawork_policy", {}), "work_mode": work_mode},
            )
            state["final_prompt"] = prompt
        lint = _lint_work_mode_prompt(prompt, work_mode)
        state["prompt_lint"] = lint
        await self.emit({"type": "prompt_lint", "step": "lint", "title": "린트 1차 결과", "lint": lint})
        if lint.get("passed"):
            state["prompt_evaluation"] = {
                "score": lint.get("score", 100),
                "issues": [],
                "improvements": ["deterministic_lint_passed"],
                "model_loop_skipped": True,
            }
            return state

        if work_mode == "fast":
            state["final_prompt"] = _repair_prompt_deterministically(state.get("final_prompt", ""), lint, work_mode)
            repaired_lint = _lint_work_mode_prompt(state["final_prompt"], work_mode)
            state["prompt_lint"] = repaired_lint
            state["prompt_evaluation"] = {
                "score": repaired_lint.get("score", 0),
                "issues": repaired_lint.get("issues", []),
                "improvements": ["fast_deterministic_repair_applied"],
                "model_loop_skipped": True,
            }
            await self.emit(
                {
                    "type": "prompt_evaluation",
                    "step": "lint",
                    "title": "FAST deterministic 보강 완료",
                    "evaluation": state["prompt_evaluation"],
                    "lint": repaired_lint,
                    "prompt": state["final_prompt"],
                }
            )
            return state

        evaluations: list[dict[str, Any]] = []
        repaired_lint = lint
        for attempt in range(1, 3):
            await self.emit(
                {
                    "type": "step",
                    "step": "evaluate",
                    "title": f"평가/개선 루프 {attempt}",
                    "message": "Qwen3.5 평가 루프로 누락된 실행 계약을 보강합니다.",
                }
            )
            content = await self.qwen.chat(
                [
                    {"role": "system", "content": _evaluate_system_prompt(work_mode)},
                    {"role": "user", "content": _compose_evaluation_prompt(state, repaired_lint, attempt)},
                ],
                temperature=0,
                max_tokens=8192,
            )
            evaluation = _parse_json_object(content) or {
                "score": 0,
                "issues": ["evaluation_json_parse_failed"],
                "revised_prompt": "",
            }
            evaluation["attempt"] = attempt
            evaluations.append(evaluation)
            revised = str(evaluation.get("revised_prompt") or "").strip()
            if not revised:
                break
            state["final_prompt"] = _strip_ultrawork_mode_switch(revised)
            if work_mode != "fast":
                state["final_prompt"] = _enforce_tshirt_policy_section(
                    state["final_prompt"],
                    {**state.get("ultrawork_policy", {}), "work_mode": work_mode},
                )
            repaired_lint = _lint_work_mode_prompt(state.get("final_prompt", ""), work_mode)
            state["prompt_lint"] = repaired_lint
            await self.emit(
                {
                    "type": "prompt_lint",
                    "step": "lint",
                    "title": f"린트 재검사 {attempt}",
                    "lint": repaired_lint,
                }
            )
            if repaired_lint.get("passed"):
                break

        evaluation_summary = _summarize_evaluations(evaluations, repaired_lint)
        if not repaired_lint.get("passed"):
            state["final_prompt"] = _repair_prompt_deterministically(
                state.get("final_prompt", ""), repaired_lint, work_mode
            )
            if work_mode != "fast":
                state["final_prompt"] = _enforce_tshirt_policy_section(
                    state["final_prompt"],
                    {**state.get("ultrawork_policy", {}), "work_mode": work_mode},
                )
            repaired_lint = _lint_work_mode_prompt(state["final_prompt"], work_mode)
            evaluation_summary["deterministic_repair_applied"] = True
        state["prompt_lint"] = repaired_lint
        state["prompt_evaluation"] = evaluation_summary
        await self.emit(
            {
                "type": "prompt_evaluation",
                "step": "evaluate",
                "title": "평가/개선 완료",
                "evaluation": evaluation_summary,
                "lint": repaired_lint,
                "prompt": state["final_prompt"],
            }
        )
        return state


def _load_prompt_guide() -> str:
    if not PROMPT_GUIDE_PATH.exists():
        return "Ultrawork prompt guide document is missing."
    return PROMPT_GUIDE_PATH.read_text(encoding="utf-8", errors="ignore")[:80_000]


def _normalize_task_size_for_builder(value: Any) -> str:
    size = str(value or "").strip().lower()
    return size if size in TASK_SIZES else ""


def _require_selected_task_size(work_mode: WorkMode, value: Any) -> str:
    if normalize_work_mode(work_mode) == "fast":
        return ""
    size = _normalize_task_size_for_builder(value)
    if not size:
        return DEFAULT_TASK_SIZE
    return size


def _project_info_event_message(project_info: dict[str, Any]) -> str:
    status = str(project_info.get("status") or "missing")
    profile = project_info.get("profile", {})
    profile_key = profile.get("key") if isinstance(profile, dict) else "unknown"
    action = str(project_info.get("action") or "").strip()
    if status == "ready":
        return f"Project Info ready: profile={profile_key}. Required reading and target/domain hints are attached."
    if status == "stale":
        return f"Project Info stale: profile={profile_key}. Project Info refresh required; stale inputs are attached."
    if status == "invalid":
        return f"Project Info invalid: profile={profile_key}. {action}"
    return "Project Info missing. Run project initialization or Project Info refresh before relying on shared project facts."


def _project_info_prompt_section(state: PromptBuilderState) -> list[str]:
    context = str(state.get("project_info_context") or "").strip()
    if not context:
        context = (
            "# Project Info Layer\n\n"
            "- Status: missing\n"
            "- Profile: missing\n"
            "- Action: Project Info Layer missing; use central knowledge docs and current files now, then run Project Info refresh before relying on generated summaries.\n\n"
            "## Required reading\n"
            "- D:/aiops/docs/<project-key>/knowledge/00-index.md (read first when present)\n"
            "- D:/aiops/docs/<project-key>/project-info/ (optional; read only if that central directory exists)\n\n"
            "## Target files/domain hints\n"
            "- Project Info Layer is missing. Do not infer a default architecture or domain map; verify against current files."
        )
    context = context[:PROJECT_INFO_CONTEXT_MAX_CHARS].strip()
    return [
        "## Project Info Layer 시작 컨텍스트",
        "- Start from this summarized Project Info Layer, then verify against the current files before editing.",
        "- Do not paste full project-info.json or full EAI markdown into prompts; use summary artifacts and targeted evidence paths.",
        "",
        context,
    ]


def _compose_intent_prompt(state: PromptBuilderState) -> str:
    guide = _prompt_guide_for_mode(state)
    return (
        "Work mode 프롬프트 작성 가이드:\n"
        f"{guide[:26000]}\n\n"
        "선택된 KIWI work mode:\n"
        f"{json.dumps({'work_mode': state.get('work_mode', 'ultrawork')}, ensure_ascii=False)}\n\n"
        "프로젝트 KIWI.md 장기 기억:\n"
        f"{state['project_context'][:30000]}\n\n"
        "Project Info Layer 공유 근거:\n"
        f"{state.get('project_info_context', '')[:30000]}\n\n"
        "Project Info Layer 상태/힌트 JSON:\n"
        f"{json.dumps(state.get('project_info', {}), ensure_ascii=False, indent=2)[:12000]}\n\n"
        "최근 빌더 대화:\n"
        f"{_format_history(state['history'])}\n\n"
        "사용자 최신 요청:\n"
        f"{state['user_message']}\n\n"
        "이 요청을 qwencode work mode 지시문으로 만들기 전에 무엇을 확인해야 하는지 JSON으로 판단하라."
    )


def _compose_builder_prompt(state: PromptBuilderState) -> str:
    guide = _prompt_guide_for_mode(state)
    intent_context = _intent_context_for_mode(state.get("intent", {}), state.get("work_mode", "ultrawork"))
    policy_context = _policy_context_for_mode(state.get("ultrawork_policy", {}), state.get("work_mode", "ultrawork"))
    context = {
        "intent": intent_context,
        "kk_docs_results": state.get("kk_docs_results", []),
        "work_mode_policy": policy_context,
        "work_mode": state.get("work_mode", "ultrawork"),
    }
    return (
        "Work mode 프롬프트 작성 가이드:\n"
        f"{guide[:70000]}\n\n"
        "프로젝트 KIWI.md 장기 기억:\n"
        f"{state['project_context'][:45000]}\n\n"
        "Project Info Layer 공유 근거:\n"
        f"{state.get('project_info_context', '')[:45000]}\n\n"
        "Project Info Layer 상태/힌트 JSON:\n"
        f"{json.dumps(state.get('project_info', {}), ensure_ascii=False, indent=2)[:12000]}\n\n"
        "KK docs MCP 검색 근거:\n"
        f"{json.dumps(state.get('kk_docs_results', []), ensure_ascii=False)[:45000]}\n\n"
        "사용자 선택 규모 정책과 프로젝트 프로필:\n"
        f"{json.dumps(policy_context, ensure_ascii=False, indent=2)}\n\n"
        "선택된 KIWI work mode:\n"
        f"{json.dumps({'work_mode': state.get('work_mode', 'ultrawork')}, ensure_ascii=False)}\n\n"
        "최근 빌더 대화:\n"
        f"{_format_history(state['history'])}\n\n"
        "사용자 최신 요청:\n"
        f"{state['user_message']}\n\n"
        "분석 및 검색 근거 JSON:\n"
        f"{json.dumps(context, ensure_ascii=False)[:70000]}\n\n"
        "이제 추가 질문이 필요하면 interview_user tool contract를 포함한 needs_input을 반환하고, 충분하면 ready와 prompt_parts를 반환하라."
    )


def _compose_system_prompt(work_mode: WorkMode) -> str:
    normalized = normalize_work_mode(work_mode)
    if normalized == "fast":
        return COMPOSE_SYSTEM_PROMPT_FAST
    if normalized == "superpowers":
        return COMPOSE_SYSTEM_PROMPT_SUPERPOWERS
    return COMPOSE_SYSTEM_PROMPT


def _intent_system_prompt(work_mode: WorkMode) -> str:
    normalized = normalize_work_mode(work_mode)
    if normalized == "fast":
        return INTENT_SYSTEM_PROMPT_FAST
    if normalized == "superpowers":
        return INTENT_SYSTEM_PROMPT_SUPERPOWERS
    return INTENT_SYSTEM_PROMPT


def _evaluate_system_prompt(work_mode: WorkMode) -> str:
    if normalize_work_mode(work_mode) == "superpowers":
        return EVALUATE_SYSTEM_PROMPT_SUPERPOWERS
    return EVALUATE_SYSTEM_PROMPT


def _prompt_guide_for_mode(state: PromptBuilderState) -> str:
    if normalize_work_mode(state.get("work_mode", "ultrawork")) == "fast":
        if state.get("fast_system_prompt"):
            return state["fast_system_prompt"]
        project = state.get("project", {})
        root = project.get("root_path") if isinstance(project, dict) else None
        return load_fast_system_prompt(root).full_text if root else FAST_PROMPT_GUIDE
    return state.get("prompt_guide", "")


def _intent_context_for_mode(intent: dict[str, Any], work_mode: WorkMode) -> dict[str, Any]:
    if normalize_work_mode(work_mode) != "fast":
        return intent
    return {
        key: value
        for key, value in intent.items()
        if key not in {"task_size", "task_size_reason", "tshirt_size", "sizing_reason", "subagents"}
    }


def _policy_context_for_mode(policy: dict[str, Any], work_mode: WorkMode) -> dict[str, Any]:
    if normalize_work_mode(work_mode) == "fast":
        return _fast_policy_context(policy)
    return policy


def _fast_policy_context(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "fast-direct",
        "execution": "Kiwi 직접 계획/실행/검증",
        "profile_label": policy.get("profile_label") or "Generic",
    }


def _compose_evaluation_prompt(state: PromptBuilderState, lint: dict[str, Any], attempt: int) -> str:
    work_mode = normalize_work_mode(state.get("work_mode", "ultrawork"))
    label = "superpowers" if work_mode == "superpowers" else "ultrawork"
    return (
        f"{label} 프롬프트 작성 가이드:\n"
        f"{state['prompt_guide'][:70000]}\n\n"
        f"평가 루프 시도 번호: {attempt}/2\n\n"
        "현재 lint 결과 JSON:\n"
        f"{json.dumps(lint, ensure_ascii=False, indent=2)}\n\n"
        "현재 최종 프롬프트:\n"
        f"{state.get('final_prompt', '')}\n\n"
        f"위 프롬프트를 Qwen3.5-397B Kiwi가 {label} mode에서 더 쉽게 실행할 수 있게 보강하라. "
        "단, KIWI UI가 전송 시 선택된 work mode prefix(lightwork/ultrawork/superpowers)를 별도로 주입하므로 revised_prompt 맨 앞에 mode switch 한 줄은 넣지 마라. "
        "반드시 JSON만 반환하고 revised_prompt에는 완성된 전체 프롬프트를 넣어라."
    )


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "(none)"
    return "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in history[-12:])


def _fallback_queries(message: str) -> list[str]:
    words = [word for word in re.split(r"[\s,.;:/()\[\]{}]+", message) if len(word) >= 3]
    preferred = [word for word in words if re.search(r"[A-Za-z0-9가-힣]", word)]
    return preferred[:5] or [message[:80]]


def _clean_string_list(value: Any, limit: int, max_len: int) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        cleaned.append(text[:max_len])
        if len(cleaned) >= limit:
            break
    return cleaned


def _normalize_interview_questions(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw = result.get("interview_questions")
    tool = result.get("interview_tool")
    if isinstance(tool, dict):
        raw = tool.get("questions", raw)
    if not isinstance(raw, list):
        raw = []

    normalized: list[dict[str, Any]] = []
    fallback_questions = _clean_string_list(result.get("questions"), limit=3, max_len=260)
    if not raw and fallback_questions:
        raw = [
            {
                "id": f"question_{index + 1}",
                "header": "확인",
                "question": question,
                "options": [
                    {"label": "예", "description": "이 방향으로 진행합니다."},
                    {"label": "아니오", "description": "다른 방향이 필요합니다."},
                ],
                "allow_other": True,
            }
            for index, question in enumerate(fallback_questions)
        ]

    for index, item in enumerate(raw[:3]):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()[:260]
        if not question:
            continue
        options: list[dict[str, str]] = []
        raw_options = item.get("options")
        if isinstance(raw_options, list):
            for option in raw_options[:4]:
                if not isinstance(option, dict):
                    continue
                label = str(option.get("label") or "").strip()[:80]
                if not label:
                    continue
                description = str(option.get("description") or "").strip()[:180]
                options.append({"label": label, "description": description})
        if len(options) < 2:
            options = [
                {"label": "권장안", "description": "Qwen이 추천하는 기본 방향으로 진행합니다."},
                {"label": "직접 입력", "description": "아래 기타 입력에 원하는 답을 적습니다."},
            ]
        normalized.append(
            {
                "id": _safe_question_id(item.get("id"), index),
                "header": str(item.get("header") or "확인").strip()[:12],
                "question": question,
                "options": options,
                "allow_other": bool(item.get("allow_other", True)),
            }
        )
    return normalized


def _safe_question_id(value: Any, index: int) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9가-힣_-]+", "_", text).strip("_")
    return text[:40] or f"question_{index + 1}"


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


def _render_ultrawork_prompt(state: PromptBuilderState, result: dict[str, Any]) -> str:
    parts = result.get("prompt_parts", {})
    if not isinstance(parts, dict):
        parts = {}
    mode = str(result.get("mode") or parts.get("mode") or "analysis").lower()
    mode_token = {
        "implement": "IMPLEMENT APPROVED",
        "review": "REVIEW ONLY",
    }.get(mode, "ANALYSIS ONLY")
    intent = state.get("intent", {})
    title = str(parts.get("title") or intent.get("task_summary") or "DCP 작업").strip()
    task = str(parts.get("task") or intent.get("task_summary") or state["user_message"]).strip()
    target_files = _clean_string_list(parts.get("target_files") or intent.get("target_files"), 20, 220)
    required_reading = _clean_string_list(parts.get("required_reading"), 20, 220)
    required_search = _clean_string_list(parts.get("required_search"), 20, 260)
    implementation_rules = _clean_string_list(parts.get("implementation_rules"), 20, 300)
    verification = _clean_string_list(parts.get("verification"), 20, 260)
    output_contract = _clean_string_list(parts.get("output_contract"), 12, 220)
    stop_conditions = _clean_string_list(parts.get("stop_conditions"), 12, 240)
    confirmed_answers = _extract_interview_answers(
        [*state.get("history", []), {"role": "user", "content": state["user_message"]}]
    )
    work_mode = normalize_work_mode(state.get("work_mode", "ultrawork"))
    selected_task_size_for_lock = None if work_mode == "fast" else state.get("selected_task_size")
    work_mode_lines = render_work_mode_lock_lines(work_mode, selected_task_size_for_lock)
    frontend_task = _is_frontend_task(state, parts)
    kk_docs_evidence = _summarize_kk_docs_evidence(state.get("kk_docs_results", []))
    project_info_section = _project_info_prompt_section(state)

    if not required_reading:
        required_reading = [
            "QWEN.md",
            "KIWI.md",
            "관련 route/view/component/store 또는 controller/service/mapper 파일",
        ]
    if not required_search:
        required_search = _default_required_search(state)
    if not implementation_rules:
        implementation_rules = [
            "먼저 요구사항을 레포 용어로 재정의하고 impact map을 작성한다.",
            "route, screen, modal/shared component, store/DataStore, API payload, downstream consumer를 편집 전 추적한다.",
            "값 추가/변경이면 default, UI binding, local state, modal result, store key, route params, spotLoad/spotSave를 확인한다.",
            "legacy branch driver(whoGbn, busnScCd, clamReason, clamCause, inqrScCd)의 의미를 임의로 바꾸지 않는다.",
            "관련 없는 리팩터링, 포맷팅, 파일 이동, 명명 변경을 하지 않는다.",
        ]
    if frontend_task:
        frontend_required_reading = [
            "관련 view/component 파일의 template, script, style 블록 또는 import된 CSS/SCSS 파일",
            "해당 화면 family의 router/view parent layout, wrapper component, 공통 button/control CSS",
            "DOM을 직접 다루는 refs, directives, mounted/updated hook, class toggle, style binding, transition/animation 코드",
        ]
        frontend_required_search = [
            'rg -n "class=|:class|v-bind:class|ref=|\\$refs|querySelector|getElementById|addEventListener|style=|:style" src',
            'rg -n "position:|z-index|overflow|transform|transition|animation|::before|::after|box-shadow|filter" src',
            'rg -n "button|btn|control|toolbar|tab|panel|drawer|inspector|modal" src',
        ]
        frontend_rules = [
            "프론트/UI 작업이면 template/script/style을 함께 읽고, 기존 DOM 계층과 CSS selector 우선순위를 먼저 요약한 뒤 편집한다.",
            "`position: relative|absolute|fixed`, `z-index`, `overflow`, `transform`, `top/left/right/bottom` 변경은 기존 containing block과 주변 layout 영향도를 설명하기 전에는 적용하지 않는다.",
            "버튼/작은 control의 블링, glow, shine 효과는 해당 버튼 bounds 안에 갇히게 만든다. 큰 absolute overlay, 화면을 가로지르는 pseudo-element, 부모 영역을 넘는 animation을 금지한다.",
            "기존 scoped style, 전역 style, channel-specific style, wrapper layout 규칙 중 어디에 넣어야 하는지 확인하고, 임의로 전역 CSS를 추가하지 않는다.",
            "화면 resize/zoom/좁은 viewport에서도 text overflow, layout shift, horizontal scroll이 생기지 않도록 width/min-width/overflow를 함께 점검한다.",
            "DOM을 직접 다루는 기존 코드가 있으면 refs/directives/class toggle과 CSS side effect를 추적하고, lifecycle hook 순서를 바꾸지 않는다.",
            "레이아웃이나 애니메이션 변경이 있으면 CSS/DOM 위험을 별도 확인 항목으로 남긴다.",
        ]
        frontend_stops = [
            "기존 layout container, containing block, scoped/global style 위치를 확인하지 못하면 CSS 편집을 중단하고 먼저 탐색한다.",
            "요구된 시각 효과가 버튼 bounds를 넘어 주변 UI에 영향을 줄 가능성이 있으면 구현 전 설계안을 다시 확인한다.",
        ]
        required_reading = _merge_unique(required_reading, frontend_required_reading, 30)
        required_search = _merge_unique(required_search, frontend_required_search, 30)
        implementation_rules = _merge_unique(implementation_rules, frontend_rules, 40)
        stop_conditions = _merge_unique(stop_conditions, frontend_stops, 20)
    if not verification:
        verification = ["가능한 로컬 검증 명령을 먼저 식별하고 실행한다.", "실행할 수 없는 검증은 이유와 대체 확인 방법을 보고한다."]
    if not output_contract:
        output_contract = ["변경 파일", "무엇을 바꿨는지", "실행한 검증", "남은 위험/질문"]
    if not stop_conditions:
        stop_conditions = [
            "업무 의미가 모호하면 편집하지 말고 질문한다.",
            "API carrier나 저장 위치가 불명확하면 질문한다.",
            "consumer가 많아 동작 변경 위험이 크면 구현 전 영향도를 보고한다.",
        ]

    if work_mode == "fast":
        return _render_fast_prompt(
            title=title,
            mode_token=mode_token,
            work_mode_lines=work_mode_lines,
            task=task,
            confirmed_answers=confirmed_answers,
            kk_docs_evidence=kk_docs_evidence,
            project_info_section=project_info_section,
            fast_runtime_injection=(
                str(state.get("fast_system_prompt_runtime") or "").strip()
                or render_fast_runtime_injection(state["project"], max_chars=10_000)
            ),
            required_reading=required_reading,
            target_files=target_files,
            required_search=required_search,
            implementation_rules=implementation_rules,
            frontend_task=frontend_task,
            verification=verification,
            output_contract=output_contract,
            stop_conditions=stop_conditions,
        )

    selected_task_size = _require_selected_task_size(work_mode, state.get("selected_task_size"))
    policy = state.get("ultrawork_policy") or build_ultrawork_policy(
        state["project"],
        intent,
        selected_task_size=selected_task_size,
        selected_task_size_reason=f"사용자가 `{selected_task_size}`를 선택했다.",
    )
    policy = {**policy, "work_mode": work_mode}
    task_size = str(policy.get("task_size") or "small")
    developer_agent = str(policy.get("developer_agent") or "coder-35")
    progress_lines = _progress_lines_for_policy(task_size, developer_agent)

    sections = [
        f"# {title}",
        "",
        f"`{mode_token}`",
        "",
        *work_mode_lines,
        "",
        "## 작업 목표",
        task,
        "",
        "## 사용자 확인 답변",
        confirmed_answers,
        "",
        "## 프로젝트 지식 베이스 우선 참고",
        *_bullet_lines(
            [
                "중앙 문서 루트 `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고, 해당 pack의 관련 문서를 seed 지식으로 사용한다.",
                "Project Info Layer, KK docs MCP `kk_search`, 현재 코드 read/search 근거로 seed 지식을 검증한다.",
                "문서와 현재 코드가 충돌하면 현재 코드 근거를 우선하고 충돌 사실을 보고한다.",
                "QWEN.md/KIWI.md는 실행 규칙과 프로젝트 메모리로 참고하되, 업무/도메인 판단은 현재 파일 근거로 확정한다.",
            ]
        ),
        "",
        "## KK docs MCP 참고 근거",
        kk_docs_evidence,
        "",
        *project_info_section,
        "",
        *render_tshirt_section(policy),
        "",
        "## 필수 읽기 파일",
        *_bullet_lines(required_reading + target_files),
        "",
        "## 필수 검색",
        *_bullet_lines(required_search),
        "",
        "## 구현 규칙",
        *_bullet_lines(implementation_rules),
        "",
        *(
            [
                "## 프론트 CSS/DOM 가드레일",
                *_bullet_lines(
                    [
                        "CSS는 기능 구현의 부속 작업이 아니라 별도 영향 범위다. 기존 selector, wrapper, scoped/global style, DOM mutation을 확인한 뒤 변경한다.",
                        "작은 버튼/컨트롤 효과는 버튼 내부에 clipping되도록 구현하고, absolute pseudo-element가 부모/주변 영역을 덮지 않게 한다.",
                        "positioning, transform, overflow, z-index는 레이아웃을 이동시킬 수 있으므로 변경 이유와 영향 영역을 먼저 적는다.",
                        "Playwright screenshot은 미래 시각 검증용으로 경로를 남길 수 있지만, 현재 폐쇄망 Qwen3.5는 vision이 꺼져 있으므로 DOM/CSS 수치, text, screenshot 파일 경로, 사람 확인 항목으로 보고한다.",
                    ]
                ),
                "",
            ]
            if frontend_task
            else []
        ),
        "## 영향도 지도 작성",
        *_bullet_lines(
            [
                "entrypoint, producer, carrier, API/request/response, persistence/cache/session, downstream consumer를 편집 전 정리한다.",
                "해당 없는 항목은 `해당 없음`이라고 쓰고, 확인하지 못한 항목은 gap으로 남긴다.",
                "공유 component/modal/store/core module을 건드릴 가능성이 있으면 모든 consumer를 먼저 찾는다.",
            ]
        ),
        "",
        "## subagent 운영 계약",
        *_bullet_lines(render_subagent_contract(policy)),
        "",
        "## qwencode 기본 tool 사용법 초간단 참조",
        *_bullet_lines(render_qwencode_tool_cheatsheet()),
        "",
        "## 검증 계획",
        *_bullet_lines(verification),
        "",
        "## 완료 보고 형식",
        *_bullet_lines(output_contract),
        "",
        "## 중단 조건",
        *_bullet_lines(stop_conditions),
        "",
        "## 진행 방식",
        *_bullet_lines(progress_lines),
    ]
    if work_mode == "superpowers":
        sections.extend(
            [
                "",
                "## superpowers skill-first 계약",
                "- superpowers policy and skill are the source of truth for this mode.",
                "- Delegated agent execution is available only after the skill-first impact map is complete.",
                f"- selected task_size `{task_size}` is the source of truth. Do not auto-estimate or replace it.",
                "- 첫 분석 단계에서 built-in `skill` tool로 `skill=\"kiwi-superpowers\"`, 그 다음 `skill=\"using-superpowers\"`를 호출한다. 요청에 맞는 개별 superpowers skill도 같은 `skill` tool로 호출한다.",
                "- `kiwi-superpowers`나 `using-superpowers`라는 이름의 도구를 직접 호출하지 않는다. 스킬 호출은 반드시 `skill` tool의 `skill` 파라미터로 한다. `skill` tool이 unavailable/unknown skill을 반환할 때만 SKILL.md 파일 직접 읽기 fallback을 사용한다.",
                "- `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고, `D:/aiops/docs/<project-key>/project-info/` 요약 산출물은 해당 central directory가 실제로 있을 때만 확인한다. project-relative `docs/<project-key>/...` 또는 `docs/kiwi/project-info/...` 경로를 시도하지 않는다.",
                "- skill 결과를 바탕으로 impact map, 작업 순서, 검증 계획을 보강한 뒤 필요할 때만 `agent`를 호출한다.",
            ]
        )
    return "\n".join(sections).strip()


def _render_fast_prompt(
    *,
    title: str,
    mode_token: str,
    work_mode_lines: list[str],
    task: str,
    confirmed_answers: str,
    kk_docs_evidence: str,
    project_info_section: list[str],
    fast_runtime_injection: str,
    required_reading: list[str],
    target_files: list[str],
    required_search: list[str],
    implementation_rules: list[str],
    frontend_task: bool,
    verification: list[str],
    output_contract: list[str],
    stop_conditions: list[str],
) -> str:
    required_reading = _filter_fast_section_lines(required_reading)
    target_files = _filter_fast_section_lines(target_files)
    required_search = _filter_fast_section_lines(required_search)
    implementation_rules = _filter_fast_section_lines(implementation_rules)
    verification = _filter_fast_section_lines(verification)
    output_contract = _filter_fast_section_lines(output_contract)
    stop_conditions = _filter_fast_section_lines(stop_conditions)
    sections = [
        f"# {title}",
        "",
        f"`{mode_token}`",
        "",
        *work_mode_lines,
        "",
        "## 작업 목표",
        task,
        "",
        "## 사용자 확인 답변",
        confirmed_answers,
        "",
        "## 프로젝트 지식 베이스 우선 참고",
        *_bullet_lines(
            [
                "중앙 문서 루트 `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고, 관련 pack 문서를 seed 지식으로 사용한다.",
                "Project Info Layer, KK docs MCP `kk_search`, 현재 코드 read/search 근거로 seed 지식을 검증한다.",
                "문서와 현재 코드가 충돌하면 현재 코드 근거를 우선하고 충돌 사실을 보고한다.",
                "QWEN.md/KIWI.md는 실행 규칙과 프로젝트 메모리로 참고한다.",
            ]
        ),
        "",
        "## KK docs MCP 참고 근거",
        kk_docs_evidence,
        "",
        *project_info_section,
        "",
        fast_runtime_injection,
        "",
        "## 필수 읽기 파일",
        *_bullet_lines(required_reading + target_files),
        "",
        "## 필수 검색",
        *_bullet_lines(required_search),
        "",
        "## 구현 규칙",
        *_bullet_lines(implementation_rules),
        "",
        *(
            [
                "## 프론트 CSS/DOM 가드레일",
                *_bullet_lines(
                    [
                        "기존 selector, wrapper, scoped/global style, DOM mutation을 확인한 뒤 변경한다.",
                        "작은 버튼/컨트롤 효과는 해당 요소 bounds 안에 제한한다.",
                        "positioning, transform, overflow, z-index 변경은 기존 layout 영향 영역을 먼저 적는다.",
                    ]
                ),
                "",
            ]
            if frontend_task
            else []
        ),
        "## 영향도 지도 작성",
        *_bullet_lines(
            [
                "entrypoint, producer, carrier, API/request/response, persistence/cache/session, downstream consumer를 편집 전 정리한다.",
                "해당 없는 항목은 `해당 없음`이라고 쓰고, 확인하지 못한 항목은 gap으로 남긴다.",
                "공유 component/modal/store/core module을 건드릴 가능성이 있으면 모든 consumer를 먼저 찾는다.",
            ]
        ),
        "",
        "## FAST/lightwork 직접 실행 계약",
        *_bullet_lines(
            [
                "Kiwi 단독으로 요구사항을 재정의하고 `todo_write` tool로 짧은 계획과 완료 조건을 먼저 기록한다.",
                "현재 파일을 읽고 가장 작은 직접 변경만 수행한다.",
                "변경 후 focused verification을 실행하거나 실행 불가 이유와 대체 확인 방법을 보고한다.",
                "영향 범위가 넓어지면 작업을 멈추고 더 강한 work mode의 새 콘솔이 필요하다고 보고한다.",
            ]
        ),
        "",
        "## qwencode 직접 tool 사용법 초간단 참조",
        *_bullet_lines(_direct_tool_cheatsheet()),
        "",
        "## 검증 계획",
        *_bullet_lines(verification),
        "",
        "## 완료 보고 형식",
        *_bullet_lines(output_contract),
        "",
        "## 중단 조건",
        *_bullet_lines(stop_conditions),
        "",
        "## 진행 방식",
        *_bullet_lines(
            [
                "`todo_write` tool로 요구사항, 누락 정보, 실행 순서, 완료 조건을 먼저 정리한다.",
                "계획한 직접 변경만 수행하고 범위를 넓히지 않는다.",
                "수정 후 검증 결과와 남은 위험을 짧게 보고한다.",
                "사용자 판단이 필요하면 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다. 일반 텍스트 질문으로 대체하지 않는다.",
            ]
        ),
    ]
    return "\n".join(sections).strip()


def _progress_lines_for_policy(task_size: str, developer_agent: str) -> list[str]:
    lines = [
        "`todo_write` tool로 요구사항, 누락 정보, 실행 순서, 완료/검증 조건을 먼저 정리한다.",
        "위 티셔츠 사이징에 맞는 ultrawork 운영 모드를 사용자에게 명확히 보고한다.",
    ]
    if task_size == "xsmall":
        lines.extend(
            [
                "xsmall이므로 subagent를 호출하지 않고 Kiwi가 직접 읽기/수정/검증을 짧게 처리한다.",
                "대상 파일, API/store/session 영향, 검증 범위가 넓어지면 현재 세션에서 임의로 size를 바꾸지 말고 더 큰 size의 새 콘솔을 시작하라고 보고한다.",
            ]
        )
    elif task_size == "small":
        lines.extend(
            [
                f"explorer-35와 `{developer_agent}` 중심으로 짧게 진행하고 planner-35/architect-35는 생략한다.",
                "공유 파일, 테스트 실패, 보안/데이터 변경이 있을 때만 reviewer-35를 호출한다.",
            ]
        )
    elif task_size == "medium":
        lines.extend(
            [
                f"explorer-35 탐색 후 `{developer_agent}`가 한두 개의 좁은 slice를 구현한다.",
                "데이터/API/store/공유 모듈 위험 신호가 있으면 architect-35를 짧게 호출한다.",
                "구현 결과는 reviewer-35로 diff와 검증 결과를 점검한다.",
            ]
        )
    else:
        lines.extend(
            [
                "planner-35로 요구사항과 수용조건을 정리하고 architect-35로 영향 범위와 변경 순서를 검토한다.",
                f"구현은 `{developer_agent}`에 좁은 slice로 위임한다.",
                "구현 결과마다 reviewer-35로 diff와 검증 결과를 점검한다.",
                "실패나 수정 루프가 필요하면 debugger-35로 원인을 정리한 뒤 적절한 구현 agent에 재위임한다.",
            ]
        )
        if task_size == "xlarge":
            lines.append("xlarge는 phase별 계획, 구현, 리뷰, 검증을 분리한다.")
    lines.append("사용자 판단이 필요하면 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다. 일반 텍스트 질문으로 대체하지 않는다.")
    return lines


def _is_frontend_task(state: PromptBuilderState, parts: dict[str, Any]) -> bool:
    intent = state.get("intent", {})
    task_type = str(intent.get("task_type") or parts.get("task_type") or "").lower()
    if task_type in {"frontend", "fullstack"}:
        return True
    text = " ".join(
        [
            state.get("user_message", ""),
            str(intent.get("task_summary") or ""),
            json.dumps(parts, ensure_ascii=False),
            json.dumps(intent.get("search_queries", []), ensure_ascii=False),
            json.dumps(intent.get("target_files", []), ensure_ascii=False),
        ]
    ).lower()
    frontend_keywords = [
        "css",
        "scss",
        "style",
        "스타일",
        "레이아웃",
        "버튼",
        "화면",
        "ui",
        "dom",
        "vue",
        "react",
        "component",
        "컴포넌트",
        "modal",
        "모달",
        "router",
        "route",
        "xterm",
        "tab",
        "panel",
        "drawer",
        "animation",
        "애니메이션",
        "bling",
        "블링",
    ]
    return any(keyword in text for keyword in frontend_keywords)


def _direct_tool_cheatsheet() -> list[str]:
    return [
        line
        for line in render_qwencode_tool_cheatsheet()
        if not line.lower().startswith("agent:")
    ]


def _filter_fast_section_lines(items: list[str]) -> list[str]:
    forbidden = (
        "티셔츠",
        "subagent",
        "coder-35",
        "reviewer-35",
        "ultrawork",
        "superpowers",
        "task_size",
        "team",
    )
    return [item for item in items if not any(token in item for token in forbidden)]


def _merge_unique(existing: list[str], additions: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *additions]:
        key = item.strip()
        if not key or key in seen:
            continue
        merged.append(key)
        seen.add(key)
        if len(merged) >= limit:
            break
    return merged


def _default_required_search(state: PromptBuilderState) -> list[str]:
    intent = state.get("intent", {})
    queries = _clean_string_list(intent.get("search_queries"), 8, 160)
    if not queries:
        queries = _fallback_queries(state["user_message"])
    lines: list[str] = []
    for query in queries[:5]:
        lines.append(f'kk-docs MCP `kk_search` 질의: "{query}"')
    for query in queries[:5]:
        lines.append(f'rg -n "{_escape_rg_query(query)}" .')
    return lines[:8]


def _extract_interview_answers(history: list[dict[str, str]]) -> str:
    answers = [
        item.get("content", "").strip()
        for item in history[-12:]
        if item.get("role") == "user" and item.get("content", "").strip().startswith("[Prompt Builder interview answers]")
    ]
    if not answers:
        return "- 아직 별도 인터뷰 답변 없음. 사용자의 원 요청, KK docs MCP 근거, 현재 코드 근거를 기준으로 진행한다."
    return "\n\n".join(answers[-2:])


def _escape_rg_query(query: str) -> str:
    return query.replace("\\", "\\\\").replace('"', '\\"')


TEAM_PROMPT_SECTIONS = [
    "## KIWI work mode lock",
    "## 작업 목표",
    "## 사용자 확인 답변",
    "## 프로젝트 지식 베이스 우선 참고",
    "## KK docs MCP 참고 근거",
    "## Project Info Layer 시작 컨텍스트",
    "## 티셔츠 사이징",
    "## 필수 읽기 파일",
    "## 필수 검색",
    "## 구현 규칙",
    "## 영향도 지도 작성",
    "## subagent 운영 계약",
    "## qwencode 기본 tool 사용법 초간단 참조",
    "## 검증 계획",
    "## 완료 보고 형식",
    "## 중단 조건",
    "## 진행 방식",
]

FAST_PROMPT_SECTIONS = [
    "## KIWI work mode lock",
    "## 작업 목표",
    "## 사용자 확인 답변",
    "## 프로젝트 지식 베이스 우선 참고",
    "## KK docs MCP 참고 근거",
    "## Project Info Layer 시작 컨텍스트",
    "## 필수 읽기 파일",
    "## 필수 검색",
    "## 구현 규칙",
    "## 영향도 지도 작성",
    "## FAST/lightwork 직접 실행 계약",
    "## qwencode 직접 tool 사용법 초간단 참조",
    "## 검증 계획",
    "## 완료 보고 형식",
    "## 중단 조건",
    "## 진행 방식",
]


def _lint_work_mode_prompt(prompt: str, work_mode: WorkMode) -> dict[str, Any]:
    if normalize_work_mode(work_mode) == "fast":
        return _lint_fast_prompt(prompt)
    return _lint_team_prompt(prompt, normalize_work_mode(work_mode))


def _lint_team_prompt(prompt: str, work_mode: WorkMode) -> dict[str, Any]:
    text = _strip_ultrawork_mode_switch(prompt)
    issues: list[str] = []
    required_sections = list(TEAM_PROMPT_SECTIONS)
    if work_mode == "superpowers":
        required_sections.append("## superpowers skill-first 계약")
    missing_sections = [section for section in required_sections if section not in text]
    if missing_sections:
        issues.append("missing_required_sections")
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        issues.append("missing_execution_mode_token")
    if f"Session work mode: `{work_mode}`" not in text or "Activation prefix:" not in text:
        issues.append("missing_mode_specific_lock")
    if "kk_search" not in text and "kk-docs" not in text:
        issues.append("missing_kk_docs_search_reference")
    if "KK docs MCP" not in text and "kk-docs" not in text:
        issues.append("missing_project_knowledge_base_reference")
    implementation_agents = [
        "coder-35",
        "dcp-front-developer",
        "dcp-backend-developer",
        "drt-front-developer",
        "drt-backend-developer",
        "drt-cms-front-developer",
        "drt-cms-backend-developer",
    ]
    is_xsmall = bool(re.search(r"(?:Kiwi\s*1차\s*산정|사용자\s*선택):\s*`?xsmall`?", text))
    if not any(agent in text for agent in implementation_agents) or (not is_xsmall and "explorer-35" not in text):
        issues.append("missing_implementation_agent_contract")
    if is_xsmall and "subagent" not in text:
        issues.append("missing_xsmall_solo_contract")
    if not is_xsmall and ("planner-35" not in text or "architect-35" not in text or "reviewer-35" not in text):
        issues.append("missing_consultant_agent_contract")
    if "티셔츠" not in text or not any(f"`{size}`" in text for size in ["xsmall", "small", "medium", "large", "xlarge"]):
        issues.append("missing_tshirt_sizing_contract")
    has_direct_tool_cheatsheet = "## qwencode 직접 tool 사용법 초간단 참조" in text
    has_legacy_tool_cheatsheet = "edit:" in text and "ask_user_question:" in text
    if not has_direct_tool_cheatsheet and not has_legacy_tool_cheatsheet:
        issues.append("missing_tool_cheatsheet")
    if "TodoWrite" not in text and "todo_write" not in text:
        issues.append("missing_todowrite_planning_gate")
    if "검증" not in text:
        issues.append("missing_verification_language")
    if "중단" not in text and "질문" not in text:
        issues.append("missing_stop_or_question_condition")
    if len(text) < 2200:
        issues.append("prompt_too_short_for_weak_model")

    score = 100
    score -= len(missing_sections) * 6
    score -= max(0, len(issues) - (1 if missing_sections else 0)) * 8
    score = max(0, score)
    return {
        "passed": score >= 86 and not missing_sections,
        "score": score,
        "issues": issues,
        "missing_sections": missing_sections,
        "required_sections": required_sections,
    }


def _lint_fast_prompt(prompt: str) -> dict[str, Any]:
    text = _strip_ultrawork_mode_switch(prompt)
    issues: list[str] = []
    missing_sections = [section for section in FAST_PROMPT_SECTIONS if section not in text]
    if missing_sections:
        issues.append("missing_required_sections")
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        issues.append("missing_execution_mode_token")
    if "Session work mode: `fast`" not in text or "Activation prefix: `lightwork`" not in text:
        issues.append("missing_mode_specific_lock")
    forbidden = ["티셔츠", "subagent", "coder-35", "ultrawork", "superpowers", "task_size", "team"]
    leaked = [token for token in forbidden if token in text]
    if leaked:
        issues.append("fast_forbidden_team_context")
    if "kk_search" not in text and "kk-docs" not in text:
        issues.append("missing_kk_docs_search_reference")
    has_direct_tool_cheatsheet = "## qwencode 직접 tool 사용법 초간단 참조" in text
    has_legacy_tool_cheatsheet = "edit:" in text and "ask_user_question:" in text
    if not has_direct_tool_cheatsheet and not has_legacy_tool_cheatsheet:
        issues.append("missing_tool_cheatsheet")
    if "TodoWrite" not in text and "todo_write" not in text:
        issues.append("missing_todowrite_planning_gate")
    if "검증" not in text:
        issues.append("missing_verification_language")
    if "중단" not in text and "질문" not in text:
        issues.append("missing_stop_or_question_condition")
    if len(text) < 1600:
        issues.append("prompt_too_short_for_weak_model")

    score = 100
    score -= len(missing_sections) * 6
    score -= max(0, len(issues) - (1 if missing_sections else 0)) * 8
    score = max(0, score)
    return {
        "passed": score >= 86 and not missing_sections and "fast_forbidden_team_context" not in issues,
        "score": score,
        "issues": issues,
        "forbidden_terms": leaked,
        "missing_sections": missing_sections,
        "required_sections": FAST_PROMPT_SECTIONS,
    }


def _repair_prompt_deterministically(prompt: str, lint: dict[str, Any], work_mode: WorkMode = "ultrawork") -> str:
    if normalize_work_mode(work_mode) == "fast":
        return _repair_fast_prompt_deterministically(prompt, lint)
    return _repair_team_prompt_deterministically(prompt, lint, normalize_work_mode(work_mode))


def _repair_fast_prompt_deterministically(prompt: str, lint: dict[str, Any]) -> str:
    text = _strip_ultrawork_mode_switch(prompt)
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        text = f"`ANALYSIS ONLY`\n\n{text}"
    direct_cheatsheet_text = "\n".join(f"- {line}" for line in _direct_tool_cheatsheet())
    repairs = {
        "## KIWI work mode lock": "- Session work mode: `fast` (FAST/lightwork)\n- Activation prefix: `lightwork`\n- This mode is locked for the current console session after first activation.\n- If the user later sends another work-mode prefix, KIWI blocks it with 409; start a new console session to change mode.",
        "## 작업 목표": "- 사용자의 요청을 현재 프로젝트 용어로 재정의하고, 완료 조건을 먼저 확인한다.",
        "## 사용자 확인 답변": "- 인터뷰 답변이 있으면 그대로 반영한다. 없으면 사용자의 원 요청을 기준으로 진행한다.",
        "## 프로젝트 지식 베이스 우선 참고": "- `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고 관련 pack 문서를 seed 지식으로 사용한다.\n- Project Info Layer는 `D:/aiops/docs/<project-key>/project-info/`가 실제로 있을 때만 선택적으로 읽는다.\n- project-relative `docs/<project-key>/...` 또는 `docs/kiwi/project-info/...` 경로를 시도하지 않는다.\n- KK docs MCP `kk_search`, 현재 코드 read/search 근거로 seed 지식을 검증한다.\n- 문서와 현재 코드가 충돌하면 현재 코드 근거를 우선한다.",
        "## KK docs MCP 참고 근거": "- 현재 KK docs MCP 검색 근거가 없으면 `kk_search`로 필요한 문서를 먼저 찾는다.",
        "## Project Info Layer 시작 컨텍스트": "\n".join(
            [
                "- Project Info Layer status: missing.",
                "- Required reading: D:/aiops/docs/<project-key>/knowledge/00-index.md when present.",
                "- Optional reading: D:/aiops/docs/<project-key>/project-info/ only if that central directory exists.",
                "- Target files/domain hints: missing; refresh Project Info before relying on shared project facts.",
                "- Do not paste full project-info.json or full EAI markdown into prompts.",
            ]
        ),
        "## 필수 읽기 파일": "- `QWEN.md`\n- `KIWI.md`\n- 관련 route/view/store 또는 controller/service/mapper 파일",
        "## 필수 검색": "- kk-docs MCP `kk_search` 질의: \"<요구사항 핵심 키워드>\"\n- `rg -n \"<요구사항 핵심 키워드>\" .`",
        "## 구현 규칙": "- 구현 전 영향도 지도를 작성한다.\n- 관련 없는 리팩터링과 광범위 포맷팅을 하지 않는다.",
        "## 영향도 지도 작성": "- entrypoint, producer, carrier, API, persistence/cache/session, downstream consumer를 정리한다.",
        "## FAST/lightwork 직접 실행 계약": "- Kiwi 단독으로 요구사항을 재정의하고 `todo_write` tool로 짧은 계획과 완료 조건을 먼저 기록한다.\n- 현재 파일을 읽고 가장 작은 직접 변경만 수행한다.\n- 변경 후 focused verification을 실행하거나 실행 불가 이유와 대체 확인 방법을 보고한다.",
        "## qwencode 직접 tool 사용법 초간단 참조": direct_cheatsheet_text,
        "## 검증 계획": "- 가능한 검증 명령을 식별해 실행한다. 실행할 수 없으면 이유와 대체 확인 방법을 보고한다.",
        "## 완료 보고 형식": "- 변경/분석 요약\n- 확인한 근거\n- 변경 파일\n- 실행한 검증\n- 남은 위험",
        "## 중단 조건": "- 업무 의미, API carrier, 저장 위치, shared consumer가 불명확하면 편집하지 말고 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool로 질문한다.",
        "## 진행 방식": "- `todo_write` tool로 요구사항, 실행 순서, 완료 조건을 먼저 정리한다.\n- 계획한 직접 변경만 수행하고 범위를 넓히지 않는다.\n- 수정 후 검증 결과와 남은 위험을 짧게 보고한다.",
    }
    appended: list[str] = []
    missing = lint.get("missing_sections")
    if isinstance(missing, list) and missing:
        appended.extend(["", "## Linter 보강 섹션"])
        for section in missing:
            if section in repairs:
                appended.extend(["", str(section), repairs[section]])
    if len(f"{text}\n{chr(10).join(appended)}") < 1600:
        appended.extend(
            [
                "",
                "## 직접 실행 보강",
                "- 시작 전에 요청을 한 문장으로 재정의하고, 완료 조건과 비목표를 분리한다.",
                "- 코드 근거가 필요한 경우 현재 레포의 실제 파일을 읽고, 추정으로 구현하지 않는다.",
                "- 파일을 읽을 때는 path, symbol, caller, consumer, branch condition을 메모한다.",
                "- 수정한 뒤에는 관련 테스트나 빌드 명령을 우선 실행하고, 불가능하면 정적 근거와 수동 확인 절차를 보고한다.",
            ]
        )
    return f"{text}\n{chr(10).join(appended)}".strip()


def _repair_team_prompt_deterministically(prompt: str, lint: dict[str, Any], work_mode: WorkMode) -> str:
    text = _strip_ultrawork_mode_switch(prompt)
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        text = f"`ANALYSIS ONLY`\n\n{text}"
    missing = lint.get("missing_sections")
    tool_cheatsheet_text = "\n".join(f"- {line}" for line in render_qwencode_tool_cheatsheet())
    definition = work_mode_definition(work_mode)
    repairs = {
        "## 작업 목표": "- 사용자의 요청을 현재 프로젝트 용어로 재정의하고, 완료 조건을 먼저 확인한다.",
        "## KIWI work mode lock": f"- Session work mode: `{definition.key}` ({definition.label})\n- Activation prefix: `{definition.prefix}`\n- This mode is locked for the current console session after first activation.\n- If the user later sends another work-mode prefix, KIWI blocks it with 409; start a new console session to change mode.",
        "## 사용자 확인 답변": "- 인터뷰 답변이 있으면 그대로 반영한다. 없으면 사용자의 원 요청, KK docs MCP 근거, 현재 코드 근거를 기준으로 진행한다.",
        "## 프로젝트 지식 베이스 우선 참고": "- `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고 관련 pack 문서를 seed 지식으로 사용한다.\n- Project Info Layer는 `D:/aiops/docs/<project-key>/project-info/`가 실제로 있을 때만 선택적으로 읽는다.\n- project-relative `docs/<project-key>/...` 또는 `docs/kiwi/project-info/...` 경로를 시도하지 않는다.\n- KK docs MCP `kk_search`, 현재 코드 read/search 근거로 seed 지식을 검증한다.\n- 문서와 현재 코드가 충돌하면 현재 코드 근거를 우선한다.",
        "## KK docs MCP 참고 근거": "- 현재 KK docs MCP 검색 근거가 없으면 `kk_search`로 필요한 문서를 먼저 찾는다.",
        "## Project Info Layer 시작 컨텍스트": "\n".join(
            [
                "- Project Info Layer status: missing.",
                "- Required reading: D:/aiops/docs/<project-key>/knowledge/00-index.md when present.",
                "- Optional reading: D:/aiops/docs/<project-key>/project-info/ only if that central directory exists.",
                "- Target files/domain hints: missing; refresh Project Info before relying on shared project facts.",
                "- Do not paste full project-info.json or full EAI markdown into prompts.",
            ]
        ),
        "## 티셔츠 사이징": "- 사용자 선택: `medium`\n- 최종 source of truth: 사용자 선택값을 따른다.\n- 선택 근거: 사용자가 선택한 규모다.\n- ultrawork 운영 모드: balanced\n- 시작 시 이 사이징 결과와 그에 맞는 계획을 사용자에게 먼저 보고한다.",
        "## 필수 읽기 파일": "- `QWEN.md`\n- `KIWI.md`\n- 관련 route/view/store 또는 controller/service/mapper 파일",
        "## 필수 검색": "- kk-docs MCP `kk_search` 질의: \"<요구사항 핵심 키워드>\"\n- `rg -n \"<요구사항 핵심 키워드>\" .`\n- 필요한 경우 현재 코드베이스에서 관련 symbol/path를 확인한다.",
        "## 구현 규칙": "- 구현 전 영향도 지도를 작성한다.\n- 관련 없는 리팩터링과 광범위 포맷팅을 하지 않는다.",
        "## 영향도 지도 작성": "- entrypoint, producer, carrier, API, persistence/cache/session, downstream consumer를 정리한다.",
        "## subagent 운영 계약": "- Kiwi는 먼저 티셔츠 사이징 결과와 실행 계획을 보고한다.\n- xsmall은 subagent 호출 없이 Kiwi가 직접 짧게 처리한다.\n- small 이상에서 파일 위치가 불명확하면 explorer-35를 최대 5개까지 병렬 read-only 탐색으로 사용한다.\n- small은 구현 agent 중심으로 짧게 진행하고 planner-35/architect-35는 생략한다.\n- medium 이상에서 데이터/API/store/공유 모듈 위험이 있으면 architect-35를 호출한다.\n- large/xlarge는 planner-35, architect-35, reviewer-35, debugger-35, tester-35를 규모에 맞게 사용한다.\n- 구현은 coder-35 또는 프로젝트 특화 developer agent가 담당한다.\n- 구현 위임에는 Objective, Scope, Files/ownership, Required reading, Mandatory workflow, Exact steps, Non-goals, Verification, Required response를 포함한다.\n- Mandatory workflow는 scope 확인 -> 현재 파일 read -> impact map -> 작은 수정 -> focused verification -> evidence 보고 순서다.\n- Required response는 scope confirmed/stop reason, files read, files changed, impact map, verification, remaining risks/exact question을 요구한다.\n- 하나의 구현 위임은 하나의 repair slice만 맡기고, 실패하면 Kiwi로 복귀한다.\n- 사용자 판단이 필요하면 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다. 일반 텍스트 질문으로 대체하지 않는다.",
        "## qwencode 기본 tool 사용법 초간단 참조": tool_cheatsheet_text,
        "## 검증 계획": "- 가능한 검증 명령을 식별해 실행한다. 실행할 수 없으면 이유와 대체 확인 방법을 보고한다.",
        "## 완료 보고 형식": "- 변경/분석 요약\n- 확인한 근거\n- 변경 파일\n- 실행한 검증\n- 남은 위험",
        "## 중단 조건": "- 업무 의미, API carrier, 저장 위치, shared consumer가 불명확하면 편집하지 말고 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool로 질문한다.",
        "## 진행 방식": "- 한국어 계획으로 요구사항을 점검한다.\n- 사용자 선택 티셔츠 사이징 결과와 규모별 계획을 먼저 보고한다.\n- xsmall은 subagent 없이 Kiwi가 단독 처리한다.\n- small은 explorer-35와 구현 agent 중심으로 짧게 처리한다.\n- medium은 구현 agent와 reviewer-35 중심으로 진행하고, 위험할 때 architect-35를 짧게 호출한다.\n- large/xlarge는 planner-35, architect-35, 구현 agent, reviewer-35, debugger-35/tester-35를 규모에 맞게 사용한다.\n- 사용자 판단이 필요하면 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다. 일반 텍스트 질문으로 대체하지 않는다.",
    }
    appended: list[str] = []
    if isinstance(missing, list) and missing:
        appended.extend(["", "## Linter 보강 섹션"])
        for section in missing:
            if section in repairs:
                appended.extend(["", str(section), repairs[section]])
    issue_repairs = {
        "missing_implementation_agent_contract": "## 구현 agent 보강 계약\n- 구현은 coder-35 또는 프로젝트 특화 developer agent가 담당한다.\n- DCP Front에서는 dcp-front-developer, dcp-services에서는 dcp-backend-developer를 사용한다.\n- DRT Front에서는 drt-front-developer, DRT API에서는 drt-backend-developer를 사용한다.\n- DRT CMS frontend 작업은 drt-cms-front-developer, backend 작업은 drt-cms-backend-developer를 사용한다.\n- 구현 agent는 Objective, Scope, Files/ownership, Required reading, Mandatory workflow, Exact steps, Non-goals, Verification command, Required response를 받은 뒤 하나의 좁은 repair slice만 수행한다.\n- Mandatory workflow는 scope 확인 -> 현재 파일 read -> impact map -> 작은 수정 -> focused verification -> evidence 보고 순서다.\n- Required response는 scope confirmed/stop reason, files read, files changed, impact map, verification, remaining risks/exact question을 포함한다.\n- 하나의 구현 위임은 하나의 repair slice만 맡기고, 실패하면 Kiwi가 debugger-35를 거친 뒤 다음 slice를 위임한다.\n- 파일 위치가 불명확하면 explorer-35를 최대 5개까지 병렬 read-only 탐색으로 사용한다.\n- 구현 agent가 2번 실패하면 3번째 시도 전 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool로 사용자 허락을 받는다.",
        "missing_xsmall_solo_contract": "## xsmall 단독 처리 보강\n- xsmall은 subagent 호출 없이 Kiwi가 직접 읽기/수정/검증을 짧게 수행한다.\n- 영향 범위가 커지면 현재 세션에서 임의로 size를 바꾸지 말고 더 큰 size의 새 콘솔을 시작하라고 보고한다.",
        "missing_consultant_agent_contract": "## consultant agent 보강 계약\n- planner-35는 요구사항과 수용조건을 점검한다.\n- architect-35는 영향도와 설계 위험을 점검한다.\n- reviewer-35는 모든 구현 결과 뒤 최종 diff와 검증 누락을 점검한다.\n- debugger-35는 실패/수정 루프 전 원인과 교정 전략을 점검한다.",
        "missing_tshirt_sizing_contract": "## 티셔츠 사이징 보강\n- 사용자 선택: `medium`\n- 최종 source of truth: 사용자 선택값을 따른다.\n- 선택 근거: 사용자가 선택한 규모다.\n- ultrawork 운영 모드: balanced\n- 시작 시 사이징 결과와 계획을 사용자에게 보고한다.",
        "missing_tool_cheatsheet": "## qwencode 기본 tool 사용법 초간단 참조\n" + tool_cheatsheet_text,
        "missing_todowrite_planning_gate": "## 계획 보강 계약\n- Kiwi는 구현 전 `todo_write` tool로 작업 순서, 현재 항목, 완료 조건을 정리한다. 도구가 없을 때만 한국어 visible plan fallback을 보고한다.",
        "missing_kk_docs_search_reference": "## 필수 검색 보강\n- kk-docs MCP `kk_search` 질의: \"<요구사항 핵심 키워드>\"\n- kk-docs MCP `kk_search` 질의: \"<화면ID|API|업무 용어>\"",
        "missing_project_knowledge_base_reference": "## 지식 베이스 보강\n- `D:/aiops/docs/<project-key>/knowledge/00-index.md`가 있으면 먼저 읽고 관련 pack 문서를 seed 지식으로 사용한다.\n- Project Info Layer는 `D:/aiops/docs/<project-key>/project-info/`가 실제로 있을 때만 선택적으로 읽는다.\n- project-relative `docs/<project-key>/...` 또는 `docs/kiwi/project-info/...` 경로를 시도하지 않는다.\n- KK docs MCP `kk_search`, 현재 코드 read/search 근거로 seed 지식을 검증한다.\n- 문서와 현재 코드가 충돌하면 현재 코드 근거를 우선한다.",
        "missing_verification_language": "## 검증 보강\n- 가능한 검증 명령을 실행하고, 실행할 수 없으면 이유와 대체 확인 방법을 보고한다.",
        "missing_mode_specific_lock": repairs["## KIWI work mode lock"],
        "missing_stop_or_question_condition": "## 중단/질문 보강\n- 업무 의미, API carrier, 저장 위치, shared consumer가 불명확하면 편집하지 말고 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool로 질문한다.",
    }
    for issue in lint.get("issues", []):
        repair = issue_repairs.get(str(issue))
        if repair and repair not in text:
            appended.extend(["", repair])
    if len(f"{text}\n{chr(10).join(appended)}") < 2200:
        appended.extend(
            [
                "",
                "## 약한 모델 실행 보강",
                "- 시작 전에 사용자의 요청을 한 문장으로 재정의하고, 완료 조건과 비목표를 분리한다.",
                "- 코드 근거가 필요한 경우 현재 레포의 실제 파일을 읽고, 추정으로 구현하지 않는다.",
                "- 파일을 읽을 때는 path, symbol, caller, consumer, branch condition을 메모한다.",
                "- 구현 전에 영향도 지도에서 entrypoint, producer, carrier, API, persistence/cache/session, downstream consumer를 채운다.",
                "- 구현 범위가 넓으면 coder-35 또는 프로젝트 특화 developer agent에 좁은 repair slice로 나누어 지시하고, 각 slice 뒤에는 reviewer-35 검토를 거친다.",
                "- 코드를 수정한 뒤에는 관련 테스트나 빌드 명령을 우선 실행하고, 불가능하면 정적 근거와 수동 확인 절차를 보고한다.",
                "- 최종 보고에는 변경 파일, 확인 근거, 검증 결과, 남은 위험, 사용자 판단이 필요한 항목을 포함한다.",
            ]
        )
    return f"{text}\n{chr(10).join(appended)}".strip()


def _summarize_evaluations(evaluations: list[dict[str, Any]], lint: dict[str, Any]) -> dict[str, Any]:
    if not evaluations:
        return {
            "score": lint.get("score", 0),
            "issues": lint.get("issues", []),
            "improvements": [],
            "attempts": [],
        }
    last = evaluations[-1]
    issues: list[str] = []
    improvements: list[str] = []
    for evaluation in evaluations:
        if isinstance(evaluation.get("issues"), list):
            issues.extend(str(item) for item in evaluation["issues"] if str(item).strip())
        if isinstance(evaluation.get("improvements"), list):
            improvements.extend(str(item) for item in evaluation["improvements"] if str(item).strip())
    return {
        "score": last.get("score", lint.get("score", 0)),
        "issues": issues[:12],
        "improvements": improvements[:12],
        "attempts": [
            {
                "attempt": item.get("attempt"),
                "score": item.get("score"),
                "issue_count": len(item.get("issues", [])) if isinstance(item.get("issues"), list) else 0,
            }
            for item in evaluations
        ],
    }


def _summarize_kk_docs_evidence(kk_docs_results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for search in kk_docs_results[:5]:
        query = str(search.get("query") or "").strip()
        if search.get("ok") is False:
            lines.append(f"- KK 검색 `{query}` 실패: {search.get('error')}")
            continue
        results = [item for item in search.get("results", []) if isinstance(item, dict)]
        lines.append(f"- KK 검색 `{query}`: {len(results)}건")
        for item in results[:3]:
            title = str(item.get("title") or "(untitled)").strip()
            topic = str(item.get("topic") or "").strip()
            confidence = item.get("confidence")
            content = re.sub(r"\s+", " ", str(item.get("content") or "")).strip()
            suffix = f" / confidence={confidence}" if confidence is not None else ""
            lines.append(f"  - {title}{f' [{topic}]' if topic else ''}{suffix}: {content[:260]}")
    return "\n".join(lines) if lines else "- KK docs MCP 검색 결과가 없거나 비활성화되어 있다."


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if str(item).strip()]


def _strip_ultrawork_mode_switch(prompt: str) -> str:
    return re.sub(
        r"^\s*(?:lightwork|fast|lw|ultrawork(?:_(?:xsmall|small|medium|large|xlarge))?|ulw(?:_(?:xsmall|small|medium|large|xlarge))?|superpowers(?:_(?:xsmall|small|medium|large|xlarge))?|spw(?:_(?:xsmall|small|medium|large|xlarge))?)(?:\r?\n)+",
        "",
        prompt.strip(),
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def _enforce_tshirt_policy_section(prompt: str, policy: dict[str, Any]) -> str:
    if not policy:
        return prompt
    section = "\n".join(render_tshirt_section(policy))
    pattern = re.compile(r"(?ms)^## 티셔츠 사이징\s*\n.*?(?=^## |\Z)")
    if pattern.search(prompt):
        return pattern.sub(section.rstrip() + "\n", prompt, count=1).strip()
    marker = "\n## 필수 읽기 파일"
    if marker in prompt:
        return prompt.replace(marker, f"\n{section}\n\n## 필수 읽기 파일", 1).strip()
    return f"{prompt.rstrip()}\n\n{section}".strip()


def _append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


INTENT_SYSTEM_PROMPT = """
너는 KIWI Prompt Builder의 의도 분석 노드다.
사용자의 삼성생명 DCP 작업 요청을 qwencode ultrawork에 넘길 수 있을지 판단한다.
반드시 JSON만 반환한다.

스키마:
{
  "task_summary": "레포 용어로 다시 쓴 한 문장",
  "task_type": "frontend|backend|fullstack|docs|review|unknown",
  "mode": "analysis|implement|review",
  "ready_hint": true,
  "missing_information": ["부족한 정보"],
  "questions": ["사용자에게 물을 질문"],
  "search_queries": ["현재 코드베이스에서 찾을 핵심 키워드"],
  "target_files": ["확실한 후보 파일 경로"],
  "risk_flags": ["주의점"]
}

규칙:
- 질문은 최대 4개, 꼭 필요한 것만 만든다.
- 검색어는 업무 용어, 서비스명, 모듈명, 화면ID, API path, store key 중심으로 만든다.
- 구현 의도가 분명하면 mode=implement, 단순 조사면 analysis, 리뷰 요청이면 review로 둔다.
- 티셔츠 사이징은 UI 사용자 선택값만 source of truth다. Prompt Builder는 규모를 산정하거나 추천하지 않는다.
- 의도 분석은 검색어, 후보 파일, 위험 신호, 누락 질문만 정리한다.
- 검색어는 이후 현재 코드베이스의 symbol/path 확인에 사용된다.
""".strip()


INTENT_SYSTEM_PROMPT_SUPERPOWERS = """
너는 KIWI Prompt Builder의 superpowers 의도 분석 노드다.
목표는 Qwen3.5-397B Kiwi가 폐쇄망 qwencode에서 skill-first로 실행할 수 있는 요청 분석을 만드는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "task_summary": "레포 용어로 다시 쓴 한 문장",
  "task_type": "frontend|backend|fullstack|docs|review|unknown",
  "mode": "analysis|implement|review",
  "ready_hint": true,
  "missing_information": ["부족한 정보"],
  "questions": ["사용자에게 물을 질문"],
  "search_queries": ["현재 코드베이스에서 찾을 핵심 키워드"],
  "target_files": ["확실한 후보 파일 경로"],
  "risk_flags": ["주의점"]
}

규칙:
- 질문은 최대 4개, 꼭 필요한 것만 만든다.
- 티셔츠 사이징은 UI 사용자 선택값만 source of truth다. Prompt Builder는 규모를 산정하거나 추천하지 않는다.
- xsmall=Kiwi 단독, small=light delegation, medium=balanced, large/xlarge=full phased delegation 기준은 선택된 size 설명에만 사용한다.
- superpowers는 skill-first mode다. 최종 프롬프트는 `kiwi-superpowers`, `using-superpowers`, 요청별 개별 skill 로드, 중앙 knowledge 우선 확인, optional Project Info 확인, impact map, 검증 계획을 먼저 요구해야 한다.
- local superpowers skill은 built-in `skill` tool로 호출하라고 명시하고, 실패 시에만 SKILL.md 파일 직접 읽기 fallback을 쓰게 한다.
- 검색어는 업무 용어, 서비스명, 모듈명, 화면ID, API path, store key 중심으로 만든다.
- 구현 의도가 분명하면 mode=implement, 단순 조사면 analysis, 리뷰 요청이면 review로 둔다.
""".strip()


INTENT_SYSTEM_PROMPT_FAST = """
너는 KIWI Prompt Builder의 FAST/lightwork 의도 분석 노드다.
사용자의 요청을 Kiwi가 직접 처리할 짧은 지시문으로 만들 수 있을지 판단한다.
반드시 JSON만 반환한다.

스키마:
{
  "task_summary": "레포 용어로 다시 쓴 한 문장",
  "task_type": "frontend|backend|fullstack|docs|review|unknown",
  "mode": "analysis|implement|review",
  "ready_hint": true,
  "missing_information": ["부족한 정보"],
  "questions": ["사용자에게 물을 질문"],
  "search_queries": ["KK docs MCP와 현재 코드베이스에서 찾을 핵심 키워드"],
  "target_files": ["확실한 후보 파일 경로"],
  "risk_flags": ["주의점"]
}

규칙:
- 질문은 최대 4개, 꼭 필요한 것만 만든다.
- 검색어는 업무 용어, 서비스명, 모듈명, 화면ID, API path, store key 중심으로 만든다.
- 구현 의도가 분명하면 mode=implement, 단순 조사면 analysis, 리뷰 요청이면 review로 둔다.
- 작은 직접 작업으로 보기 어렵거나 위험 범위가 넓으면 risk_flags에 stronger_work_mode_needed를 넣는다.
- 검색어는 이후 현재 코드베이스의 symbol/path 확인에 사용된다.
""".strip()


COMPOSE_SYSTEM_PROMPT = """
너는 KIWI Prompt Builder의 최종 조립 노드다.
목표는 약한 코딩 모델도 안전하게 따를 수 있는 qwencode ultrawork용 구조화 프롬프트를 만드는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "status": "ready|needs_input",
  "mode": "analysis|implement|review",
  "assistant_message": "사용자에게 보여줄 짧은 설명",
  "questions": ["status가 needs_input이면 필요한 질문"],
  "interview_tool": {
    "name": "interview_user",
    "reason": "사용자 확인이 필요한 이유",
    "questions": [
      {
        "id": "stable_snake_case_id",
        "header": "12자 이내 라벨",
        "question": "사용자에게 묻는 한 문장",
        "options": [
          {"label": "추천 보기", "description": "이 보기를 고르면 프롬프트가 어떻게 달라지는지"},
          {"label": "다른 보기", "description": "영향 설명"}
        ],
        "allow_other": true
      }
    ]
  },
  "prompt_parts": {
    "title": "작업 제목",
    "task": "구체화된 작업 목표",
    "target_files": ["후보 파일"],
    "required_reading": ["필수 읽기 파일"],
    "required_search": ["현재 코드베이스에서 실행할 검색 명령 또는 확인 항목"],
    "implementation_rules": ["구현 규칙"],
    "verification": ["검증 계획"],
    "output_contract": ["완료 보고 항목"],
    "stop_conditions": ["중단 조건"]
  }
}

판단 규칙:
- 구현 대상, 화면/도메인, 기대 동작 중 핵심이 비어 있으면 needs_input을 반환한다.
- needs_input이면 반드시 interview_tool.name=\"interview_user\"와 clickable option에 맞는 interview_tool.questions를 포함한다.
- interview_user 질문은 최대 3개, 각 질문의 options는 2~4개로 만든다.
- 현재 코드에서 먼저 확인해야 할 검색어와 읽기 파일이 명확하면 ready로 만들 수 있다.
- ready이면 필수 검색, 영향도 지도, subagent 운영 계약, 검증 계획을 prompt_parts에 반영한다.
- UI에서 전달된 사용자 선택 티셔츠 사이징을 최종 source of truth로 존중한다. Prompt Builder가 규모를 산정하거나 추천하지 않는다.
- 최종 프롬프트에서 사용자 선택 규모와 선택 규모별 실행 계획을 먼저 보고하도록 만든다.
- xsmall은 subagent 호출 없이 Kiwi 단독 처리, small은 light 모드, medium은 developer+review 중심, large/xlarge는 planner/architect/reviewer/debugger/tester까지 쓰는 full 모드로 분기한다.
- DCP Front 프로젝트에서는 구현 agent 이름을 `dcp-front-developer`로 쓴다. dcp-services 또는 하위 모듈에서는 `dcp-backend-developer`로 쓴다.
- DRT Front 프로젝트에서는 `drt-front-developer`, DRT API 프로젝트에서는 `drt-backend-developer`를 쓴다.
- DRT CMS 프로젝트에서는 frontend/Quasar 화면이면 `drt-cms-front-developer`, backend/API/DB이면 `drt-cms-backend-developer`를 쓴다. 그 외에는 `coder-35`를 쓴다.
- DCP 작업은 route/screen/store/API/EAI/Redis 흐름을 추적하도록 지시한다.
- DRT 작업은 route/view/Pinia/DrtHttpClient/service 또는 controller/service/mapper/XML/profile config 흐름을 추적하도록 지시한다.
- 보험금 청구나 상태 전파 작업은 positional array, DataStore, route params, spotLoad/spotSave, downstream consumer를 특히 강조한다.
- 구현 agent 결과마다 reviewer-35 리뷰를 필수로 넣고, 실패/수정 루프 전에는 debugger-35가 원인과 교정 전략을 정리하게 한다.
- 애매하거나 사용자 판단이 필요한 항목은 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출하라고 지시한다. 일반 텍스트 질문으로 대체하지 않는다.
- read_file은 `file_path` 절대경로, edit은 `file_path/old_string/new_string`, ask_user_question은 `questions` 객체 배열이라는 실제 파라미터명을 1줄씩 얇게 넣는다.
- 관련 없는 리팩터링과 광범위 포맷팅을 금지한다.
""".strip()


COMPOSE_SYSTEM_PROMPT_FAST = """
너는 KIWI Prompt Builder의 FAST/lightwork 최종 조립 노드다.
목표는 Kiwi가 직접 계획, 실행, 검증할 수 있는 짧고 명확한 qwencode 지시문 재료를 만드는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "status": "ready|needs_input",
  "mode": "analysis|implement|review",
  "assistant_message": "사용자에게 보여줄 짧은 설명",
  "questions": ["status가 needs_input이면 필요한 질문"],
  "interview_tool": {
    "name": "interview_user",
    "reason": "사용자 확인이 필요한 이유",
    "questions": [
      {
        "id": "stable_snake_case_id",
        "header": "12자 이내 라벨",
        "question": "사용자에게 묻는 한 문장",
        "options": [
          {"label": "추천 보기", "description": "이 보기를 고르면 프롬프트가 어떻게 달라지는지"},
          {"label": "다른 보기", "description": "영향 설명"}
        ],
        "allow_other": true
      }
    ]
  },
  "prompt_parts": {
    "title": "작업 제목",
    "task": "구체화된 작업 목표",
    "target_files": ["후보 파일"],
    "required_reading": ["필수 읽기 파일"],
    "required_search": ["KK docs MCP 검색어와 현재 코드 확인 항목"],
    "implementation_rules": ["구현 규칙"],
    "verification": ["검증 계획"],
    "output_contract": ["완료 보고 항목"],
    "stop_conditions": ["중단 조건"]
  }
}

판단 규칙:
- 구현 대상, 화면/도메인, 기대 동작 중 핵심이 비어 있으면 needs_input을 반환한다.
- needs_input이면 반드시 interview_tool.name=\"interview_user\"와 clickable option에 맞는 interview_tool.questions를 포함한다.
- interview_user 질문은 최대 3개, 각 질문의 options는 2~4개로 만든다.
- ready이면 KK docs MCP 문서 근거 확인, 현재 코드 검색, 영향도 지도, 직접 실행 규칙, 검증 계획, 중단 조건을 prompt_parts에 반영한다.
- DCP 작업은 route/screen/store/API/EAI/Redis 흐름을 추적하도록 지시한다.
- 보험금 청구나 상태 전파 작업은 positional array, DataStore, route params, spotLoad/spotSave, downstream consumer를 특히 강조한다.
- 프론트/UI/CSS 작업이면 기존 CSS 구조, scoped/global style 위치, DOM 조작 방식, containing block, selector 우선순위, layout/animation side effect를 prompt_parts에 반영한다.
- 애매하거나 사용자 판단이 필요한 항목은 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출하라고 지시한다. 일반 텍스트 질문으로 대체하지 않는다.
- read_file은 `file_path` 절대경로, edit은 `file_path/old_string/new_string`, ask_user_question은 `questions` 객체 배열이라는 실제 파라미터명을 1줄씩 얇게 넣는다.
- 관련 없는 리팩터링과 광범위 포맷팅을 금지한다.
""".strip()


EVALUATE_SYSTEM_PROMPT = """
너는 KIWI Prompt Builder의 프롬프트 평가/개선 노드다.
목표는 Qwen3.5-397B Kiwi, 프로젝트 특화 developer agent, explorer-35 subagent가 폐쇄망에서 실수 없이 실행할 수 있는 ultrawork 프롬프트로 보강하는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "score": 0,
  "issues": ["문제"],
  "improvements": ["보강한 점"],
  "revised_prompt": "work mode switch 줄 없이 시작하는 완성된 전체 프롬프트"
}

규칙:
- revised_prompt는 반드시 전체 프롬프트다. patch나 일부 섹션만 반환하지 않는다.
- KIWI UI가 전송 시 선택된 work mode prefix(lightwork/ultrawork/superpowers)를 별도로 주입하므로 revised_prompt 맨 앞에 mode switch 한 줄을 넣지 않는다.
- lint가 지적한 missing section은 모두 채운다.
- 필수 검색, 영향도 지도, subagent 운영 계약, 검증 계획, 중단 조건을 구체화한다.
- 티셔츠 사이징 섹션과 규모별 ultrawork 운영 분기가 빠졌으면 보강한다.
- DCP/DRT/CMS 특화 프로젝트면 profile에 맞는 developer agent를 유지하고, 그 외에는 `coder-35`를 구현 agent로 유지한다.
- qwencode 기본 tool 사용법 치트시트는 10줄 안팎으로 얇게 유지한다.
- 구현 agent 이후 reviewer-35 필수 리뷰와 실패/수정 루프 전 debugger-35 분석 계약이 빠졌으면 보강한다.
- 약한 모델이 바로 실행할 수 있게 모호한 표현을 줄이고 실행 순서를 명확히 한다.
- 코드 수정이 허용되지 않은 mode면 ANALYSIS ONLY 또는 REVIEW ONLY를 유지한다.
""".strip()


COMPOSE_SYSTEM_PROMPT_SUPERPOWERS = """
너는 KIWI Prompt Builder의 superpowers 최종 조립 노드다.
목표는 Qwen3.5-397B Kiwi가 폐쇄망 qwencode에서 중앙 knowledge docs, optional Project Info Layer, `kiwi-superpowers`/`using-superpowers` 및 요청별 개별 skill을 안전하게 먼저 사용하도록 만드는 구조화 프롬프트 재료를 만드는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "status": "ready|needs_input",
  "mode": "analysis|implement|review",
  "assistant_message": "사용자에게 보여줄 짧은 설명",
  "questions": ["status가 needs_input이면 필요한 질문"],
  "interview_tool": {
    "name": "interview_user",
    "reason": "사용자 확인이 필요한 이유",
    "questions": [
      {
        "id": "stable_snake_case_id",
        "header": "12자 이내 라벨",
        "question": "사용자에게 묻는 한 문장",
        "options": [
          {"label": "추천 보기", "description": "이 보기를 고르면 프롬프트가 어떻게 달라지는지"},
          {"label": "다른 보기", "description": "영향 설명"}
        ],
        "allow_other": true
      }
    ]
  },
  "prompt_parts": {
    "title": "작업 제목",
    "task": "구체화된 작업 목표",
    "target_files": ["후보 파일"],
    "required_reading": ["필수 읽기 파일"],
    "required_search": ["현재 코드베이스에서 실행할 검색 명령 또는 확인 항목"],
    "implementation_rules": ["구현 규칙"],
    "verification": ["검증 계획"],
    "output_contract": ["완료 보고 항목"],
    "stop_conditions": ["중단 조건"]
  }
}

판단 규칙:
- ready이면 중앙 knowledge 우선 확인, optional Project Info Layer, `kiwi-superpowers`/`using-superpowers` skill-first 계약, selected task_size source of truth, impact map, 검증 계획을 prompt_parts에 반영한다.
- local superpowers skill은 built-in `skill` tool로 호출하라고 반영하고, 실패 시에만 SKILL.md 파일 직접 읽기 fallback을 쓰게 한다.
- selected task_size from UI is the source of truth. Do not describe a Prompt Builder recommendation.
- superpowers policy and skill are the source of truth for this mode. Delegated agents are used only after skill-first context is loaded.
- DCP Front 프로젝트에서는 구현 agent 이름을 `dcp-front-developer`로 쓴다. dcp-services 또는 하위 모듈에서는 `dcp-backend-developer`로 쓴다.
- DRT Front 프로젝트에서는 `drt-front-developer`, DRT API 프로젝트에서는 `drt-backend-developer`를 쓴다.
- DRT CMS 프로젝트에서는 frontend/Quasar 화면이면 `drt-cms-front-developer`, backend/API/DB이면 `drt-cms-backend-developer`를 쓴다. 그 외에는 `coder-35`를 쓴다.
- xsmall은 agent 호출 없이 Kiwi 단독 처리, small은 한 개 narrow implementation slice, medium은 explorer/developer/reviewer 중심, large/xlarge는 planner/architect/reviewer/debugger/tester까지 분기한다.
- 애매하거나 사용자 판단이 필요한 항목은 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출하라고 지시한다. 일반 텍스트 질문으로 대체하지 않는다.
- read_file은 `file_path` 절대경로, edit은 `file_path/old_string/new_string`, ask_user_question은 `questions` 객체 배열이라는 실제 파라미터명을 1줄씩 얇게 넣는다.
- 관련 없는 리팩터링과 광범위 포맷팅을 금지한다.
""".strip()


EVALUATE_SYSTEM_PROMPT_SUPERPOWERS = """
너는 KIWI Prompt Builder의 superpowers 프롬프트 평가/개선 노드다.
목표는 Qwen3.5-397B Kiwi가 폐쇄망에서 중앙 knowledge docs, optional Project Info Layer, `kiwi-superpowers`/`using-superpowers` 및 요청별 개별 skill을 먼저 읽고 안전하게 실행할 수 있는 프롬프트로 보강하는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "score": 0,
  "issues": ["문제"],
  "improvements": ["보강한 점"],
  "revised_prompt": "work mode switch 줄 없이 시작하는 완성된 전체 프롬프트"
}

규칙:
- revised_prompt는 반드시 전체 프롬프트다. patch나 일부 섹션만 반환하지 않는다.
- KIWI UI가 전송 시 선택된 work mode prefix(lightwork/ultrawork/superpowers)를 별도로 주입하므로 revised_prompt 맨 앞에 mode switch 한 줄을 넣지 않는다.
- 중앙 knowledge 우선 확인, optional Project Info Layer 시작 컨텍스트, 티셔츠 사이징, `kiwi-superpowers`/`using-superpowers` skill tool 우선 계약, 영향도 지도, 검증 계획, 중단 조건을 모두 유지한다.
- selected task_size from UI is the source of truth. Do not invent, score, recommend, or replace the selected size.
- superpowers policy and skill are the source of truth for this mode.
- DCP/DRT/CMS 특화 프로젝트면 profile에 맞는 developer agent를 유지하고, 그 외에는 `coder-35`를 구현 agent로 유지한다.
- 약한 모델이 바로 실행할 수 있게 모호한 표현을 줄이고 실행 순서를 명확히 한다.
- 코드 수정이 허용되지 않은 mode면 ANALYSIS ONLY 또는 REVIEW ONLY를 유지한다.
""".strip()
