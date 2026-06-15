from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.project_info import analyze_project_info, load_project_info_context, project_knowledge_dir  # noqa: E402
from backend.app.qwencode_runtime import _patch_work_mode_policy_script  # noqa: E402
from backend.app.ultrawork_policy import build_ultrawork_policy, detect_project_profile  # noqa: E402


REF_ROOT = ROOT.parent / "ref"
DRT_FRONT = REF_ROOT / "drt-front-main"
DRT_API = REF_ROOT / "drt-api-main"
DRT_CMS = REF_ROOT / "drt-cms-main"
PACK_ROOT = ROOT / "docs" / "project-knowledge-packs" / "v1"
AGENT_DIR = ROOT / "docs" / "ultrawork-agents"

DOC_FILES = {
    "00-index.md",
    "01-repository-map.md",
    "02-build-and-runtime.md",
    "03-system-boundaries.md",
    "04-domain-glossary.md",
    "05-api-and-contracts.md",
    "06-data-model.md",
    "06-frontend-css-and-dom.md",
    "07-state-and-data-propagation.md",
    "08-integrations.md",
    "09-security-auth-privacy.md",
    "10-testing-and-quality.md",
    "11-operations-and-deployment.md",
    "12-change-playbooks.md",
    "99-gaps-and-questions.md",
    "_worklog.md",
}
QUALITY_SECTIONS = [
    "## Worker Startup Checklist",
    "## Current-file Verification",
    "## Profile-specific Focus",
    "## Evidence Refresh Targets",
    "## Change Risk Flags",
    "## Done Criteria For This Document",
]

EXPECTED_AGENTS = {
    "dcp-front": "dcp-front-developer",
    "dcp-services": "dcp-backend-developer",
    "drt-front": "drt-front-developer",
    "drt-api": "drt-backend-developer",
}
DRT_AGENT_FILES = {
    "drt-front-developer.md": ["Vue 3", "Vite", "Pinia", "DrtHttpClient", "route -> view"],
    "drt-backend-developer.md": ["Spring Boot", "MyBatis", "controller -> service", "mapper XML", "Redis"],
    "drt-cms-front-developer.md": ["Quasar", "ag-grid", "frontend/src/services", "route", "grid"],
    "drt-cms-backend-developer.md": ["Spring Boot 3", "Java 17", "REST", "MyBatis", "generated domain"],
}
SPECIALIZED_AGENTS = [
    "coder-35",
    "dcp-front-developer",
    "dcp-backend-developer",
    "drt-front-developer",
    "drt-backend-developer",
    "drt-cms-front-developer",
    "drt-cms-backend-developer",
]


def main() -> None:
    assert_reference_roots()
    assert_profile_detection()
    assert_agent_prompts()
    assert_project_info_analysis()
    assert_runtime_policy_mentions_agents()
    assert_knowledge_packs()
    assert_project_knowledge_pack_context()


def assert_reference_roots() -> None:
    for path in [DRT_FRONT, DRT_API, DRT_CMS]:
        assert path.exists(), f"missing reference source: {path}"


def assert_profile_detection() -> None:
    cases = [
        (DRT_FRONT, "drt-front", "drt-front-developer"),
        (DRT_FRONT / "dev", "drt-front", "drt-front-developer"),
        (DRT_API, "drt-api", "drt-backend-developer"),
        (DRT_CMS, "drt-cms", "drt-cms-backend-developer"),
        (DRT_CMS / "frontend", "drt-cms", "drt-cms-backend-developer"),
        (DRT_CMS / "backend", "drt-cms", "drt-cms-backend-developer"),
    ]
    for root, profile_key, default_agent in cases:
        profile = detect_project_profile(root)
        assert profile is not None, f"profile not detected for {root}"
        assert profile.key == profile_key, f"{root} detected as {profile.key}, expected {profile_key}"
        assert profile.developer_agent == default_agent, f"{root} default agent mismatch"

    frontend_policy = build_ultrawork_policy(
        DRT_CMS,
        {"task_summary": "frontend/src/views/system/menu-mng 화면 그리드 버튼 수정", "target_files": ["frontend/src/views/system/menu-mng/menu-list.vue"]},
        selected_task_size="medium",
    )
    assert frontend_policy["developer_agent"] == "drt-cms-front-developer", frontend_policy

    backend_policy = build_ultrawork_policy(
        DRT_CMS,
        {"task_summary": "backend REST resource와 MyBatis XML 조건 수정", "target_files": ["backend/src/main/java/com/samsunglife/drt/cms/rest/CategoryResource.java"]},
        selected_task_size="medium",
    )
    assert backend_policy["developer_agent"] == "drt-cms-backend-developer", backend_policy


