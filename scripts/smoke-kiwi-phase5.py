#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build" / "e2e-smoke"
VENV_DIR = ROOT / "build" / "e2e-smoke-venv"
PROJECTS_DIR = BUILD_DIR / "projects"
RUNTIME_DIR = BUILD_DIR / "qwen-runtime"
EVIDENCE_PATH = BUILD_DIR / "phase5-smoke-evidence.json"


class SmokeProcess:
    def __init__(self, name: str, command: list[str], env: dict[str, str], cwd: Path):
        self.name = name
        self.command = command
        self.proc = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self.lines: list[str] = []
        self.thread = threading.Thread(target=self._drain, daemon=True)
        self.thread.start()

    def _drain(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.lines.append(line.rstrip("\n"))
            self.lines = self.lines[-400:]

    def stop(self) -> None:
        if self.proc.poll() is not None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=8)

    def tail(self, count: int = 80) -> str:
        return "\n".join(self.lines[-count:])


class StubLlmHandler(BaseHTTPRequestHandler):
    request_log: list[dict[str, Any]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        self.request_log.append({"path": self.path, "payload": payload})
        response = {
            "id": "chatcmpl-phase5-smoke",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.get("model") or "phase5-stub",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": llm_response_content(payload)},
                    "finish_reason": "stop",
                }
            ],
        }
        raw = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def llm_response_content(payload: dict[str, Any]) -> str:
    marker = extract_phase5_marker(payload)
    task = "Update the Phase 5 fixture greeting text and verify through focused local checks."
    if marker:
        task = f"{task} Preserve marker {marker} in the generated instruction."
    return json.dumps(
        {
            "task_summary": "Update the Phase 5 fixture greeting and verify the change.",
            "task_type": "frontend",
            "mode": "implement",
            "search_queries": ["phase5 fixture greeting", "phase5 verification"],
            "target_files": ["src/phase5-fixture.ts"],
            "missing_information": [],
            "questions": [],
            "risk_flags": [],
            "status": "ready",
            "assistant_message": "Phase 5 smoke prompt is ready.",
            "prompt_parts": {
                "title": "Phase 5 fixture greeting update",
                "task": task,
                "target_files": ["src/phase5-fixture.ts"],
                "required_reading": ["KIWI.md", "src/phase5-fixture.ts"],
                "required_search": ["rg -n \"phase5Greeting|Phase 5\" src"],
                "implementation_rules": [
                    "Read the current fixture file before editing.",
                    "Keep the change narrow and avoid unrelated formatting.",
                    "Report any mismatch between Project Info and current files.",
                ],
                "verification": ["python3 -m compileall scripts/phase5_qwen_shim.py"],
                "output_contract": ["changed files", "verification result", "remaining risks"],
                "stop_conditions": ["Stop and ask if the target file is missing."],
            },
        },
        ensure_ascii=False,
    )


