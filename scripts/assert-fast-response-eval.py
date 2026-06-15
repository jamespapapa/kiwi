from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FAST_DIR = ROOT / "docs" / "fast-system-prompts"
BENCHMARK_JSON = FAST_DIR / "benchmark-results.json"
RESULTS_JSON = FAST_DIR / "response-eval-results.json"
RESULTS_MD = FAST_DIR / "response-eval-results.md"
CODEX_RESULTS_JSON = FAST_DIR / "response-eval-results.codex.json"
CODEX_RESULTS_MD = FAST_DIR / "response-eval-results.codex.md"
METHOD_MD = FAST_DIR / "response-eval-method.md"
EVALUATION_REPORT_MD = FAST_DIR / "evaluation-report.md"
CODEX_FAIL_CLOSURE_MD = FAST_DIR / "response-eval-codex-fail-closures.md"
RUNNER = ROOT / "scripts" / "run-fast-response-eval.py"
ASSERTION = ROOT / "scripts" / "assert-fast-response-eval.py"

SCHEMA_VERSION = "fast-response-eval-results.v1"
RUBRIC_KEYS = [
    "project_info_current_file_verification",
    "todowrite_planning",
    "short_korean_plan",
    "minimal_scope",
    "focused_verification",
    "stop_question_conditions",
    "forbidden_leakage_absent",
]
RUBRIC_LABELS = {
    "project_info_current_file_verification": "Project Info 먼저 읽기/현재 파일 검증 언급",
    "todowrite_planning": "todo_write 계획 사용",
    "short_korean_plan": "짧은 한국어 계획",
    "minimal_scope": "최소 수정 범위 유지",
    "focused_verification": "focused verification 제시",
    "stop_question_conditions": "stop/question 조건 인식",
    "forbidden_leakage_absent": "FAST 금지어 누수 없음",
}
FORBIDDEN_PATTERNS = [
    r"task_size",
    r"티셔츠",
    r"\bultrawork\b",
    r"\bsuperpowers\b",
    r"\bteam\b",
    r"subagent",
    r"\bcoder-35\b",
    r"\bdcp-front-developer\b",
    r"\bdcp-backend-developer\b",
    r"coder\s+delegation",
    r"agent\s+delegation",
    r"agent\s+tool",
    r"agent\s+호출",
    r"subagent_type",
]
MATRIX_SUCCESS_TASK_ID = "front_claim_intro_text"
MATRIX_FAIL_TASK_ID = "front_datastore_payload_trace"
MATRIX_WEAK_TASK_IDS = {"front_button_css_containment", "services_eai_parameter_trace"}
TEST_CODEX_MODEL = "gpt-5.4-mini"
REQUIRED_CODEX_FLAGS = ["--ephemeral", "--sandbox", "read-only"]
OPTIONAL_APPROVAL_ARGS = ["--ask-for-approval", "never"]


def main() -> None:
    assert_required_artifacts()
    benchmark = load_json(BENCHMARK_JSON)
    results = load_json(RESULTS_JSON)
    assert_method_document()
    assert_results_schema(results, benchmark)
    assert_task_coverage(results, benchmark)
    assert_pass_fail_mixed(results)
    assert_scoring_consistency(results)
    assert_forbidden_detection(results)
    assert_fallback_runner_record(results)
    assert_markdown_results(results)
    assert_real_codex_artifact_response()
    assert_real_codex_fail_closure()
    assert_codex_fake_runner_matrix()
    assert_stable_generated_at_policy()
    print("fast response eval assertions passed")


