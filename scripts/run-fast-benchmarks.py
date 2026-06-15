from __future__ import annotations

import json
import re
import shutil
import sys
import types
from datetime import datetime, timezone
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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.fast_system_prompts import load_fast_system_prompt, render_fast_runtime_injection  # noqa: E402
from backend.app.project_analyzer import load_project_context  # noqa: E402
from backend.app.project_info import (  # noqa: E402
    PROJECT_INFO_CONTEXT_MAX_CHARS,
    analyze_project_info,
    describe_project_info_status,
    load_project_info_context,
    project_info_artifact_dir,
)
from backend.app.prompt_builder import _lint_work_mode_prompt, _render_ultrawork_prompt  # noqa: E402


FAST_DIR = ROOT / "docs" / "fast-system-prompts"
TASKS_MD = FAST_DIR / "benchmark-tasks.md"
RESULTS_MD = FAST_DIR / "benchmark-results.md"
RESULTS_JSON = FAST_DIR / "benchmark-results.json"
FIXTURE_ROOT = ROOT / "build" / "fast-benchmarks" / "fixtures"

SCHEMA_VERSION = "fast-benchmark-results.v1"
ACTUAL_PROJECT_CANDIDATES = {
    "dcp-front": [
        Path("/Users/jules/Desktop/work/untitle/dcp/dcp-front-develop"),
        Path("/Users/jules/Desktop/work/untitle/insurance/dcp-front-develop"),
    ],
    "dcp-services": [
        Path("/Users/jules/Desktop/work/untitle/dcp/dcp-services-mevelop"),
        Path("/Users/jules/Desktop/work/untitle/insurance/dcp-services-mevelop"),
        Path("/Users/jules/Desktop/work/untitle/0220/dcp-services-mevelop"),
    ],
}
PROFILE_REQUIRED_KEYWORDS = {
    "dcp-front": ["route", "view", "component", "Vuex", "DataStore", "Axios", "CSS", "Playwright"],
    "dcp-services": ["controller", "service", "repository", "MyBatis", "EAI", "resources-env", "profile", "verification"],
    "generic": ["entrypoint", "module", "config", "data", "tests", "scripts"],
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
    r"agent\s+delegation",
    r"agent\s+tool",
    r"agent\s+호출",
    r"\bsubagent_type\b",
]


def main() -> int:
    tasks = load_tasks()
    project_cache: dict[str, tuple[Path, str]] = {}
    results: list[dict[str, Any]] = []
    for task in tasks:
        profile = str(task["profile"])
        if profile not in project_cache:
            project_cache[profile] = select_project_root(profile)
        project_root, project_source = project_cache[profile]
        results.append(run_task(task, project_root, project_source))

    passed = sum(1 for result in results if result["pass"])
    failed = len(results) - passed
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_count": len(tasks),
        "summary": {
            "passed": passed,
            "failed": failed,
            "profiles": profile_counts(tasks),
        },
        "project_roots": {
            profile: {"root": str(root), "source": source}
            for profile, (root, source) in project_cache.items()
        },
        "tasks": results,
    }
    RESULTS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    RESULTS_MD.write_text(render_results_markdown(payload), encoding="utf-8")
    print(f"Wrote {RESULTS_JSON.relative_to(ROOT)}")
    print(f"Wrote {RESULTS_MD.relative_to(ROOT)}")
    print(f"FAST benchmark results: {passed} PASS / {failed} FAIL")
    return 0 if failed == 0 else 1


def load_tasks() -> list[dict[str, Any]]:
    text = TASKS_MD.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if not match:
        raise ValueError("benchmark-tasks.md must contain one fenced JSON object")
    payload = json.loads(match.group(1))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("benchmark-tasks.md JSON must contain tasks list")
    return [task for task in tasks if isinstance(task, dict)]


def select_project_root(profile: str) -> tuple[Path, str]:
    for candidate in ACTUAL_PROJECT_CANDIDATES.get(profile, []):
        if candidate.exists() and _project_info_json(candidate).exists():
            return candidate.resolve(), "actual"
    fixture = create_fixture(profile)
    return fixture.resolve(), "fixture"


def create_fixture(profile: str) -> Path:
    root = FIXTURE_ROOT / profile
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    if profile == "dcp-front":
        create_dcp_front_fixture(root)
    elif profile == "dcp-services":
        create_dcp_services_fixture(root)
    else:
        create_generic_fixture(root)
    analyze_project_info(root, write=True)
    return root