def assert_agent_prompts() -> None:
    for filename, required_terms in DRT_AGENT_FILES.items():
        path = AGENT_DIR / filename
        assert path.exists(), f"missing DRT agent prompt: {path}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{filename} missing Qwen native YAML frontmatter"
        frontmatter = text.split("\n---\n", 1)[0]
        for required in [
            f"name: {filename.removesuffix('.md')}",
            "model: openai:Qwen3.5-397B",
            "approvalMode: yolo",
            "tools:",
            "  - read_file",
            "  - grep_search",
            "  - glob",
            "  - list_directory",
            "  - edit",
            "  - write_file",
            "  - run_shell_command",
        ]:
            assert required in frontmatter, f"{filename} missing native frontmatter term: {required}"
        assert "tools: read," not in frontmatter, f"{filename} has invalid string tools frontmatter"
        for term in required_terms:
            assert term in text, f"{filename} missing required term: {term}"
        assert "Mandatory Workflow" in text, f"{filename} missing workflow contract"
        assert "Required Response" in text, f"{filename} missing response contract"


def assert_project_info_analysis() -> None:
    cases = {
        "drt-front": DRT_FRONT,
        "drt-api": DRT_API,
        "drt-cms": DRT_CMS,
    }
    required_markers = {
        "drt-front": ["DrtHttpClient", "route-view-flow", "Pinia"],
        "drt-api": ["Spring Boot", "controller-service-flow", "MyBatis"],
        "drt-cms": ["integrated admin", "drt-cms", "frontend"],
    }
    for profile_key, root in cases.items():
        bundle = analyze_project_info(root, write=False)
        errors = bundle.get("validation", {}).get("errors", [])
        assert not errors, f"{profile_key} Project Info validation errors: {errors[:5]}"
        assert bundle["profile"]["key"] == profile_key, f"{profile_key} profile analysis mismatch"
        serialized = json.dumps(bundle["artifacts"], ensure_ascii=False)
        for marker in required_markers[profile_key]:
            assert marker in serialized, f"{profile_key} Project Info missing marker: {marker}"


def assert_runtime_policy_mentions_agents() -> None:
    team_context = (ROOT / "backend" / "app" / "qwencode_runtime.py").read_text(encoding="utf-8")
    for agent in SPECIALIZED_AGENTS:
        assert agent in team_context, f"team mode context missing agent: {agent}"
    assert "DCP/DRT/CMS implementation agents" in team_context

    sample_policy = """
function normalize(agentType) { return String(agentType || "").toLowerCase(); }
function isCoderAgent(agentType) {
  return normalize(agentType).startsWith("coder-35");
}
const canMutate = isCoderAgent(agentType);
Only a coder-35 worker may edit files or write memory in Ultrawork mode.
Kiwi, Qwen3.5 consultant agents, tester, and explorer are intentionally read-only for direct file mutation. Use the registered `agent` tool with subagent_type `coder-35` and pass a concrete work order.
Mutating shell commands are allowed only from a coder-35 worker in Ultrawork mode.
Kiwi may run orchestration and read-only diagnostics, and tester-35 may run verification commands. File-changing shell commands must be delegated through the registered `agent` tool with subagent_type `coder-35`.
"""
    patched = _patch_work_mode_policy_script(sample_policy)
    for agent in SPECIALIZED_AGENTS:
        assert agent in patched, f"patched runtime policy missing agent: {agent}"
    assert "DCP/DRT/CMS implementation agents" in patched


