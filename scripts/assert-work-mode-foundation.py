from __future__ import annotations

import asyncio
import json
import sys
import types
import importlib.util
import tempfile
from pathlib import Path


class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _StubBaseModel:
    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    def model_dump(self, **_: object) -> dict[str, object]:
        return dict(self.__dict__)


def _stub_field(default=None, default_factory=None, **_: object):
    if default_factory is not None:
        return default_factory()
    return default


if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.HTTPException = _StubHTTPException
    sys.modules["fastapi"] = fastapi_stub
if "pydantic" not in sys.modules:
    pydantic_stub = types.ModuleType("pydantic")
    pydantic_stub.BaseModel = _StubBaseModel
    pydantic_stub.Field = _stub_field
    sys.modules["pydantic"] = pydantic_stub
if "httpx" not in sys.modules:
    httpx_stub = types.ModuleType("httpx")

    class _StubHTTPError(Exception):
        pass

    class _StubHTTPStatusError(_StubHTTPError):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            self.response = kwargs.get("response") or types.SimpleNamespace(status_code=0, text="")

    class _StubTimeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _StubAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            raise _StubHTTPError("httpx stub cannot perform network calls")

    httpx_stub.HTTPError = _StubHTTPError
    httpx_stub.HTTPStatusError = _StubHTTPStatusError
    httpx_stub.Timeout = _StubTimeout
    httpx_stub.AsyncClient = _StubAsyncClient
    sys.modules["httpx"] = httpx_stub

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
VISIBLE_SUPERPOWERS_GATE = "## " + "superpowers " + "mandatory " + "skill gate"

from fastapi import HTTPException

import backend.app.prompt_builder as prompt_builder_module
from backend.app.kk_mcp import ensure_project_qwencode_mcp_settings
from backend.app.prompt_builder import (
    PromptBuilderRuntime,
    _compose_builder_prompt,
    _compose_intent_prompt,
    _intent_system_prompt,
    _lint_work_mode_prompt,
    _render_ultrawork_prompt,
)
from backend.app.qwencode_runtime import (
    _patch_ultrawork_activation_message,
    _patch_work_mode_policy_script,
    _patch_work_mode_state_script,
)
from backend.app.ultrawork_policy import build_ultrawork_policy
from backend.app.ultrawork_console import ConsoleSession, _command_with_approval_mode, _prepare_submitted_work_mode_prompt


TEAM_LOG_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "team-log-lib.js"
POLICY_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "orchestration-policy.js"


def main() -> None:
    assert_prompt_modes()
    assert_fast_builder_context()
    assert_size_selector_ui_and_api_fields()
    assert_non_fast_prompt_builder_defaults_missing_selected_size_to_medium()
    assert_initial_prompt_size_contract()
    assert_runtime_context_split()
    assert_tshirt_source_of_truth()
    assert_selected_size_final_prompt_and_console_policy()
    assert_fast_internal_state_has_no_task_size()
    assert_mode_mismatch_409()
    assert_dangerous_mode_respected()
    assert_console_terminal_ui_guardrails()
    assert_frontend_pre_activation_lock_path()
    print("work mode foundation assertions passed")


def assert_prompt_modes() -> None:
    fast = render_prompt("fast")
    for forbidden in ["티셔츠", "subagent", "coder-35", "ultrawork 팀"]:
        assert forbidden not in fast, f"FAST prompt leaked forbidden term: {forbidden}"
    assert "Activation prefix: `lightwork`" in fast
    assert "## FAST/lightwork 직접 실행 계약" in fast
    assert _lint_work_mode_prompt(fast, "fast")["passed"]

    ultrawork = render_prompt("ultrawork")
    assert "Activation prefix: `ultrawork_small`" in ultrawork
    assert "## 티셔츠 사이징" in ultrawork
    assert _lint_work_mode_prompt(ultrawork, "ultrawork")["passed"]

    superpowers = render_prompt("superpowers")
    assert "Activation prefix: `superpowers_small`" in superpowers
    assert "## 티셔츠 사이징" in superpowers
    assert "## superpowers skill-first 계약" in superpowers
    assert _lint_work_mode_prompt(superpowers, "superpowers")["passed"]


