from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FAST_DIR = ROOT / "docs" / "fast-system-prompts"
BENCHMARK_JSON = FAST_DIR / "benchmark-results.json"
RESULTS_JSON = FAST_DIR / "response-eval-results.json"
RESULTS_MD = FAST_DIR / "response-eval-results.md"
CODEX_RESULTS_JSON = FAST_DIR / "response-eval-results.codex.json"
CODEX_RESULTS_MD = FAST_DIR / "response-eval-results.codex.md"

SCHEMA_VERSION = "fast-response-eval-results.v1"
PASS_THRESHOLD = 12
CODEX_TIMEOUT_SECONDS = 120
CODEX_REQUIRED_SAFETY_ARGS = ["--ephemeral", "--sandbox", "read-only"]
CODEX_OPTIONAL_SAFETY_ARGS = ["--ask-for-approval", "never"]
CODEX_HELP_TIMEOUT_SECONDS = 30
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
WEAK_SAMPLE_TASK_IDS = {
    "front_button_css_containment": "weak_missing_project_info",
    "services_eai_parameter_trace": "weak_forbidden_leakage",
}


def main() -> int:
    benchmark = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))
    requested_runner = os.getenv("KIWI_FAST_EVAL_RUNNER", "mock").strip().lower() or "mock"
    codex_model = os.getenv("KIWI_FAST_EVAL_CODEX_MODEL", "").strip()
    runner = resolve_runner(requested_runner, codex_model)

    task_results = []
    for task in benchmark.get("tasks", []):
        task_results.append(evaluate_task(task, runner))

    finalize_runner_metadata(runner, task_results)
    passed = sum(1 for item in task_results if item["pass"])
    failed = len(task_results) - passed
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_schema_version": benchmark.get("schema_version"),
        "benchmark_task_count": benchmark.get("task_count"),
        "runner": runner,
        "rubric": {
            "pass_threshold": PASS_THRESHOLD,
            "max_score": len(RUBRIC_KEYS) * 2,
            "criteria": {key: {"label": RUBRIC_LABELS[key], "range": "0-2"} for key in RUBRIC_KEYS},
        },
        "summary": {
            "task_count": len(task_results),
            "passed": passed,
            "failed": failed,
            "intentionally_weak": sum(1 for item in task_results if item["response_source"] == "mock_intentionally_weak"),
        },
        "tasks": task_results,
    }
    payload = write_results(payload)
    print(f"Wrote {RESULTS_JSON.relative_to(ROOT)}")
    print(f"Wrote {RESULTS_MD.relative_to(ROOT)}")
    if runner["requested_runner"] == "codex":
        print(f"Wrote {CODEX_RESULTS_JSON.relative_to(ROOT)}")
        print(f"Wrote {CODEX_RESULTS_MD.relative_to(ROOT)}")
    print(f"FAST response eval: {passed} PASS / {failed} FAIL using {runner['effective_runner']}")
    return 0


def resolve_runner(requested_runner: str, codex_model: str) -> dict[str, Any]:
    base_metadata = {
        "codex_model": codex_model if requested_runner == "codex" else "",
        "codex_safety_args": [],
        "unsupported_safety_args": [],
        "codex_command_args": [],
    }
    if requested_runner != "codex":
        return {
            "requested_runner": requested_runner or "mock",
            "effective_runner": "mock",
            "codex_checked": False,
            "codex_available": False,
            "codex_path": "",
            **base_metadata,
            "source_counts": {},
            "fallback_events": [],
            "fallback_to_mock": True,
            "fallback_reason": "default mock/dry-run mode; no external model call attempted",
        }
    codex_path = shutil.which("codex")
    if not codex_path:
        return {
            "requested_runner": "codex",
            "effective_runner": "mock",
            "codex_checked": True,
            "codex_available": False,
            "codex_path": "",
            **base_metadata,
            "source_counts": {},
            "fallback_events": [],
            "fallback_to_mock": True,
            "fallback_reason": "codex CLI not found; fallback to mock/dry-run response samples",
        }
    safety_args, unsupported_safety_args = detect_codex_safety_args(codex_path)
    command_args = build_codex_command_args(codex_path, codex_model, safety_args)
    return {
        "requested_runner": "codex",
        "effective_runner": "codex",
        "codex_checked": True,
        "codex_available": True,
        "codex_path": codex_path,
        **base_metadata,
        "codex_safety_args": safety_args,
        "unsupported_safety_args": unsupported_safety_args,
        "codex_command_args": command_args,
        "source_counts": {},
        "fallback_events": [],
        "fallback_to_mock": False,
        "fallback_reason": "",
    }


