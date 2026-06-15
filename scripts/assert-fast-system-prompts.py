from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import types
from pathlib import Path


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

FAST_DIR = ROOT / "docs" / "fast-system-prompts"
REQUIRED_ARTIFACTS = [
    FAST_DIR / "README.md",
    FAST_DIR / "fast-system-prompt.dcp-front.md",
    FAST_DIR / "fast-system-prompt.dcp-services.md",
    FAST_DIR / "fast-system-prompt.generic.md",
    FAST_DIR / "evaluation-rubric.md",
    FAST_DIR / "evaluation-report.md",
]
PROFILE_PROMPTS = {
    "dcp-front": FAST_DIR / "fast-system-prompt.dcp-front.md",
    "dcp-services": FAST_DIR / "fast-system-prompt.dcp-services.md",
    "generic": FAST_DIR / "fast-system-prompt.generic.md",
}
PROFILE_KEYWORDS = {
    "dcp-front": [
        "Project Info Layer",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "D:/aiops/docs/<project-key>/project-info",
        "optional Project Info Layer summaries",
        "route",
        "view",
        "component",
        "Vuex",
        "DataStore",
        "Axios",
        "CSS",
        "Playwright",
        "current files",
        "minimal diff",
        "focused verification",
        "stop and ask",
    ],
    "dcp-services": [
        "Project Info Layer",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "D:/aiops/docs/<project-key>/project-info",
        "optional Project Info Layer summaries",
        "controller",
        "service",
        "repository",
        "MyBatis",
        "EAI",
        "resources-env",
        "profile",
        "verification",
        "current files",
        "minimal diff",
        "focused verification",
        "stop and ask",
    ],
    "generic": [
        "Project Info Layer",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "D:/aiops/docs/<project-key>/project-info",
        "optional Project Info Layer summaries",
        "current files",
        "entrypoint",
        "minimal diff",
        "focused verification",
        "stop and ask",
    ],
}
FAST_FORBIDDEN_PATTERNS = [
    r"\btask_size\b",
    r"티셔츠",
    r"\bultrawork\b",
    r"\bsuperpowers\b",
    r"\bteam\b",
    r"\bsubagent\b",
    r"\bcoder-35\b",
    r"\bdcp-front-developer\b",
    r"\bdcp-backend-developer\b",
    r"coder\s+delegation",
    r"agent\s+tool",
    r"agent\s+호출",
    r"\bsubagent_type\b",
]


def main() -> None:
    assert_required_artifacts()
    assert_profile_prompt_keywords_and_forbidden_terms()
    assert_prompt_files_split_runtime_and_human_review()
    assert_runtime_references()
    assert_prompt_builder_and_console_outputs()
    assert_runtime_and_offline_bundle_installation()
    assert_evaluation_documents()
    print("fast system prompt assertions passed")


def assert_required_artifacts() -> None:
    for path in REQUIRED_ARTIFACTS:
        assert path.exists(), f"missing required FAST artifact: {path.relative_to(ROOT)}"


def assert_profile_prompt_keywords_and_forbidden_terms() -> None:
    for profile, path in PROFILE_PROMPTS.items():
        text = path.read_text(encoding="utf-8")
        for keyword in PROFILE_KEYWORDS[profile]:
            assert keyword in text, f"{path.relative_to(ROOT)} missing keyword: {keyword}"
        assert_forbidden_absent(text, path.relative_to(ROOT).as_posix())
        assert "Read central project docs before broad analysis or edits" in text
        assert "only if that central directory exists" in text
        assert "Verify every Project Info claim against current files before editing" in text
        assert "`todo_write` tool" in text, f"{path.relative_to(ROOT)} missing mandatory TodoWrite planning"
        assert "do not produce any size report" in text.lower(), f"{path.relative_to(ROOT)} missing FAST no-size-report guard"


def assert_prompt_files_split_runtime_and_human_review() -> None:
    for path in PROFILE_PROMPTS.values():
        text = path.read_text(encoding="utf-8")
        assert "## Runtime Injection Summary" in text, f"{path.relative_to(ROOT)} missing runtime summary"
        assert "## Human-Review Final Prompt" in text, f"{path.relative_to(ROOT)} missing human prompt"
        assert text.index("## Runtime Injection Summary") < text.index("## Human-Review Final Prompt")