def render_prompt(mode: str) -> str:
    state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "보험금 청구 화면 문구를 한 줄 수정하고 검증해줘.",
        "work_mode": mode,
        **({"selected_task_size": "small"} if mode != "fast" else {}),
        "history": [],
        "intent": {
            "task_summary": "보험금 청구 화면 문구를 한 줄 수정한다.",
            "task_type": "frontend",
            "mode": "implement",
            "task_size": "small",
            "task_size_reason": "한 화면의 좁은 수정이다.",
            "search_queries": ["보험금 청구", "문구"],
            "target_files": ["src/views/claim/Sample.vue"],
        },
        "kk_docs_results": [
            {
                "query": "보험금 청구",
                "ok": True,
                "results": [
                    {
                        "title": "청구 화면 가이드",
                        "topic": "claim",
                        "confidence": 0.86,
                        "content": "보험금 청구 화면 문구 기준",
                    }
                ],
            }
        ],
    }
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "프롬프트를 생성했습니다.",
        "prompt_parts": {
            "title": "보험금 청구 화면 문구 수정",
            "task": "보험금 청구 화면의 안내 문구를 한 줄 수정하고 확인한다.",
            "verification": ["npm run typecheck"],
        },
    }
    return _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]


def assert_fast_builder_context() -> None:
    state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "문구 한 줄 수정",
        "work_mode": "fast",
        "history": [],
        "project_context": "KIWI.md",
        "prompt_guide": "티셔츠 subagent coder-35 ultrawork 팀 task_size",
        "intent": {
            "task_summary": "문구 한 줄 수정",
            "task_size": "large",
            "task_size_reason": "should be filtered",
            "search_queries": ["문구"],
        },
        "ultrawork_policy": {
            "task_size": "large",
            "task_size_reason": "should be filtered",
            "developer_agent": "coder-35",
            "subagents": ["coder-35", "reviewer-35"],
        },
        "kk_docs_results": [],
    }
    prompt = _compose_builder_prompt(state)  # type: ignore[arg-type]
    intent_prompt = _compose_intent_prompt(state)  # type: ignore[arg-type]
    system_prompt = _intent_system_prompt("fast")
    for label, text in {
        "builder": prompt,
        "intent": intent_prompt,
        "intent_system": system_prompt,
    }.items():
        for forbidden in ["티셔츠", "subagent", "coder-35", "ultrawork 팀", "task_size"]:
            assert forbidden not in text, f"FAST {label} context leaked forbidden term: {forbidden}"


def assert_runtime_context_split() -> None:
    team_log = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_team_log = _patch_work_mode_state_script(_patch_ultrawork_activation_message(team_log))
    assert_patched_team_log(patched_team_log, "backend runtime")

    bundle = load_bundle_module()
    patched_bundle_team_log = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(team_log))
    assert_patched_team_log(patched_bundle_team_log, "offline bundle")

    policy = POLICY_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_policy = _patch_work_mode_policy_script(policy)
    assert 'mode === "fast" && isAgentTool(toolName)' in patched_policy
    assert "FAST/lightwork mode is locked to direct Kiwi work." in patched_policy
    assert "without subagents" not in patched_policy
    assert 'mode === "superpowers" && isSkillTool(toolName)' in patched_policy
    patched_bundle_policy = bundle.patch_work_mode_policy_script(policy)
    assert "FAST/lightwork mode is locked to direct Kiwi work." in patched_bundle_policy
    assert "without subagents" not in patched_bundle_policy
    assert 'mode === "superpowers" && isSkillTool(toolName)' in patched_bundle_policy


