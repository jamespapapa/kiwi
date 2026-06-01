from __future__ import annotations

import asyncio
import json
import re
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Literal, TypedDict

from .config import get_internal_settings
from .db import APP_ROOT, now_iso
from .kk_mcp import KkMcpClient
from .project_analyzer import load_project_context
from .qwen_client import QwenClient

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - requirements include langgraph.
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]


PromptBuildStatus = Literal["running", "succeeded", "failed"]
BuilderMode = Literal["analysis", "implement", "review"]

BUILDER_LOG_DIR = APP_ROOT / "data" / "prompt-builder"
PROMPT_GUIDE_PATH = APP_ROOT / "docs" / "ultrawork-prompt-template.md"


class PromptBuilderState(TypedDict, total=False):
    project: dict[str, Any]
    user_message: str
    history: list[dict[str, str]]
    project_context: str
    prompt_guide: str
    intent: dict[str, Any]
    kk_docs_results: list[dict[str, Any]]
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
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        BUILDER_LOG_DIR.mkdir(parents=True, exist_ok=True)
        run = {
            "id": run_id,
            "project_id": project["id"],
            "project_name": project["name"],
            "status": "running",
            "created_at": now_iso(),
            "completed_at": None,
            "message": message,
            "assistant_message": "",
            "questions": [],
            "interview_questions": [],
            "final_prompt": "",
            "events": [],
            "log_path": str(BUILDER_LOG_DIR / f"{run_id}.jsonl"),
        }
        self._runs[run_id] = run
        asyncio.create_task(self._execute(run_id, project, message, history))
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
            state = await runtime.run(project, message, history, settings.max_context_chars)
            run = self._runs[run_id]
            result = state.get("result", {})
            run["assistant_message"] = str(result.get("assistant_message", "")).strip()
            run["questions"] = [str(item) for item in result.get("questions", []) if str(item).strip()]
            run["interview_questions"] = _normalize_interview_questions(result)
            run["final_prompt"] = state.get("final_prompt", "")
            run["prompt_lint"] = state.get("prompt_lint", {})
            run["prompt_evaluation"] = state.get("prompt_evaluation", {})
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
            "status": run["status"],
            "created_at": run["created_at"],
            "completed_at": run["completed_at"],
            "message": run["message"],
            "assistant_message": run["assistant_message"],
            "questions": run["questions"],
            "interview_questions": run.get("interview_questions", []),
            "final_prompt": run["final_prompt"],
            "prompt_lint": run.get("prompt_lint", {}),
            "prompt_evaluation": run.get("prompt_evaluation", {}),
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
    ) -> PromptBuilderState:
        root = Path(project["root_path"])
        state: PromptBuilderState = {
            "project": project,
            "user_message": message,
            "history": history[-12:],
            "project_context": load_project_context(root, min(max_context_chars, 80_000)),
            "prompt_guide": _load_prompt_guide(),
        }
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
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": _compose_intent_prompt(state)},
            ],
            temperature=0,
            max_tokens=4096,
        )
        intent = _parse_json_object(content) or {
            "task_summary": state["user_message"],
            "task_type": "unknown",
            "mode": "analysis",
            "search_queries": _fallback_queries(state["user_message"]),
            "target_files": [],
            "missing_information": [],
            "questions": [],
            "risk_flags": ["intent_json_parse_failed"],
        }
        state["intent"] = intent
        await self.emit(
            {
                "type": "intent",
                "step": "intent",
                "title": "의도 분석 완료",
                "intent": intent,
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
                "message": "KK 문서 근거, 프로젝트 기억, 대화 이력을 합쳐 ultrawork용 지시문을 만듭니다.",
            }
        )
        content = await self.qwen.chat(
            [
                {"role": "system", "content": COMPOSE_SYSTEM_PROMPT},
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
                "message": "최종 프롬프트가 ultrawork 실행 계약과 필수 섹션을 만족하는지 확인합니다.",
            }
        )
        lint = _lint_ultrawork_prompt(prompt)
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
                    {"role": "system", "content": EVALUATE_SYSTEM_PROMPT},
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
            repaired_lint = _lint_ultrawork_prompt(state.get("final_prompt", ""))
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
            state["final_prompt"] = _repair_prompt_deterministically(state.get("final_prompt", ""), repaired_lint)
            repaired_lint = _lint_ultrawork_prompt(state["final_prompt"])
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