def assert_required_artifacts() -> None:
    for path in [BENCHMARK_JSON, RESULTS_JSON, RESULTS_MD, METHOD_MD, EVALUATION_REPORT_MD, RUNNER, ASSERTION]:
        assert path.exists(), f"missing required FAST response eval artifact: {path.relative_to(ROOT)}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_method_document() -> None:
    text = METHOD_MD.read_text(encoding="utf-8")
    for required in [
        "GPT-5.5 xhigh evaluator",
        "mock/dry-run",
        "KIWI_FAST_EVAL_RUNNER=codex",
        "KIWI_FAST_EVAL_CODEX_MODEL",
        "--ephemeral",
        "--sandbox read-only",
        "--ask-for-approval never",
        "feature-detected",
        "response-eval-results.codex.json",
        "0-2",
        "Project Info",
        "current files",
        "TodoWrite",
        "short Korean plan",
        "minimal scope",
        "focused verification",
        "stop/question",
        "forbidden leakage",
        "intentionally weak",
        "failure patterns",
        "accepted improvements",
        "fake codex executable",
        "source_counts",
        "fallback_events",
        "codex_available",
        "codex_model",
        "unsupported_safety_args",
        "codex-originated FAIL",
        "accepted prompt improvement",
        "accepted rubric improvement",
        "not accepted with reason",
        "stable generated_at",
    ]:
        assert required in text, f"response-eval-method.md missing: {required}"


def assert_results_schema(results: dict[str, Any], benchmark: dict[str, Any]) -> None:
    assert results.get("schema_version") == SCHEMA_VERSION
    assert results.get("benchmark_schema_version") == benchmark.get("schema_version")
    assert results.get("benchmark_task_count") == benchmark.get("task_count")
    assert isinstance(results.get("runner"), dict), "runner metadata missing"
    assert isinstance(results.get("summary"), dict), "summary missing"
    assert isinstance(results.get("tasks"), list), "tasks list missing"
    for field in [
        "requested_runner",
        "effective_runner",
        "fallback_to_mock",
        "fallback_reason",
        "source_counts",
        "fallback_events",
        "codex_available",
        "codex_model",
        "codex_safety_args",
        "unsupported_safety_args",
        "codex_command_args",
    ]:
        assert field in results["runner"], f"runner metadata missing {field}"
    assert isinstance(results["runner"]["source_counts"], dict), "runner source_counts must be object"
    assert isinstance(results["runner"]["fallback_events"], list), "runner fallback_events must be list"
    assert isinstance(results["runner"]["codex_available"], bool), "runner codex_available must be boolean"
    assert isinstance(results["runner"]["codex_model"], str), "runner codex_model must be string"
    assert isinstance(results["runner"]["codex_safety_args"], list), "runner codex_safety_args must be list"
    assert isinstance(results["runner"]["unsupported_safety_args"], list), (
        "runner unsupported_safety_args must be list"
    )
    assert isinstance(results["runner"]["codex_command_args"], list), "runner codex_command_args must be list"


def assert_task_coverage(results: dict[str, Any], benchmark: dict[str, Any]) -> None:
    benchmark_ids = {str(item.get("task_id")) for item in benchmark.get("tasks", [])}
    result_ids = {str(item.get("task_id")) for item in results.get("tasks", [])}
    assert result_ids == benchmark_ids, "response eval task ids do not match benchmark task ids"
    assert results["summary"].get("task_count") == len(benchmark_ids)


def assert_pass_fail_mixed(results: dict[str, Any]) -> None:
    passed = int(results["summary"].get("passed", -1))
    failed = int(results["summary"].get("failed", -1))
    assert passed > 0, "response eval must include at least one PASS"
    assert failed > 0, "response eval must include at least one FAIL"
    assert passed + failed == len(results.get("tasks", [])), "summary pass/fail count mismatch"
    weak = [item for item in results["tasks"] if item.get("response_source") == "mock_intentionally_weak"]
    assert len(weak) >= 2, "mock mode must include at least two intentionally weak response samples"
    assert all(item.get("pass") is False for item in weak), "intentionally weak samples must fail"


