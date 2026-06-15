from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
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
            self.response = kwargs.get("response") or types.SimpleNamespace(
                status_code=0,
                text="",
            )

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
REF = ROOT.parent / "ref" / "superpowers-main"
sys.path.insert(0, str(ROOT))

from backend.app.prompt_builder import (  # noqa: E402
    _compose_builder_prompt,
    _compose_intent_prompt,
    _intent_system_prompt,
    _lint_work_mode_prompt,
    _render_ultrawork_prompt,
)
from backend.app.qwencode_runtime import (  # noqa: E402
    _install_kiwi_superpowers_extension,
    _patch_qwen_cli_hooks,
    _patch_ultrawork_activation_message,
    _patch_work_mode_activation_script,
    _patch_work_mode_policy_script,
    _patch_work_mode_state_script,
)
from backend.app.ultrawork_policy import build_ultrawork_policy  # noqa: E402


TEAM_LOG_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "team-log-lib.js"
POLICY_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "orchestration-policy.js"
ACTIVATION_SAMPLE = ROOT.parent / "deliverables" / "qwencode-explorer35-20260604" / "scripts" / "ultrawork-activate.js"
QWEN_017_RUNTIME = ROOT.parent / "deliverables" / "qwen-code-offline-win11-v0.17.1"
CLI_SAMPLE = QWEN_017_RUNTIME / "app" / "cli.js"
CLI_CHUNK_SAMPLE = QWEN_017_RUNTIME / "app" / "chunks" / "chunk-2KEXT6RB.js"


def main() -> None:
    assert_reference_source_exists()
    assert_analysis_document()
    assert_superpowers_runtime_assets()
    assert_superpowers_prompt_contract()
    assert_runtime_and_offline_patches()
    assert_qwen_cli_hook_patches()
    assert_runtime_mutation_policy_blockers_fixed()
    assert_runtime_policy_executable_matrix()
    assert_superpowers_xsmall_context_is_direct_and_non_xsmall_is_team_guarded()
    assert_fast_mode_has_no_team_concepts()
    assert_runtime_assets_have_no_remote_or_claude_only_dependency()
    print("superpowers porting assertions passed")


def assert_reference_source_exists() -> None:
    assert REF.exists(), f"missing upstream reference source: {REF}"
    for relative in [
        "README.md",
        "hooks/session-start",
        "skills/using-superpowers/SKILL.md",
        "skills/test-driven-development/SKILL.md",
        "skills/systematic-debugging/SKILL.md",
        "skills/verification-before-completion/SKILL.md",
    ]:
        assert (REF / relative).exists(), f"missing upstream reference file: {relative}"


def assert_analysis_document() -> None:
    path = ROOT / "docs" / "superpowers-porting-analysis.md"
    assert path.exists(), "missing docs/superpowers-porting-analysis.md"
    text = path.read_text(encoding="utf-8")
    required_sections = [
        "# Superpowers Porting Analysis",
        "## Upstream Structure",
        "## Claude And Internet Dependencies",
        "## Skill And Workflow Model",
        "## KIWI Qwencode Porting Decisions",
        "## Runtime Asset Mapping",
        "## Removed Or Replaced Dependencies",
        "## Verification Assertions",
    ]
    for section in required_sections:
        assert section in text, f"analysis doc missing section: {section}"
    for required in [
        "../ref/superpowers-main",
        "SessionStart",
        "using-superpowers",
        "skill-first",
        "Project Info Layer",
        "kiwi-superpowers",
        "Qwen",
        "offline",
    ]:
        assert required in text, f"analysis doc missing core evidence term: {required}"


def assert_superpowers_runtime_assets() -> None:
    skill_path = ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "SKILL.md"
    workflow_path = ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "superpowers-workflows.md"
    command_path = ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "command-contract.md"
    hook_path = ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "hook-policy.md"
    policy_path = ROOT / "docs" / "superpowers-runtime-policy.md"
    for path in [skill_path, workflow_path, command_path, hook_path, policy_path]:
        assert path.exists(), f"missing superpowers runtime asset: {path.relative_to(ROOT)}"

    skill = skill_path.read_text(encoding="utf-8")
    for required in [
        "skill-first",
        "central project docs",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "D:/aiops/docs/<project-key>/project-info",
        "built-in `skill` tool",
        "work mode lock",
        "selected task_size",
        "xsmall",
        "small",
        "medium",
        "large",
        "xlarge",
        "kiwi-superpowers",
    ]:
        assert required in skill, f"kiwi-superpowers skill missing contract term: {required}"

    command = command_path.read_text(encoding="utf-8")
    for required in ["superpowers", "spw", "selected task_size", "source of truth"]:
        assert required in command, f"superpowers command contract missing term: {required}"

    hook = hook_path.read_text(encoding="utf-8")
    for required in [
        "runtime activation",
        "pre-tool policy",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "built-in `skill` tool",
        "kiwi-superpowers",
    ]:
        assert required in hook, f"superpowers hook policy missing term: {required}"

    policy = policy_path.read_text(encoding="utf-8")
    for required in [
        "SUPERPOWERS_POLICY",
        "D:/aiops/docs/<project-key>/knowledge/00-index.md",
        "D:/aiops/docs/<project-key>/project-info",
        "built-in `skill` tool",
        "kiwi-superpowers",
        "selected task_size",
        "source of truth",
        "skill-first",
    ]:
        assert required in policy, f"superpowers policy missing term: {required}"