def _compose_intent_prompt(state: PromptBuilderState) -> str:
    return (
        "Ultrawork 프롬프트 작성 가이드:\n"
        f"{state['prompt_guide'][:26000]}\n\n"
        "프로젝트 KIWI.md 장기 기억:\n"
        f"{state['project_context'][:30000]}\n\n"
        "최근 빌더 대화:\n"
        f"{_format_history(state['history'])}\n\n"
        "사용자 최신 요청:\n"
        f"{state['user_message']}\n\n"
        "이 요청을 qwencode ultrawork 지시문으로 만들기 전에 무엇을 확인해야 하는지 JSON으로 판단하라."
    )


def _compose_builder_prompt(state: PromptBuilderState) -> str:
    context = {
        "intent": state.get("intent", {}),
        "kk_docs_results": state.get("kk_docs_results", []),
    }
    return (
        "Ultrawork 프롬프트 작성 가이드:\n"
        f"{state['prompt_guide'][:70000]}\n\n"
        "프로젝트 KIWI.md 장기 기억:\n"
        f"{state['project_context'][:45000]}\n\n"
        "KK docs MCP 검색 근거:\n"
        f"{json.dumps(state.get('kk_docs_results', []), ensure_ascii=False)[:45000]}\n\n"
        "최근 빌더 대화:\n"
        f"{_format_history(state['history'])}\n\n"
        "사용자 최신 요청:\n"
        f"{state['user_message']}\n\n"
        "분석 및 검색 근거 JSON:\n"
        f"{json.dumps(context, ensure_ascii=False)[:70000]}\n\n"
        "이제 추가 질문이 필요하면 interview_user tool contract를 포함한 needs_input을 반환하고, 충분하면 ready와 prompt_parts를 반환하라."
    )