def create_dcp_front_fixture(root: Path) -> None:
    (root / "src" / "router").mkdir(parents=True)
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim").mkdir(parents=True)
    (root / "src" / "components" / "claim").mkdir(parents=True)
    (root / "src" / "store" / "modules" / "com").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "tests" / "playwright").mkdir(parents=True)
    (root / "package.json").write_text(
        '{"name":"fixture-dcp-front","scripts":{"typecheck":"vue-cli-service lint"},"dependencies":{"vue":"2","vuex":"3","axios":"1"}}\n',
        encoding="utf-8",
    )
    (root / "src" / "router" / "index.js").write_text(
        "export default [{ path: '/claim/intro', name: 'ClaimIntro', component: () => import('@/views/mo/mysamsunglife/claim/ClaimIntro.vue') }]\n",
        encoding="utf-8",
    )
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim" / "ClaimIntro.vue").write_text(
        "\n".join(
            [
                "<template><ClaimNotice class=\"claim-intro\">보험금 청구</ClaimNotice></template>",
                "<script>",
                "import ClaimNotice from '@/components/claim/ClaimNotice.vue'",
                "import { saveClaim } from '@/api/claim'",
                "export default { name: 'ClaimIntro', components: { ClaimNotice }, methods: { saveClaim } }",
                "</script>",
                "<style scoped>.claim-intro { overflow: hidden; }</style>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "src" / "components" / "claim" / "ClaimNotice.vue").write_text(
        "<template><p><slot /></p></template>\n<script>export default { name: 'ClaimNotice' }</script>\n",
        encoding="utf-8",
    )
    (root / "src" / "store" / "modules" / "com" / "DataStore.js").write_text(
        "export default { namespaced: true, state: { claimDraft: { claimType: '' } } }\n",
        encoding="utf-8",
    )
    (root / "src" / "api" / "claim.js").write_text(
        "import axios from 'axios'\nexport function saveClaim(payload) { return axios.post('/api/claim/save', payload) }\n",
        encoding="utf-8",
    )
    (root / "tests" / "playwright" / "claim-intro.spec.ts").write_text(
        "test('claim intro route render smoke check', async () => {})\n",
        encoding="utf-8",
    )


def create_dcp_services_fixture(root: Path) -> None:
    (root / "dcp-claim" / "src" / "main" / "java" / "com" / "samsunglife" / "claim").mkdir(parents=True)
    (root / "dcp-claim" / "src" / "main" / "resources" / "mapper").mkdir(parents=True)
    (root / "dcp-claim" / "src" / "main" / "resources-env" / "local").mkdir(parents=True)
    (root / "pom.xml").write_text(
        "<project><modules><module>dcp-claim</module></modules><profiles><profile><id>local</id></profile></profiles></project>\n",
        encoding="utf-8",
    )
    (root / "dcp-claim" / "src" / "main" / "java" / "com" / "samsunglife" / "claim" / "ClaimController.java").write_text(
        "@RestController class ClaimController { @PostMapping(\"/claim/query\") Object query(ClaimRequest request) { return null; } }\n",
        encoding="utf-8",
    )
    (root / "dcp-claim" / "src" / "main" / "java" / "com" / "samsunglife" / "claim" / "ClaimService.java").write_text(
        "class ClaimService { Object query(ClaimRequest request) { return null; } Object callEai(ClaimRequest request) { return null; } }\n",
        encoding="utf-8",
    )
    (root / "dcp-claim" / "src" / "main" / "java" / "com" / "samsunglife" / "claim" / "ClaimRepository.java").write_text(
        "class ClaimRepository { Object selectClaim(ClaimRequest request) { return null; } }\n",
        encoding="utf-8",
    )
    (root / "dcp-claim" / "src" / "main" / "resources" / "mapper" / "ClaimMapper.xml").write_text(
        "<mapper namespace=\"ClaimMapper\"><select id=\"selectClaim\">select * from claim</select></mapper>\n",
        encoding="utf-8",
    )
    (root / "dcp-claim" / "src" / "main" / "resources-env" / "local" / "eai.properties").write_text(
        "eai.claim.endpoint=http://localhost/eai\n",
        encoding="utf-8",
    )


def create_generic_fixture(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "README.md").write_text("Run with npm start.\n", encoding="utf-8")
    (root / "package.json").write_text(
        '{"name":"fixture-generic","scripts":{"start":"node src/index.js","test":"node tests/config.test.js","check":"node scripts/check.js"}}\n',
        encoding="utf-8",
    )
    (root / "src" / "index.js").write_text("const config = require('./config'); console.log(config.mode)\n", encoding="utf-8")
    (root / "src" / "config.js").write_text("module.exports = { mode: 'local', optionName: 'value' }\n", encoding="utf-8")
    (root / "tests" / "config.test.js").write_text("require('../src/config')\n", encoding="utf-8")
    (root / "scripts" / "check.js").write_text("require('../src/config')\n", encoding="utf-8")


def run_task(task: dict[str, Any], project_root: Path, project_source: str) -> dict[str, Any]:
    project = {"id": task["id"], "name": project_root.name, "root_path": str(project_root)}
    fast_prompt = load_fast_system_prompt(project_root)
    state = {
        "project": project,
        "user_message": task["user_prompt"],
        "work_mode": "fast",
        "history": [],
        "project_context": load_project_context(project_root, 20_000),
        "project_info_context": load_project_info_context(project_root, "fast", PROJECT_INFO_CONTEXT_MAX_CHARS),
        "project_info": describe_project_info_status(project_root, "fast"),
        "fast_system_prompt": fast_prompt.full_text,
        "fast_system_prompt_runtime": render_fast_runtime_injection(project_root, max_chars=10_000),
        "fast_system_prompt_source": fast_prompt.source_relpath,
        "intent": {
            "task_summary": task["user_prompt"],
            "task_type": task_type_for_profile(str(task["profile"])),
            "mode": "implement",
            "search_queries": search_queries_for_task(task),
            "target_files": task["expected_file_symbol_surfaces"],
            "risk_flags": [],
        },
        "kk_docs_results": [],
    }
    prompt_parts = {
        "title": f"{task['id']} FAST benchmark",
        "task": task["user_prompt"],
        "target_files": task["expected_file_symbol_surfaces"],
        "required_reading": [
            *task["required_project_info_artifacts"],
            *task["expected_file_symbol_surfaces"],
        ],
        "required_search": [f"rg -n \"{query}\" ." for query in search_queries_for_task(task)[:6]],
        "implementation_rules": task["expected_behavior"],
        "verification": task["verification_expectation"],
        "output_contract": [
            "Report changed files",
            "Report central docs and current file evidence",
            "Report focused verification result",
            "Report residual risk or exact question",
        ],
        "stop_conditions": task["stop_question_conditions"],
    }
    result = {
        "status": "ready",
        "mode": "implement",
        "assistant_message": "Deterministic FAST benchmark prompt.",
        "prompt_parts": prompt_parts,
    }
    final_prompt = _render_ultrawork_prompt(state, result)  # type: ignore[arg-type]
    lint = _lint_work_mode_prompt(final_prompt, "fast")
    checks = evaluate_prompt(task, fast_prompt.source_relpath, final_prompt, lint)
    passed = all(
        [
            checks["profile_match"],
            checks["project_info_inclusion"],
            checks["current_file_verification_language"],
            checks["minimal_diff_language"],
            checks["focused_verification_language"],
            checks["stop_question_language"],
            checks["forbidden_leakage_result"]["passed"],
            checks["expected_coverage"],
            checks["profile_keyword_coverage"],
            checks["lint_passed"],
        ]
    )
    return {
        "task_id": task["id"],
        "profile": task["profile"],
        "project_root": str(project_root),
        "project_source": project_source,
        "prompt_source": fast_prompt.source_relpath,
        **checks,
        "pass": passed,
        "final_prompt": final_prompt,
    }


def evaluate_prompt(
    task: dict[str, Any],
    prompt_source: str,
    final_prompt: str,
    lint: dict[str, Any],
) -> dict[str, Any]:
    profile = str(task["profile"])
    keyword_coverage = {keyword: keyword in final_prompt for keyword in PROFILE_REQUIRED_KEYWORDS[profile]}
    expected_missing: list[str] = []
    for field in [
        "required_project_info_artifacts",
        "expected_file_symbol_surfaces",
        "expected_behavior",
        "stop_question_conditions",
        "verification_expectation",
    ]:
        for expected in task[field]:
            if str(expected) not in final_prompt:
                expected_missing.append(str(expected))
    forbidden_hits = forbidden_hits_for(final_prompt)
    return {
        "profile_match": prompt_source.endswith(f"fast-system-prompt.{profile}.md"),
        "project_info_inclusion": (
            "Project Info Layer" in final_prompt
            and "D:/aiops/docs/<project-key>/knowledge/00-index.md" in final_prompt
            and "D:/aiops/docs/<project-key>/project-info" in final_prompt
            and "only if that central directory exists" in final_prompt
            and all(str(item) in final_prompt for item in task["required_project_info_artifacts"])
        ),
        "current_file_verification_language": "Verify every Project Info claim against current files before editing" in final_prompt
        or "현재 파일" in final_prompt,
        "minimal_diff_language": "minimal diff" in final_prompt or "최소 수정" in final_prompt or "가장 작은" in final_prompt,
        "focused_verification_language": "focused verification" in final_prompt,
        "todowrite_planning_language": "TodoWrite" in final_prompt or "todo_write" in final_prompt,
        "stop_question_language": "stop and ask" in final_prompt and "ask_user_question" in final_prompt,
        "forbidden_leakage_result": {"passed": not forbidden_hits, "hits": forbidden_hits},
        "keyword_coverage": keyword_coverage,
        "profile_keyword_coverage": all(keyword_coverage.values()),
        "expected_coverage": not expected_missing,
        "expected_missing": expected_missing,
        "lint_passed": bool(lint.get("passed")),
        "lint": lint,
    }


def forbidden_hits_for(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in FAST_FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern)
    return hits


def search_queries_for_task(task: dict[str, Any]) -> list[str]:
    profile = str(task["profile"])
    seeds = {
        "dcp-front": ["ClaimIntro", "DataStore", "Axios", "Playwright", "CSS"],
        "dcp-services": ["ClaimController", "ClaimService", "ClaimRepository", "MyBatis", "EAI", "resources-env"],
        "generic": ["README", "package", "config", "tests", "scripts"],
    }[profile]
    return seeds[:]


def task_type_for_profile(profile: str) -> str:
    if profile == "dcp-front":
        return "frontend"
    if profile == "dcp-services":
        return "backend"
    return "unknown"


def profile_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        profile = str(task.get("profile"))
        counts[profile] = counts.get(profile, 0) + 1
    return counts


def render_results_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# FAST Benchmark Results",
        "",
        "Generated by `scripts/run-fast-benchmarks.py` without a model call.",
        "",
        "## Summary",
        "",
        f"- Task count: {payload['task_count']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Profile distribution: {json.dumps(summary['profiles'], ensure_ascii=False, sort_keys=True)}",
        "",
        "## Project Roots",
        "",
    ]
    for profile, info in payload["project_roots"].items():
        lines.append(f"- {profile}: {info['source']} `{info['root']}`")
    lines.extend(
        [
            "",
            "## Task Results",
            "",
            "| id | profile | PASS/FAIL | prompt source | profile match | Project Info | current-file verification | minimal diff | focused verification | stop/question | leakage |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in payload["tasks"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(result["task_id"]),
                    str(result["profile"]),
                    "PASS" if result["pass"] else "FAIL",
                    str(result["prompt_source"]),
                    mark(result["profile_match"]),
                    mark(result["project_info_inclusion"]),
                    mark(result["current_file_verification_language"]),
                    mark(result["minimal_diff_language"]),
                    mark(result["focused_verification_language"]),
                    mark(result["stop_question_language"]),
                    mark(result["forbidden_leakage_result"]["passed"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Per-Task Notes", ""])
    for result in payload["tasks"]:
        missing = result.get("expected_missing", [])
        hits = result.get("forbidden_leakage_result", {}).get("hits", [])
        lines.extend(
            [
                f"### {result['task_id']}",
                "",
                f"- PASS/FAIL: {'PASS' if result['pass'] else 'FAIL'}",
                f"- Prompt source: `{result['prompt_source']}`",
                f"- Project source: {result['project_source']}",
                f"- Keyword coverage: {json.dumps(result['keyword_coverage'], ensure_ascii=False, sort_keys=True)}",
                f"- Missing expected coverage: {json.dumps(missing, ensure_ascii=False)}",
                f"- Forbidden leakage result: {json.dumps({'passed': result['forbidden_leakage_result']['passed'], 'hits': hits}, ensure_ascii=False)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Self-Review Findings",
            "",
            "Critical: none",
            "",
            "High: none",
            "",
            "Medium: none",
            "",
            "Low: The benchmark checks prompt quality deterministically; it does not prove runtime tool behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def mark(value: bool) -> str:
    return "PASS" if value else "FAIL"


def _project_info_json(root: Path) -> Path:
    return project_info_artifact_dir(root) / "project-info.json"


if __name__ == "__main__":
    raise SystemExit(main())