def assert_superpowers_prompt_contract() -> None:
    policy = build_ultrawork_policy(
        {"name": "generic", "root_path": str(ROOT)},
        {
            "task_summary": "여러 화면과 저장 흐름을 확인하고 수정한다.",
            "task_type": "frontend",
            "task_size": "medium",
            "task_size_reason": "사용자가 medium을 선택했다.",
            "search_queries": ["claim", "DataStore"],
            "target_files": ["src/views/Sample.vue"],
        },
        selected_task_size="large",
        selected_task_size_reason="assertion user selected large",
    )
    state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "청구 화면 저장 흐름을 고쳐줘.",
        "work_mode": "superpowers",
        "selected_task_size": "large",
        "history": [],
        "project_context": "KIWI.md",
        "project_info_context": "# Project Info Layer\n\nEvidence: D:/aiops/docs/<project-key>/project-info/project-summary.md",
        "project_info": {"status": "ready", "profile": {"key": "generic"}},
        "intent": {
            "task_summary": "청구 화면 저장 흐름 수정",
            "task_type": "frontend",
            "mode": "implement",
            "task_size": "large",
            "task_size_reason": "assertion user selected large",
            "search_queries": ["claim", "DataStore"],
            "target_files": ["src/views/Sample.vue"],
        },
        "kk_docs_results": [],
        "ultrawork_policy": policy,
    }
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "superpowers prompt",
        "prompt_parts": {
            "title": "청구 화면 저장 흐름 수정",
            "task": "청구 화면 저장 흐름을 확인하고 필요한 최소 수정을 수행한다.",
            "verification": ["npm run typecheck"],
        },
    }
    prompt = _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]
    for required in [
        "## Project Info Layer 시작 컨텍스트",
        "사용자 선택: `large`",
        "최종 source of truth: 사용자 선택값",
        "## superpowers skill-first 계약",
        "`kiwi-superpowers`",
        "superpowers policy and skill are the source of truth",
        "selected task_size",
    ]:
        assert required in prompt, f"superpowers final prompt missing: {required}"
    assert "Kiwi 1차 산정" not in prompt, "superpowers prompt used Kiwi recommendation as final sizing"
    assert not re.search(r"ultrawork.{0,60}source of truth|source of truth.{0,60}ultrawork", prompt, re.I | re.S), (
        "superpowers prompt made ultrawork look like the source of truth"
    )
    assert _lint_work_mode_prompt(prompt, "superpowers")["passed"], "superpowers final prompt failed work-mode lint"


def assert_runtime_and_offline_patches() -> None:
    team_log = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_team_log = _patch_work_mode_state_script(_patch_ultrawork_activation_message(team_log))
    assert_superpowers_runtime_context(patched_team_log, "backend runtime")

    policy = POLICY_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_policy = _patch_work_mode_policy_script(policy)
    assert 'mode === "superpowers" && isSkillTool(toolName)' in patched_policy
    assert "Allowed by superpowers skill-first policy." in patched_policy

    activation = ACTIVATION_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_activation = _patch_work_mode_activation_script(activation)
    assert "teamModeContext(trigger, input.prompt || \"\", input)" in patched_activation, (
        "backend activation patch must pass submitted prompt and input to teamModeContext"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_root = Path(temp_dir)
        _install_kiwi_superpowers_extension(runtime_root)
        assert_installed_superpowers_extension(runtime_root, "backend runtime installer")

    bundle = load_bundle_module()
    patched_bundle_team_log = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(team_log))
    assert_superpowers_runtime_context(patched_bundle_team_log, "offline bundle runtime")
    patched_bundle_policy = bundle.patch_work_mode_policy_script(policy)
    assert patched_policy == patched_bundle_policy, "backend/offline orchestration policy patches drifted"
    assert 'mode === "superpowers" && isSkillTool(toolName)' in patched_bundle_policy
    assert "Allowed by superpowers skill-first policy." in patched_bundle_policy
    patched_bundle_activation = bundle.patch_work_mode_activation_script(activation)
    assert patched_activation == patched_bundle_activation, "backend/offline activation patches drifted"

    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_root = Path(temp_dir)
        bundle.install_kiwi_superpowers_extension(runtime_root)
        assert_installed_superpowers_extension(runtime_root, "offline bundle installer")