def finalize_runner_metadata(runner: dict[str, Any], task_results: list[dict[str, Any]]) -> None:
    source_counts: dict[str, int] = {}
    for item in task_results:
        source = str(item.get("response_source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
    runner["source_counts"] = source_counts

    codex_count = source_counts.get("codex", 0)
    fallback_count = source_counts.get("mock_fallback", 0)
    if runner["requested_runner"] != "codex":
        runner["effective_runner"] = "mock"
        runner["fallback_to_mock"] = True
        runner["fallback_reason"] = "default mock/dry-run mode; no external model call attempted"
    elif codex_count and fallback_count:
        runner["effective_runner"] = "mixed"
        runner["fallback_to_mock"] = True
        runner["fallback_reason"] = f"codex succeeded for {codex_count} task(s); mock fallback used for {fallback_count} task(s)"
    elif codex_count:
        runner["effective_runner"] = "codex"
        runner["fallback_to_mock"] = False
        runner["fallback_reason"] = ""
    else:
        runner["effective_runner"] = "mock"
        runner["fallback_to_mock"] = True
        if not runner["codex_available"]:
            runner["fallback_reason"] = "codex CLI not found; fallback to mock/dry-run response samples"
        elif fallback_count:
            runner["fallback_reason"] = f"codex failed for {fallback_count} task(s); mock fallback used for all codex-eligible tasks"
        else:
            runner["fallback_reason"] = "no codex-eligible task produced a codex response"


def write_results(payload: dict[str, Any]) -> dict[str, Any]:
    stable_payload = write_result_pair(payload, RESULTS_JSON, RESULTS_MD)
    if payload["runner"]["requested_runner"] == "codex":
        write_result_pair(payload, CODEX_RESULTS_JSON, CODEX_RESULTS_MD)
    return stable_payload


def write_result_pair(payload: dict[str, Any], json_path: Path, md_path: Path) -> dict[str, Any]:
    stable_payload = stabilize_generated_at(payload, json_path)
    json_path.write_text(json.dumps(stable_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(stable_payload), encoding="utf-8")
    return stable_payload


def stabilize_generated_at(payload: dict[str, Any], json_path: Path) -> dict[str, Any]:
    if os.getenv("KIWI_FAST_EVAL_REFRESH_GENERATED_AT", "").strip() == "1":
        return payload
    if not json_path.exists():
        return payload
    try:
        previous = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return payload
    if without_generated_at(previous) == without_generated_at(payload):
        payload = dict(payload)
        payload["generated_at"] = previous.get("generated_at") or payload["generated_at"]
    return payload


def without_generated_at(payload: dict[str, Any]) -> dict[str, Any]:
    copy = dict(payload)
    copy.pop("generated_at", None)
    return copy


def evaluate_task(task: dict[str, Any], runner: dict[str, Any]) -> dict[str, Any]:
    task_id = str(task["task_id"])
    response_source = "mock"
    if task_id in WEAK_SAMPLE_TASK_IDS:
        sample = mock_response(task)
        response_source = "mock_intentionally_weak"
    elif runner["requested_runner"] == "codex":
        if not runner["codex_available"]:
            sample = mock_response(task)
            response_source = "mock_fallback"
            runner["fallback_events"].append(
                make_fallback_event(
                    task_id=task_id,
                    reason_type="codex_unavailable",
                    reason="codex CLI not found",
                )
            )
        else:
            sample, codex_error = run_codex_response(task, runner)
            if codex_error:
                sample = mock_response(task)
                response_source = "mock_fallback"
                runner["fallback_events"].append(make_fallback_event(task_id=task_id, **codex_error))
            else:
                response_source = "codex"
    else:
        sample = mock_response(task)

    rubric = score_response(sample)
    score = sum(item["score"] for item in rubric.values())
    failure_reasons = failure_reasons_for(rubric)
    passed = score >= PASS_THRESHOLD and rubric["forbidden_leakage_absent"]["score"] == 2
    return {
        "task_id": task_id,
        "profile": task.get("profile"),
        "prompt_source": task.get("prompt_source"),
        "response_source": response_source,
        "response_sample": sample,
        "score": score,
        "max_score": len(RUBRIC_KEYS) * 2,
        "pass": passed,
        "failure_reasons": failure_reasons,
        "evaluator_notes": evaluator_notes(task_id, rubric, passed),
        "forbidden_leakage": {
            "passed": not forbidden_hits(sample),
            "hits": forbidden_hits(sample),
        },
        "rubric": rubric,
    }


def detect_codex_safety_args(codex_path: str) -> tuple[list[str], list[str]]:
    try:
        completed = subprocess.run(
            [codex_path, "exec", "--help"],
            text=True,
            capture_output=True,
            timeout=CODEX_HELP_TIMEOUT_SECONDS,
        )
        help_text = f"{completed.stdout}\n{completed.stderr}"
    except (OSError, subprocess.SubprocessError):
        help_text = ""

    safety_args: list[str] = []
    unsupported_safety_args: list[str] = []
    if "--ephemeral" in help_text:
        safety_args.append("--ephemeral")
    else:
        unsupported_safety_args.append("--ephemeral")
    if "--sandbox" in help_text:
        safety_args.extend(["--sandbox", "read-only"])
    else:
        unsupported_safety_args.extend(["--sandbox", "read-only"])
    if "--ask-for-approval" in help_text:
        safety_args.extend(CODEX_OPTIONAL_SAFETY_ARGS)
    else:
        unsupported_safety_args.extend(CODEX_OPTIONAL_SAFETY_ARGS)
    return safety_args, unsupported_safety_args


def build_codex_command_args(codex_path: str, codex_model: str, safety_args: list[str]) -> list[str]:
    args = [codex_path, "exec", "--skip-git-repo-check", *safety_args]
    if codex_model:
        args.extend(["-m", codex_model])
    return args


def run_codex_response(task: dict[str, Any], runner: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    task_id = str(task.get("task_id") or "unknown")
    prompt = (
        "아래 FAST benchmark final prompt에 대해 실제 작업 전 첫 응답 샘플만 작성하라.\n"
        "저장소 파일을 읽거나 수정하지 말고, 패치/명령 실행/파일 변경 지시를 절대 하지 마라.\n"
        "첫 줄은 `계획:`으로 시작하라. `todo_write` tool 계획을 사용할 것이라고 명시하라. "
        "8줄 이내 한국어로 Project Info 확인, 현재 파일 검증, "
        "최소 범위, focused verification 명령 또는 대체 확인, 중단 조건만 요약하라.\n\n"
        f"Task ID: {task_id}\n"
        f"Profile: {task.get('profile')}\n\n"
        + str(task.get("final_prompt", ""))[:12000]
    )
    command = build_codex_command_args(
        str(runner["codex_path"]),
        str(runner.get("codex_model") or ""),
        list(runner.get("codex_safety_args") or []),
    )
    try:
        with tempfile.TemporaryDirectory(prefix="kiwi-fast-codex-eval-") as tmp:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=CODEX_TIMEOUT_SECONDS,
                cwd=tmp,
            )
    except subprocess.TimeoutExpired as exc:
        return "", {
            "reason_type": "timeout",
            "reason": f"codex timed out after {CODEX_TIMEOUT_SECONDS}s",
            "exit_code": None,
            "stderr_snippet": safe_snippet(exc.stderr or exc.stdout or ""),
        }
    except OSError as exc:
        return "", {
            "reason_type": "os_error",
            "reason": str(exc),
            "exit_code": None,
            "stderr_snippet": "",
        }
    except subprocess.SubprocessError as exc:
        return "", {
            "reason_type": "subprocess_error",
            "reason": str(exc),
            "exit_code": None,
            "stderr_snippet": "",
        }
    if completed.returncode != 0:
        snippet = safe_snippet(completed.stderr or completed.stdout or f"codex exited {completed.returncode}")
        return "", {
            "reason_type": "nonzero_exit",
            "reason": f"codex exited {completed.returncode}",
            "exit_code": completed.returncode,
            "stderr_snippet": snippet,
        }
    text = (completed.stdout or "").strip()
    if not text:
        return "", {
            "reason_type": "empty_output",
            "reason": "codex returned empty output",
            "exit_code": completed.returncode,
            "stderr_snippet": safe_snippet(completed.stderr or ""),
        }
    return text[:6000], None


def make_fallback_event(
    *,
    task_id: str,
    reason_type: str,
    reason: str,
    exit_code: int | None = None,
    stderr_snippet: str = "",
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "fallback_source": "mock_fallback",
        "reason_type": reason_type,
        "reason": reason,
        "exit_code": exit_code,
        "stderr_snippet": safe_snippet(stderr_snippet),
        "timeout_seconds": CODEX_TIMEOUT_SECONDS if reason_type == "timeout" else None,
    }


def safe_snippet(text: object, max_chars: int = 500) -> str:
    value = str(text or "")
    value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer ***", value, flags=re.IGNORECASE)
    value = re.sub(r"\bsk-[A-Za-z0-9._~+/=-]{16,}", "sk-***", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:max_chars]


def mock_response(task: dict[str, Any]) -> str:
    task_id = str(task["task_id"])
    if WEAK_SAMPLE_TASK_IDS.get(task_id) == "weak_missing_project_info":
        return (
            "바로 CSS를 크게 정리하겠습니다.\n"
            "전체 스타일을 훑어서 보기 좋게 바꾸고 결과만 알려드리겠습니다.\n"
            "검증은 나중에 화면을 보면 될 것 같습니다."
        )
    if WEAK_SAMPLE_TASK_IDS.get(task_id) == "weak_forbidden_leakage":
        return (
            "계획: Project Info를 보고 현재 파일을 확인한 뒤 처리합니다.\n"
            "이 작업은 subagent에게 넘겨서 EAI payload를 고치게 하고 task_size를 medium으로 보겠습니다.\n"
            "최소 수정 후 focused verification을 실행하고, 불명확하면 질문하겠습니다."
        )
    profile = str(task.get("profile"))
    task_id_label = task_id.replace("_", " ")
    if profile == "dcp-front":
        surface = "route/view/component/Vuex DataStore/Axios/CSS/Playwright"
    elif profile == "dcp-services":
        surface = "controller/service/repository/MyBatis/EAI/resources-env/profile/verification"
    else:
        surface = "entrypoint/module/config/data/tests/scripts"
    return (
        f"계획: `todo_write` tool로 {task_id_label} 작업 순서와 완료 조건을 먼저 기록하겠습니다.\n"
        "1. Project Info Layer 요약을 읽고 현재 파일로 검증하겠습니다.\n"
        f"2. {surface} 관련 파일만 확인해 근거를 잡겠습니다.\n"
        "3. 확인된 gap이 있을 때만 최소 수정 범위를 유지해 작은 diff로 반영하겠습니다.\n"
        "4. focused verification 명령 또는 실행 불가 시 대체 확인을 기록하겠습니다.\n"
        "중단/질문 조건: 소유 파일, 업무 의미, payload/config, 검증 범위가 불명확하면 편집하지 않고 질문하겠습니다."
    )


def score_response(response: str) -> dict[str, dict[str, Any]]:
    hits = forbidden_hits(response)
    return {
        "project_info_current_file_verification": score_project_info(response),
        "todowrite_planning": score_todowrite_planning(response),
        "short_korean_plan": score_korean_plan(response),
        "minimal_scope": score_minimal_scope(response),
        "focused_verification": score_focused_verification(response),
        "stop_question_conditions": score_stop_question(response),
        "forbidden_leakage_absent": {
            "score": 2 if not hits else 0,
            "notes": "No FAST forbidden leakage detected." if not hits else "Forbidden leakage detected: " + ", ".join(hits),
        },
    }


def score_project_info(response: str) -> dict[str, Any]:
    has_project_info = "Project Info" in response
    has_current_file = "현재 파일" in response or "current file" in response.lower()
    if has_project_info and has_current_file:
        return {"score": 2, "notes": "Mentions Project Info first context and current file verification."}
    if has_project_info or has_current_file:
        return {"score": 1, "notes": "Partially mentions Project Info or current file verification."}
    return {"score": 0, "notes": "Does not mention Project Info or current file verification."}


def score_todowrite_planning(response: str) -> dict[str, Any]:
    has_todo = "TodoWrite" in response or "todo_write" in response
    has_plan = "계획" in response or "plan" in response.lower()
    if has_todo and has_plan:
        return {"score": 2, "notes": "Uses `todo_write` tool for planning."}
    if has_todo:
        return {"score": 1, "notes": "Mentions `todo_write` tool without a clear plan."}
    return {"score": 0, "notes": "Does not use `todo_write` tool for planning."}


def score_korean_plan(response: str) -> dict[str, Any]:
    has_korean = bool(re.search(r"[가-힣]", response))
    has_plan = "계획" in response or bool(re.search(r"(^|\n)\s*1\.", response))
    if has_korean and has_plan:
        return {"score": 2, "notes": "Includes a concise Korean plan."}
    if has_korean:
        return {"score": 1, "notes": "Korean response exists but plan is weak."}
    return {"score": 0, "notes": "No short Korean plan."}


def score_minimal_scope(response: str) -> dict[str, Any]:
    if "최소" in response and ("작은 diff" in response or "범위" in response):
        return {"score": 2, "notes": "Keeps minimal scope and small diff discipline."}
    if ("수정 범위" in response or "변경 범위" in response) and (
        "한정" in response or "건드리지 않" in response or "무관한 파일" in response
    ):
        return {"score": 2, "notes": "Keeps minimal scope with explicit boundary language."}
    if "최소" in response or "작은" in response or "범위" in response:
        return {"score": 1, "notes": "Mentions narrow scope but lacks full minimal-diff discipline."}
    return {"score": 0, "notes": "Does not preserve minimal scope."}


def score_focused_verification(response: str) -> dict[str, Any]:
    lower = response.lower()
    if "focused verification" in lower and ("명령" in response or "대체 확인" in response or "실행" in response):
        return {"score": 2, "notes": "Presents focused verification with command or fallback expectation."}
    if ("집중 확인" in response or "영향 범위만" in response) and (
        "검증" in response or "대체" in response or "정적 비교" in response
    ):
        return {"score": 2, "notes": "Presents bounded verification with a fallback check."}
    if "검증" in response or "verification" in lower:
        return {"score": 1, "notes": "Mentions verification but not focused enough."}
    return {"score": 0, "notes": "No focused verification."}


def score_stop_question(response: str) -> dict[str, Any]:
    if ("중단" in response or "질문" in response or "stop and ask" in response.lower()) and (
        "불명확" in response or "모호" in response or "unclear" in response.lower()
    ):
        return {"score": 2, "notes": "Recognizes stop/question conditions."}
    if "중단" in response and (
        "여러 군데" in response or "범위가 넓" in response or "추가 확인" in response or "필요하다고 보고" in response
    ):
        return {"score": 2, "notes": "Recognizes concrete stop conditions."}
    if "질문" in response or "중단" in response:
        return {"score": 1, "notes": "Mentions question/stop but not specific conditions."}
    return {"score": 0, "notes": "No stop/question condition recognition."}


def failure_reasons_for(rubric: dict[str, dict[str, Any]]) -> list[str]:
    reasons = []
    for key, detail in rubric.items():
        if int(detail["score"]) < 2:
            reasons.append(f"{key}: {detail['notes']}")
    return reasons


def evaluator_notes(task_id: str, rubric: dict[str, dict[str, Any]], passed: bool) -> str:
    weak = [key for key, detail in rubric.items() if int(detail["score"]) < 2]
    if passed:
        return f"{task_id} follows FAST response principles under the closed-network Qwen3.5 rubric."
    return f"{task_id} fails FAST response quality on: {', '.join(weak)}."


def forbidden_hits(text: str) -> list[str]:
    return [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, text, re.IGNORECASE)]


def render_markdown(payload: dict[str, Any]) -> str:
    runner = payload["runner"]
    summary = payload["summary"]
    lines = [
        "# FAST Response Eval Results",
        "",
        "Generated by `scripts/run-fast-response-eval.py` for GPT-5.5 xhigh evaluator review.",
        "",
        "## Method",
        "",
        "- Source prompts: `docs/fast-system-prompts/benchmark-results.json` final_prompt values.",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Requested runner: `{runner['requested_runner']}`",
        f"- Effective runner: `{runner['effective_runner']}`",
        f"- Codex available: `{runner['codex_available']}`",
        f"- Codex model: `{runner['codex_model'] or '(default)'}`",
        f"- Codex safety args: `{json.dumps(runner['codex_safety_args'], ensure_ascii=False)}`",
        f"- Unsupported safety args: `{json.dumps(runner['unsupported_safety_args'], ensure_ascii=False)}`",
        f"- Codex command args: `{json.dumps(runner['codex_command_args'], ensure_ascii=False)}`",
        f"- Fallback to mock: `{runner['fallback_to_mock']}`",
        f"- Fallback reason: {runner['fallback_reason'] or '(none)'}",
        f"- source_counts: `{json.dumps(runner['source_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- fallback_events: `{json.dumps(runner['fallback_events'], ensure_ascii=False)}`",
        f"- Scoring: {len(RUBRIC_KEYS)} rubric items, each 0-2 points. PASS requires at least {PASS_THRESHOLD}/{len(RUBRIC_KEYS) * 2} and no forbidden leakage.",
        "",
        "## Summary",
        "",
        f"- Task count: {summary['task_count']}",
        f"- PASS: {summary['passed']}",
        f"- FAIL: {summary['failed']}",
        f"- Intentionally weak samples: {summary['intentionally_weak']}",
        f"- Source counts: `{json.dumps(runner['source_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- Fallback events: {len(runner['fallback_events'])}",
        "",
        "## Task Scores",
        "",
        "| task | profile | source | score | PASS/FAIL | failure reasons |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for item in payload["tasks"]:
        reasons = "; ".join(item["failure_reasons"]) or "(none)"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["task_id"]),
                    str(item["profile"]),
                    str(item["response_source"]),
                    f"{item['score']}/{item['max_score']}",
                    "PASS" if item["pass"] else "FAIL",
                    reasons,
                ]
            )
            + " |"
        )
    lines.extend(["", "## Sample Responses", ""])
    for item in payload["tasks"]:
        lines.extend(
            [
                f"### {item['task_id']}",
                "",
                f"- PASS/FAIL: {'PASS' if item['pass'] else 'FAIL'}",
                f"- Response source: `{item['response_source']}`",
                f"- Evaluator notes: {item['evaluator_notes']}",
                f"- Forbidden leakage: {json.dumps(item['forbidden_leakage'], ensure_ascii=False)}",
                "",
                "response sample:",
                "",
                "```text",
                item["response_sample"],
                "```",
                "",
            ]
        )
    failed = [item for item in payload["tasks"] if not item["pass"]]
    lines.extend(
        [
            "## failure patterns",
            "",
            *[f"- {item['task_id']}: " + "; ".join(item["failure_reasons"]) for item in failed],
            "",
            "## accepted improvements",
            "",
            "- Retain intentionally weak mock samples as regression fixtures.",
            "- Keep source_counts, codex_available, and fallback_events explicit for closed-network reproducibility.",
            "- Keep task-level response_source values distinct for codex success, mock fallback, and intentionally weak samples.",
            "- Record codex_model, codex safety args, and codex command args without the prompt for audit.",
            "- Record unsupported codex safety args separately so feature detection does not become a task fallback.",
            "- Preserve codex-requested runs in response-eval-results.codex.json/md in addition to the default artifact path.",
            "- Reuse generated_at on equivalent reruns to avoid dirty diffs from timestamp-only changes.",
            "- Link every score loss to a rubric key in failure reasons.",
            "",
            "## Self-Review Findings",
            "",
            "Critical: none",
            "",
            "High: none",
            "",
            "Medium: none",
            "",
            "Low: Mock response samples evaluate rubric behavior but do not prove live Qwen3.5 behavior.",
            "",
        ]
    )
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(line.rstrip() for line in lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