def assert_tshirt_source_of_truth() -> None:
    missing = make_session("ultrawork")
    defaulted = _prepare_submitted_work_mode_prompt(missing, "ultrawork\n\nsize 없이 직접 실행")
    assert "ultrawork_medium" in defaulted.splitlines()[0]
    assert "## 티셔츠 사이징" not in defaulted
    assert "## Project Info Layer 시작 컨텍스트" not in defaulted
    assert "[KIWI_WORK_MODE_LOCK]" not in defaulted
    assert "Prompt Builder 추천값" not in defaulted
    assert "Kiwi 1차 산정" not in defaulted

    suffixed = make_session("superpowers")
    suffixed_generated = _prepare_submitted_work_mode_prompt(suffixed, "superpowers_xlarge\n\nsize suffix 직접 실행")
    assert "superpowers_xlarge" in suffixed_generated.splitlines()[0]
    assert "## 티셔츠 사이징" not in suffixed_generated
    assert VISIBLE_SUPERPOWERS_GATE not in suffixed_generated
    assert "kiwi-superpowers" not in suffixed_generated
    assert "using-superpowers" not in suffixed_generated
    assert "Do not use `tool_search`, `select:`" not in suffixed_generated

    session = make_session("ultrawork")
    generated = _prepare_submitted_work_mode_prompt(
        session,
        "ultrawork\n\n넓은 작업을 처리해줘",
        task_size="large",
        task_size_reason="assertion selected size",
    )
    assert generated.splitlines()[0] == "ultrawork_large"
    assert "## 티셔츠 사이징" not in generated
    assert "assertion selected size" not in generated

    session = make_session("superpowers")
    legacy_prompt = (
        "superpowers\n\n"
        "## 티셔츠 사이징\n"
        "- Kiwi 1차 산정: `medium`\n"
        "- 산정 이유: Prompt Builder source of truth\n\n"
        "## 작업 목표\n"
        "이미 생성된 프롬프트를 실행한다."
    )
    default_replaced = _prepare_submitted_work_mode_prompt(session, legacy_prompt)
    assert "사용자 선택: `medium`" in default_replaced
    assert "Kiwi 1차 산정" not in default_replaced
    assert VISIBLE_SUPERPOWERS_GATE not in default_replaced

    session = make_session("superpowers")
    replaced = _prepare_submitted_work_mode_prompt(
        session,
        legacy_prompt,
        task_size="large",
        task_size_reason="assertion selected large",
    )
    assert replaced.count("## 티셔츠 사이징") == 1
    assert "사용자 선택: `large`" in replaced
    assert "최종 source of truth: 사용자 선택값" in replaced
    assert "assertion selected large" in replaced
    assert "Kiwi 1차 산정: `medium`" not in replaced
    assert VISIBLE_SUPERPOWERS_GATE not in replaced