def assert_qwen_cli_hook_patches() -> None:
    assert CLI_SAMPLE.exists(), f"missing Qwen 0.17 CLI sample: {CLI_SAMPLE}"
    assert CLI_CHUNK_SAMPLE.exists(), f"missing Qwen 0.17 CLI chunk sample: {CLI_CHUNK_SAMPLE}"

    bundle = load_bundle_module()
    samples = {
        "cli": CLI_SAMPLE.read_text(encoding="utf-8", errors="replace"),
        "chunk": CLI_CHUNK_SAMPLE.read_text(encoding="utf-8", errors="replace"),
    }
    for label, source in samples.items():
        backend_patched = _patch_qwen_cli_hooks(source)
        offline_patched = bundle.patch_qwen_cli_hooks(source)
        assert backend_patched == offline_patched, f"backend/offline Qwen CLI hook patch drifted for {label}"
        if "const functionResponses = []" in source:
            assert "function normalizeKiwiToolName(name)" in backend_patched, (
                f"{label} must normalize common Kiwi tool aliases"
            )
            assert 'compact === "todowrite" || compact === "mcptodowrite"' in backend_patched, (
                f"{label} must normalize TodoWrite/MCP todo aliases to todo_write"
            )
            assert 'compact === "askuserquestion" || compact === "mcpaskuserquestion"' in backend_patched, (
                f"{label} must normalize AskUserQuestion/MCP ask aliases to ask_user_question"
            )
            assert "const rawName = fc.name" in backend_patched and "fc.name = name3" in backend_patched, (
                f"{label} must update functionCall name before registry lookup"
            )
        if label == "cli":
            assert "if (Array.isArray(value)) value = value[value.length - 1];" in backend_patched, (
                "cli approval mode parser must tolerate duplicate approval-mode argv arrays"
            )
            assert 'if (typeof value !== "string") value = String(value ?? "");' in backend_patched, (
                "cli approval mode parser must tolerate non-string values without TypeError"
            )
            assert 'agentApprovalModes.get(agentId) ?? "yolo" /* YOLO */' in backend_patched, (
                "cli subagent approval panel must default to yolo"
            )
            assert "const agentTypeForHooks = String(this.config?.name || this.config?.getName?.()" in backend_patched, (
                "cli direct hook path must derive subagent identity from config"
            )
            assert "agentTypeForHooks" in backend_patched, "cli direct hook call must pass agentTypeForHooks"
        else:
            assert "agent_type: agentType || void 0" in backend_patched, (
                f"{label} firePreToolUseHook payload must include agent_type"
            )
            post_hook = extract_between(
                backend_patched,
                "async function firePostToolUseHook",
                "__name(firePostToolUseHook",
            )
            assert "agent_type: agentType || void 0" not in post_hook, (
                f"{label} must not inject undefined agentType into PostToolUse"
            )
        assert (
            "String(this.config?.name || this.config?.getName?.() || this.config?.getSubagentName?.() || this.config?.getAgentName?.() || \"\")"
            in backend_patched
        ), f"{label} scheduler hook path must pass subagent identity"


