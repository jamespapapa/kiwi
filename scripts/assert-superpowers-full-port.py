from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT.parent / "ref" / "superpowers-main"
FULL_PORT_DIR = ROOT / "docs" / "superpowers-full-port"
SKILLS_DIR = ROOT / "docs" / "superpowers-skills"
sys.path.insert(0, str(ROOT))

REQUIRED_QWEN_SKILLS = [
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "executing-plans",
    "test-driven-development",
    "systematic-debugging",
    "verification-before-completion",
    "requesting-code-review",
    "receiving-code-review",
    "subagent-driven-development",
    "dispatching-parallel-agents",
    "finishing-a-development-branch",
    "using-git-worktrees",
]

OPTIONAL_PORTED_SKILLS = [
    "writing-skills",
]

CORE_SKILL_REQUIRED_CONCEPTS = {
    "test-driven-development": [
        ("iron_law", [r"Iron Law", r"NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"]),
        ("failing_test_first", [r"failing test first", r"test first"]),
        ("delete_prewritten_production_code", [r"delete prewritten production code", r"delete it", r"Start over"]),
        ("red_green_refactor", [r"red-green-refactor", r"RED", r"GREEN", r"REFACTOR"]),
        ("good_bad_test_examples", [r"Good test", r"Bad test", r"tests real behavior", r"tests mock"]),
        ("mock_antipattern", [r"mock anti-pattern", r"over-mocking", r"tests mock"]),
        ("overengineering_antipattern", [r"over-engineer", r"YAGNI", r"extra options"]),
    ],
    "systematic-debugging": [
        ("reproduce", [r"reproduce", r"reproduction evidence"]),
        ("earliest_wrong_value", [r"earliest wrong value", r"bad value", r"trace backward"]),
        ("one_hypothesis", [r"one hypothesis", r"single hypothesis", r"one variable at a time"]),
        ("condition_based_waiting", [r"condition-based wait", r"poll until", r"no fixed sleep"]),
        ("polluter_isolation", [r"polluter isolation", r"order-dependent", r"bisect"]),
        ("defense_in_depth_after_root_cause", [r"defense-in-depth", r"after root cause"]),
        ("root_cause_tracing", [r"root-cause tracing", r"trace data flow", r"fix at source"]),
    ],
    "subagent-driven-development": [
        ("implementer_work_order", [r"implementer work order", r"IMPLEMENTER WORK ORDER", r"objective", r"non-goals"]),
        ("spec_reviewer_template", [r"spec compliance reviewer", r"SPEC COMPLIANCE REVIEWER PROMPT"]),
        ("code_quality_reviewer_template", [r"code quality reviewer", r"CODE QUALITY REVIEWER PROMPT"]),
        ("independent_verification", [r"independent verification", r"fresh subagent", r"reviewer"]),
        ("status_escalation", [r"DONE_WITH_CONCERNS", r"BLOCKED", r"escalate"]),
        ("two_stage_review", [r"two-stage review", r"spec", r"quality"]),
    ],
    "writing-skills": [
        ("best_practices", [r"best-practices", r"concise trigger", r"progressive disclosure"]),
        ("persuasion", [r"persuasion", r"specific", r"actionable"]),
        ("testing_with_subagents", [r"testing with subagents", r"subagent skill testing"]),
        ("graphviz_decision", [r"graphviz", r"render", r"decision"]),
        ("examples", [r"examples", r"good example", r"bad example"]),
        ("anti_patterns", [r"anti-pattern", r"vague trigger", r"long undifferentiated"]),
    ],
    "requesting-code-review": [
        ("independent_review", [r"independent review", r"fresh reviewer", r"reviewer-35"]),
        ("reviewer_prompt_template", [r"reviewer prompt", r"REVIEW REQUEST TEMPLATE"]),
        ("severity_first", [r"Critical", r"High", r"Medium", r"Low", r"severity"]),
        ("file_line_findings", [r"file/line", r"line evidence"]),
        ("no_style_only_review", [r"style-only", r"correctness"]),
    ],
    "receiving-code-review": [
        ("evaluate_not_obey", [r"evaluate", r"not orders", r"suggestions"]),
        ("triage_all_findings", [r"triage", r"Critical", r"High", r"Medium", r"Low"]),
        ("fix_one_at_a_time", [r"one at a time", r"focused verification"]),
        ("pushback", [r"push back", r"technical reasoning"]),
        ("no_performative_agreement", [r"performative agreement", r"no gratitude"]),
    ],
    "writing-plans": [
        ("zero_context_engineer", [r"zero context", r"another worker", r"without guessing"]),
        ("file_structure_first", [r"file structure", r"before defining tasks"]),
        ("bite_sized_tasks", [r"bite-sized", r"2-5 minutes"]),
        ("plan_header", [r"Implementation Plan", r"Goal", r"Architecture", r"Tech Stack"]),
        ("no_placeholders", [r"No placeholders", r"TBD", r"TODO"]),
        ("execution_handoff", [r"Execution handoff", r"Subagent-Driven", r"Inline Execution"]),
    ],
    "brainstorming": [
        ("hard_gate", [r"HARD GATE", r"user approval", r"before implementation"]),
        ("anti_pattern_simple_design", [r"too simple", r"need a design", r"anti-pattern"]),
        ("one_question_at_a_time", [r"one question at a time"]),
        ("two_three_approaches", [r"2-3 approaches", r"two or three"]),
        ("write_design_doc", [r"design doc", r"docs/superpowers/specs"]),
        ("spec_self_review", [r"spec self-review", r"placeholders", r"ambiguity"]),
        ("graph_render_decision", [r"graph", r"render", r"image input"]),
    ],
}