def assert_size_selector_ui_and_api_fields() -> None:
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    for required in [
        "task-size-selector",
        "work-mode-task-size",
        "티셔츠 사이즈",
        "ultrawork/superpowers size selector",
        "showTaskSizeSelector = builderWorkMode !== \"fast\"",
        "task_size: selectedTaskSize",
        "selectedTaskSizeConsoleMeta",
        "agent 팀 구성",
        "운영 방식",
        'useState<TaskSize>("medium")',
        "workModePrefix(workMode, selectedTaskSize)",
        "${base}_${taskSize}",
    ]:
        assert required in page, f"frontend size selector missing: {required}"
    assert "Prompt Builder 추천값" not in page, "Prompt Builder recommendation UI must be removed"
    assert "<h2>런타임 정보</h2>" in page, "runtime information panel must exist above agent information"
    runtime_panel = extract_between(page, "<h2>런타임 정보</h2>", "<h2>에이전트 정보</h2>")
    for required in ["qwencode", "kk-docs MCP", "kk-code-analysis MCP"]:
        assert required in runtime_panel, f"runtime info panel missing: {required}"
    assert "<h2>AI 모델 정보</h2>" not in page, "old AI model section title must be renamed"
    ai_panel = extract_between(page, "<h2>에이전트 정보</h2>", "<h2>AGENT TOKENS</h2>")
    assert "<small>{item.detail}</small>" not in ai_panel, "agent role detail labels must not render beside info icons"
    for forbidden in ["kk-docs MCP", "kk-code-analysis MCP", "<strong>qwencode</strong>"]:
        assert forbidden not in ai_panel, f"agent information panel still contains runtime item: {forbidden}"
    assert "work-mode-info" in page, "work mode buttons must expose info tooltip icons"
    for forbidden in ['detail: "direct"', 'detail: "agents"', 'detail: "skills"', "<small>{option.detail}</small>"]:
        assert forbidden not in page, f"work mode UI still renders meaningless detail text: {forbidden}"
    for size in ["xsmall", "small", "medium", "large", "xlarge"]:
        assert f'key: "{size}"' in page, f"frontend size option missing: {size}"

    models = (ROOT / "backend" / "app" / "models.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    builder = (ROOT / "backend" / "app" / "prompt_builder.py").read_text(encoding="utf-8")
    policy = (ROOT / "backend" / "app" / "ultrawork_policy.py").read_text(encoding="utf-8")
    assert "class PromptBuilderRequest" in models and "task_size: str | None" in models
    assert "payload.task_size" in main
    policy_builder_body = extract_between(policy, "def build_ultrawork_policy(", "def estimate_task_size(")
    assert "estimate_task_size(" not in policy_builder_body, "ultrawork policy must not auto-estimate t-shirt sizing"
    for required in ["selected_task_size", "recommended_task_size", "task_size_source"]:
        assert required in builder, f"Prompt Builder state/public API missing: {required}"


def assert_non_fast_prompt_builder_defaults_missing_selected_size_to_medium() -> None:
    builder = (ROOT / "backend" / "app" / "prompt_builder.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    models = (ROOT / "backend" / "app" / "models.py").read_text(encoding="utf-8")
    assert "_require_selected_task_size(" in builder, "Prompt Builder must normalize selected task_size"
    assert "DEFAULT_TASK_SIZE" in builder, "Prompt Builder must default non-FAST missing size to medium"
    assert "selected_task_size_missing" not in builder, "Prompt Builder must not fail missing non-FAST size under default-medium contract"
    assert 'or "small"' not in extract_between(
        builder,
        "async def run(",
        "def _build_graph",
    ), "Prompt Builder runtime must not default missing selected size to small"
    assert "validate_prompt_builder_task_size" in main, "Prompt Builder API must keep FAST task_size guard at backend boundary"
    assert "task_size: str | None" in models, "PromptBuilderRequest must carry task_size field"


def assert_initial_prompt_size_contract() -> None:
    models = (ROOT / "backend" / "app" / "models.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    console = (ROOT / "backend" / "app" / "ultrawork_console.py").read_text(encoding="utf-8")
    assert "class UltraworkSessionStartRequest" in models
    start_request = extract_between(models, "class UltraworkSessionStartRequest", "class UltraworkInputRequest")
    assert "task_size: str | None" in start_request, "initial_prompt start request must carry selected task_size"
    assert "task_size_reason: str | None" in start_request, "initial_prompt start request must carry task_size_reason"
    assert "validate_initial_prompt_task_size" in main, "session start API must guard initial_prompt task_size"
    assert "task_size=payload.task_size" in main, "session start API must pass selected size to console"
    assert "_validate_start_prompt_task_size(" in console, "console manager must guard direct initial_prompt calls"
    start_session = extract_between(console, "async def start_session(", "def get_session")
    assert "task_size: str | None" in start_session, "console start_session must accept selected task_size"
    assert "self._delayed_input(state.id, initial_prompt, 0.8, normalized_task_size" in start_session, (
        "initial_prompt delayed input must preserve normalized/default selected task_size"
    )
    delayed_input = extract_between(console, "async def _delayed_input(", "async def _broadcast")
    assert "task_size: str | None" in delayed_input, "_delayed_input must accept selected task_size"
    assert "task_size_reason=task_size_reason" in delayed_input, "_delayed_input must pass selected size into send_input"


def assert_selected_size_final_prompt_and_console_policy() -> None:
    policy = build_ultrawork_policy(
        {"name": "generic", "root_path": str(ROOT)},
        {
            "task_summary": "여러 화면과 API 흐름을 함께 수정한다.",
            "task_type": "fullstack",
            "target_files": ["a.ts", "b.ts", "c.ts", "d.ts"],
            "risk_flags": ["api", "store", "shared"],
        },
        selected_task_size="xsmall",
        selected_task_size_reason="assertion user selected xsmall",
    )
    state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "넓어 보이지만 사용자가 xsmall로 처리하라고 선택했다.",
        "work_mode": "ultrawork",
        "history": [],
        "intent": {
            "task_summary": "여러 화면과 API 흐름을 함께 수정한다.",
            "task_type": "fullstack",
            "mode": "implement",
            "search_queries": ["api", "store"],
            "target_files": ["a.ts", "b.ts", "c.ts", "d.ts"],
            "risk_flags": ["api", "store", "shared"],
        },
        "selected_task_size": "xsmall",
        "ultrawork_policy": policy,
        "kk_docs_results": [],
    }
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "프롬프트를 생성했습니다.",
        "prompt_parts": {
            "title": "사용자 선택 사이징 검증",
            "task": "선택 사이즈를 final prompt에 반영한다.",
            "verification": ["npm run typecheck"],
        },
    }
    prompt = _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]
    assert "사용자 선택: `xsmall`" in prompt
    assert "Prompt Builder 추천값:" not in prompt
    assert "최종 source of truth: 사용자 선택값" in prompt
    assert "xsmall 모드: subagent를 호출하지 않는다" in prompt
    assert "Kiwi 1차 산정: `xsmall`" not in prompt

    session = make_session("ultrawork")
    generated = _prepare_submitted_work_mode_prompt(
        session,
        "ultrawork\n\n여러 화면과 API 흐름을 수정한다.",
        task_size="medium",
        task_size_reason="assertion user selected medium",
    )
    assert generated.splitlines()[0] == "ultrawork_medium"
    assert "Prompt Builder 추천값:" not in generated
    assert "## 티셔츠 사이징" not in generated
    assert "medium 모드" not in generated