def extract_phase5_marker(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    match = re.search(r"PHASE5_FAST_GENERATED_PROMPT_MARKER_[A-Z0-9_]+", text)
    return match.group(0) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="KIWI Phase 5 E2E smoke")
    parser.parse_args()
    processes: list[SmokeProcess] = []
    evidence: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "initial_failure": {
            "command": "python3 scripts/smoke-kiwi-phase5.py",
            "first_observed_message": "[Errno 2] No such file or directory before Phase 5 harness was added",
        },
        "checks": [],
    }
    llm_server: ThreadingHTTPServer | None = None
    try:
        reset_fixture_tree()
        basic_project = create_fixture_project("phase5-basic", "basic")
        codex_project = create_fixture_project("phase5-codex", "codex")

        llm_port = free_port()
        llm_server = ThreadingHTTPServer(("127.0.0.1", llm_port), StubLlmHandler)
        threading.Thread(target=llm_server.serve_forever, daemon=True).start()

        backend_port = free_port()
        web_port = free_port()
        backend_base = f"http://127.0.0.1:{backend_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        backend_python = ensure_backend_python()
        codex_probe = ensure_codex_for_smoke()

        backend_env = os.environ.copy()
        if codex_probe["prepend_path"]:
            backend_env["PATH"] = f"{codex_probe['prepend_path']}{os.pathsep}{backend_env.get('PATH', '')}"
        backend_env.update(
            {
                "PYTHONPATH": str(ROOT),
                "KIWI_DB_PATH": str(BUILD_DIR / "kiwi.sqlite3"),
                "KIWI_QWENCODE_RUNTIME_DIR": str(RUNTIME_DIR),
                "KIWI_PHASE5_TEST_MODE": "1",
                "KIWI_PHASE5_TEST_API_BASE_URL": f"http://127.0.0.1:{llm_port}/v1",
                "KIWI_PHASE5_TEST_CODER_API_BASE_URL": f"http://127.0.0.1:{llm_port}/v1",
            }
        )
        record(evidence, "codex smoke runner", codex_probe)
        processes.append(
            SmokeProcess(
                "backend",
                [
                    str(backend_python),
                    "-m",
                    "uvicorn",
                    "backend.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(backend_port),
                ],
                backend_env,
                ROOT,
            )
        )
        wait_http_ok(f"{backend_base}/api/health", "backend health")
        record(evidence, "backend started", {"url": backend_base})

        web_env = os.environ.copy()
        web_env["NEXT_PUBLIC_KIWI_API_URL"] = backend_base
        processes.append(
            SmokeProcess(
                "web",
                [str(ROOT / "node_modules" / ".bin" / "next"), "dev", "-H", "127.0.0.1", "-p", str(web_port)],
                web_env,
                ROOT,
            )
        )
        wait_http_ok(web_base, "web root", timeout=80)
        record(evidence, "web started", {"url": web_base})
        assert_dom_smoke(web_base, evidence)

        api_json(
            backend_base,
            "PUT",
            "/api/settings",
            {"kk_docs_mcp_enabled": False, "request_timeout_seconds": 15},
        )
        basic = initialize_project(backend_base, basic_project)
        codex = initialize_project(backend_base, codex_project)
        assert_project_info(backend_base, basic["project"]["id"], evidence)

        fast_run = assert_fast_prompt_builder(backend_base, basic["project"]["id"], evidence)
        assert_fast_console_session(backend_base, fast_run, evidence)
        assert_ultrawork_and_superpowers(backend_base, basic["project"]["id"], evidence)
        assert_codex_backed_shim(backend_base, codex["project"]["id"], codex_project, evidence)
        assert_static_frontend_contracts(evidence)
        assert_windows_package_sources(evidence)

        evidence["completed_at"] = datetime.now(timezone.utc).isoformat()
        EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("KIWI Phase 5 smoke PASS")
        print(json.dumps({"evidence": str(EVIDENCE_PATH), "checks": len(evidence["checks"])}, ensure_ascii=False))
        return 0
    except Exception as exc:
        evidence["failed_at"] = datetime.now(timezone.utc).isoformat()
        evidence["failure"] = str(exc)
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"KIWI Phase 5 smoke FAIL: {exc}", file=sys.stderr)
        for process in processes:
            print(f"\n--- {process.name} log tail ---", file=sys.stderr)
            print(process.tail(), file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            process.stop()
        if llm_server is not None:
            llm_server.shutdown()
            llm_server.server_close()


def reset_fixture_tree() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    (RUNTIME_DIR / "app").mkdir(parents=True, exist_ok=True)
    (RUNTIME_DIR / "scripts").mkdir(parents=True, exist_ok=True)
    (RUNTIME_DIR / "portable-runtime").mkdir(parents=True, exist_ok=True)
    write_smoke_qwen_skills(RUNTIME_DIR / "templates" / "project" / ".qwen" / "skills")
    write_smoke_qwen_agents(RUNTIME_DIR / "templates" / "project" / ".qwen" / "agents")
    (RUNTIME_DIR / "app" / "cli.js").write_text("// Phase 5 smoke runtime placeholder\n", encoding="utf-8")
    qwen_init = RUNTIME_DIR / "qwen-init.cmd"
    qwen_init.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "project=\"${1:-$(pwd)}\"\n"
        f"mkdir -p \"$project/.qwen/skills\" \"$project/.qwen/agents\"\n"
        f"cp -R {shell_quote(str(RUNTIME_DIR / 'templates' / 'project' / '.qwen' / 'skills'))}/. \"$project/.qwen/skills/\"\n"
        f"cp -R {shell_quote(str(RUNTIME_DIR / 'templates' / 'project' / '.qwen' / 'agents'))}/. \"$project/.qwen/agents/\"\n",
        encoding="utf-8",
    )
    qwen_init.chmod(0o755)
    run_qwen = RUNTIME_DIR / "run-qwen.cmd"
    run_qwen.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"exec {shell_quote(sys.executable)} {shell_quote(str(ROOT / 'scripts' / 'phase5_qwen_shim.py'))} "
        f"--runtime {shell_quote(str(RUNTIME_DIR))} --project \"$(pwd)\" "
        "--variant \"${KIWI_PHASE5_SHIM_VARIANT:-basic}\"\n",
        encoding="utf-8",
    )
    run_qwen.chmod(0o755)


def write_smoke_qwen_skills(skills_dir: Path) -> None:
    for name in ("kiwi-superpowers", "using-superpowers"):
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        source = ROOT / "docs" / "superpowers-skills" / name / "SKILL.md"
        if source.exists():
            shutil.copy2(source, skill_dir / "SKILL.md")
            continue
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Phase 5 smoke local Qwen skill fixture.\n---\n\n"
            f"# {name}\n\n"
            "Read D:/aiops/docs/<project-key>/knowledge/00-index.md first when present. "
            "Use optional Project Info Layer summaries only under D:/aiops/docs/<project-key>/project-info when that central directory exists. "
            "Use Qwen native skill loading for local runtime skills; do not use remote discovery or external plugin lookup.\n",
            encoding="utf-8",
        )


def write_smoke_qwen_agents(agents_dir: Path) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "architect-35",
        "coder-35",
        "debugger-35",
        "explorer-35",
        "planner-35",
        "reviewer-35",
        "tester-35",
        "dcp-front-developer",
        "dcp-backend-developer",
        "drt-front-developer",
        "drt-backend-developer",
        "drt-cms-front-developer",
        "drt-cms-backend-developer",
    ):
        source = ROOT / "docs" / "ultrawork-agents" / f"{name}.md"
        target = agents_dir / f"{name}.md"
        if source.exists():
            shutil.copy2(source, target)
            continue
        target.write_text(
            f"---\nname: {name}\ndescription: Phase 5 smoke Qwen subagent fixture.\n---\n\n# {name}\n",
            encoding="utf-8",
        )