def assert_scoring_consistency(results: dict[str, Any]) -> None:
    for item in results["tasks"]:
        task_id = str(item.get("task_id"))
        rubric = item.get("rubric")
        assert isinstance(rubric, dict), f"{task_id} missing rubric object"
        assert set(rubric) == set(RUBRIC_KEYS), f"{task_id} rubric keys mismatch"
        total = 0
        failure_reasons = item.get("failure_reasons")
        assert isinstance(failure_reasons, list), f"{task_id} failure_reasons must be list"
        for key in RUBRIC_KEYS:
            detail = rubric[key]
            assert isinstance(detail, dict), f"{task_id} rubric item {key} must be object"
            assert "score" in detail and "notes" in detail, f"{task_id} rubric item {key} missing score/notes"
            score = detail["score"]
            assert isinstance(score, int) and 0 <= score <= 2, f"{task_id} rubric item {key} score out of range"
            total += score
            if score < 2:
                assert any(key in str(reason) for reason in failure_reasons), (
                    f"{task_id} score loss for {key} is not linked to failure reason"
                )
        assert item.get("score") == total, f"{task_id} score total mismatch"
        expected_pass = total >= 12 and rubric["forbidden_leakage_absent"]["score"] == 2
        assert item.get("pass") is expected_pass, f"{task_id} pass/fail inconsistent with score"
        assert isinstance(item.get("response_sample"), str) and item["response_sample"].strip(), (
            f"{task_id} missing response sample"
        )
        assert isinstance(item.get("evaluator_notes"), str) and item["evaluator_notes"].strip(), (
            f"{task_id} missing evaluator notes"
        )


def assert_forbidden_detection(results: dict[str, Any]) -> None:
    detected = []
    for item in results["tasks"]:
        sample = str(item.get("response_sample") or "")
        expected_hits = forbidden_hits(sample)
        recorded_hits = item.get("forbidden_leakage", {}).get("hits")
        assert recorded_hits == expected_hits, f"{item.get('task_id')} forbidden hit mismatch"
        forbidden_score = item["rubric"]["forbidden_leakage_absent"]["score"]
        assert forbidden_score == (2 if not expected_hits else 0), f"{item.get('task_id')} forbidden score mismatch"
        if expected_hits:
            detected.append(item.get("task_id"))
    assert detected, "response eval must include at least one sample with detected forbidden leakage"


def assert_fallback_runner_record(results: dict[str, Any]) -> None:
    runner = results["runner"]
    assert runner["effective_runner"] in {"mock", "codex", "mixed"}
    assert isinstance(runner["fallback_to_mock"], bool)
    source_counts = runner["source_counts"]
    counted_sources: dict[str, int] = {}
    for item in results["tasks"]:
        source = str(item.get("response_source"))
        counted_sources[source] = counted_sources.get(source, 0) + 1
    assert source_counts == counted_sources, "runner source_counts must match task response_source counts"
    for event in runner["fallback_events"]:
        assert isinstance(event, dict), "fallback_events entries must be objects"
        for field in ["task_id", "fallback_source", "reason"]:
            assert str(event.get(field) or "").strip(), f"fallback event missing {field}"
    fallback_task_ids = {
        str(item.get("task_id"))
        for item in results["tasks"]
        if item.get("response_source") == "mock_fallback"
    }
    fallback_event_task_ids = {str(event.get("task_id")) for event in runner["fallback_events"]}
    assert fallback_task_ids <= fallback_event_task_ids, "mock_fallback tasks must have matching fallback_events"
    if runner["effective_runner"] == "mock":
        assert runner["fallback_to_mock"] is True
        assert str(runner["fallback_reason"]).strip(), "mock/fallback run must record fallback_reason"
    if runner["effective_runner"] == "mixed":
        assert runner["fallback_events"], "mixed codex/mock run must record fallback_events"
        assert source_counts.get("codex", 0) > 0, "mixed run must include codex responses"
        assert source_counts.get("mock_fallback", 0) > 0, "mixed run must include mock_fallback responses"
    assert "mock" in str(runner.get("fallback_reason", "")).lower() or runner["effective_runner"] in {"codex", "mixed"}