def assert_runtime_mutation_policy_blockers_fixed() -> None:
    policy = POLICY_SAMPLE.read_text(encoding="utf-8", errors="replace")
    backend_policy = _patch_work_mode_policy_script(policy)
    bundle = load_bundle_module()
    offline_policy = bundle.patch_work_mode_policy_script(policy)
    assert backend_policy == offline_policy, "backend/offline mutation policy patches drifted"
    for label, text in {"backend": backend_policy, "offline": offline_policy}.items():
        assert "function isImplementationAgent(agentType)" in text, f"{label} policy lacks implementation-agent helper"
        assert "IMPLEMENTATION_AGENTS.some((agent) => name.startsWith(agent))" in text, (
            f"{label} policy must use the full implementation agent registry"
        )
        assert "function isKnownReadOnlyAgent(agentType)" in text, f"{label} policy missing read-only agent helper"
        assert "function inferAgentType(input)" in text, f"{label} policy must infer subagent identity from hook payload"
        assert "const agentType = inferAgentType(input);" in text, f"{label} policy must use inferred subagent identity"
        assert "const canMutate = isImplementationAgent(agentType);" in text, (
            f"{label} policy must still compute implementation identity for advisory context"
        )
        assert "Allowed by advisory mutation policy; Qwen subagent identity may be missing or drifted." in text, (
            f"{label} policy must allow writes instead of hard-denying identity drift"
        )
        assert "Allowed by implementation fallback because Qwen did not expose subagent identity" not in text, (
            f"{label} policy must use normalized advisory mutation wording"
        )
        assert "prompt_id" in text and "subagent_name" in text, f"{label} policy missing fallback identity fields"
        for agent in [
            "coder-35",
            "dcp-front-developer",
            "dcp-backend-developer",
            "drt-front-developer",
            "drt-backend-developer",
            "drt-cms-front-developer",
            "drt-cms-backend-developer",
        ]:
            assert agent in text, f"{label} policy does not recognize {agent} as mutating implementation agent"
        assert "Only a coder-35 worker may edit files" not in text, f"{label} policy still says coder-35 only for writes"
        assert "Only the selected implementation agent may edit files" not in text, (
            f"{label} policy still hard-denies writes by selected implementation identity"
        )
        assert "Mutating shell commands are allowed only from a coder-35 worker" not in text, (
            f"{label} policy still says coder-35 only for mutating shell"
        )
        assert "Mutating shell commands are allowed only from the selected implementation agent" not in text, (
            f"{label} policy still hard-denies mutating shell by selected implementation identity"
        )
        assert "Prefer the selected implementation agent" in text, f"{label} policy missing advisory implementation wording"
        assert "DCP/DRT/CMS implementation agents" in text, f"{label} policy missing specialized implementation agent wording"
        assert 'mode === "superpowers" && taskSize === "xsmall" && isMainKiwi(agentType)' in text, (
            f"{label} policy must allow superpowers xsmall Kiwi direct mutation"
        )
        assert 'mode === "superpowers" && taskSize === "xsmall" && isAgentTool(toolName)' in text, (
            f"{label} policy must block superpowers xsmall agent delegation"
        )