def ensure_codex_for_smoke() -> dict[str, Any]:
    candidates: list[Path] = []
    path_codex = shutil.which("codex")
    if path_codex:
        candidates.append(Path(path_codex))
    nvm_root = Path.home() / ".nvm" / "versions" / "node"
    if nvm_root.exists():
        candidates.extend(
            sorted(
                nvm_root.glob(
                    "*/lib/node_modules/@openai/codex/node_modules/@openai/codex-*/vendor/*/bin/codex"
                )
            )
        )
    failure = "codex executable not found"
    seen: set[str] = set()
    for codex_path in candidates:
        codex = str(codex_path)
        if codex in seen:
            continue
        seen.add(codex)
        probe = subprocess.run(
            [codex, "--version"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        if probe.returncode == 0:
            prepend_path = ""
            if not path_codex or Path(path_codex).resolve() != codex_path.resolve():
                prepend_path = str(codex_path.parent)
            return {
                "mode": "real",
                "path": codex,
                "prepend_path": prepend_path,
                "version": (probe.stdout or probe.stderr).strip()[:300],
            }
        failure = (probe.stderr or probe.stdout).strip()[:1000]

    bin_dir = BUILD_DIR / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "codex"
    fake.write_text(
        f"""#!{sys.executable}
from __future__ import annotations

import sys
from pathlib import Path

args = sys.argv[1:]
if "--version" in args:
    print("codex smoke fake 0.0")
    raise SystemExit(0)
if len(args) >= 2 and args[0] == "exec" and "--help" in args:
    print("Usage: codex exec [--ephemeral] [--sandbox <mode>] [--skip-git-repo-check] [--ignore-rules] [--output-last-message <path>]")
    raise SystemExit(0)
if args and args[0] == "exec":
    message = "KIWI_CODEX_BACKED_SHIM_OK"
    if "--output-last-message" in args:
        index = args.index("--output-last-message")
        if index + 1 < len(args):
            Path(args[index + 1]).write_text(message + "\\n", encoding="utf-8")
    print(message)
    raise SystemExit(0)
print("codex smoke fake supports only exec", file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return {
        "mode": "local-fake",
        "path": str(fake),
        "prepend_path": str(bin_dir),
        "reason": failure,
    }


def ensure_backend_python() -> Path:
    override = os.getenv("KIWI_PHASE5_BACKEND_PYTHON", "").strip()
    py313 = shutil.which("python3.13")
    py3 = shutil.which("python3")
    candidates: list[Path | None] = [
        Path(override).expanduser() if override else None,
        ROOT / ".venv" / "bin" / "python",
        VENV_DIR / "bin" / "python",
        Path(sys.executable),
        Path(py313) if py313 else None,
        Path(py3) if py3 else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists() and python_has_module(candidate, "uvicorn"):
            return candidate

    python = Path(shutil.which("python3.13") or sys.executable)
    venv_python = VENV_DIR / "bin" / "python"
    if not venv_python.exists():
        subprocess.run([str(python), "-m", "venv", str(VENV_DIR)], cwd=str(ROOT), check=True)
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(ROOT / "backend" / "requirements.txt")],
        cwd=str(ROOT),
        check=True,
    )
    if not python_has_module(venv_python, "uvicorn"):
        raise AssertionError(f"backend venv did not install uvicorn: {venv_python}")
    return venv_python


def python_has_module(python: Path, module: str) -> bool:
    completed = subprocess.run(
        [str(python), "-c", f"import {module}"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def create_fixture_project(name: str, variant: str) -> Path:
    project = PROJECTS_DIR / name
    (project / "src").mkdir(parents=True, exist_ok=True)
    (project / "README.md").write_text(
        f"# {name}\n\nPhase 5 smoke fixture for KIWI local E2E.\n",
        encoding="utf-8",
    )
    (project / "package.json").write_text(
        json.dumps(
            {
                "name": name,
                "private": True,
                "scripts": {"typecheck": "tsc --noEmit", "build": "echo build"},
                "dependencies": {"typescript": "^5.7.0"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "tsconfig.json").write_text(
        json.dumps({"compilerOptions": {"strict": True, "target": "ES2022"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (project / "src" / "phase5-fixture.ts").write_text(
        "export const phase5Greeting = 'Phase 5 fixture ready';\n",
        encoding="utf-8",
    )
    write_smoke_qwen_skills(project / ".qwen" / "skills")
    write_smoke_qwen_agents(project / ".qwen" / "agents")
    qwen_cmd = project / "qwen.cmd"
    qwen_cmd.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"# KIWI runtime marker: \"{RUNTIME_DIR / 'run-qwen.cmd'}\"\n"
        f"export KIWI_PHASE5_SHIM_VARIANT={shell_quote(variant)}\n"
        f"exec {shell_quote(sys.executable)} {shell_quote(str(ROOT / 'scripts' / 'phase5_qwen_shim.py'))} "
        f"--runtime {shell_quote(str(RUNTIME_DIR))} --project \"$(pwd)\" --variant {shell_quote(variant)}\n",
        encoding="utf-8",
    )
    qwen_cmd.chmod(0o755)
    return project


def initialize_project(base: str, project: Path) -> dict[str, Any]:
    data = api_json(base, "POST", "/api/projects/initialize", {"path": str(project), "extra_notes": "Phase 5 smoke"})
    summary = data["summary"]
    harness = summary.get("qwen_harness", {})
    assert harness.get("status") == "exists", f"qwen harness not accepted for {project}: {harness}"
    return data


def assert_project_info(base: str, project_id: str, evidence: dict[str, Any]) -> None:
    api_json(base, "POST", f"/api/projects/{project_id}/project-info/refresh")
    data = api_json(base, "GET", f"/api/projects/{project_id}/project-info")
    bundle = data["bundle"]
    assert bundle["validation"]["ok"] is True, bundle["validation"]
    assert "project-summary" in bundle["artifacts"], "project-summary artifact missing"
    record(
        evidence,
        "project info ready",
        {
            "schema": bundle["schema_version"],
            "artifact_dir": bundle["artifact_dir"],
            "stale": data["stale"].get("is_stale"),
        },
    )


def assert_fast_prompt_builder(base: str, project_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    marker = "PHASE5_FAST_GENERATED_PROMPT_MARKER_API_TO_CONSOLE"
    run = start_prompt_builder(
        base,
        {
            "project_id": project_id,
            "message": f"Update the fixture greeting in a narrow FAST run. {marker}",
            "work_mode": "fast",
            "history": [],
        },
    )
    prompt = run["final_prompt"]
    lint = run.get("prompt_lint") or {}
    assert run["status"] == "succeeded", run
    assert lint.get("passed") is True, lint
    assert not lint.get("forbidden_terms"), lint
    assert "Activation prefix: `lightwork`" in prompt
    assert "Session work mode: `fast`" in prompt
    assert marker in prompt, "FAST Prompt Builder final_prompt missing strict generated marker"
    assert "Project Info Layer" in prompt
    assert "knowledge/00-index.md" in prompt, "FAST prompt missing central knowledge index reference"
    assert "project-info/project-summary.md" in prompt, "FAST prompt missing central Project Info summary reference"
    for forbidden in ["task_size", "티셔츠", "subagent", "coder-35", "ultrawork", "superpowers", "coder delegation"]:
        assert forbidden not in prompt, f"FAST prompt leaked forbidden term {forbidden!r}"
    assert run["project_info"].get("status") in {"ready", "stale"}, run["project_info"]
    record(
        evidence,
        "fast prompt builder",
        {
            "run_id": run["id"],
            "lint_score": lint.get("score"),
            "final_prompt_chars": len(prompt),
            "project_info_status": run["project_info"].get("status"),
            "generated_prompt_marker": marker,
        },
    )
    run["_phase5_marker"] = marker
    return run


def assert_fast_console_session(base: str, fast_run: dict[str, Any], evidence: dict[str, Any]) -> None:
    project_id = fast_run["project_id"]
    initial_prompt = fast_run["final_prompt"]
    marker = fast_run["_phase5_marker"]
    session = api_json(
        base,
        "POST",
        "/api/ultrawork/sessions",
        {"project_id": project_id, "work_mode": "fast", "initial_prompt": initial_prompt, "cols": 120, "rows": 30},
    )["session"]
    assert session["work_mode"] == "fast", session
    assert session["work_mode_locked"] is True, session
    sse_text = read_sse_until(
        base,
        f"/api/ultrawork/sessions/{session['id']}/events",
        lambda text: "KIWI_SHIM_PROMPT_BEGIN" in text and marker in text,
        timeout=20,
    )
    log_text = wait_file_contains(Path(session["log_path"]), marker, timeout=20)
    assert "lightwork" in log_text, "lightwork activation prefix missing from terminal log"
    assert "Project Info Layer" in log_text, "Project Info context missing from console injection"
    assert marker in log_text, "FAST console did not send generated Prompt Builder final_prompt marker to qwen shim log"
    assert marker in sse_text, "FAST console did not send generated Prompt Builder final_prompt marker to qwen shim SSE"
    error = api_json(
        base,
        "POST",
        f"/api/ultrawork/sessions/{session['id']}/input",
        {"text": "ultrawork\n\ntry to switch mode", "submit": True},
        expected_status=409,
    )
    assert "work mode" in error["__body__"] or "잠겨" in error["__body__"], error
    api_json(base, "POST", f"/api/ultrawork/sessions/{session['id']}/stop")
    record(
        evidence,
        "fast console session",
        {
            "session_id": session["id"],
            "log_path": session["log_path"],
            "sse_contains_generated_marker": marker in sse_text,
            "log_contains_generated_marker": marker in log_text,
            "sent_final_prompt_chars": len(initial_prompt),
            "generated_prompt_marker": marker,
            "mode_switch_status": 409,
        },
    )


def assert_ultrawork_and_superpowers(base: str, project_id: str, evidence: dict[str, Any]) -> None:
    default_builder = start_prompt_builder(
        base,
        {
            "project_id": project_id,
            "message": "non-fast missing size defaults to medium",
            "work_mode": "ultrawork",
            "history": [],
        },
    )
    assert default_builder["task_size"] == "medium", default_builder
    assert "사용자 선택: `medium`" in default_builder["final_prompt"]

    default_console = api_json(
        base,
        "POST",
        "/api/ultrawork/sessions",
        {
            "project_id": project_id,
            "work_mode": "ultrawork",
            "initial_prompt": "ultrawork run without size should default medium",
            "cols": 120,
            "rows": 30,
        },
    )["session"]
    assert default_console["task_size"] == "medium", default_console
    assert default_console["work_mode_prefix"] == "ultrawork_medium", default_console
    api_json(base, "POST", f"/api/ultrawork/sessions/{default_console['id']}/stop")

    ultra_run = start_prompt_builder(
        base,
        {
            "project_id": project_id,
            "message": "Update a fixture across source and verification with medium scope.",
            "work_mode": "ultrawork",
            "task_size": "medium",
            "history": [],
        },
    )
    assert ultra_run["status"] == "succeeded", ultra_run
    assert ultra_run["task_size"] == "medium", ultra_run
    assert ultra_run["selected_task_size"] == "medium", ultra_run
    assert ultra_run["task_size_source"] == "user", ultra_run
    assert ultra_run["ultrawork_mode"] == "balanced", ultra_run
    assert "사용자 선택: `medium`" in ultra_run["final_prompt"]
    assert "최종 source of truth: 사용자 선택값" in ultra_run["final_prompt"]
    assert "medium 모드" in ultra_run["final_prompt"]
    assert "reviewer-35" in ultra_run["final_prompt"]

    super_run = start_prompt_builder(
        base,
        {
            "project_id": project_id,
            "message": "Use superpowers for the same fixture and keep selected size as source of truth.",
            "work_mode": "superpowers",
            "task_size": "medium",
            "history": [],
        },
    )
    assert super_run["status"] == "succeeded", super_run
    assert super_run["task_size"] == "medium", super_run
    assert super_run["selected_task_size"] == "medium", super_run
    assert super_run["task_size_source"] == "user", super_run
    assert super_run["ultrawork_mode"] == "balanced", super_run
    assert "## superpowers skill-first 계약" in super_run["final_prompt"]
    assert "selected task_size `medium` is the source of truth" in super_run["final_prompt"]

    session = api_json(
        base,
        "POST",
        "/api/ultrawork/sessions",
        {
            "project_id": project_id,
            "work_mode": "superpowers",
            "initial_prompt": super_run["final_prompt"],
            "task_size": "medium",
            "task_size_reason": "Phase 5 smoke selected medium.",
            "cols": 120,
            "rows": 30,
        },
    )["session"]
    sse_text = read_sse_until(
        base,
        f"/api/ultrawork/sessions/{session['id']}/events",
        lambda text: "Phase 5 shim received console prompt" in text and "superpowers skill-first 계약" in text,
        timeout=25,
    )
    log_text = wait_file_contains(Path(session["log_path"]), "superpowers skill-first 계약", timeout=20)
    assert "사용자 선택: `medium`" in log_text
    assert "PreToolUse" in sse_text
    assert "subagent_type" in sse_text and "description" in sse_text and "prompt" in sse_text
    api_json(base, "POST", f"/api/ultrawork/sessions/{session['id']}/stop")
    record(
        evidence,
        "ultrawork and superpowers",
        {
            "default_builder_status": "succeeded",
            "default_builder_task_size": default_builder["task_size"],
            "default_console_task_size": default_console["task_size"],
            "ultrawork_run_id": ultra_run["id"],
            "superpowers_run_id": super_run["id"],
            "superpowers_session_id": session["id"],
            "team_event_api_fields": ["subagent_type", "description", "prompt"],
        },
    )


def assert_codex_backed_shim(base: str, project_id: str, project: Path, evidence: dict[str, Any]) -> None:
    session = api_json(
        base,
        "POST",
        "/api/ultrawork/sessions",
        {
            "project_id": project_id,
            "work_mode": "fast",
            "initial_prompt": "Codex-backed shim must call gpt-5.4-mini exactly once.",
            "cols": 120,
            "rows": 30,
        },
    )["session"]
    read_sse_until(
        base,
        f"/api/ultrawork/sessions/{session['id']}/events",
        lambda text: "KIWI_CODEX_BACKED_SHIM_OK" in text,
        timeout=220,
    )
    log_text = wait_file_contains(Path(session["log_path"]), "KIWI_CODEX_BACKED_SHIM_OK", timeout=220)
    codex_log = project / ".kiwi-shim" / "codex-call.json"
    codex_text = wait_file_contains(codex_log, "gpt-5.4-mini", timeout=5)
    codex_records = [json.loads(line) for line in codex_text.splitlines() if line.strip()]
    assert len(codex_records) == 1, codex_records
    record_data = codex_records[0]
    assert record_data["returncode"] == 0, record_data
    assert "KIWI_CODEX_BACKED_SHIM_OK" in record_data.get("last_message", "") or "KIWI_CODEX_BACKED_SHIM_OK" in log_text
    command = record_data["command"]
    assert any(item == "gpt-5.4-mini" for item in command), command
    assert "--sandbox" in command and "read-only" in command, command
    assert "--skip-git-repo-check" in command, command
    assert "--ignore-rules" in command, command
    if record_data.get("help_supports_ephemeral"):
        assert "--ephemeral" in command, "codex exec supports --ephemeral but shim command omitted it"
    api_json(base, "POST", f"/api/ultrawork/sessions/{session['id']}/stop")
    record(
        evidence,
        "codex backed shim",
        {
            "session_id": session["id"],
            "log_path": session["log_path"],
            "codex_log": str(codex_log),
            "codex_last_message": record_data.get("last_message", "")[:300],
            "codex_command": command,
            "codex_help_supports_ephemeral": bool(record_data.get("help_supports_ephemeral")),
            "codex_command_has_ephemeral": "--ephemeral" in command,
        },
    )


def assert_dom_smoke(web_base: str, evidence: dict[str, Any]) -> None:
    chrome = find_chrome()
    if not chrome:
        raise AssertionError("DOM smoke requires Chrome or Chromium executable; none found")
    profile_dir = BUILD_DIR / "chrome-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    node = shutil.which("node")
    if not node:
        raise AssertionError("DOM smoke requires node for Chrome DevTools Protocol driver")
    driver = BUILD_DIR / "dom-smoke.mjs"
    driver.write_text(DOM_SMOKE_DRIVER, encoding="utf-8")
    port = free_port()
    env = os.environ.copy()
    env.update(
        {
            "KIWI_DOM_CHROME": chrome,
            "KIWI_DOM_URL": web_base,
            "KIWI_DOM_PORT": str(port),
            "KIWI_DOM_PROFILE": str(profile_dir),
        }
    )
    completed = subprocess.run(
        [node, str(driver)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"DOM smoke failed: stdout={completed.stdout[-1000:]} stderr={completed.stderr[-2000:]}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"DOM smoke did not return JSON: {completed.stdout[-2000:]}") from exc
    dom_text = str(payload.get("innerText") or "")
    required = ["FAST", "프롬프트", "확장하기", "타임라인", "티셔츠 사이즈", "런타임 정보", "ultrawork", "superpowers"]
    missing = [item for item in required if item not in dom_text]
    assert not missing, f"DOM smoke missing rendered UI text: {missing}"
    layout = payload.get("layout") or {}
    initial = layout.get("initial") or {}
    focused = layout.get("focused") or {}
    focus_samples = layout.get("focusSamples") or []
    focus_skipped = bool(layout.get("focusSkipped"))
    assert initial.get("pageOverflow") == 0, f"initial page overflow detected: {initial}"
    assert focused.get("pageOverflow") == 0, f"terminal focus page overflow detected: {focused}"
    assert focus_samples, f"DOM smoke must collect focus stability samples: {layout}"
    max_xterm_horizontal_overflow = 12
    for sample in focus_samples:
        assert sample.get("pageOverflow") == 0, f"page overflow toggled during focus: {focus_samples}"
        assert sample.get("viewportOverflowY") == initial.get("viewportOverflowY"), (
            f"xterm viewport overflow mode toggled during focus: {focus_samples}"
        )
        assert sample.get("panelH") == initial.get("panelH"), f"terminal panel height changed during focus: {focus_samples}"
        assert sample.get("screenW", 0) <= sample.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm screen overflow during focus: {sample}"
        assert sample.get("rowsW", 0) <= sample.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm rows overflow during focus: {sample}"
        assert sample.get("screenH", 0) <= sample.get("viewportH", 0) + 1, f"xterm screen height overflow during focus: {sample}"
    if not focus_skipped:
        stable_samples = focus_samples[3:]
        for key in ("termH", "viewportH", "screenH", "cmdH", "inputH"):
            values = [float(sample.get(key) or 0) for sample in stable_samples]
            assert max(values) - min(values) <= 0.75, f"{key} jittered during focus: {focus_samples}"
    assert initial.get("commandBarExists") is True, f"bottom command bar must be restored: {initial}"
    assert focused.get("commandBarExists") is True, f"bottom command bar must stay restored: {focused}"
    assert 58 <= initial.get("cmdH", 0) <= 90, f"command bar default height must stay compact: {layout}"
    assert 22 <= initial.get("inputH", 0) <= 50, f"command input default height must stay compact: {layout}"
    assert initial.get("inputReadOnly") is False, f"command input should use disabled, not readonly: {initial}"
    if focus_skipped:
        assert initial.get("inputDisabled") is True, f"focus smoke may only be skipped for disabled command input: {layout}"
    else:
        assert focused.get("cmdH", 0) > initial.get("cmdH", 0) + 80, f"command bar must expand on focus: {layout}"
        assert focused.get("inputH", 0) >= 150, f"command input must expand on focus: {layout}"
    assert initial.get("panelH") == focused.get("panelH"), f"terminal panel total height changed across focus: {layout}"
    if not focus_skipped:
        assert focused.get("termH", 0) < initial.get("termH", 0), f"terminal must shrink when command input expands: {layout}"
    assert focused.get("viewportOverflowY") == initial.get("viewportOverflowY"), f"xterm viewport overflow mode must not toggle: {layout}"
    assert initial.get("screenH", 0) <= initial.get("viewportH", 0) + 1, f"xterm screen must fit viewport before focus: {initial}"
    assert focused.get("screenH", 0) <= focused.get("viewportH", 0) + 1, f"xterm screen must fit viewport: {focused}"
    assert initial.get("screenW", 0) <= initial.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm screen must stay within padded viewport before focus: {initial}"
    assert focused.get("screenW", 0) <= focused.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm screen must stay within padded viewport: {focused}"
    assert initial.get("rowsW", 0) <= initial.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm rows must stay within padded viewport before focus: {initial}"
    assert focused.get("rowsW", 0) <= focused.get("viewportW", 0) + max_xterm_horizontal_overflow, f"xterm rows must stay within padded viewport: {focused}"
    record(
        evidence,
        "dom smoke",
        {
            "url": web_base,
            "chrome": chrome,
            "driver": "chrome-devtools-protocol",
            "checked_text": required,
            "inner_text_chars": len(dom_text),
            "terminal_layout": layout,
        },
    )


def find_chrome() -> str:
    candidates = [
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return ""


DOM_SMOKE_DRIVER = r"""
import { spawn } from "node:child_process";

const chrome = process.env.KIWI_DOM_CHROME;
const url = process.env.KIWI_DOM_URL;
const port = process.env.KIWI_DOM_PORT;
const profile = process.env.KIWI_DOM_PROFILE;

if (!chrome || !url || !port || !profile) {
  throw new Error("missing DOM smoke environment");
}

const child = spawn(chrome, [
  "--headless=new",
  "--window-size=1920,1080",
  "--disable-gpu",
  "--no-sandbox",
  "--disable-dev-shm-usage",
  `--user-data-dir=${profile}`,
  `--remote-debugging-port=${port}`,
  url
], { stdio: ["ignore", "pipe", "pipe"] });

let stderr = "";
child.stderr.on("data", (chunk) => {
  stderr += chunk.toString();
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getJson(path) {
  const response = await fetch(`http://127.0.0.1:${port}${path}`);
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return await response.json();
}

async function waitForPage() {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    try {
      const pages = await getJson("/json/list");
      const page = pages.find((item) => item.type === "page" && item.webSocketDebuggerUrl);
      if (page) {
        return page;
      }
    } catch {
      // Chrome is still starting.
    }
    await sleep(250);
  }
  throw new Error(`Chrome DevTools page not ready: ${stderr.slice(-1000)}`);
}

function cdpRequest(socket, method, params = {}) {
  const id = cdpRequest.nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    const onMessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id !== id) {
        return;
      }
      socket.removeEventListener("message", onMessage);
      if (data.error) {
        reject(new Error(JSON.stringify(data.error)));
      } else {
        resolve(data.result || {});
      }
    };
    socket.addEventListener("message", onMessage);
  });
}
cdpRequest.nextId = 1;