def assert_fast_internal_state_has_no_task_size() -> None:
    original_policy_builder = prompt_builder_module.build_ultrawork_policy

    def fail_policy_builder(*_: object, **__: object) -> dict[str, object]:
        raise AssertionError("FAST path must not call build_ultrawork_policy")

    class FakeQwen:
        async def chat(self, *_: object, **__: object) -> str:
            return (
                '{"task_summary":"문구 한 줄 수정","task_type":"frontend","mode":"implement",'
                '"task_size":"large","task_size_reason":"should be ignored",'
                '"search_queries":["문구"],"target_files":["src/a.vue"],"risk_flags":[]}'
            )

    async def emit(_: dict[str, object]) -> None:
        return None

    state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "문구 한 줄 수정",
        "work_mode": "fast",
        "history": [],
        "project_context": "KIWI.md",
        "prompt_guide": "FAST",
    }
    prompt_builder_module.build_ultrawork_policy = fail_policy_builder  # type: ignore[assignment]
    try:
        runtime = PromptBuilderRuntime(FakeQwen(), emit, types.SimpleNamespace())
        result = asyncio.run(runtime._intent_node(state))  # type: ignore[arg-type]
        assert "ultrawork_policy" not in result
        assert_no_task_size_keys(result)
        fast_prompt = _render_ultrawork_prompt(
            {
                **result,
                "kk_docs_results": [],
                "intent": {"task_summary": "문구 한 줄 수정", "task_size": "large"},
            },
            {
                "status": "ready",
                "mode": "implement",
                "assistant_message": "FAST prompt",
                "prompt_parts": {"title": "FAST", "task": "문구 한 줄 수정", "verification": ["npm run typecheck"]},
            },
        )
        assert "task_size" not in fast_prompt
    finally:
        prompt_builder_module.build_ultrawork_policy = original_policy_builder  # type: ignore[assignment]


