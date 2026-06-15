from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path
from typing import Any


class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _StubBaseModel:
    def __init__(self, **data: object) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def model_dump(self, **_: object) -> dict[str, object]:
        return dict(self.__dict__)


def _stub_field(default: object = None, default_factory: object = None, **_: object) -> object:
    if callable(default_factory):
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
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args)
            self.response = kwargs.get("response") or types.SimpleNamespace(status_code=0, text="")

    class _StubTimeout:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

    class _StubAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args: object) -> bool:
            return False

        async def post(self, *_args: object, **_kwargs: object):
            raise _StubHTTPError("httpx stub cannot perform network calls")

    httpx_stub.HTTPError = _StubHTTPError
    httpx_stub.HTTPStatusError = _StubHTTPStatusError
    httpx_stub.Timeout = _StubTimeout
    httpx_stub.AsyncClient = _StubAsyncClient
    sys.modules["httpx"] = httpx_stub


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.project_info import (  # noqa: E402
    PROJECT_INFO_CONTEXT_MAX_CHARS,
    analyze_project_info,
    describe_project_info_status,
    load_project_info_context,
    project_info_artifact_dir,
)
from backend.app.prompt_builder import (  # noqa: E402
    PromptBuilderManager,
    PromptBuilderRuntime,
    _compose_builder_prompt,
    _compose_intent_prompt,
    _render_ultrawork_prompt,
)
from backend.app.qwencode_runtime import (  # noqa: E402
    _patch_ultrawork_activation_message,
    _patch_work_mode_state_script,
)
from backend.app.ultrawork_console import ConsoleSession, _prepare_submitted_work_mode_prompt  # noqa: E402
from backend.app.ultrawork_policy import build_ultrawork_policy  # noqa: E402


DCP_SERVICES = Path("/Users/jules/Desktop/work/untitle/dcp/dcp-services-mevelop")
TEAM_LOG_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "team-log-lib.js"
FAST_PROJECT_INFO_FORBIDDEN_TERMS = [
    "task_size",
    "티셔츠",
    "subagent",
    "coder delegation",
    "ultrawork 팀",
    "coder-35",
    "dcp-front-developer",
    "dcp-backend-developer",
    "drt-front-developer",
    "drt-backend-developer",
    "drt-cms-front-developer",
    "drt-cms-backend-developer",
    "Implementation agent",
    "implementation_agent",
    "구현 agent",
    "구현 에이전트",
    "developer_agent",
    "developer agent",
]


def main() -> None:
    original_docs_dir = os.environ.get("KIWI_AIOPS_DOCS_DIR")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.environ["KIWI_AIOPS_DOCS_DIR"] = str(Path(tmp) / "aiops-docs")
            project_root = Path(tmp) / "sample-dcp-front"
            make_sample_project(project_root)
            analyze_project_info(project_root, write=True)

            assert_final_prompts_include_project_info(project_root)
            assert_prompt_builder_contexts_include_project_info(project_root)
            assert_prompt_builder_events_and_api(project_root)
            assert_missing_project_info(project_root.parent / "missing-info-project")
            assert_stale_project_info(project_root)
            assert_console_activation_keeps_runtime_context_hidden(project_root)
        finally:
            if original_docs_dir is None:
                os.environ.pop("KIWI_AIOPS_DOCS_DIR", None)
            else:
                os.environ["KIWI_AIOPS_DOCS_DIR"] = original_docs_dir

    assert_runtime_and_offline_bundle_project_info_hooks()
    assert_frontend_project_info_event_handling()
    assert_large_project_info_not_in_prompt_context()
    print("project info integration assertions passed")