try {
  const page = await waitForPage();
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  const innerText = await evaluateInnerText(socket);
  const layout = await evaluateTerminalLayout(socket);
  console.log(JSON.stringify({ innerText, layout }));
  socket.close();
} finally {
  child.kill("SIGTERM");
  setTimeout(() => child.kill("SIGKILL"), 1000).unref();
}

async function evaluateValue(socket, expression) {
  const result = await cdpRequest(socket, "Runtime.evaluate", {
    expression,
    returnByValue: true
  });
  return result.result?.value;
}

async function evaluateTerminalLayout(socket) {
  const expression = `(() => {
    const q = (selector) => document.querySelector(selector);
    const height = (selector) => {
      const node = q(selector);
      return node ? Math.round(node.getBoundingClientRect().height * 100) / 100 : null;
    };
    const width = (selector) => {
      const node = q(selector);
      return node ? Math.round(node.getBoundingClientRect().width * 100) / 100 : null;
    };
    const html = document.documentElement;
    const body = document.body;
    const viewport = q('.terminal.console-terminal .xterm-viewport');
    const screen = q('.terminal.console-terminal .xterm-screen');
    const rows = q('.terminal.console-terminal .xterm-rows');
    const command = q('.terminal-command-bar');
    const input = q('.command-bar-input');
    return {
      pageOverflow: Math.max(0, html.scrollHeight - html.clientHeight, body.scrollHeight - body.clientHeight),
      termH: height('.terminal.console-terminal'),
      termW: width('.terminal.console-terminal'),
      viewportH: height('.terminal.console-terminal .xterm-viewport'),
      viewportW: width('.terminal.console-terminal .xterm-viewport'),
      screenH: height('.terminal.console-terminal .xterm-screen'),
      screenW: width('.terminal.console-terminal .xterm-screen'),
      rowsW: width('.terminal.console-terminal .xterm-rows'),
      panelH: height('.terminal-panel'),
      areaH: height('.terminal-area'),
      cmdH: height('.terminal-command-bar'),
      inputH: height('.command-bar-input'),
      commandBarExists: Boolean(command),
      viewportOverflowY: viewport ? getComputedStyle(viewport).overflowY : null,
      viewportScrollbarWidth: viewport ? getComputedStyle(viewport).scrollbarWidth : null,
      screenOverflow: screen && viewport ? Math.round((screen.getBoundingClientRect().height - viewport.getBoundingClientRect().height) * 100) / 100 : null,
      screenOverflowX: screen && viewport ? Math.round((screen.getBoundingClientRect().width - viewport.getBoundingClientRect().width) * 100) / 100 : null,
      rowsOverflowX: rows && viewport ? Math.round((rows.getBoundingClientRect().width - viewport.getBoundingClientRect().width) * 100) / 100 : null,
      inputDisabled: input ? input.disabled : null,
      inputReadOnly: input ? input.readOnly : null,
      active: document.activeElement?.className || document.activeElement?.tagName
    };
  })()`;
  const initial = await evaluateValue(socket, expression);
  if (initial.inputDisabled) {
    return { initial, focused: initial, focusSamples: [initial], focusSkipped: true };
  }
  await cdpRequest(socket, "Runtime.evaluate", {
    expression: "document.querySelector('.command-bar-input')?.focus()",
    returnByValue: true
  });
  const focusSamples = [];
  for (let index = 0; index < 20; index += 1) {
    await sleep(16);
    focusSamples.push(await evaluateValue(socket, expression));
  }
  const focused = focusSamples[focusSamples.length - 1];
  return { initial, focused, focusSamples };
}