def assert_runtime_references() -> None:
    sources = {
        "backend fast loader": ROOT / "backend" / "app" / "fast_system_prompts.py",
        "Prompt Builder": ROOT / "backend" / "app" / "prompt_builder.py",
        "Console activation": ROOT / "backend" / "app" / "ultrawork_console.py",
        "backend runtime": ROOT / "backend" / "app" / "qwencode_runtime.py",
        "offline bundle": ROOT / "scripts" / "build-offline-bundle.py",
    }
    for label, path in sources.items():
        assert path.exists(), f"{label} source missing: {path.relative_to(ROOT)}"
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "fast-system-prompts" in text, f"{label} does not reference docs/fast-system-prompts"
    prompt_builder = sources["Prompt Builder"].read_text(encoding="utf-8", errors="replace")
    assert "load_fast_system_prompt" in prompt_builder, "Prompt Builder must load FAST system prompt by profile"


def assert_prompt_builder_and_console_outputs() -> None:
    from backend.app.fast_system_prompts import load_fast_system_prompt, render_fast_runtime_injection
    from backend.app.prompt_builder import _render_ultrawork_prompt
    from backend.app.ultrawork_console import ConsoleSession, _prepare_submitted_work_mode_prompt

    with tempfile.TemporaryDirectory() as tmp:
        front_root = Path(tmp) / "sample-dcp-front"
        front_root.mkdir()
        (front_root / "package.json").write_text('{"dependencies":{"vue":"2","vuex":"3","axios":"1"}}\n', encoding="utf-8")
        loaded = load_fast_system_prompt(front_root)
        assert loaded.profile_key == "dcp-front"
        assert "fast-system-prompt.dcp-front.md" in loaded.source_path.as_posix()
        injection = render_fast_runtime_injection(front_root, max_chars=6000)
        assert "FAST system prompt source" in injection
        assert "fast-system-prompt.dcp-front.md" in injection
        assert "route" in injection and "DataStore" in injection and "Playwright" in injection
        assert_forbidden_absent(injection, "render_fast_runtime_injection")

        state = {
            "project": {"name": "sample-dcp-front", "root_path": str(front_root)},
            "user_message": "보험금 청구 화면 문구를 한 줄 수정해줘.",
            "work_mode": "fast",
            "history": [],
            "project_context": "KIWI.md",
            "project_info_context": "# Project Info Layer\n\n- Status: missing\n- Profile: dcp-front",
            "intent": {
                "task_summary": "보험금 청구 화면 문구를 한 줄 수정한다.",
                "task_type": "frontend",
                "mode": "implement",
                "search_queries": ["보험금 청구"],
                "target_files": ["src/views/claim/ClaimIntro.vue"],
            },
            "kk_docs_results": [],
        }
        result = {
            "status": "ready",
            "mode": "implement",
            "assistant_message": "FAST prompt",
            "prompt_parts": {"title": "문구 수정", "task": "문구 한 줄 수정", "verification": ["npm run typecheck"]},
        }
        prompt = _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]
        assert "FAST system prompt source" in prompt
        assert "fast-system-prompt.dcp-front.md" in prompt
        assert "## FAST System Prompt Runtime Summary" in prompt
        assert_forbidden_absent(prompt, "Prompt Builder FAST final prompt")

        session = ConsoleSession(
            id="assert-fast",
            project_id="project",
            project_name="sample-dcp-front",
            root_path=str(front_root),
            command=["qwen.cmd"],
            work_mode="fast",  # type: ignore[arg-type]
            log_path=ROOT / "data" / "ultrawork" / "assert-fast.log",
            team_events_path=None,
            team_event_offset=0,
            chat_events_dir=None,
            chat_events_path=None,
            chat_event_offset=0,
            chat_started_after=0,
            created_at="2026-06-06T00:00:00",
        )
        console_prompt = _prepare_submitted_work_mode_prompt(session, "fast\n\n문구 한 줄 수정")
        assert console_prompt.splitlines()[0] == "lightwork"
        assert "FAST system prompt source" not in console_prompt
        assert "fast-system-prompt.dcp-front.md" not in console_prompt
        assert "## Project Info Layer 시작 컨텍스트" not in console_prompt
        assert_forbidden_absent(console_prompt, "Console FAST activation prompt")