QWEN_TOOL_NAMES = [
    "skill",
    "agent",
    "todo_write",
    "read_file",
    "grep_search",
    "glob",
    "list_directory",
    "edit",
    "write_file",
    "run_shell_command",
    "ask_user_question",
]

FORBIDDEN_RUNTIME_PATTERNS = [
    r"\bClaude Code\b",
    r"\bCLAUDE_PLUGIN_ROOT\b",
    r"/plugin\s+install",
    r"\bclaude\s+--",
    r"\bclaude\b",
    r"raw\.githubusercontent\.com",
    r"github\.com/obra/superpowers",
    r"https?://",
    r"\bcurl\b",
    r"\bnpx\b",
    r"\bnpm\s+install\b",
    r"\bpip\s+install\b",
    r"vision\s+is\s+available",
]

TRIGGER_FIXTURES = [
    ("brainstorm a feature before coding", ["brainstorming"]),
    ("let's brainstorm alternatives", ["brainstorming"]),
    ("write a plan for this migration", ["writing-plans"]),
    ("create implementation plan", ["writing-plans"]),
    ("execute the approved plan", ["executing-plans"]),
    ("follow the plan step by step", ["executing-plans"]),
    ("add behavior with a failing test first", ["test-driven-development"]),
    ("write a failing test for the regression", ["test-driven-development"]),
    ("debug this failing test", ["systematic-debugging", "test-driven-development"]),
    ("investigate root cause before fixing", ["systematic-debugging"]),
    ("verify before done", ["verification-before-completion"]),
    ("prove completion with verification", ["verification-before-completion"]),
    ("request code review", ["requesting-code-review"]),
    ("get a reviewer for this diff", ["requesting-code-review"]),
    ("handle the review comments", ["receiving-code-review"]),
    ("receive code review and fix findings", ["receiving-code-review"]),
    ("split into agents", ["subagent-driven-development", "dispatching-parallel-agents"]),
    ("dispatch parallel agents for independent files", ["dispatching-parallel-agents"]),
    ("use subagents for implementation", ["subagent-driven-development"]),
    ("finish this development branch", ["finishing-a-development-branch"]),
    ("use git worktrees for parallel implementation", ["using-git-worktrees"]),
    ("activate superpowers skill-first", ["using-superpowers"]),
]


def main() -> None:
    assert_upstream_exists()
    upstream_assets = collect_upstream_assets()
    assert_inventory(upstream_assets)
    assert_parity_matrix(upstream_assets)
    assert_decision_log()
    assert_qwen_skill_library()
    assert_core_skill_concepts()
    assert_trigger_fixtures()
    assert_runtime_and_offline_installers()
    assert_fast_mode_isolation()
    assert_review_packet()
    print("superpowers full port assertions passed")


def assert_upstream_exists() -> None:
    assert UPSTREAM.exists(), f"missing upstream superpowers reference: {UPSTREAM}"
    for relative in ["skills", "hooks", ".claude-plugin/plugin.json", "tests"]:
        assert (UPSTREAM / relative).exists(), f"missing upstream asset root: {relative}"


def collect_upstream_assets() -> list[str]:
    return sorted(
        asset.relative_to(UPSTREAM).as_posix()
        for asset in UPSTREAM.rglob("*")
        if asset.is_file() and ".git" not in asset.relative_to(UPSTREAM).parts
    )