def _compose_evaluation_prompt(state: PromptBuilderState, lint: dict[str, Any], attempt: int) -> str:
    return (
        "Ultrawork 프롬프트 작성 가이드:\n"
        f"{state['prompt_guide'][:70000]}\n\n"
        f"평가 루프 시도 번호: {attempt}/2\n\n"
        "현재 lint 결과 JSON:\n"
        f"{json.dumps(lint, ensure_ascii=False, indent=2)}\n\n"
        "현재 최종 프롬프트:\n"
        f"{state.get('final_prompt', '')}\n\n"
        "위 프롬프트를 Qwen3.5-397B-A17B + Qwen3-Coder-Next ultrawork 팀이 더 쉽게 실행할 수 있게 보강하라. "
        "단, KIWI UI가 전송 시 ultrawork 모드 스위치를 별도로 주입하므로 revised_prompt 맨 앞에 ultrawork 한 줄은 넣지 마라. "
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
    frontend_task = _is_frontend_task(state, parts)

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
            "레이아웃이나 애니메이션 변경이 있으면 architect-35 또는 reviewer-35에게 CSS/DOM 위험을 명시적으로 검토시킨다.",
        ]
        frontend_stops = [
            "기존 layout container, containing block, scoped/global style 위치를 확인하지 못하면 CSS 편집을 중단하고 먼저 탐색한다.",
            "요구된 시각 효과가 버튼 bounds를 넘어 주변 UI에 영향을 줄 가능성이 있으면 구현 전 설계안을 reviewer-35에 확인시킨다.",
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

    kk_docs_evidence = _summarize_kk_docs_evidence(state.get("kk_docs_results", []))

    sections = [
        f"# {title}",
        "",
        f"`{mode_token}`",
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
                "문서 지식은 로컬 정적 문서가 아니라 KK docs MCP의 `kk_search` 결과를 기준으로 삼는다.",
                "KK 문서와 현재 코드가 충돌하면 현재 코드 근거를 우선하고 충돌 사실을 보고한다.",
                "QWEN.md/KIWI.md는 실행 규칙과 프로젝트 메모리로만 참고하고, 업무/도메인 문서 근거로 과신하지 않는다.",
            ]
        ),
        "",
        "## KK docs MCP 참고 근거",
        kk_docs_evidence,
        "",
        "## 필수 읽기 파일",
        *_bullet_lines(required_reading + target_files),
        "",
        "## 필수 검색",
        *_bullet_lines(_merge_unique(required_search, ["필요 시 `kk-docs` MCP의 `kk_search`로 관련 사내 문서 근거를 확인한다."], 32)),
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
        *_bullet_lines(
            [
                "Kiwi는 먼저 한국어 visible plan 또는 TodoWrite/todo_write로 작업 순서와 완료 조건을 정리한다.",
                "요구사항, 수용조건, 누락 정보, 실행 순서가 모호하면 `agent` tool로 planner-35를 호출한다.",
                "파일 위치가 불명확하면 explorer-next에 짧은 read-only 탐색만 맡긴다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.",
                "복잡/위험/cross-module/data/security/CSS-layout 작업이면 구현 위임 전에 architect-35로 영향 범위와 설계 위험을 검토한다.",
                "기존 코드 수정 후 테스트 통과/빌드 실패/오류 수정 미션은 구현 위임 전에 debugger-35가 실패 표면, root cause, 최소 수정 slice를 먼저 정리한다.",
                "구현은 coder-35가 담당한다. Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않고 coder-35에 위임한다.",
                "coder-35는 Qwen3.5-397B를 사용하며 edit, write_file, run_shell_command를 작업 성격에 맞게 사용하되 한 번에 하나의 좁은 repair slice만 수행한다.",
                "coder-35가 2번 실패하면 3번째 시도 전 실제 tool 이름인 `ask_user_question`으로 사용자 허락을 받는다.",
                "구현 위임에는 Objective, Scope, Files/ownership, Exact steps, Non-goals, Verification, Expected response를 포함한다.",
                "하나의 구현 위임은 하나의 repair slice만 맡긴다. 구현 agent는 한 번의 coherent change와 한 번의 focused verification 후 Kiwi로 복귀해야 하며, 검증 실패 시 계속 삽질하지 말고 실패 출력과 가설을 반환한다.",
                "coder-35 위임에는 반드시 failure 시 stop-and-return-to-Kiwi 규칙을 명시한다.",
                "구현 결과가 나오면 반드시 reviewer-35가 최종 diff/위험/검증 근거를 리뷰한 뒤 다음 구현 루프 또는 완료 보고로 넘어간다.",
                "reviewer-35/tester-35 실패, edit 실패, 테스트 실패, 반복 tool 실패가 있으면 다음 수정 지시 전에 debugger-35가 원인과 교정 전략을 정리한다.",
                "진행 중 애매하거나 사용자 판단이 필요하면 일반 텍스트 질문 대신 `ask_user_question` tool을 호출한다. UI 표시명은 AskUserQuestion이다.",
            ]
        ),
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
        "- 한국어 계획으로 요구사항, 누락 정보, 실행 순서를 정리한다.",
        "- 필요하면 planner-35로 요구사항과 수용조건을 점검한다.",
        "- 복잡하거나 위험하면 architect-35로 영향 범위와 변경 순서를 검토한다.",
        "- 구현은 coder-35에 좁은 slice로 위임한다.",
        "- 구현 결과마다 reviewer-35로 diff와 검증 결과를 점검한다.",
        "- 실패나 수정 루프가 필요하면 debugger-35로 원인을 정리한 뒤 적절한 구현 agent에 재위임한다.",
        "- 사용자 판단이 필요하면 `ask_user_question` tool로 묻는다.",
    ]
    return "\n".join(sections).strip()


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
    return [f'kk-docs MCP `kk_search` 질의: "{query}"' for query in queries[:8]]


def _extract_interview_answers(history: list[dict[str, str]]) -> str:
    answers = [
        item.get("content", "").strip()
        for item in history[-12:]
        if item.get("role") == "user" and item.get("content", "").strip().startswith("[Prompt Builder interview answers]")
    ]
    if not answers:
        return "- 아직 별도 인터뷰 답변 없음. 사용자의 원 요청과 KK docs MCP 근거를 기준으로 진행한다."
    return "\n\n".join(answers[-2:])


REQUIRED_PROMPT_SECTIONS = [
    "## 작업 목표",
    "## 사용자 확인 답변",
    "## 프로젝트 지식 베이스 우선 참고",
    "## KK docs MCP 참고 근거",
    "## 필수 읽기 파일",
    "## 필수 검색",
    "## 구현 규칙",
    "## 영향도 지도 작성",
    "## subagent 운영 계약",
    "## 검증 계획",
    "## 완료 보고 형식",
    "## 중단 조건",
    "## 진행 방식",
]