def assert_no_task_size_keys(value: object, path: str = "state") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert "task_size" not in str(key), f"FAST internal state leaked {path}.{key}"
            assert_no_task_size_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_task_size_keys(child, f"{path}[{index}]")


def assert_patched_team_log(patched_team_log: str, label: str) -> None:
    fast_context = extract_between(
        patched_team_log,
        "function fastModeContext(trigger",
        "function superpowersXsmallContext(trigger, prompt",
    )
    for forbidden in ["t-shirt", "subagent", "coder-35", "reviewer-35", "Direct ultrawork sizing gate"]:
        assert forbidden not in fast_context, f"{label} FAST runtime context leaked: {forbidden}"
    for required in [
        "FAST/lightwork has no size report",
        "`todo_write` tool",
        "User question protocol",
        "Before calling `ask_user_question`, first load/check the tool usage or schema",
        "registered `agent` delegation mechanism",
        "do not claim a mode conflict",
    ]:
        assert required in fast_context, f"{label} FAST runtime context missing: {required}"
    assert "ask with `ask_user_question`" not in fast_context, f"{label} FAST ask guidance is too weak"
    assert "mcp_todowrite" not in fast_context and "mcp_ask_user_question" not in fast_context
    team_context = extract_between(
        patched_team_log,
        "function teamModeContext(trigger, prompt = \"\", input = {})",
        "function truncate",
    )
    for required in [
        "t-shirt",
        "subagent",
        "coder-35",
        "reviewer-35",
        "superpowers",
        "`todo_write` tool is mandatory",
        "User question protocol",
        "Before calling `ask_user_question`, first load/check the tool usage or schema",
    ]:
        assert required in team_context, f"{label} team runtime context missing: {required}"
    assert "ask with `ask_user_question`" not in team_context, f"{label} team ask guidance is too weak"
    assert "mcp_todowrite" not in team_context and "mcp_ask_user_question" not in team_context
    for required in [
        "const base = value.replace",
        "superpowers|spw)_(xsmall|small|medium|large|xlarge)",
        'return match ? match[1].toLowerCase() : "medium"',
        'return state.mode || workModeFromTrigger(state.trigger) || ""',
        'if (!state?.active) return ""',
    ]:
        assert required in patched_team_log, f"{label} sized trigger runtime support missing: {required}"