async function evaluateInnerText(socket) {
  let lastError = "";
  for (let attempt = 0; attempt < 20; attempt++) {
    try {
      const result = await cdpRequest(socket, "Runtime.evaluate", {
        expression: "document.body ? document.body.innerText : ''",
        returnByValue: true
      });
      const value = result.result?.value || "";
      if (value.trim()) {
        return value;
      }
    } catch (error) {
      lastError = String(error?.message || error);
    }
    await sleep(500);
  }
  throw new Error(`DOM text did not stabilize: ${lastError}`);
}
""".strip()


def assert_static_frontend_contracts(evidence: dict[str, Any]) -> None:
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    required = [
        'prefix: "lightwork"',
        'mode: "balanced"',
        "explorer-35, 구현 agent, architect-35, reviewer-35",
        "summarizeToolInput",
        "formatTeamEventTitle",
        "formatTeamEventSummary",
        "subagent_type",
        "description",
        "prompt",
        "command",
    ]
    missing = [item for item in required if item not in page]
    assert not missing, f"frontend timeline/team contract strings missing: {missing}"
    record(evidence, "frontend contracts", {"checked_strings": required})


def assert_windows_package_sources(evidence: dict[str, Any]) -> None:
    doc = ROOT / "docs" / "windows-qwencode-validation.md"
    collector = ROOT / "scripts" / "collect-windows-validation-evidence.py"
    assert doc.exists(), "docs/windows-qwencode-validation.md is missing"
    assert collector.exists(), "scripts/collect-windows-validation-evidence.py is missing"
    doc_text = doc.read_text(encoding="utf-8")
    collector_text = collector.read_text(encoding="utf-8")
    for token in [
        r"D:\aiops\qwencode",
        "qwen-init",
        "qwen.cmd",
        "lightwork",
        "ultrawork",
        "superpowers",
        "Project Info",
        "team-events.jsonl",
        "kiwi-offline-win11-py313.zip",
    ]:
        assert token in doc_text, f"Windows validation doc missing {token}"
    assert "collect-windows-validation-evidence" in collector_text
    record(evidence, "windows validation package sources", {"doc": str(doc), "collector": str(collector)})


def start_prompt_builder(base: str, payload: dict[str, Any]) -> dict[str, Any]:
    created = api_json(base, "POST", "/api/prompt-builder/runs", payload)
    run_id = created["run"]["id"]
    return wait_for(
        f"prompt builder {run_id}",
        lambda: api_json(base, "GET", f"/api/prompt-builder/runs/{run_id}")["run"],
        lambda run: run["status"] != "running",
        timeout=60,
    )


def api_json(
    base: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
        if status != expected_status:
            raise AssertionError(f"{method} {path} returned {status}, expected {expected_status}: {raw}") from exc
        return {"__status__": status, "__body__": raw}
    if status != expected_status:
        raise AssertionError(f"{method} {path} returned {status}, expected {expected_status}: {raw}")
    return json.loads(raw) if raw else {}


def read_sse_until(base: str, path: str, predicate: Callable[[str], bool], timeout: float) -> str:
    request = urllib.request.Request(f"{base}{path}", method="GET")
    deadline = time.time() + timeout
    collected = ""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while time.time() < deadline:
            try:
                line = response.readline().decode("utf-8", errors="replace")
            except (TimeoutError, socket.timeout, OSError):
                break
            if not line:
                break
            collected += line
            if predicate(collected):
                return collected
    raise AssertionError(f"SSE predicate not satisfied for {path}; collected tail={collected[-2000:]}")


def wait_file_contains(path: Path, needle: str, timeout: float) -> str:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        if path.exists():
            last = path.read_text(encoding="utf-8", errors="replace")
            if needle in last:
                return last
        time.sleep(0.25)
    raise AssertionError(f"{path} did not contain {needle!r}; tail={last[-2000:]}")


def wait_http_ok(url: str, label: str, timeout: float = 45) -> None:
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise AssertionError(f"{label} endpoint not ready at {url}: {last_error}")


def wait_for(
    label: str,
    getter: Callable[[], dict[str, Any]],
    done: Callable[[dict[str, Any]], bool],
    timeout: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = getter()
        if done(last):
            return last
        time.sleep(0.5)
    raise AssertionError(f"{label} did not finish before timeout: {last}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def record(evidence: dict[str, Any], name: str, data: dict[str, Any]) -> None:
    evidence["checks"].append({"name": name, "data": data})


if __name__ == "__main__":
    raise SystemExit(main())