def make_sample_project(root: Path) -> None:
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim").mkdir(parents=True)
    (root / "src" / "router").mkdir(parents=True)
    (root / "src" / "store" / "modules" / "com").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "components").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"name":"sample-dcp-front","scripts":{"typecheck":"vue-cli-service lint"},"dependencies":{"vue":"2","axios":"1"}}\n',
        encoding="utf-8",
    )
    (root / "src" / "router" / "index.js").write_text(
        "\n".join(
            [
                "import Vue from 'vue'",
                "import Router from 'vue-router'",
                "import ClaimIntro from '@/views/mo/mysamsunglife/claim/ClaimIntro.vue'",
                "Vue.use(Router)",
                "export default new Router({ routes: [{ path: '/claim/intro', name: 'ClaimIntro', component: ClaimIntro }] })",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim" / "ClaimIntro.vue").write_text(
        "\n".join(
            [
                "<template><section class=\"claim-intro\">보험금 청구</section></template>",
                "<script>",
                "import claimApi from '@/api/claim'",
                "export default {",
                "  name: 'ClaimIntro',",
                "  methods: { submitClaim() { return claimApi.saveClaim({ claimType: 'internet' }) } }",
                "}",
                "</script>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "src" / "api" / "claim.js").write_text(
        "import axios from 'axios'\nexport function saveClaim(payload) { return axios.post('/api/claim/save', payload) }\n",
        encoding="utf-8",
    )
    (root / "src" / "store" / "modules" / "com" / "DataStore.js").write_text(
        "export default { namespaced: true, state: { claimDraft: null } }\n",
        encoding="utf-8",
    )


def assert_final_prompts_include_project_info(project_root: Path) -> None:
    fast_prompt = render_prompt(project_root, "fast")
    assert_project_info_prompt_section(fast_prompt, "fast final prompt", project_root)
    assert_fast_project_info_no_leaks(fast_prompt, "fast final prompt")
    assert "FAST direct mode" in fast_prompt

    for mode, selected_size in [("ultrawork", "medium"), ("superpowers", "large")]:
        prompt = render_prompt(project_root, mode, selected_size=selected_size)
        assert_project_info_prompt_section(prompt, f"{mode} final prompt", project_root)
        assert f"사용자 선택: `{selected_size}`" in prompt
        assert "최종 source of truth: 사용자 선택값" in prompt
        if mode == "superpowers":
            assert "## superpowers skill-first 계약" in prompt


def assert_prompt_builder_contexts_include_project_info(project_root: Path) -> None:
    for mode in ["fast", "ultrawork", "superpowers"]:
        state = prompt_state(project_root, mode, selected_size="small")
        intent_prompt = _compose_intent_prompt(state)  # type: ignore[arg-type]
        compose_prompt = _compose_builder_prompt(state)  # type: ignore[arg-type]
        for label, text in {"intent": intent_prompt, "compose": compose_prompt}.items():
            assert "Project Info Layer 공유 근거" in text, f"{mode} {label} missing Project Info context"
            assert "Profile: dcp-front" in text, f"{mode} {label} missing profile"
            assert "Status: ready" in text, f"{mode} {label} missing ready status"
            assert "Required reading" in text, f"{mode} {label} missing required reading"
            assert "Target files/domain hints" in text, f"{mode} {label} missing target/domain hints"
        if mode == "fast":
            assert_fast_project_info_no_leaks(intent_prompt, "fast intent prompt")
            assert_fast_project_info_no_leaks(compose_prompt, "fast compose prompt")


def assert_prompt_builder_events_and_api(project_root: Path) -> None:
    events: list[dict[str, Any]] = []

    async def emit(event: dict[str, Any]) -> None:
        events.append(event)

    async def run_runtime() -> dict[str, Any]:
        runtime = PromptBuilderRuntime(
            FakeQwen(),
            emit,
            types.SimpleNamespace(
                kk_docs_mcp_enabled=False,
                kk_docs_mcp_url="",
                max_context_chars=120_000,
            ),
        )
        return await runtime.run(
            {"id": "sample", "name": "sample-dcp-front", "root_path": str(project_root)},
            "보험금 청구 화면 문구를 수정해줘.",
            [],
            120_000,
            "ultrawork",
            "medium",
        )

    state = asyncio.run(run_runtime())
    project_info_events = [event for event in events if event.get("type") == "project_info"]
    assert project_info_events, "Prompt Builder did not emit a Project Info event"
    event_info = project_info_events[0]["project_info"]
    assert event_info["status"] == "ready"
    assert event_info["profile"]["key"] == "dcp-front"
    assert event_info["required_reading"], event_info
    assert event_info["target_hints"], event_info
    assert state.get("project_info", {}).get("status") == "ready"
    assert "## Project Info Layer 시작 컨텍스트" in state.get("final_prompt", "")

    manager = PromptBuilderManager()
    public = manager._public_run(
        {
            "id": "run",
            "project_id": "project",
            "project_name": "sample",
            "work_mode": "ultrawork",
            "work_mode_label": "ultrawork",
            "status": "succeeded",
            "created_at": "2026-06-06T00:00:00",
            "completed_at": "2026-06-06T00:00:01",
            "message": "msg",
            "assistant_message": "ok",
            "questions": [],
            "interview_questions": [],
            "final_prompt": state["final_prompt"],
            "task_size": "medium",
            "task_size_reason": "user selected",
            "task_size_source": "user",
            "selected_task_size": "medium",
            "recommended_task_size": "small",
            "recommended_task_size_reason": "narrow",
            "ultrawork_mode": "balanced",
            "prompt_lint": {},
            "prompt_evaluation": {},
            "project_info": state["project_info"],
            "log_path": "data/prompt-builder/run.jsonl",
            "events": [],
        }
    )
    assert public["project_info"]["status"] == "ready"
    assert public["project_info"]["profile"]["key"] == "dcp-front"


def assert_missing_project_info(project_root: Path) -> None:
    project_root.mkdir(parents=True)
    (project_root / "package.json").write_text('{"name":"missing-info"}\n', encoding="utf-8")
    prompt = render_prompt(project_root, "ultrawork", selected_size="small")
    assert "Status: missing" in prompt
    assert "Project Info refresh" in prompt or "project initialization" in prompt
    assert "Profile: dcp-front" not in prompt, "missing Project Info must not hallucinate a profile"
    info = describe_project_info_status(project_root, "ultrawork")
    assert info["status"] == "missing"
    assert info["required_reading"], info


def assert_stale_project_info(project_root: Path) -> None:
    source = project_root / "src" / "api" / "claim.js"
    source.write_text(source.read_text(encoding="utf-8") + "\nexport const staleForAssertion = true\n", encoding="utf-8")
    context = load_project_info_context(project_root, "ultrawork", PROJECT_INFO_CONTEXT_MAX_CHARS)
    assert "Status: stale" in context
    assert "Stale: true" in context
    assert "Changed inputs: src/api/claim.js" in context
    prompt = render_prompt(project_root, "superpowers", selected_size="large")
    assert "Project Info refresh required" in prompt
    assert "src/api/claim.js" in prompt
    info = describe_project_info_status(project_root, "superpowers")
    assert info["status"] == "stale"
    assert any(item["path"] == "src/api/claim.js" for item in info["stale"]["changed"])


def assert_console_activation_keeps_runtime_context_hidden(project_root: Path) -> None:
    for mode, task_size in [("fast", None), ("ultrawork", "medium"), ("superpowers", "large")]:
        session = ConsoleSession(
            id=f"assert-{mode}",
            project_id="project",
            project_name=project_root.name,
            root_path=str(project_root),
            command=["qwen.cmd"],
            work_mode=mode,  # type: ignore[arg-type]
            log_path=ROOT / "data" / "ultrawork" / f"assert-{mode}.log",
            team_events_path=None,
            team_event_offset=0,
            chat_events_dir=None,
            chat_events_path=None,
            chat_event_offset=0,
            chat_started_after=0,
            created_at="2026-06-06T00:00:00",
        )
        text = _prepare_submitted_work_mode_prompt(
            session,
            f"{'lightwork' if mode == 'fast' else mode}\n\n보험금 청구 화면을 확인해줘.",
            task_size=task_size,
            task_size_reason="assertion selected size" if task_size else None,
        )
        assert "## Project Info Layer 시작 컨텍스트" not in text, f"{mode} direct console input pasted runtime context"
        assert "[KIWI_WORK_MODE_LOCK]" not in text, f"{mode} direct console input pasted work-mode lock contract"
        assert text.splitlines()[0] == ("lightwork" if mode == "fast" else f"{mode}_{task_size}")
        if mode == "fast":
            assert "## 티셔츠 사이징" not in text
        else:
            assert "## 티셔츠 사이징" not in text


def assert_runtime_and_offline_bundle_project_info_hooks() -> None:
    assert TEAM_LOG_SAMPLE.exists(), f"missing runtime sample: {TEAM_LOG_SAMPLE}"
    source = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched = _patch_ultrawork_activation_message(_patch_work_mode_state_script(source))
    assert_runtime_project_info_context(patched, "backend runtime")

    bundle = load_bundle_module()
    patched_bundle = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(source))
    assert_runtime_project_info_context(patched_bundle, "offline bundle runtime")

    for path in [
        ROOT / "docs" / "ultrawork-runtime-policy.md",
        ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "SKILL.md",
    ]:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "Project Info Layer" in text, f"{path} missing Project Info runtime instruction"
        assert "D:/aiops/docs/<project-key>/project-info" in text, f"{path} missing portable Project Info path"

    includes = set(bundle.SOURCE_INCLUDE)
    assert {"backend", "scripts", "docs"}.issubset(includes), bundle.SOURCE_INCLUDE
    for required in [
        ROOT / "backend" / "app" / "project_info.py",
        ROOT / "scripts" / "assert-project-info-layer.py",
        ROOT / "scripts" / "assert-project-info-quality.py",
        ROOT / "scripts" / "assert-project-info-integration.py",
    ]:
        assert required.exists(), f"offline source include would miss required file: {required}"


def assert_frontend_project_info_event_handling() -> None:
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    for required in [
        "type ProjectInfoStatus",
        "project_info?: ProjectInfoStatus",
        "payload.type === \"project_info\"",
        "setBuilderRunProjectInfo(payload.project_info)",
        "\"project_info\"",
        "Project Info ready",
        "Project Info stale",
        "Project Info missing",
    ]:
        assert required in page, f"frontend missing explicit Project Info event handling: {required}"


def assert_large_project_info_not_in_prompt_context() -> None:
    assert DCP_SERVICES.exists(), f"dcp-services fixture missing: {DCP_SERVICES}"
    project_info_dir = project_info_artifact_dir(DCP_SERVICES)
    project_json = project_info_dir / "project-info.json"
    eai_md = project_info_dir / "api" / "eai-interface-index.md"
    assert project_json.stat().st_size > 8_000_000, project_json.stat().st_size
    assert eai_md.stat().st_size > 4_000_000, eai_md.stat().st_size

    context = load_project_info_context(DCP_SERVICES, "ultrawork", PROJECT_INFO_CONTEXT_MAX_CHARS)
    assert len(context) <= PROJECT_INFO_CONTEXT_MAX_CHARS + 80, len(context)
    assert len(context) < project_json.stat().st_size // 100
    assert len(context) < eai_md.stat().st_size // 50
    assert '"source_manifest"' not in context
    assert not context.lstrip().startswith("{")

    prompt = render_prompt(DCP_SERVICES, "ultrawork", selected_size="medium")
    assert len(prompt) < 90_000, len(prompt)
    assert '"source_manifest"' not in prompt
    assert not prompt.lstrip().startswith("{")


def render_prompt(project_root: Path, mode: str, selected_size: str = "medium") -> str:
    state = prompt_state(project_root, mode, selected_size)
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "프롬프트를 생성했습니다.",
        "prompt_parts": {
            "title": "보험금 청구 화면 확인",
            "task": "보험금 청구 화면의 안내 문구와 저장 흐름을 확인한다.",
            "verification": ["npm run typecheck"],
        },
    }
    return _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]


def prompt_state(project_root: Path, mode: str, selected_size: str = "medium") -> dict[str, Any]:
    intent = {
        "task_summary": "보험금 청구 화면의 안내 문구와 저장 흐름을 확인한다.",
        "task_type": "frontend",
        "mode": "implement",
        "search_queries": ["보험금 청구", "ClaimIntro", "DataStore"],
        "target_files": ["src/views/mo/mysamsunglife/claim/ClaimIntro.vue", "src/api/claim.js"],
        "risk_flags": ["store", "api"],
    }
    state: dict[str, Any] = {
        "project": {"id": "sample", "name": project_root.name, "root_path": str(project_root)},
        "user_message": "보험금 청구 화면의 안내 문구와 저장 흐름을 확인해줘.",
        "work_mode": mode,
        "history": [],
        "project_context": "KIWI.md project memory",
        "project_info_context": load_project_info_context(project_root, mode, PROJECT_INFO_CONTEXT_MAX_CHARS),
        "project_info": describe_project_info_status(project_root, mode),
        "prompt_guide": "Ultrawork prompt guide",
        "intent": intent,
        "kk_docs_results": [],
    }
    if mode != "fast":
        policy = build_ultrawork_policy(
            state["project"],
            intent,
            selected_task_size=selected_size,
            selected_task_size_reason=f"사용자가 `{selected_size}`를 선택했다.",
        )
        state["selected_task_size"] = selected_size
        state["ultrawork_policy"] = policy
    return state


def assert_project_info_prompt_section(text: str, label: str, project_root: Path) -> None:
    artifact_dir = project_info_artifact_dir(project_root).as_posix()
    for required in [
        "## Project Info Layer 시작 컨텍스트",
        "# Project Info Layer",
        "Profile:",
        "Status:",
        "Required reading",
        "Target files/domain hints",
        f"{artifact_dir}/project-summary.md",
    ]:
        assert required in text, f"{label} missing Project Info marker: {required}"


def assert_fast_project_info_no_leaks(text: str, label: str) -> None:
    for forbidden in FAST_PROJECT_INFO_FORBIDDEN_TERMS:
        assert forbidden not in text, f"{label} leaked FAST-forbidden Project Info term: {forbidden}"


def assert_runtime_project_info_context(text: str, label: str) -> None:
    for required in [
        "Project Info Layer",
        "projectKnowledgeIndex(input)",
        "projectInfoRoot(input)",
        "projectDocsRuntimeLine(input)",
        "D:/aiops/docs/${projectDocsKey(input)}",
        "only if",
        "Never try project-relative",
        "Project Info refresh",
        "Do not paste full project-info.json",
    ]:
        assert required in text, f"{label} missing runtime Project Info instruction: {required}"


def load_bundle_module() -> Any:
    module_path = ROOT / "scripts" / "build-offline-bundle.py"
    spec = importlib.util.spec_from_file_location("build_offline_bundle_project_info_assert", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeQwen:
    calls = 0

    async def chat(self, *_: object, **__: object) -> str:
        self.calls += 1
        if self.calls == 1:
            return (
                '{"task_summary":"보험금 청구 화면 문구 수정","task_type":"frontend","mode":"implement",'
                '"search_queries":["보험금 청구","ClaimIntro"],'
                '"target_files":["src/views/mo/mysamsunglife/claim/ClaimIntro.vue"],'
                '"risk_flags":["api"]}'
            )
        return (
            '{"status":"ready","mode":"implement","assistant_message":"ready",'
            '"prompt_parts":{"title":"보험금 청구 화면 문구 수정",'
            '"task":"보험금 청구 화면 문구를 수정하고 저장 흐름을 확인한다.",'
            '"required_reading":["src/views/mo/mysamsunglife/claim/ClaimIntro.vue"],'
            '"target_files":["src/api/claim.js"],'
            '"verification":["npm run typecheck"]}}'
        )


if __name__ == "__main__":
    main()