def assert_knowledge_packs() -> None:
    manifest_path = PACK_ROOT / "manifest.json"
    assert manifest_path.exists(), "missing knowledge pack manifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == "v1"
    assert set(manifest["profiles"]) == {"dcp-front", "dcp-services", "drt-front", "drt-api", "drt-cms"}
    for profile in manifest["profiles"]:
        base = PACK_ROOT / profile / "docs" / "knowledge"
        assert base.exists(), f"missing knowledge dir for {profile}"
        actual = {path.name for path in base.iterdir() if path.is_file()}
        missing = DOC_FILES - actual
        assert not missing, f"{profile} missing knowledge docs: {sorted(missing)}"
        for name in DOC_FILES:
            text = (base / name).read_text(encoding="utf-8")
            assert 'kiwi_knowledge_pack_version: "v1"' in text, f"{profile}/{name} missing version front matter"
            assert f'profile: "{profile}"' in text, f"{profile}/{name} missing profile front matter"
            assert len(text.splitlines()) >= 55, f"{profile}/{name} is too shallow"
            for section in QUALITY_SECTIONS:
                assert section in text, f"{profile}/{name} missing quality section: {section}"
            assert "implementation_agent:" not in text, f"{profile}/{name} must not embed implementation agent routing"
            for agent_name in SPECIALIZED_AGENTS:
                assert agent_name not in text, f"{profile}/{name} leaked agent name into knowledge pack: {agent_name}"
        for subdir in ["apis", "data", "flows", "modules", "decisions"]:
            files = list((base / subdir).glob("*.md"))
            assert files, f"{profile} missing {subdir} detail docs"
            for path in files:
                text = path.read_text(encoding="utf-8")
                assert len(text.splitlines()) >= 45, f"{path} is too shallow"
                for section in QUALITY_SECTIONS:
                    assert section in text, f"{path} missing quality section: {section}"
                assert "implementation_agent:" not in text, f"{path} must not embed implementation agent routing"
                for agent_name in SPECIALIZED_AGENTS:
                    assert agent_name not in text, f"{path} leaked agent name into knowledge pack: {agent_name}"
        index = (base / "00-index.md").read_text(encoding="utf-8")
        if profile.startswith("drt"):
            assert f"ref/{profile.replace('drt-api', 'drt-api-main').replace('drt-front', 'drt-front-main').replace('drt-cms', 'drt-cms-main')}" in index
        agent = EXPECTED_AGENTS.get(profile)
        if agent:
            assert agent in (PACK_ROOT / profile / "README.md").read_text(encoding="utf-8")


def assert_project_knowledge_pack_context() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-knowledge-pack-") as raw_tmp:
        tmp = Path(raw_tmp)
        os.environ["KIWI_AIOPS_DOCS_DIR"] = str(tmp / "aiops-docs")
        (tmp / "package.json").write_text(
            json.dumps({"scripts": {"test": "echo ok"}, "dependencies": {"vue": "^3.0.0"}}, indent=2) + "\n",
            encoding="utf-8",
        )
        (tmp / "src").mkdir()
        (tmp / "src" / "main.ts").write_text("import { createApp } from 'vue';\ncreateApp({}).mount('#app');\n", encoding="utf-8")
        shutil.copytree(PACK_ROOT / "drt-front" / "docs" / "knowledge", project_knowledge_dir(tmp))
        analyze_project_info(tmp, write=True)

        fast_context = load_project_info_context(tmp, "fast")
        team_context = load_project_info_context(tmp, "ultrawork")
        for context in [fast_context, team_context]:
            assert "## Project Knowledge Pack" in context
            assert project_knowledge_dir(tmp).as_posix() + "/00-index.md" in context
            assert "kiwi_knowledge_pack_version" not in context
            assert "seed knowledge" in context
            assert "current repository files" in context
        forbidden_fast_terms = [
            "drt-front-developer",
            "implementation_agent",
            "Implementation agent",
            "developer_agent",
            "subagent",
            "task_size",
        ]
        for term in forbidden_fast_terms:
            assert term not in fast_context, f"FAST knowledge context leaked forbidden term: {term}"


if __name__ == "__main__":
    main()