def _lint_ultrawork_prompt(prompt: str) -> dict[str, Any]:
    text = _strip_ultrawork_mode_switch(prompt)
    issues: list[str] = []
    missing_sections = [section for section in REQUIRED_PROMPT_SECTIONS if section not in text]
    if missing_sections:
        issues.append("missing_required_sections")
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        issues.append("missing_execution_mode_token")
    if "kk_search" not in text and "kk-docs" not in text:
        issues.append("missing_kk_docs_search_reference")
    if "coder-35" not in text or "explorer-next" not in text:
        issues.append("missing_coder_35_contract")
    if "planner-35" not in text or "architect-35" not in text or "reviewer-35" not in text:
        issues.append("missing_consultant_agent_contract")
    if "계획" not in text and "plan" not in text.lower() and "TodoWrite" not in text and "todo_write" not in text:
        issues.append("missing_todowrite_planning_gate")
    if "KK docs MCP" not in text and "kk-docs" not in text:
        issues.append("missing_project_knowledge_base_reference")
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
        "required_sections": REQUIRED_PROMPT_SECTIONS,
    }


def _repair_prompt_deterministically(prompt: str, lint: dict[str, Any]) -> str:
    text = _strip_ultrawork_mode_switch(prompt)
    if not any(token in text for token in ["`IMPLEMENT APPROVED`", "`ANALYSIS ONLY`", "`REVIEW ONLY`"]):
        text = f"`ANALYSIS ONLY`\n\n{text}"
    missing = lint.get("missing_sections")
    repairs = {
        "## 작업 목표": "- 사용자의 요청을 현재 프로젝트 용어로 재정의하고, 완료 조건을 먼저 확인한다.",
        "## 사용자 확인 답변": "- 인터뷰 답변이 있으면 그대로 반영한다. 없으면 사용자의 원 요청을 기준으로 진행한다.",
        "## 프로젝트 지식 베이스 우선 참고": "- 문서 지식은 KK docs MCP `kk_search` 결과를 기준으로 삼는다.\n- 로컬 정적 문서를 문서 근거로 사용하지 않는다.",
        "## KK docs MCP 참고 근거": "- 현재 KK docs MCP 검색 근거가 없으면 `kk_search`로 필요한 문서를 먼저 찾는다.",
        "## 필수 읽기 파일": "- `QWEN.md`\n- `KIWI.md`\n- 관련 route/view/store 또는 controller/service/mapper 파일",
        "## 필수 검색": "- kk-docs MCP `kk_search` 질의: \"<요구사항 핵심 키워드>\"\n- 필요한 경우 현재 코드베이스에서 관련 symbol/path를 확인한다.",
        "## 구현 규칙": "- 구현 전 영향도 지도를 작성한다.\n- 관련 없는 리팩터링과 광범위 포맷팅을 하지 않는다.",
        "## 영향도 지도 작성": "- entrypoint, producer, carrier, API, persistence/cache/session, downstream consumer를 정리한다.",
        "## subagent 운영 계약": "- Kiwi는 먼저 한국어 계획으로 요구사항과 실행 순서를 정리한다.\n- 요구사항/수용조건/순서가 모호하면 planner-35를 호출한다.\n- 파일 위치가 불명확하면 explorer-next를 최대 5개까지 병렬 read-only 탐색으로 사용한다.\n- 테스트 통과/빌드 실패/오류 수정 미션은 구현 전 debugger-35가 root cause와 최소 repair slice를 정리한다.\n- 구현은 coder-35가 담당하고, Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않는다.\n- 하나의 구현 위임은 하나의 repair slice만 맡기고, 검증 실패 시 계속 수정하지 말고 Kiwi로 복귀한다.\n- coder-35 위임에는 Objective, Scope, Files/ownership, Exact steps, Non-goals, Verification, Expected response, failure 시 stop-and-return-to-Kiwi 규칙을 명시한다.\n- 구현 결과마다 reviewer-35가 리뷰한다. 실패/수정 루프 전에는 debugger-35가 원인과 교정 전략을 정리한다. 검증은 tester-35 또는 로컬 명령으로 확인한다.\n- 사용자 판단이 필요하면 `ask_user_question` tool로 묻는다.",
        "## 검증 계획": "- 가능한 검증 명령을 식별해 실행한다. 실행할 수 없으면 이유와 대체 확인 방법을 보고한다.",
        "## 완료 보고 형식": "- 변경/분석 요약\n- 확인한 근거\n- 변경 파일\n- 실행한 검증\n- 남은 위험",
        "## 중단 조건": "- 업무 의미, API carrier, 저장 위치, shared consumer가 불명확하면 편집하지 말고 `ask_user_question` tool로 질문한다.",
        "## 진행 방식": "- 한국어 계획으로 요구사항을 점검한다.\n- 파일 위치가 불명확하면 explorer-next로 병렬 read-only 탐색을 수행한다.\n- 복잡하거나 위험하면 architect-35로 영향 범위를 검토한다.\n- 구현은 coder-35에 좁은 slice로 위임한다.\n- 구현 결과마다 reviewer-35로 최종 결과를 검토한다.\n- 실패나 수정 루프가 필요하면 debugger-35로 원인을 정리한다.\n- 사용자 판단이 필요하면 `ask_user_question` tool로 묻는다.",
    }
    appended: list[str] = []
    if isinstance(missing, list) and missing:
        appended.extend(["", "## Linter 보강 섹션"])
        for section in missing:
            if section in repairs:
                appended.extend(["", str(section), repairs[section]])
    issue_repairs = {
        "missing_kk_docs_search_reference": "## 필수 검색 보강\n- kk-docs MCP `kk_search` 질의: \"<요구사항 핵심 키워드>\"\n- kk-docs MCP `kk_search` 질의: \"<화면ID|API|업무 용어>\"",
        "missing_coder_35_contract": "## 구현 agent 보강 계약\n- 구현은 coder-35가 담당하고, Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않는다.\n- coder-35는 Objective, Scope, Files/ownership, Required reading, Exact steps, Non-goals, Verification command, Expected response를 받은 뒤 하나의 좁은 repair slice만 수행한다.\n- 하나의 구현 위임은 하나의 repair slice만 맡기고, 실패하면 Kiwi가 debugger-35를 거친 뒤 다음 slice를 위임한다.\n- 파일 위치가 불명확하면 explorer-next를 최대 5개까지 병렬 read-only 탐색으로 사용한다.\n- coder-35가 2번 실패하면 3번째 시도 전 `ask_user_question`으로 사용자 허락을 받는다.",
        "missing_consultant_agent_contract": "## consultant agent 보강 계약\n- planner-35는 요구사항과 수용조건을 점검한다.\n- architect-35는 영향도와 설계 위험을 점검한다.\n- reviewer-35는 모든 구현 결과 뒤 최종 diff와 검증 누락을 점검한다.\n- debugger-35는 실패/수정 루프 전 원인과 교정 전략을 점검한다.",
        "missing_todowrite_planning_gate": "## 계획 보강 계약\n- Kiwi는 구현 전 한국어 visible plan 또는 TodoWrite/todo_write로 작업 순서, 현재 항목, 완료 조건을 정리한다.",
        "missing_project_knowledge_base_reference": "## 지식 베이스 보강\n- 문서 근거는 KK docs MCP `kk_search` 결과를 우선한다.\n- 로컬 정적 문서는 문서 근거로 사용하지 않는다.",
        "missing_verification_language": "## 검증 보강\n- 가능한 검증 명령을 실행하고, 실행할 수 없으면 이유와 대체 확인 방법을 보고한다.",
        "missing_stop_or_question_condition": "## 중단/질문 보강\n- 업무 의미, API carrier, 저장 위치, shared consumer가 불명확하면 편집하지 말고 `ask_user_question` tool로 질문한다.",
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
                "- 문서 근거는 먼저 KK docs MCP `kk_search`로 찾고, 코드 근거가 필요한 경우에만 현재 레포의 실제 파일을 읽는다.",
                "- 파일을 읽을 때는 path, symbol, caller, consumer, branch condition을 메모한다.",
                "- 구현 전에 영향도 지도에서 entrypoint, producer, carrier, API, persistence/cache/session, downstream consumer를 채운다.",
                "- 구현 범위가 넓으면 coder-35에 좁은 repair slice로 나누어 지시하고, 각 slice 뒤에는 reviewer-35 검토를 거친다.",
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
    return re.sub(r"^\s*ultrawork(?:\r?\n)+", "", prompt.strip(), count=1, flags=re.IGNORECASE).strip()


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
  "search_queries": ["KK docs MCP kk_search로 찾을 문서 검색어"],
  "target_files": ["확실한 후보 파일 경로"],
  "risk_flags": ["주의점"]
}