def load_bundle_module():
    module_path = ROOT / "scripts" / "build-offline-bundle.py"
    spec = importlib.util.spec_from_file_location("build_offline_bundle_assert", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_mode_mismatch_409() -> None:
    session = make_session("fast")
    try:
        _prepare_submitted_work_mode_prompt(session, "ultrawork\n\n작업해줘")
    except HTTPException as exc:
        assert exc.status_code == 409
        assert "새 세션" in str(exc.detail)
    else:
        raise AssertionError("different work mode prefix did not raise 409")


def assert_dangerous_mode_respected() -> None:
    assert _command_with_approval_mode(["qwen.cmd"], dangerous_mode=False) == ["qwen.cmd", "--approval-mode", "yolo"]
    assert _command_with_approval_mode(["qwen.cmd"], dangerous_mode=True) == ["qwen.cmd", "--approval-mode", "yolo"]
    assert _command_with_approval_mode(["qwen.cmd", "--approval-mode", "default"], dangerous_mode=True) == [
        "qwen.cmd",
        "--approval-mode",
        "default",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        settings = types.SimpleNamespace(
            kk_docs_mcp_enabled=False,
            kk_docs_mcp_url="",
            kk_code_analysis_mcp_enabled=False,
            kk_code_analysis_mcp_url="",
            kk_mcp_token="",
            dangerous_mode=False,
        )
        settings_path = ensure_project_qwencode_mcp_settings(tmp, settings)
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data["tools"]["approvalMode"] == "yolo"
        assert "sandbox" not in data["tools"]
        assert data["ui"]["compactMode"] is True
        assert data["ui"]["useTerminalBuffer"] is False
    with tempfile.TemporaryDirectory() as tmp:
        settings = types.SimpleNamespace(
            kk_docs_mcp_enabled=False,
            kk_docs_mcp_url="",
            kk_code_analysis_mcp_enabled=False,
            kk_code_analysis_mcp_url="",
            kk_mcp_token="",
            dangerous_mode=True,
        )
        settings_path = ensure_project_qwencode_mcp_settings(tmp, settings)
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert data["tools"]["approvalMode"] == "yolo"
        assert "sandbox" not in data["tools"]
        assert data["ui"]["compactMode"] is True
        assert data["ui"]["useTerminalBuffer"] is False


def assert_console_terminal_ui_guardrails() -> None:
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    css = (ROOT / "app" / "globals.css").read_text(encoding="utf-8")
    assert "windowsPty" in page and 'backend: "winpty"' in page, "frontend xterm must use Windows PTY mode"
    assert "windowsMode: true" not in page, "frontend must not use deprecated xterm windowsMode"
    assert "pendingFitTimeoutRef" not in page, "terminal resize must not use delayed timeout loops"
    assert "lastSnapshotSessionRef" in page, "snapshot handling must not reset xterm repeatedly for the same session"
    assert "commandBarFocused" in page and "commandText" in page, "bottom command input state must exist"
    assert "terminal-statusbar" in page and "terminal-command-bar" in page, "bottom command input UI must exist"
    assert ".terminal-statusbar" in css and ".terminal-command-bar" in css, "bottom command input CSS must exist"
    assert "grid-template-rows: 52px minmax(0, 1fr)" in css, "shell content row must not grow past the viewport"
    assert "height: calc(100dvh - 94px)" not in css, "workspace height must be owned by the shell grid"
    assert "grid-template-rows: minmax(0, 1fr) auto" in css, "terminal and command bar must use in-flow auto rows"
    assert ".terminal-command-bar.focused" in css and "min-height: 160px" in css, "command input must expand on focus"
    assert ".terminal-command-bar.focused .command-bar-input" in css, (
        "focused command textarea must expand without absolute overlay"
    )
    assert "position: absolute" not in css.split(".terminal-command-bar.focused", 1)[1].split(".terminal-command-bar.disabled", 1)[0], (
        "focused command bar must not overlay the terminal"
    )
    assert "rows: TERMINAL_MIN_ROWS" in page, "xterm must not start with an oversized row count before first fit"
    assert "proposed.cols - 1" not in page, "xterm fit must not hide sizing bugs with a fixed column subtraction"
    assert "proposed.rows - 1" not in page, "xterm fit must not hide sizing bugs with a fixed row subtraction"
    assert "proposed.cols" in page and "proposed.rows" in page, "xterm fit must use FitAddon dimensions"
    assert "measureTerminalOverflow(host, terminal.cols, terminal.rows)" in page, (
        "xterm fit must correct actual rendered DOM overflow instead of clipping rows with CSS"
    )
    assert "convertEol: true" in page, "xterm must convert LF output to stable CRLF rendering"
    assert "new ResizeObserver" in page, "xterm host resize must be observed directly"
    assert ".terminal.console-terminal .xterm-screen" not in css, "xterm rows must not be clipped by CSS"
    assert ".terminal.console-terminal .xterm-rows" not in css, "xterm rows must not be clipped by CSS"
    terminal_host_css = css.split(".terminal.console-terminal {", 1)[1].split("}", 1)[0]
    assert "padding: 8px 10px;" in terminal_host_css, "terminal host must keep the stable 6/4 padded xterm frame"
    xterm_viewport_css = css.split(".terminal.console-terminal .xterm-viewport {", 1)[1].split("}", 1)[0]
    assert "overflow-y" not in xterm_viewport_css, "xterm viewport overflow must be controlled by xterm"
    assert "scrollbar-gutter" not in xterm_viewport_css, "xterm viewport must not reserve permanent scrollbar gutter"
    assert "queueTerminalWrite" not in page and "terminal.write(pending)" not in page, (
        "terminal output must be written directly instead of delayed through a paint queue"
    )
    assert 'event.key === "Enter" && event.shiftKey' in page and 'bracketed_paste: true' in page, (
        "xterm direct input must handle Shift+Enter as a submit-free newline attempt"
    )
    assert ".terminal.console-terminal .xterm-viewport::-webkit-scrollbar" in css and "scrollbar-width: none" in css, (
        "xterm scrollbar chrome must be hidden without clipping xterm rows"
    )
    assert "grid-template-columns: 22px 1fr auto 56px;" in css, "command bar must keep the stable prompt/input/hint/send layout"
    assert "command-bar-hint" in page and "Enter ↵ · Shift+Enter ⏎" in page, "command bar hint must be restored"
    assert "disabled={!consoleRunning}" in page and "readOnly={!consoleRunning}" not in page, "command input must use the stable disabled state"
    assert "contain: layout paint;" not in css, "layout containment breaks xterm measurement and can flicker"
    assert "contain: strict" not in css, "strict containment breaks xterm measurement and can flicker"
    console = (ROOT / "backend" / "app" / "ultrawork_console.py").read_text(encoding="utf-8")
    assert "Windows qwencode interactive console requires pywinpty" in console
    assert "except (ImportError, OSError) as exc" in console
    assert "from winpty import PtyProcess" in console
    assert "sys.executable" in console and "import_error={exc!r}" in console
    assert 'except ImportError:\n                state.mode = "pipe"' not in console
    bundle = (ROOT / "scripts" / "build-offline-bundle.py").read_text(encoding="utf-8")
    assert 'PYWINPTY_REQUIREMENT = "pywinpty==3.0.3"' in bundle
    assert "--upgrade --force-reinstall pywinpty==3.0.3" in bundle
    assert "from winpty import PtyProcess; print('pywinpty OK')" in bundle


def assert_frontend_pre_activation_lock_path() -> None:
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    forbidden = [
        "terminalPendingSubmitRef",
        "handlePreActivationTerminalData",
        "sendPreActivationTerminalPrompt",
        "xtermRef.current?.write(data)",
    ]
    for term in forbidden:
        assert term not in page, f"frontend must not locally echo or buffer xterm pre-activation input: {term}"
    assert "prepareConsoleText(text)" in page
    assert "textHasAnyWorkModePrefix(text)" in page
    assert "workModeActivatedRef.current = true" in page


def make_session(work_mode: str) -> ConsoleSession:
    return ConsoleSession(
        id="assert-session",
        project_id="project",
        project_name="project",
        root_path=str(ROOT),
        command=["qwen.cmd"],
        work_mode=work_mode,  # type: ignore[arg-type]
        log_path=ROOT / "data" / "ultrawork" / "assert.log",
        team_events_path=None,
        team_event_offset=0,
        chat_events_dir=None,
        chat_events_path=None,
        chat_event_offset=0,
        chat_started_after=0,
        created_at="2026-06-06T00:00:00",
    )


def extract_between(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index + len(start))
    return text[start_index:end_index]


if __name__ == "__main__":
    main()