def assert_markdown_results(results: dict[str, Any]) -> None:
    text = RESULTS_MD.read_text(encoding="utf-8")
    for required in [
        "GPT-5.5 xhigh evaluator",
        "PASS",
        "FAIL",
        "response sample",
        "failure patterns",
        "accepted improvements",
        "source_counts",
        "fallback_events",
        "Codex available",
        "Codex model",
        "Codex safety args",
        "Unsupported safety args",
        "Codex command args",
        "Critical: none",
        "High: none",
        "Medium: none",
    ]:
        assert required in text, f"response-eval-results.md missing: {required}"
    for item in results["tasks"]:
        assert str(item["task_id"]) in text, f"response-eval-results.md missing task {item['task_id']}"


def forbidden_hits(text: str) -> list[str]:
    return [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, text, re.IGNORECASE)]


def assert_codex_fake_runner_matrix() -> None:
    previous_codex_json = CODEX_RESULTS_JSON.read_text(encoding="utf-8") if CODEX_RESULTS_JSON.exists() else None
    previous_codex_md = CODEX_RESULTS_MD.read_text(encoding="utf-8") if CODEX_RESULTS_MD.exists() else None
    if previous_codex_json is not None:
        assert_codex_artifact_schema(json.loads(previous_codex_json), benchmark=load_json(BENCHMARK_JSON))
    with tempfile.TemporaryDirectory(prefix="kiwi-fast-fake-codex-") as tmp:
        try:
            tmp_path = Path(tmp)
            fake_codex = tmp_path / "codex"
            log_path = tmp_path / "fake-codex.jsonl"
            fake_codex.write_text(
                '''#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

HELP_SUPPORTED = """Run Codex non-interactively
Options:
      --ephemeral
  -s, --sandbox <SANDBOX_MODE>
      --ask-for-approval <POLICY>
  -m, --model <MODEL>
"""
HELP_UNSUPPORTED = """Run Codex non-interactively
Options:
      --ephemeral
  -s, --sandbox <SANDBOX_MODE>
  -m, --model <MODEL>
"""

if len(sys.argv) >= 3 and sys.argv[1] == "exec" and sys.argv[2] == "--help":
    mode = os.environ.get("KIWI_FAKE_CODEX_HELP_MODE", "supported")
    print(HELP_SUPPORTED if mode == "supported" else HELP_UNSUPPORTED)
    raise SystemExit(0)

prompt = sys.stdin.read()
if not prompt and sys.argv:
    prompt = sys.argv[-1]
log_path = os.environ["KIWI_FAKE_CODEX_LOG"]
with open(log_path, "a", encoding="utf-8") as handle:
    handle.write(json.dumps({"argv": sys.argv, "prompt": prompt[:500]}, ensure_ascii=False) + "\\n")
if "front_datastore_payload_trace" in prompt:
    sys.stderr.write("simulated codex nonzero failure for response eval matrix\\n")
    raise SystemExit(42)
print("계획: Project Info Layer를 먼저 읽고 현재 파일 근거로 확인하겠습니다.\\n"
      "1. 필요한 파일만 확인해 최소 수정 범위를 정하겠습니다.\\n"
      "2. focused verification 명령 또는 대체 확인을 기록하겠습니다.\\n"
      "중단/질문 조건: 업무 의미나 검증 범위가 불명확하면 편집하지 않고 질문하겠습니다.")
''',
                encoding="utf-8",
            )
            fake_codex.chmod(fake_codex.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            run_fake_codex_case(tmp_path, log_path, "supported", expect_approval_arg=True)
            run_fake_codex_case(tmp_path, log_path, "unsupported", expect_approval_arg=False)
        finally:
            if previous_codex_json is not None:
                CODEX_RESULTS_JSON.write_text(previous_codex_json, encoding="utf-8")
            if previous_codex_md is not None:
                CODEX_RESULTS_MD.write_text(previous_codex_md, encoding="utf-8")


def run_fake_codex_case(
    tmp_path: Path,
    log_path: Path,
    help_mode: str,
    *,
    expect_approval_arg: bool,
) -> None:
    if log_path.exists():
        log_path.unlink()
    env = os.environ.copy()
    env["KIWI_FAST_EVAL_RUNNER"] = "codex"
    env["KIWI_FAST_EVAL_CODEX_MODEL"] = TEST_CODEX_MODEL
    env["KIWI_FAKE_CODEX_LOG"] = str(log_path)
    env["KIWI_FAKE_CODEX_HELP_MODE"] = help_mode
    env["PATH"] = str(tmp_path) + os.pathsep + env.get("PATH", "")
    completed = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert completed.returncode == 0, (
        f"fake codex response eval runner failed for {help_mode}: "
        + (completed.stderr or completed.stdout or f"exit {completed.returncode}")[:1000]
    )
    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines, f"fake codex executable was not invoked for {help_mode}"
    records = [json.loads(line) for line in lines]
    for record in records:
        assert_codex_argv(record["argv"], expect_approval_arg=expect_approval_arg)
    matrix_results = load_json(RESULTS_JSON)
    runner = matrix_results["runner"]
    assert runner["requested_runner"] == "codex", f"fake codex {help_mode} requested_runner mismatch"
    assert runner["codex_available"] is True, f"fake codex {help_mode} must record codex_available true"
    assert runner["codex_model"] == TEST_CODEX_MODEL, f"fake codex {help_mode} must record codex_model"
    assert runner["effective_runner"] == "mixed", f"fake codex {help_mode} must record mixed effective_runner"
    assert_codex_safety_metadata(runner, expect_approval_arg=expect_approval_arg)
    source_counts = runner["source_counts"]
    assert source_counts.get("codex", 0) > 0, f"fake codex {help_mode} missing codex success task"
    assert source_counts.get("mock_fallback", 0) > 0, f"fake codex {help_mode} missing codex failure fallback task"
    assert source_counts.get("mock_intentionally_weak", 0) >= 2, f"fake codex {help_mode} missing weak samples"
    by_id = {str(item["task_id"]): item for item in matrix_results["tasks"]}
    assert by_id[MATRIX_SUCCESS_TASK_ID]["response_source"] == "codex", (
        f"codex success task not distinguished for {help_mode}"
    )
    assert by_id[MATRIX_FAIL_TASK_ID]["response_source"] == "mock_fallback", (
        f"codex failure fallback task not distinguished for {help_mode}"
    )
    for task_id in MATRIX_WEAK_TASK_IDS:
        assert by_id[task_id]["response_source"] == "mock_intentionally_weak", (
            f"{task_id} weak sample not distinguished for {help_mode}"
        )
    fallback_events = runner["fallback_events"]
    assert any(event.get("task_id") == MATRIX_FAIL_TASK_ID for event in fallback_events), (
        f"codex failure fallback event not recorded for {help_mode}"
    )
    assert all("simulated codex nonzero failure" in str(event) or event.get("task_id") != MATRIX_FAIL_TASK_ID for event in fallback_events), (
        f"codex stderr snippet missing from fallback event for {help_mode}"
    )
    assert all("--ask-for-approval" not in str(event) for event in fallback_events), (
        f"unsupported approval flag leaked into fallback_events for {help_mode}"
    )
    assert CODEX_RESULTS_JSON.exists(), "codex runner must preserve response-eval-results.codex.json"
    assert CODEX_RESULTS_MD.exists(), "codex runner must preserve response-eval-results.codex.md"
    assert_codex_artifact_schema(
        load_json(CODEX_RESULTS_JSON),
        benchmark=load_json(BENCHMARK_JSON),
        require_matrix_sources=True,
        expect_approval_arg=expect_approval_arg,
    )


def assert_real_codex_artifact_response() -> None:
    if not CODEX_RESULTS_JSON.exists():
        return
    results = load_json(CODEX_RESULTS_JSON)
    runner = results.get("runner") or {}
    if runner.get("requested_runner") == "codex" and runner.get("codex_available") is True:
        source_counts = runner.get("source_counts") or {}
        assert source_counts.get("codex", 0) >= 1, "real codex artifact must include at least one codex response"


def assert_real_codex_fail_closure() -> None:
    if not CODEX_RESULTS_JSON.exists():
        return
    results = load_json(CODEX_RESULTS_JSON)
    codex_failures = [
        item
        for item in results.get("tasks", [])
        if item.get("response_source") == "codex" and item.get("pass") is False
    ]
    if not codex_failures:
        return

    closure_text = EVALUATION_REPORT_MD.read_text(encoding="utf-8")
    if CODEX_FAIL_CLOSURE_MD.exists():
        closure_text += "\n" + CODEX_FAIL_CLOSURE_MD.read_text(encoding="utf-8")
    classification_markers = [
        "accepted prompt improvement",
        "accepted rubric improvement",
        "accepted benchmark adjustment",
        "not accepted with reason",
    ]
    lower_closure_text = closure_text.lower()
    for item in codex_failures:
        task_id = str(item.get("task_id") or "")
        assert task_id in closure_text, f"codex-originated FAIL closure missing task_id: {task_id}"
        for reason in item.get("failure_reasons") or []:
            assert str(reason) in closure_text, f"codex-originated FAIL closure missing failure reason for {task_id}: {reason}"
        task_marker = f"task_id: {task_id.lower()}"
        task_start = lower_closure_text.find(task_marker)
        assert task_start >= 0, f"codex-originated FAIL closure missing task marker: task_id: {task_id}"
        next_task_start = lower_closure_text.find("task_id:", task_start + len(task_marker))
        task_section = lower_closure_text[task_start:] if next_task_start < 0 else lower_closure_text[task_start:next_task_start]
        assert any(marker in task_section for marker in classification_markers), (
            f"codex-originated FAIL closure missing classification for {task_id}"
        )


def assert_codex_argv(argv: list[str], *, expect_approval_arg: bool) -> None:
    assert argv[:2] and argv[1] == "exec", f"fake codex argv did not use exec: {argv}"
    assert ("-m" in argv or "--model" in argv), f"fake codex argv missing model option: {argv}"
    if "-m" in argv:
        assert argv[argv.index("-m") + 1] == TEST_CODEX_MODEL, f"fake codex -m value mismatch: {argv}"
    if "--model" in argv:
        assert argv[argv.index("--model") + 1] == TEST_CODEX_MODEL, f"fake codex --model value mismatch: {argv}"
    for flag in REQUIRED_CODEX_FLAGS:
        assert flag in argv, f"fake codex argv missing required safety flag/value {flag}: {argv}"
    assert argv[argv.index("--sandbox") + 1] == "read-only", f"fake codex argv must use --sandbox read-only: {argv}"
    assert "Task ID:" not in " ".join(argv), f"fake codex argv must not contain prompt body: {argv}"
    if expect_approval_arg:
        assert argv[argv.index("--ask-for-approval") + 1] == "never", (
            f"fake codex argv must use --ask-for-approval never when supported: {argv}"
        )
    else:
        assert "--ask-for-approval" not in argv, f"fake codex argv must skip unsupported approval flag: {argv}"


def assert_codex_safety_metadata(runner: dict[str, Any], *, expect_approval_arg: bool) -> None:
    safety_args = runner.get("codex_safety_args") or []
    unsupported_safety_args = runner.get("unsupported_safety_args") or []
    for flag in REQUIRED_CODEX_FLAGS:
        assert flag in safety_args, f"codex safety args missing required flag/value {flag}: {safety_args}"
    assert safety_args[safety_args.index("--sandbox") + 1] == "read-only", (
        f"codex safety args must use --sandbox read-only: {safety_args}"
    )
    if expect_approval_arg:
        assert "--ask-for-approval" in safety_args, f"supported approval flag missing from safety args: {safety_args}"
        assert safety_args[safety_args.index("--ask-for-approval") + 1] == "never", (
            f"supported approval flag must use never: {safety_args}"
        )
        assert "--ask-for-approval" not in unsupported_safety_args, (
            f"supported approval flag incorrectly recorded unsupported: {unsupported_safety_args}"
        )
    else:
        assert "--ask-for-approval" not in safety_args, f"unsupported approval flag used in safety args: {safety_args}"
        assert unsupported_safety_args == OPTIONAL_APPROVAL_ARGS, (
            f"unsupported approval flag must be recorded: {unsupported_safety_args}"
        )


def assert_codex_artifact_schema(
    results: dict[str, Any],
    benchmark: dict[str, Any],
    require_matrix_sources: bool = False,
    expect_approval_arg: bool | None = None,
) -> None:
    assert results.get("schema_version") == SCHEMA_VERSION
    assert results.get("benchmark_schema_version") == benchmark.get("schema_version")
    assert results.get("benchmark_task_count") == benchmark.get("task_count")
    runner = results.get("runner")
    assert isinstance(runner, dict), "codex artifact runner metadata missing"
    assert runner.get("requested_runner") == "codex", "codex artifact requested_runner mismatch"
    assert runner.get("codex_available") is True, "codex artifact must record codex_available true"
    assert runner.get("codex_model") == TEST_CODEX_MODEL, "codex artifact codex_model mismatch"
    safety_args = runner.get("codex_safety_args") or []
    for flag in REQUIRED_CODEX_FLAGS:
        assert flag in safety_args, f"codex artifact safety args missing {flag}"
    assert isinstance(runner.get("unsupported_safety_args"), list), "codex artifact unsupported_safety_args missing"
    if expect_approval_arg is not None:
        assert_codex_safety_metadata(runner, expect_approval_arg=expect_approval_arg)
        assert_codex_argv(runner.get("codex_command_args") or [], expect_approval_arg=expect_approval_arg)
    else:
        assert "Task ID:" not in " ".join(str(arg) for arg in runner.get("codex_command_args") or []), (
            "codex artifact command args must not include prompt body"
        )
    assert isinstance(runner.get("source_counts"), dict), "codex artifact source_counts missing"
    assert isinstance(runner.get("fallback_events"), list), "codex artifact fallback_events missing"
    counted_sources: dict[str, int] = {}
    for item in results.get("tasks", []):
        source = str(item.get("response_source"))
        counted_sources[source] = counted_sources.get(source, 0) + 1
    assert runner["source_counts"] == counted_sources, "codex artifact source_counts mismatch"
    if require_matrix_sources:
        assert runner["source_counts"].get("codex", 0) > 0, "codex artifact missing codex response source"
        assert runner["source_counts"].get("mock_fallback", 0) > 0, "codex artifact missing mock_fallback source"
        assert runner["source_counts"].get("mock_intentionally_weak", 0) >= 2, (
            "codex artifact missing intentionally weak sources"
        )
        assert any(event.get("task_id") == MATRIX_FAIL_TASK_ID for event in runner["fallback_events"]), (
            "codex artifact missing fallback event for fake failure task"
        )


def assert_stable_generated_at_policy() -> None:
    env = os.environ.copy()
    env.pop("KIWI_FAST_EVAL_RUNNER", None)
    env.pop("KIWI_FAST_EVAL_CODEX_MODEL", None)
    first = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert first.returncode == 0, "first stable generated_at run failed: " + (first.stderr or first.stdout)[:1000]
    first_results = RESULTS_JSON.read_text(encoding="utf-8")
    first_generated_at = load_json(RESULTS_JSON).get("generated_at")
    second = subprocess.run(
        [sys.executable, str(RUNNER)],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert second.returncode == 0, "second stable generated_at run failed: " + (second.stderr or second.stdout)[:1000]
    second_results = RESULTS_JSON.read_text(encoding="utf-8")
    second_generated_at = load_json(RESULTS_JSON).get("generated_at")
    assert first_generated_at == second_generated_at, "generated_at changed on equivalent rerun"
    assert first_results == second_results, "response-eval-results.json changed on equivalent rerun"


if __name__ == "__main__":
    main()