규칙:
- 질문은 최대 4개, 꼭 필요한 것만 만든다.
- 검색어는 업무 용어, 서비스명, 모듈명, 화면ID, API path, store key 중심으로 만든다.
- 구현 의도가 분명하면 mode=implement, 단순 조사면 analysis, 리뷰 요청이면 review로 둔다.
- 문서 근거는 로컬 정적 문서가 아니라 KK docs MCP 검색에 의존한다.
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
    "required_search": ["KK docs MCP 검색어와 필요한 코드 확인 항목"],
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
- KK docs MCP 근거가 부족해도 먼저 검색해야 할 질의가 명확하면 ready로 만들 수 있다.
- ready이면 KK docs MCP 문서 근거, 필수 검색, 영향도 지도, subagent 운영 계약, 검증 계획을 prompt_parts에 반영한다.
- DCP 작업은 route/screen/store/API/EAI/Redis 흐름을 추적하도록 지시한다.
- 보험금 청구나 상태 전파 작업은 positional array, DataStore, route params, spotLoad/spotSave, downstream consumer를 특히 강조한다.
- 프론트/UI/CSS 작업이면 기존 CSS 구조, scoped/global style 위치, DOM 조작 방식, containing block, selector 우선순위, layout/animation side effect를 반드시 prompt_parts에 반영한다.
- 버튼/작은 control의 glow/bling/animation은 버튼 bounds 안에 제한하고, position/absolute/z-index/overflow/transform 변경은 기존 layout 근거를 확인하도록 지시한다.
- coder-35 구현 결과마다 reviewer-35 리뷰를 필수로 넣고, 실패/수정 루프 전에는 debugger-35가 원인과 교정 전략을 정리하게 한다.
- 애매하거나 사용자 판단이 필요한 항목은 실제 tool 이름인 `ask_user_question` 호출 지시를 넣는다. UI 표시명은 AskUserQuestion이다.
- 관련 없는 리팩터링과 광범위 포맷팅을 금지한다.
""".strip()


EVALUATE_SYSTEM_PROMPT = """
너는 KIWI Prompt Builder의 프롬프트 평가/개선 노드다.
목표는 Qwen3.5-397B-A17B Kiwi, coder-35, explorer-next subagent가 폐쇄망에서 실수 없이 실행할 수 있는 ultrawork 프롬프트로 보강하는 것이다.
반드시 JSON만 반환한다.