def assert_inventory(upstream_assets: list[str]) -> None:
    path = FULL_PORT_DIR / "inventory.md"
    assert path.exists(), "missing inventory: docs/superpowers-full-port/inventory.md"
    text = path.read_text(encoding="utf-8")
    for section in [
        "# Superpowers Full Port Inventory",
        "## Scope",
        "## Decision Codes",
        "## Upstream Asset Inventory",
        "## Closed-Network Decisions",
    ]:
        assert section in text, f"inventory missing section: {section}"
    for code in ["PORT", "ADAPT", "MERGE", "DEFER", "REMOVE"]:
        assert code in text, f"inventory missing decision code: {code}"
    missing = [asset for asset in upstream_assets if asset not in text]
    assert not missing, "missing inventory entries for upstream assets: " + ", ".join(missing[:20])
    classified = [
        asset
        for asset in upstream_assets
        if re.search(rf"\|\s*{re.escape(asset)}\s*\|\s*(PORT|ADAPT|MERGE|DEFER|REMOVE)\s*\|", text)
    ]
    assert len(classified) == len(upstream_assets), (
        f"inventory classification count mismatch: {len(classified)}/{len(upstream_assets)} accounted"
    )
    for required in [
        "Qwen3.5 image input is enabled through provider modalities",
        "No external fetch",
        "closed network",
        "Project Info Layer",
    ]:
        assert required in text, f"inventory missing closed-network evidence: {required}"


def assert_parity_matrix(upstream_assets: list[str]) -> None:
    path = FULL_PORT_DIR / "parity-matrix.md"
    assert path.exists(), "missing parity matrix: docs/superpowers-full-port/parity-matrix.md"
    text = path.read_text(encoding="utf-8")
    for section in [
        "# Superpowers Full Port Parity Matrix",
        "## Skill Parity",
        "## Hook And Command Parity",
        "## Test And Fixture Parity",
        "## Unsupported Or Removed Behavior",
    ]:
        assert section in text, f"parity matrix missing section: {section}"
    for skill in REQUIRED_QWEN_SKILLS:
        assert skill in text, f"parity matrix missing required skill: {skill}"
    for term in [
        "Project Info Layer",
        "Qwen tool mapping",
        "closed network",
        "FAST/lightwork",
        "selected_task_size",
        "xsmall",
    ]:
        assert term in text, f"parity matrix missing invariant: {term}"
    for asset in upstream_assets:
        if asset.startswith(("skills/", "hooks/", "tests/")):
            assert asset in text, f"parity matrix missing upstream asset reference: {asset}"


def assert_decision_log() -> None:
    candidates = [FULL_PORT_DIR / "unsupported-decisions.md", FULL_PORT_DIR / "inventory.md"]
    found = False
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "Unsupported Decision Log" in text and "DEFER" in text and "REMOVE" in text:
            found = True
    assert found, "missing unsupported decision log"


def assert_qwen_skill_library() -> None:
    assert SKILLS_DIR.exists(), "missing Qwen skill source directory: docs/superpowers-skills"
    all_skill_names = REQUIRED_QWEN_SKILLS + OPTIONAL_PORTED_SKILLS
    missing = [name for name in REQUIRED_QWEN_SKILLS if not (SKILLS_DIR / name / "SKILL.md").exists()]
    assert not missing, "missing Qwen skill folders: " + ", ".join(missing)
    for name in all_skill_names:
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for section in ["## When to use", "## Steps", "## Stop conditions", "## Verification", "## Qwen tool mapping"]:
            assert section in text, f"{name} missing section: {section}"
        for required in ["Project Info Layer", "D:/aiops/docs/<project-key>/project-info", "FAST/lightwork", "superpowers"]:
            assert required in text, f"{name} missing invariant: {required}"
        tool_mentions = [tool for tool in QWEN_TOOL_NAMES if re.search(rf"`{re.escape(tool)}`|\b{re.escape(tool)}\b", text)]
        assert len(tool_mentions) >= 6, f"{name} has weak Qwen tool mapping: {tool_mentions}"
        for pattern in FORBIDDEN_RUNTIME_PATTERNS:
            assert not re.search(pattern, text, re.I), f"{name} contains forbidden runtime text: {pattern}"
        for vision_term in [
            "image input",
            "provider modalities",
            "serving adapter rejects image media",
            "DOM/CSS/text",
        ]:
            assert vision_term in text, f"{name} missing vision fallback contract: {vision_term}"