def assert_runtime_and_offline_bundle_installation() -> None:
    from backend.app.qwencode_runtime import _install_kiwi_fast_system_prompts, _patch_work_mode_state_script

    bundle = load_bundle_module()
    team_log_sample = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "team-log-lib.js"
    team_log = team_log_sample.read_text(encoding="utf-8", errors="replace")
    backend_patched = _patch_work_mode_state_script(team_log)
    bundle_patched = bundle.patch_work_mode_state_script(team_log)
    for label, text in {"backend runtime": backend_patched, "offline bundle": bundle_patched}.items():
        fast_context = extract_between(text, "function fastModeContext(trigger", "function superpowersXsmallContext")
        assert "FAST system prompt source" in fast_context, f"{label} missing FAST system prompt source"
        assert "fast-system-prompt.dcp-front.md" in fast_context, f"{label} missing dcp-front source path"
        assert "fast-system-prompt.dcp-services.md" in fast_context, f"{label} missing dcp-services source path"
        assert "fast-system-prompt.generic.md" in fast_context, f"{label} missing generic source path"
        assert "FAST/lightwork has no size report" in fast_context, f"{label} missing no-size-report guard"
        assert "`todo_write` tool" in fast_context, f"{label} missing mandatory TodoWrite planning"
        assert "User question protocol" in fast_context, f"{label} missing ask_user_question protocol"
        assert "Before calling `ask_user_question`, first load/check the tool usage or schema" in fast_context, (
            f"{label} missing ask_user_question schema-first guard"
        )
        assert "ask with `ask_user_question`" not in fast_context, f"{label} ask_user_question guidance is too weak"
        assert "do not claim a mode conflict" in fast_context, f"{label} missing denial conflict guard"
        assert_forbidden_absent(fast_context, f"{label} fast runtime context")

    with tempfile.TemporaryDirectory() as tmp:
        runtime_root = Path(tmp)
        _install_kiwi_fast_system_prompts(runtime_root)
        assert_installed_fast_prompts(runtime_root, "backend runtime installer")
    with tempfile.TemporaryDirectory() as tmp:
        runtime_root = Path(tmp)
        bundle.install_kiwi_fast_system_prompts(runtime_root)
        assert_installed_fast_prompts(runtime_root, "offline bundle installer")

    manifest_text = (ROOT / "scripts" / "build-offline-bundle.py").read_text(encoding="utf-8")
    assert "fastSystemPrompts" in manifest_text, "bundle manifest must include fastSystemPrompts"


def assert_evaluation_documents() -> None:
    rubric = (FAST_DIR / "evaluation-rubric.md").read_text(encoding="utf-8")
    report = (FAST_DIR / "evaluation-report.md").read_text(encoding="utf-8")
    for required in ["objective rubric", "benchmark tasks", "weakness", "accepted improvements"]:
        assert required in rubric.lower(), f"evaluation rubric missing: {required}"
        assert required in report.lower(), f"evaluation report missing: {required}"
    for required in [
        "GPT-5.5 xhigh evaluator",
        "evaluation packet",
        "benchmark prompts",
        "expected behavior",
        "failure patterns",
        "accepted improvements",
        "self-review findings",
    ]:
        assert required in report, f"evaluation report missing evaluator packet term: {required}"
    assert "Critical: none" in report
    assert "High: none" in report
    assert "Medium: none" in report
    assert not re.search(r"(Critical|High|Medium):\s*(open|unresolved|finding)", report, re.IGNORECASE)


def assert_forbidden_absent(text: str, label: str) -> None:
    for pattern in FAST_FORBIDDEN_PATTERNS:
        assert not re.search(pattern, text, re.IGNORECASE), f"{label} leaked FAST forbidden pattern: {pattern}"


def assert_installed_fast_prompts(runtime_root: Path, label: str) -> None:
    for base in [
        runtime_root / "portable-user" / ".qwen" / "extensions" / "fast-system-prompts",
        runtime_root / "extensions" / "fast-system-prompts",
    ]:
        assert (base / "fast-system-prompt.dcp-front.md").exists(), f"{label} missing dcp-front install"
        assert (base / "fast-system-prompt.dcp-services.md").exists(), f"{label} missing dcp-services install"
        assert (base / "fast-system-prompt.generic.md").exists(), f"{label} missing generic install"


def load_bundle_module():
    module_path = ROOT / "scripts" / "build-offline-bundle.py"
    spec = importlib.util.spec_from_file_location("build_offline_bundle_fast_assert", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_between(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index + len(start))
    return text[start_index:end_index]


if __name__ == "__main__":
    main()