스키마:
{
  "score": 0,
  "issues": ["문제"],
  "improvements": ["보강한 점"],
  "revised_prompt": "ultrawork 모드 스위치 줄 없이 시작하는 완성된 전체 프롬프트"
}

규칙:
- revised_prompt는 반드시 전체 프롬프트다. patch나 일부 섹션만 반환하지 않는다.
- KIWI UI가 전송 시 ultrawork 모드 스위치를 별도로 주입하므로 revised_prompt 맨 앞에 ultrawork 한 줄을 넣지 않는다.
- lint가 지적한 missing section은 모두 채운다.
- 프로젝트 지식 베이스 참고, 필수 검색, 영향도 지도, subagent 운영 계약, 검증 계획, 중단 조건을 구체화한다.
- 프론트/UI/CSS 요청이면 CSS/DOM 가드레일, containing block 확인, scoped/global style 위치, animation bounds 제한, horizontal scroll/text overflow 확인을 구체화한다.
- coder-35 이후 reviewer-35 필수 리뷰와 실패/수정 루프 전 debugger-35 분석 계약이 빠졌으면 보강한다.
- 약한 모델이 바로 실행할 수 있게 모호한 표현을 줄이고 실행 순서를 명확히 한다.
- 코드 수정이 허용되지 않은 mode면 ANALYSIS ONLY 또는 REVIEW ONLY를 유지한다.
""".strip()