def _concept_present(text: str, patterns: list[str]) -> bool:
    return all(re.search(pattern, text, re.I | re.M) for pattern in patterns)


def assert_core_skill_concepts() -> None:
    parity_text = (FULL_PORT_DIR / "parity-matrix.md").read_text(encoding="utf-8")
    review_text = (FULL_PORT_DIR / "review-packet.md").read_text(encoding="utf-8")
    missing: list[str] = []
    missing_parity: list[str] = []
    missing_review: list[str] = []
    for skill, concepts in CORE_SKILL_REQUIRED_CONCEPTS.items():
        path = SKILLS_DIR / skill / "SKILL.md"
        assert path.exists(), f"{skill} required concept check missing SKILL.md"
        text = path.read_text(encoding="utf-8")
        for concept, patterns in concepts:
            if not _concept_present(text, patterns):
                missing.append(f"{skill}:{concept}")
            parity_pattern = rf"{re.escape(skill)}.*Required concept coverage:.*\b{re.escape(concept)}\b"
            if not re.search(parity_pattern, parity_text, re.I | re.S):
                missing_parity.append(f"{skill}:{concept}")
            review_pattern = rf"docs/superpowers-skills/{re.escape(skill)}/SKILL\.md:\d+.*\b{re.escape(concept)}\b"
            if not re.search(review_pattern, review_text, re.I):
                missing_review.append(f"{skill}:{concept}")
    assert not missing, "core skill required concepts missing from SKILL.md: " + ", ".join(missing[:30])
    assert not missing_parity, "parity matrix missing required concept coverage: " + ", ".join(missing_parity[:30])
    assert not missing_review, "review packet missing SKILL.md line evidence: " + ", ".join(missing_review[:30])


def classify_trigger(text: str) -> set[str]:
    lowered = text.lower()
    matches: set[str] = set()
    rules = [
        ("brainstorming", [r"brainstorm", r"alternatives?", r"explore options"]),
        ("writing-plans", [r"write (a )?plan", r"implementation plan", r"plan for"]),
        ("executing-plans", [r"execute .*plan", r"follow .*plan", r"approved plan"]),
        ("test-driven-development", [r"failing test", r"test first", r"add behavior", r"regression"]),
        ("systematic-debugging", [r"debug", r"root cause", r"failing test", r"investigate"]),
        ("verification-before-completion", [r"verify before", r"prove completion", r"done"]),
        ("requesting-code-review", [r"request code review", r"get a reviewer", r"review this diff"]),
        ("receiving-code-review", [r"review comments", r"receive code review", r"fix findings"]),
        ("subagent-driven-development", [r"subagents?", r"split into agents", r"agents for implementation"]),
        ("dispatching-parallel-agents", [r"parallel agents", r"dispatch .*agents", r"independent files", r"split into agents"]),
        ("finishing-a-development-branch", [r"finish .*branch", r"development branch"]),
        ("using-git-worktrees", [r"worktrees?", r"parallel implementation"]),
        ("using-superpowers", [r"superpowers", r"skill-first"]),
    ]
    for skill, patterns in rules:
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.add(skill)
    return matches


def assert_trigger_fixtures() -> None:
    assert len(TRIGGER_FIXTURES) >= 20, "missing trigger fixtures: need at least 20 deterministic cases"
    fixture_path = FULL_PORT_DIR / "trigger-fixtures.json"
    assert fixture_path.exists(), "missing trigger fixtures: docs/superpowers-full-port/trigger-fixtures.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(fixtures, list), "trigger fixtures must be a JSON list"
    assert len(fixtures) >= 20, "trigger fixture file must contain at least 20 cases"
    for item in fixtures:
        assert item.get("prompt") and item.get("expected_skills"), f"invalid trigger fixture item: {item}"
        detected = classify_trigger(str(item["prompt"]))
        expected = set(item["expected_skills"])
        assert expected <= detected, (
            f"trigger fixture mismatch for {item['prompt']!r}: expected {sorted(expected)}, got {sorted(detected)}"
        )
    for prompt, expected_skills in TRIGGER_FIXTURES:
        detected = classify_trigger(prompt)
        assert set(expected_skills) <= detected, (
            f"built-in trigger fixture mismatch for {prompt!r}: expected {expected_skills}, got {sorted(detected)}"
        )