def assert_runtime_policy_executable_matrix() -> None:
    team_log = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    activation = ACTIVATION_SAMPLE.read_text(encoding="utf-8", errors="replace")
    policy = POLICY_SAMPLE.read_text(encoding="utf-8", errors="replace")

    backend_team_log = _patch_work_mode_state_script(_patch_ultrawork_activation_message(team_log))
    backend_activation = _patch_work_mode_activation_script(activation)
    backend_policy = _patch_work_mode_policy_script(policy)

    bundle = load_bundle_module()
    offline_team_log = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(team_log))
    offline_activation = bundle.patch_work_mode_activation_script(activation)
    offline_policy = bundle.patch_work_mode_policy_script(policy)

    assert backend_team_log == offline_team_log, "backend/offline team-log executable patches drifted"
    assert backend_activation == offline_activation, "backend/offline activation executable patches drifted"
    assert backend_policy == offline_policy, "backend/offline policy executable patches drifted"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        scripts_dir = temp_root / "scripts"
        runtime_dir = temp_root / "portable-runtime"
        scripts_dir.mkdir()
        runtime_dir.mkdir()
        (scripts_dir / "team-log-lib.js").write_text(backend_team_log, encoding="utf-8")
        (scripts_dir / "ultrawork-activate.js").write_text(backend_activation, encoding="utf-8")
        (scripts_dir / "orchestration-policy.js").write_text(backend_policy, encoding="utf-8")

        cases = [
            {
                "label": "superpowers xsmall activation then main edit allow",
                "mode": "superpowers",
                "task_size": "xsmall",
                "tool_name": "edit",
                "tool_input": {"file_path": "/tmp/project/src/App.tsx", "old_string": "a", "new_string": "b"},
                "expected": "allow",
            },
            {
                "label": "superpowers xsmall agent call deny",
                "mode": "superpowers",
                "task_size": "xsmall",
                "tool_name": "agent",
                "tool_input": {
                    "subagent_type": "coder-35",
                    "description": "implement xsmall",
                    "prompt": "make the change",
                },
                "expected": "deny",
            },
            {
                "label": "superpowers medium main edit advisory allow",
                "mode": "superpowers",
                "task_size": "medium",
                "tool_name": "edit",
                "tool_input": {"file_path": "/tmp/project/src/App.tsx", "old_string": "a", "new_string": "b"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium main windows dir shell allow",
                "mode": "superpowers",
                "task_size": "medium",
                "tool_name": "run_shell_command",
                "tool_input": {"command": 'dir "D:\\\\aiops\\\\docs\\\\kiwi" /b 2>nul || echo DIR_NOT_FOUND'},
                "expected": "allow",
            },
            {
                "label": "superpowers medium coder-35 write_file allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "coder-35",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/project/docs/report.md", "content": "# report\n"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium coder prompt-id write_file allow",
                "mode": "superpowers",
                "task_size": "medium",
                "prompt_id": "a1fee2ad-0536-45d0-abcd-a99b642b4185#coder-35-24c83d1c#1",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/project/docs/report.md", "content": "# report\n"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium dcp-front-developer edit allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "dcp-front-developer",
                "tool_name": "edit",
                "tool_input": {"file_path": "/tmp/project/src/App.vue", "old_string": "a", "new_string": "b"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium unknown identity write advisory allow",
                "mode": "superpowers",
                "task_size": "medium",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/project/docs/report.md", "content": "# report\n"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium reviewer identity write advisory allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "reviewer-35",
                "tool_name": "write_file",
                "tool_input": {"file_path": "/tmp/project/docs/review.md", "content": "# review\n"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium unknown identity mutating shell advisory allow",
                "mode": "superpowers",
                "task_size": "medium",
                "tool_name": "run_shell_command",
                "tool_input": {"command": "touch generated.txt"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium dcp-backend-developer mutating shell allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "dcp-backend-developer",
                "tool_name": "run_shell_command",
                "tool_input": {"command": "touch generated.txt"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium drt-front-developer edit allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "drt-front-developer",
                "tool_name": "edit",
                "tool_input": {"file_path": "/tmp/project/dev/src/App.vue", "old_string": "a", "new_string": "b"},
                "expected": "allow",
            },
            {
                "label": "superpowers medium drt-cms-backend-developer mutating shell allow",
                "mode": "superpowers",
                "task_size": "medium",
                "agent_type": "drt-cms-backend-developer",
                "tool_name": "run_shell_command",
                "tool_input": {"command": "touch generated.txt"},
                "expected": "allow",
            },
            {
                "label": "FAST agent call deny",
                "mode": "fast",
                "task_size": "xsmall",
                "tool_name": "agent",
                "tool_input": {
                    "subagent_type": "coder-35",
                    "description": "delegate in fast",
                    "prompt": "make the change",
                },
                "expected": "deny",
            },
            {
                "label": "ultrawork medium dcp-front-developer edit allow",
                "mode": "ultrawork",
                "task_size": "medium",
                "agent_type": "dcp-front-developer",
                "tool_name": "edit",
                "tool_input": {"file_path": "/tmp/project/src/App.vue", "old_string": "a", "new_string": "b"},
                "expected": "allow",
            },
        ]
        for index, case in enumerate(cases):
            session_id = f"assert-policy-{index}"
            cwd = f"/tmp/project-{index}"
            activate_runtime_policy_case(
                scripts_dir / "ultrawork-activate.js",
                runtime_dir,
                mode=str(case["mode"]),
                task_size=str(case["task_size"]),
                cwd=cwd,
                session_id=session_id,
                label=str(case["label"]),
            )
            decision = run_runtime_policy_case(
                scripts_dir / "orchestration-policy.js",
                runtime_dir,
                cwd=cwd,
                session_id=session_id,
                label=str(case["label"]),
                tool_name=str(case["tool_name"]),
                tool_input=case["tool_input"],  # type: ignore[arg-type]
                agent_type=str(case.get("agent_type", "")),
                prompt_id=str(case.get("prompt_id", "")),
            )
            assert decision == case["expected"], (
                f"{case['label']} expected {case['expected']} but got {decision}"
            )

        second_turn_session = "assert-superpowers-second-turn"
        second_turn_cwd = "/tmp/superpowers-second-turn"
        activate_runtime_policy_case(
            scripts_dir / "ultrawork-activate.js",
            runtime_dir,
            mode="superpowers",
            task_size="medium",
            cwd=second_turn_cwd,
            session_id=second_turn_session,
            label="superpowers first turn activation",
        )
        second_turn_context = run_runtime_activation_context(
            scripts_dir / "ultrawork-activate.js",
            runtime_dir,
            prompt="파일로 만들어줘.",
            cwd=second_turn_cwd,
            session_id=second_turn_session,
            label="superpowers second turn context",
        )
        assert "Active KIWI work mode: superpowers" in second_turn_context, (
            f"second superpowers turn did not retain superpowers context: {second_turn_context}"
        )
        assert "Active KIWI work mode: ultrawork" not in second_turn_context, (
            "second superpowers turn fell back to ultrawork context"
        )

    for label, text in {"backend": backend_policy, "offline": offline_policy}.items():
        assert "  const mode = activeWorkMode(input);\n  const taskSize = activeTaskSize(input);" in text, (
            f"{label} policy must compute mode/taskSize inside main before mode gates"
        )
        assert text.index("  const mode = activeWorkMode(input);") < text.index('  if (mode === "fast"'), (
            f"{label} policy computes mode after mode gates"
        )
        assert text.index("  const taskSize = activeTaskSize(input);") < text.index('  if (mode === "fast"'), (
            f"{label} policy computes taskSize after mode gates"
        )


def assert_superpowers_xsmall_context_is_direct_and_non_xsmall_is_team_guarded() -> None:
    team_log = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    backend_team_log = _patch_work_mode_state_script(_patch_ultrawork_activation_message(team_log))
    bundle = load_bundle_module()
    offline_team_log = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(team_log))
    assert backend_team_log == offline_team_log, "backend/offline team-log context patches drifted"

    xsmall_prompt = "\n".join(
        [
            "superpowers",
            "",
            "## 티셔츠 사이징",
            "- 사용자 선택: `xsmall`",
            "- 최종 source of truth: 사용자 선택값을 따른다.",
            "",
            "## 원 사용자 요청",
            "문구 한 줄 수정",
        ]
    )
    medium_prompt = xsmall_prompt.replace("`xsmall`", "`medium`")
    xsmall_context = render_team_mode_context(
        backend_team_log,
        "superpowers",
        xsmall_prompt,
        cwd="D:/work/dcp/dcp-services-mevelop",
    )
    medium_context = render_team_mode_context(
        backend_team_log,
        "superpowers",
        medium_prompt,
        cwd="D:/work/dcp/dcp-services-mevelop",
    )

    assert "Kiwi direct work" in xsmall_context, "superpowers xsmall context must explicitly allow Kiwi direct work"
    assert "Kiwi must not directly edit files" not in xsmall_context, (
        "superpowers xsmall context still conflicts with direct work by forbidding Kiwi edits"
    )
    assert "Only the implementation agent may edit files" not in xsmall_context, (
        "superpowers xsmall context still injects implementation-agent-only mutation rule"
    )
    assert "do not call subagents for xsmall" in xsmall_context
    assert "Prefer the selected implementation agent" in medium_context, (
        "superpowers non-xsmall context must keep advisory implementation guidance"
    )
    assert "Kiwi must not directly edit files" not in medium_context, (
        "superpowers non-xsmall context must not hard-prohibit Kiwi direct mutation by identity"
    )
    assert "Only the selected implementation agent may edit files" not in medium_context, (
        "superpowers non-xsmall context must not inject selected implementation hard-deny wording"
    )
    assert "DCP/DRT/CMS implementation agents" in medium_context, (
        "superpowers non-xsmall context must mention specialized implementation agents"
    )
    assert "project_key=dcp-services" in medium_context, "runtime context must resolve dcp-services docs key"
    assert "D:/aiops/docs/dcp-services/knowledge/00-index.md" in medium_context, (
        "runtime context must inject concrete dcp-services central docs path"
    )
    assert "D:/aiops/docs/dcp/knowledge/00-index.md" not in medium_context, (
        "runtime context must not use parent dcp docs key"
    )


def assert_superpowers_runtime_context(text: str, label: str) -> None:
    for required in [
        "function projectDocsKey(input)",
        "projectKnowledgeIndex(input)",
        "projectInfoRoot(input)",
        "projectDocsRuntimeLine(input)",
        "D:/aiops/docs/${projectDocsKey(input)}",
        "Local Superpowers Skills",
        "kiwi-superpowers",
        "invoke local superpowers with the built-in skill tool",
        'skill="kiwi-superpowers"',
        'skill="using-superpowers"',
        "including large and xlarge",
        "First tool actions after this activation: call the built-in skill tool",
        "Do not call `todo_write`, read broad repository files, implement, or call `agent`",
        "SUPERPOWERS_POLICY.md",
        "superpowers policy and skill are the source of truth",
    ]:
        assert required in text, f"{label} missing superpowers runtime instruction: {required}"
    for stale in [
        "D:/aiops/docs/<project-key>/knowledge first",
        "load or account for local Qwen skills",
        "tool_search",
        "select:",
        "native skill lookup",
        "Qwen native skills",
        "native local Qwen skills",
    ]:
        assert stale not in text, f"{label} still contains stale placeholder instruction: {stale}"


def assert_installed_superpowers_extension(runtime_root: Path, label: str) -> None:
    required_skills = ["kiwi-superpowers", "using-superpowers"]
    for extension_dir in [
        runtime_root / "portable-user" / ".qwen" / "extensions" / "superpowers",
        runtime_root / "extensions" / "superpowers",
    ]:
        assert (extension_dir / "qwen-extension.json").exists(), f"{label} missing qwen-extension.json"
        assert (extension_dir / "QWEN.md").exists(), f"{label} missing superpowers QWEN.md"
        assert (extension_dir / "SUPERPOWERS_POLICY.md").exists(), f"{label} missing SUPERPOWERS_POLICY.md"
        assert (extension_dir / "skills" / "kiwi-superpowers" / "SKILL.md").exists(), (
            f"{label} missing kiwi-superpowers skill"
        )
        policy_text = (extension_dir / "QWEN.md").read_text(encoding="utf-8")
        assert "D:/aiops/docs/<project-key>/project-info" in policy_text
        assert "kiwi-superpowers" in policy_text
    for skills_dir in [
        runtime_root / "portable-user" / ".qwen" / "skills",
        runtime_root / "templates" / "project" / ".qwen" / "skills",
    ]:
        for skill_name in required_skills:
            assert (skills_dir / skill_name / "SKILL.md").exists(), (
                f"{label} missing direct Qwen skill path: {skills_dir / skill_name / 'SKILL.md'}"
            )


def assert_fast_mode_has_no_team_concepts() -> None:
    dirty_state = {
        "project": {"name": "generic", "root_path": str(ROOT)},
        "user_message": "문구 한 줄 수정",
        "work_mode": "fast",
        "history": [],
        "project_context": "KIWI.md",
        "project_info_context": "# Project Info Layer\n\nEvidence: D:/aiops/docs/<project-key>/project-info/project-summary.md",
        "project_info": {"status": "ready", "profile": {"key": "generic"}},
        "prompt_guide": "superpowers ultrawork team subagent task_size",
        "intent": {
            "task_summary": "문구 한 줄 수정",
            "task_size": "large",
            "task_size_reason": "should be filtered",
            "search_queries": ["문구"],
            "target_files": ["src/views/Sample.vue"],
        },
        "ultrawork_policy": {
            "task_size": "large",
            "task_size_reason": "should be filtered",
            "developer_agent": "coder-35",
            "subagents": ["coder-35", "reviewer-35"],
        },
        "kk_docs_results": [],
    }
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "FAST prompt",
        "prompt_parts": {
            "title": "문구 한 줄 수정",
            "task": "문구 한 줄을 수정한다.",
            "verification": ["npm run typecheck"],
        },
    }
    fast_texts = {
        "final": _render_ultrawork_prompt(dirty_state, result),  # type: ignore[arg-type]
        "intent": _compose_intent_prompt(dirty_state),  # type: ignore[arg-type]
        "compose": _compose_builder_prompt(dirty_state),  # type: ignore[arg-type]
        "intent_system": _intent_system_prompt("fast"),
    }
    team_log = TEAM_LOG_SAMPLE.read_text(encoding="utf-8", errors="replace")
    patched_team_log = _patch_work_mode_state_script(_patch_ultrawork_activation_message(team_log))
    fast_texts["console_activation"] = extract_between(
        patched_team_log,
        "function fastModeContext(trigger",
        "function superpowersXsmallContext(trigger, prompt",
    )
    forbidden = ["superpowers", "ultrawork", "team", "subagent", "task_size"]
    for label, text in fast_texts.items():
        lowered = text.lower()
        for token in forbidden:
            assert token not in lowered, f"FAST {label} leaked forbidden team concept: {token}"
    console_activation = fast_texts["console_activation"]
    for required in [
        "FAST/lightwork has no size report",
        "`todo_write` tool",
        "User question protocol",
        "Before calling `ask_user_question`, first load/check the tool usage or schema",
        "do not claim a mode conflict",
    ]:
        assert required in console_activation, f"FAST runtime activation missing: {required}"
    assert "ask with `ask_user_question`" not in console_activation, "FAST ask_user_question guidance is too weak"
    assert "mcp_todowrite" not in console_activation and "mcp_ask_user_question" not in console_activation


def assert_runtime_assets_have_no_remote_or_claude_only_dependency() -> None:
    runtime_files = [
        path
        for root in [ROOT / "docs" / "superpowers-skills"]
        for path in root.rglob("*")
        if path.is_file()
    ]
    runtime_files.append(ROOT / "docs" / "superpowers-runtime-policy.md")
    forbidden_patterns = [
        r"\bCLAUDE_PLUGIN_ROOT\b",
        r"\bClaude Code\b",
        r"/plugin\s+install",
        r"gemini\s+extensions\s+install",
        r"raw\.githubusercontent\.com",
        r"github\.com/obra/superpowers",
        r"https?://",
        r"\bnpx\b",
        r"\bcurl\b",
        r"\bnpm\s+install\b",
        r"\bpip\s+install\b",
    ]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in forbidden_patterns:
            assert not re.search(pattern, text, re.I), (
                f"runtime asset keeps remote or Claude-only dependency {pattern}: {path.relative_to(ROOT)}"
            )


def load_bundle_module():
    path = ROOT / "scripts" / "build-offline-bundle.py"
    spec = importlib.util.spec_from_file_location("build_offline_bundle_assert_superpowers", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_team_mode_context(team_log_text: str, trigger: str, prompt: str, cwd: str | None = None) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        module_path = Path(temp_dir) / "team-log-lib.js"
        module_path.write_text(team_log_text, encoding="utf-8")
        script = (
            "const lib = require(process.argv[1]);"
            "const trigger = process.argv[2];"
            "const prompt = JSON.parse(process.argv[3]);"
            "const input = JSON.parse(process.argv[4]);"
            "process.stdout.write(JSON.stringify(lib.teamModeContext(trigger, prompt, input)));"
        )
        input_payload = {"cwd": cwd} if cwd else {}
        result = subprocess.run(
            ["node", "-e", script, str(module_path), trigger, json.dumps(prompt), json.dumps(input_payload)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
    return json.loads(result.stdout)


def activate_runtime_policy_case(
    activation_script: Path,
    runtime_dir: Path,
    *,
    mode: str,
    task_size: str,
    cwd: str,
    session_id: str,
    label: str,
) -> None:
    prompt = "\n".join(
        [
            mode,
            "",
            "## 티셔츠 사이징",
            f"- 사용자 선택: `{task_size}`",
            f"- selected_task_size: `{task_size}`",
            "- 최종 source of truth: 사용자 선택값을 따른다.",
            "",
            "## 원 사용자 요청",
            f"runtime policy assertion: {label}",
        ]
    )
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": prompt,
        "cwd": cwd,
        "session_id": session_id,
    }
    output = run_node_hook(activation_script, runtime_dir, payload, label)
    assert output.get("decision") == "allow", f"{label} activation was not allowed: {output}"


def run_runtime_policy_case(
    policy_script: Path,
    runtime_dir: Path,
    *,
    cwd: str,
    session_id: str,
    label: str,
    tool_name: str,
    tool_input: dict[str, object],
    agent_type: str = "",
    prompt_id: str = "",
) -> str:
    payload = {
        "hook_event_name": "PreToolUse",
        "cwd": cwd,
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if agent_type:
        payload["agent_type"] = agent_type
    if prompt_id:
        payload["prompt_id"] = prompt_id
    output = run_node_hook(policy_script, runtime_dir, payload, label)
    decision = output.get("hookSpecificOutput", {}).get("permissionDecision")
    assert isinstance(decision, str), f"{label} policy output missing permissionDecision: {output}"
    return decision


def run_runtime_activation_context(
    activation_script: Path,
    runtime_dir: Path,
    *,
    prompt: str,
    cwd: str,
    session_id: str,
    label: str,
) -> str:
    output = run_node_hook(
        activation_script,
        runtime_dir,
        {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "cwd": cwd, "session_id": session_id},
        label,
    )
    context = output.get("hookSpecificOutput", {}).get("additionalContext")
    assert isinstance(context, str), f"{label} activation context missing: {output}"
    return context


def run_node_hook(script_path: Path, runtime_dir: Path, payload: dict[str, object], label: str) -> dict[str, object]:
    env = {
        **dict(os.environ),
        "QWEN_RUNTIME_DIR": str(runtime_dir),
        "QWEN_TEAM_LOG": "0",
    }
    result = subprocess.run(
        ["node", str(script_path)],
        input=json.dumps(payload),
        cwd=script_path.parent,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{label} node hook failed with exit {result.returncode}: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    try:
        output = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{label} node hook returned invalid JSON: {result.stdout!r}") from exc
    assert isinstance(output, dict), f"{label} node hook returned non-object JSON: {output!r}"
    return output


def extract_between(text: str, start: str, end: str) -> str:
    assert start in text and end in text, f"unable to extract between {start!r} and {end!r}"
    return text.split(start, 1)[1].split(end, 1)[0]


if __name__ == "__main__":
    main()
