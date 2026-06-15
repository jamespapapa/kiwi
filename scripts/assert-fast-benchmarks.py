from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FAST_DIR = ROOT / "docs" / "fast-system-prompts"
TASKS_MD = FAST_DIR / "benchmark-tasks.md"
RESULTS_MD = FAST_DIR / "benchmark-results.md"
RESULTS_JSON = FAST_DIR / "benchmark-results.json"
RUNNER = ROOT / "scripts" / "run-fast-benchmarks.py"
ASSERTION = ROOT / "scripts" / "assert-fast-benchmarks.py"

REQUIRED_TASK_FIELDS = [
    "id",
    "profile",
    "user_prompt",
    "required_project_info_artifacts",
    "expected_file_symbol_surfaces",
    "expected_behavior",
    "stop_question_conditions",
    "verification_expectation",
]
PROFILE_MIN_COUNTS = {"dcp-front": 4, "dcp-services": 4, "generic": 2}
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


def main() -> None:
    assert_required_artifacts()
    tasks = load_tasks()
    assert_task_schema(tasks)
    assert_task_distribution(tasks)
    assert_no_forbidden_leakage(TASKS_MD.read_text(encoding="utf-8"), "benchmark-tasks.md")
    results = load_results()
    assert_results_schema(results, tasks)
    assert_results_pass(results, tasks)
    assert_markdown_results(results)
    print("fast benchmark assertions passed")


def assert_required_artifacts() -> None:
    for path in [TASKS_MD, RESULTS_MD, RESULTS_JSON, RUNNER, ASSERTION]:
        assert path.exists(), f"missing required FAST benchmark artifact: {path.relative_to(ROOT)}"


def load_tasks() -> list[dict[str, Any]]:
    text = TASKS_MD.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    assert match, "benchmark-tasks.md must contain one fenced JSON object"
    payload = json.loads(match.group(1))
    tasks = payload.get("tasks")
    assert isinstance(tasks, list), "benchmark-tasks.md JSON must contain tasks list"
    return [task for task in tasks if isinstance(task, dict)]


def load_results() -> dict[str, Any]:
    return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))


def assert_task_schema(tasks: list[dict[str, Any]]) -> None:
    assert len(tasks) >= sum(PROFILE_MIN_COUNTS.values()), "benchmark task count is below required minimum"
    seen: set[str] = set()
    for task in tasks:
        for field in REQUIRED_TASK_FIELDS:
            assert field in task, f"task missing required field {field}: {task.get('id')}"
        task_id = str(task["id"])
        assert task_id and task_id not in seen, f"duplicate or empty task id: {task_id}"
        seen.add(task_id)
        profile = str(task["profile"])
        assert profile in PROFILE_MIN_COUNTS, f"invalid task profile {profile}: {task_id}"
        for field in REQUIRED_TASK_FIELDS[3:]:
            value = task[field]
            assert isinstance(value, list) and value, f"task {task_id} field {field} must be a non-empty list"
        required_artifacts = set(str(item) for item in task["required_project_info_artifacts"])
        assert "project-summary.md" in required_artifacts, f"task {task_id} must require project-summary.md"
        assert "verification-guide.md" in required_artifacts, f"task {task_id} must require verification-guide.md"
        task_text = json.dumps(task, ensure_ascii=False)
        for keyword in PROFILE_REQUIRED_KEYWORDS[profile]:
            assert keyword in task_text, f"task {task_id} missing profile keyword {keyword}"


def assert_task_distribution(tasks: list[dict[str, Any]]) -> None:
    counts = {profile: 0 for profile in PROFILE_MIN_COUNTS}
    for task in tasks:
        counts[str(task["profile"])] += 1
    for profile, minimum in PROFILE_MIN_COUNTS.items():
        assert counts[profile] >= minimum, f"profile {profile} has {counts[profile]} tasks; expected at least {minimum}"


def assert_results_schema(results: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    assert results.get("schema_version") == "fast-benchmark-results.v1"
    assert results.get("task_count") == len(tasks)
    assert isinstance(results.get("tasks"), list), "results JSON must contain tasks list"
    by_id = {str(task["id"]): task for task in tasks}
    result_ids = {str(item.get("task_id")) for item in results["tasks"] if isinstance(item, dict)}
    assert result_ids == set(by_id), "result task ids do not match benchmark task ids"
    for result in results["tasks"]:
        task_id = str(result.get("task_id"))
        task = by_id[task_id]
        for field in [
            "prompt_source",
            "profile_match",
            "project_info_inclusion",
            "current_file_verification_language",
            "minimal_diff_language",
            "focused_verification_language",
            "todowrite_planning_language",
            "stop_question_language",
            "forbidden_leakage_result",
            "keyword_coverage",
            "pass",
            "final_prompt",
        ]:
            assert field in result, f"result {task_id} missing {field}"
        assert str(result["prompt_source"]).endswith(f"fast-system-prompt.{task['profile']}.md"), (
            f"result {task_id} prompt source does not match profile"
        )


def assert_results_pass(results: dict[str, Any], tasks: list[dict[str, Any]]) -> None:
    by_id = {str(task["id"]): task for task in tasks}
    assert results.get("summary", {}).get("failed") == 0, "benchmark summary has failed tasks"
    for result in results["tasks"]:
        task_id = str(result["task_id"])
        task = by_id[task_id]
        assert result["pass"] is True, f"benchmark task did not pass: {task_id}"
        for boolean_field in [
            "profile_match",
            "project_info_inclusion",
            "current_file_verification_language",
            "minimal_diff_language",
            "focused_verification_language",
            "stop_question_language",
        ]:
            assert result[boolean_field] is True, f"result {task_id} failed {boolean_field}"
        leakage = result["forbidden_leakage_result"]
        assert isinstance(leakage, dict) and leakage.get("passed") is True, f"result {task_id} leaked forbidden terms"
        assert_no_forbidden_leakage(str(result["final_prompt"]), f"final prompt {task_id}")
        coverage = result["keyword_coverage"]
        assert isinstance(coverage, dict), f"result {task_id} keyword coverage must be object"
        for keyword in PROFILE_REQUIRED_KEYWORDS[str(task["profile"])]:
            assert coverage.get(keyword) is True, f"result {task_id} missing keyword coverage {keyword}"
        for field in [
            "required_project_info_artifacts",
            "expected_file_symbol_surfaces",
            "expected_behavior",
            "stop_question_conditions",
            "verification_expectation",
        ]:
            for expected in task[field]:
                assert str(expected) in result["final_prompt"], f"result {task_id} prompt missing task expectation: {expected}"


def assert_markdown_results(results: dict[str, Any]) -> None:
    text = RESULTS_MD.read_text(encoding="utf-8")
    assert_no_forbidden_leakage(text, "benchmark-results.md")
    assert "PASS" in text and "FAIL" in text, "benchmark-results.md must document PASS/FAIL columns"
    for result in results["tasks"]:
        task_id = str(result["task_id"])
        assert task_id in text, f"benchmark-results.md missing task id {task_id}"
        assert str(result["prompt_source"]) in text, f"benchmark-results.md missing prompt source for {task_id}"
    assert "Critical: none" in text
    assert "High: none" in text
    assert "Medium: none" in text


def assert_no_forbidden_leakage(text: str, label: str) -> None:
    for pattern in FAST_FORBIDDEN_PATTERNS:
        assert not re.search(pattern, text, re.IGNORECASE), f"{label} leaked forbidden pattern: {pattern}"


if __name__ == "__main__":
    main()