def assert_runtime_and_offline_installers() -> None:
    runtime_path = ROOT / "backend" / "app" / "qwencode_runtime.py"
    bundle_path = ROOT / "scripts" / "build-offline-bundle.py"
    for path in [runtime_path, bundle_path]:
        text = path.read_text(encoding="utf-8")
        assert "docs\" / \"superpowers-skills" in text or "docs\" / \"superpowers-skills\"" in text, (
            f"{path.relative_to(ROOT)} does not install docs/superpowers-skills"
        )
        assert "iterdir()" in text and "SKILL.md" in text, f"{path.relative_to(ROOT)} does not discover skill folders"
        assert "install_kiwi_superpowers_extension" in text, f"{path.relative_to(ROOT)} missing superpowers installer"
    with tempfile.TemporaryDirectory() as temp_dir:
        import importlib.util

        from backend.app.qwencode_runtime import _install_kiwi_superpowers_extension

        runtime_root = Path(temp_dir) / "runtime"
        _install_kiwi_superpowers_extension(runtime_root)
        for extension_dir in [
            runtime_root / "portable-user" / ".qwen" / "extensions" / "superpowers",
            runtime_root / "extensions" / "superpowers",
        ]:
            installed = sorted(path.name for path in (extension_dir / "skills").iterdir() if (path / "SKILL.md").exists())
            for name in REQUIRED_QWEN_SKILLS:
                assert name in installed, f"backend installer missing skill {name}"
        for skills_dir in [
            runtime_root / "portable-user" / ".qwen" / "skills",
            runtime_root / "templates" / "project" / ".qwen" / "skills",
        ]:
            installed = sorted(path.name for path in skills_dir.iterdir() if (path / "SKILL.md").exists())
            for name in REQUIRED_QWEN_SKILLS:
                assert name in installed, f"backend installer missing direct Qwen skill {name} in {skills_dir}"

        spec = importlib.util.spec_from_file_location("bundle_superpowers_full_assert", bundle_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bundle_runtime = Path(temp_dir) / "bundle-runtime"
        module.install_kiwi_superpowers_extension(bundle_runtime)
        backend_skills = sorted(
            path.name
            for path in (runtime_root / "portable-user" / ".qwen" / "extensions" / "superpowers" / "skills").iterdir()
            if (path / "SKILL.md").exists()
        )
        bundle_skills = sorted(
            path.name
            for path in (bundle_runtime / "portable-user" / ".qwen" / "extensions" / "superpowers" / "skills").iterdir()
            if (path / "SKILL.md").exists()
        )
        assert backend_skills == bundle_skills, f"backend/offline install list drift: {backend_skills} != {bundle_skills}"
        for skills_dir in [
            bundle_runtime / "portable-user" / ".qwen" / "skills",
            bundle_runtime / "templates" / "project" / ".qwen" / "skills",
        ]:
            installed = sorted(path.name for path in skills_dir.iterdir() if (path / "SKILL.md").exists())
            assert installed == bundle_skills, f"offline direct Qwen skill list drift in {skills_dir}: {installed} != {bundle_skills}"


def assert_fast_mode_isolation() -> None:
    fast_paths = [
        ROOT / "docs" / "fast-system-prompts",
        ROOT / "backend" / "app" / "fast_system_prompts.py",
    ]
    for path in fast_paths:
        if path.is_dir():
            files = [candidate for candidate in path.rglob("*") if candidate.is_file()]
        else:
            files = [path]
        for file_path in files:
            text = file_path.read_text(encoding="utf-8", errors="replace").lower()
            assert "kiwi-superpowers" not in text, f"FAST asset leaked superpowers skill: {file_path.relative_to(ROOT)}"
            assert "superpowers skill" not in text, f"FAST asset leaked superpowers skill content: {file_path.relative_to(ROOT)}"


def assert_review_packet() -> None:
    path = FULL_PORT_DIR / "review-packet.md"
    assert path.exists(), "missing review packet: docs/superpowers-full-port/review-packet.md"
    text = path.read_text(encoding="utf-8")
    for section in [
        "# Superpowers Full Port Review Packet",
        "## Reviewer Role",
        "## Rubric",
        "## Evidence",
        "## Score",
    ]:
        assert section in text, f"review packet missing section: {section}"
    for item in [
        "inventory 15",
        "skill fidelity 20",
        "closed-network 15",
        "runtime/offline 15",
        "mode/task_size/Project Info 10",
        "trigger coverage 10",
        "docs/evidence 10",
        "regression 5",
        "100/100",
    ]:
        assert item in text, f"review packet missing rubric item: {item}"
    assert "PASS" in text and "100/100" in text, "review packet must record 100/100 PASS"


if __name__ == "__main__":
    main()
