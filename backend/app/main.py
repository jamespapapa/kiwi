from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent_runtime import KiwiAgentRuntime
from .coder_runner import CoderRunManager
from .config import get_internal_settings, get_public_settings, update_settings
from .db import connect, init_db, json_dumps, json_loads, now_iso, row_to_dict
from .models import (
    CancelRunResponse,
    ChatRequest,
    CoderRunRequest,
    FolderPickResponse,
    PromptBuilderRequest,
    ProjectInitializeRequest,
    PublicSettings,
    SessionCreateRequest,
    SettingsUpdate,
    UltraworkInputRequest,
    UltraworkResizeRequest,
    UltraworkSessionStartRequest,
)
from .project_analyzer import analyze_project, load_project_context, write_initial_kiwi
from .prompt_builder import PromptBuilderManager
from .qwen_client import QwenClient, _chat_endpoint
from .qwencode_runtime import (
    find_latest_qwencode_runtime,
    find_project_qwen_command,
    resolve_project_qwen_runtime,
    resolve_qwen_init_command,
)
from .security import normalize_existing_dir
from .ultrawork_console import UltraworkConsoleManager


app = FastAPI(title="KIWI Local Agent Runtime")
runner = CoderRunManager()
console = UltraworkConsoleManager()
prompt_builder = PromptBuilderManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await console.stop_all()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/diagnostics/llm")
async def diagnose_llm(target: str = "orchestrator") -> dict[str, Any]:
    settings = get_internal_settings()
    if target == "coder":
        base_url = settings.coder_api_base_url
        model = settings.coder_model
    else:
        base_url = settings.api_base_url
        model = settings.orchestrator_model
        target = "orchestrator"

    diagnostic_settings = settings.model_copy(
        update={
            "api_base_url": base_url,
            "orchestrator_model": model,
            "api_key": "sk-local-coder" if target == "coder" else "sk-local-qwen35",
        }
    )
    endpoint = _chat_endpoint(base_url)
    started = time.perf_counter()
    try:
        content = await QwenClient(diagnostic_settings).chat(
            [
                {"role": "system", "content": "Reply with exactly: KIWI_OK"},
                {"role": "user", "content": "ping"},
            ],
            model=model,
            temperature=0,
            max_tokens=32,
        )
        return {
            "ok": True,
            "target": target,
            "endpoint": endpoint,
            "model": model,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "sample": content[:500],
        }
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "target": target,
            "endpoint": endpoint,
            "model": model,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error_type": "http_status",
            "status_code": exc.response.status_code,
            "response_body": exc.response.text[:2000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "target": target,
            "endpoint": endpoint,
            "model": model,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


@app.get("/api/settings", response_model=PublicSettings)
def read_settings() -> PublicSettings:
    return get_public_settings()


@app.put("/api/settings", response_model=PublicSettings)
def save_settings(payload: SettingsUpdate) -> PublicSettings:
    return update_settings(payload)


@app.post("/api/folders/pick", response_model=FolderPickResponse)
async def pick_folder() -> FolderPickResponse:
    return await asyncio.to_thread(_pick_folder_dialog)


@app.post("/api/projects/initialize")
def initialize_project(payload: ProjectInitializeRequest) -> dict[str, Any]:
    root = normalize_existing_dir(payload.path)
    summary = analyze_project(root)
    write_initial_kiwi(root, summary, payload.extra_notes)
    summary["qwen_harness"] = _ensure_qwen_project_harness(root)
    summary["runtime_checks"] = _collect_runtime_checks(root, summary["qwen_harness"])
    project_id = _upsert_project(root, summary)
    return {"project": _get_project(project_id), "summary": summary}


@app.get("/api/projects")
def list_projects() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    return [_project_from_row(row) for row in rows]


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return _require_project(project_id)


@app.get("/api/projects/{project_id}/kiwi")
def get_project_kiwi(project_id: str) -> dict[str, str]:
    project = _require_project(project_id)
    path = Path(project["root_path"]) / "KIWI.md"
    if not path.exists():
        return {"content": ""}
    return {"content": path.read_text(encoding="utf-8", errors="ignore")}


@app.post("/api/sessions")
def create_session(payload: SessionCreateRequest) -> dict[str, Any]:
    _require_project(payload.project_id)
    session_id = str(uuid.uuid4())
    created_at = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions(id, project_id, title, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (session_id, payload.project_id, payload.title, created_at, created_at),
        )
    return _require_session(session_id)


@app.get("/api/sessions")
def list_sessions(project_id: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_sessions WHERE project_id = ? ORDER BY updated_at DESC",
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/sessions/{session_id}/messages")
def list_messages(session_id: str) -> list[dict[str, Any]]:
    _require_session(session_id)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [_message_from_row(row) for row in rows]


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> dict[str, Any]:
    project = _require_project(payload.project_id)
    _require_session(payload.session_id)
    settings = get_internal_settings()
    history = _recent_history(payload.session_id)
    _insert_message(payload.session_id, "user", payload.message, {})

    context = load_project_context(Path(project["root_path"]), settings.max_context_chars)
    runtime = KiwiAgentRuntime(QwenClient(settings))
    try:
        result = await runtime.run(
            payload.message,
            context,
            history,
            dangerous_mode=settings.dangerous_mode,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Qwen API 오류: "
                f"endpoint={exc.request.url} "
                f"model={settings.orchestrator_model} "
                f"status={exc.response.status_code} "
                f"body={exc.response.text[:1000]}"
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qwen 호출 실패: {exc}") from exc

    metadata: dict[str, Any] = {
        "decision": result.get("decision", {}),
        "approval_required": result.get("approval_required", False),
    }
    response = result.get("response", "").strip() or "처리 결과가 비어 있습니다."
    coder_prompt = result.get("pending_coder_prompt")

    if coder_prompt:
        if settings.dangerous_mode:
            run = await runner.start_run(payload.session_id, project, coder_prompt)
            metadata["coder_run_id"] = run["id"]
        else:
            metadata["pending_action"] = {"type": "qwencode", "prompt": coder_prompt}

    assistant_message = _insert_message(payload.session_id, "assistant", response, metadata)
    _touch_session(payload.session_id)
    return {
        "message": assistant_message,
        "metadata": metadata,
    }


@app.post("/api/coder-runs")
async def start_coder_run(payload: CoderRunRequest) -> dict[str, Any]:
    project = _require_project(payload.project_id)
    _require_session(payload.session_id)
    run = await runner.start_run(payload.session_id, project, payload.prompt)
    _insert_message(
        payload.session_id,
        "assistant",
        "승인에 따라 qwencode 실행을 시작했습니다.",
        {"type": "coder_run_started", "coder_run_id": run["id"]},
    )
    _touch_session(payload.session_id)
    return {"run": run}


@app.post("/api/prompt-builder/runs")
async def start_prompt_builder_run(payload: PromptBuilderRequest) -> dict[str, Any]:
    project = _require_project(payload.project_id)
    history = [item.model_dump() for item in payload.history][-12:]
    run = await prompt_builder.start_run(project, payload.message, history)
    return {"run": run}


@app.get("/api/prompt-builder/runs/{run_id}")
def get_prompt_builder_run(run_id: str) -> dict[str, Any]:
    run = prompt_builder.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="프롬프트 빌더 실행을 찾을 수 없습니다.")
    return {"run": run}


@app.get("/api/prompt-builder/runs/{run_id}/events")
async def prompt_builder_events(run_id: str) -> StreamingResponse:
    if not prompt_builder.get_run(run_id):
        raise HTTPException(status_code=404, detail="프롬프트 빌더 실행을 찾을 수 없습니다.")

    async def generate() -> Any:
        async for event in prompt_builder.stream_events(run_id):
            yield f"event: {event.get('type', 'message')}\n"
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/coder-runs/{run_id}")
def get_coder_run(run_id: str) -> dict[str, Any]:
    run = runner.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="coder run을 찾을 수 없습니다.")
    return run


@app.get("/api/coder-runs/{run_id}/events")
async def coder_run_events(run_id: str) -> StreamingResponse:
    if not runner.get_run(run_id):
        raise HTTPException(status_code=404, detail="coder run을 찾을 수 없습니다.")

    async def generate() -> Any:
        async for event in runner.stream_events(run_id):
            yield f"event: {event.get('type', 'message')}\n"
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/coder-runs/{run_id}/cancel", response_model=CancelRunResponse)
async def cancel_coder_run(run_id: str) -> CancelRunResponse:
    return CancelRunResponse(cancelled=await runner.cancel_run(run_id))


@app.post("/api/ultrawork/sessions")
async def start_ultrawork_session(payload: UltraworkSessionStartRequest) -> dict[str, Any]:
    project = _require_project(payload.project_id)
    session = await console.start_session(
        project,
        initial_prompt=payload.initial_prompt,
        cols=payload.cols,
        rows=payload.rows,
    )
    return {"session": session}


@app.get("/api/ultrawork/sessions/{session_id}")
def get_ultrawork_session(session_id: str) -> dict[str, Any]:
    session = console.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Ultrawork 콘솔 세션을 찾을 수 없습니다.")
    return {"session": session}


@app.post("/api/ultrawork/sessions/{session_id}/input")
async def send_ultrawork_input(session_id: str, payload: UltraworkInputRequest) -> dict[str, Any]:
    return await console.send_input(
        session_id,
        payload.text,
        submit=payload.submit,
        bracketed_paste=payload.bracketed_paste,
    )


@app.post("/api/ultrawork/sessions/{session_id}/resize")
async def resize_ultrawork_session(session_id: str, payload: UltraworkResizeRequest) -> dict[str, Any]:
    return await console.resize_session(session_id, cols=payload.cols, rows=payload.rows)


@app.post("/api/ultrawork/sessions/{session_id}/stop")
async def stop_ultrawork_session(session_id: str) -> dict[str, Any]:
    return {"session": await console.stop_session(session_id)}


@app.get("/api/ultrawork/sessions/{session_id}/events")
async def ultrawork_session_events(session_id: str) -> StreamingResponse:
    if not console.get_session(session_id):
        raise HTTPException(status_code=404, detail="Ultrawork 콘솔 세션을 찾을 수 없습니다.")

    async def generate() -> Any:
        async for event in console.stream_events(session_id):
            yield f"event: {event.get('type', 'message')}\n"
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _pick_folder_dialog() -> FolderPickResponse:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="KIWI 프로젝트 폴더 선택")
        root.destroy()
        if not selected:
            return FolderPickResponse(cancelled=True)
        return FolderPickResponse(path=str(Path(selected).resolve()))
    except Exception as exc:
        platform_hint = "Windows 로컬 데스크톱 세션에서 실행 중인지 확인하세요." if sys.platform == "win32" else ""
        return FolderPickResponse(error=f"OS 폴더 피커를 열 수 없습니다. {platform_hint} {exc}".strip())


def _ensure_qwen_project_harness(root: Path) -> dict[str, Any]:
    existing = find_project_qwen_command(root)
    preferred_runtime = find_latest_qwencode_runtime()
    project_runtime = resolve_project_qwen_runtime(root) if existing else None
    runtime_mismatch = bool(
        existing
        and project_runtime
        and preferred_runtime
        and project_runtime.resolve() != preferred_runtime.resolve()
    )
    if existing and not runtime_mismatch:
        return {
            "status": "exists",
            "command": str(existing),
            "project_runtime_dir": str(project_runtime) if project_runtime else None,
            "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
        }

    command = resolve_qwen_init_command()
    if not command:
        return {
            "status": "skipped",
            "reason": "qwen-init.cmd not found",
            "project_command": str(existing) if existing else None,
            "project_runtime_dir": str(project_runtime) if project_runtime else None,
            "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
        }

    if os.name != "nt":
        return {
            "status": "mismatch" if runtime_mismatch else "skipped",
            "reason": (
                "프로젝트 qwen.cmd 런타임이 현재 우선 런타임과 다릅니다. "
                "Windows 폐쇄망에서 프로젝트 초기화를 다시 실행하면 qwen-init이 하네스를 재생성합니다."
                if runtime_mismatch
                else "qwen-init.cmd is Windows-only; it will run during Windows offline initialization."
            ),
            "command": command,
            "project_command": str(existing) if existing else None,
            "project_runtime_dir": str(project_runtime) if project_runtime else None,
            "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
        }

    try:
        completed = subprocess.run(
            [*command, str(root)],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "command": command}

    project_command = find_project_qwen_command(root)
    succeeded = completed.returncode == 0 and project_command
    return {
        "status": ("reset" if runtime_mismatch else "succeeded") if succeeded else "failed",
        "exit_code": completed.returncode,
        "command": command,
        "project_command": str(project_command) if project_command else None,
        "previous_project_command": str(existing) if existing else None,
        "previous_project_runtime_dir": str(project_runtime) if project_runtime else None,
        "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _collect_runtime_checks(root: Path, qwen_harness: dict[str, Any]) -> dict[str, Any]:
    qwen_init_command = resolve_qwen_init_command()
    project_command = find_project_qwen_command(root)
    project_qwen_runtime = resolve_project_qwen_runtime(root)
    preferred_qwen_runtime = find_latest_qwencode_runtime()
    qwen_runtime = project_qwen_runtime or preferred_qwen_runtime
    runtime_mismatch = bool(
        project_qwen_runtime
        and preferred_qwen_runtime
        and project_qwen_runtime.resolve() != preferred_qwen_runtime.resolve()
    )
    node_executable = _find_qwen_node(qwen_runtime) or _which_runtime_executable("node", ["node.exe", "node"])

    items = [
        _run_version_check("Java", _which_runtime_executable("java", ["java.exe", "java"]), ["-version"], root),
        _run_version_check("Python", Path(sys.executable), ["--version"], root),
        _run_version_check("Node", node_executable, ["--version"], root),
        _run_version_check("Maven", _which_runtime_executable("mvn", ["mvn.cmd", "mvn.bat", "mvn.exe", "mvn"]), ["-version"], root),
    ]

    return {
        "checked_at": now_iso(),
        "cwd": str(root),
        "items": items,
        "qwen": {
            "harness_status": qwen_harness.get("status"),
            "harness_reason": qwen_harness.get("reason") or qwen_harness.get("error"),
            "qwen_init_command": _command_display(qwen_init_command),
            "qwen_init_available": bool(qwen_init_command),
            "project_command": str(project_command) if project_command else None,
            "project_command_exists": bool(project_command),
            "runtime_dir": str(qwen_runtime) if qwen_runtime else None,
            "project_runtime_dir": str(project_qwen_runtime) if project_qwen_runtime else None,
            "preferred_runtime_dir": str(preferred_qwen_runtime) if preferred_qwen_runtime else None,
            "runtime_mismatch": runtime_mismatch,
        },
    }


def _find_qwen_node(qwen_runtime: Path | None) -> Path | None:
    if qwen_runtime is None:
        return None
    for candidate in [
        qwen_runtime / "node" / "node.exe",
        qwen_runtime / "node" / "node",
        qwen_runtime / "node.exe",
        qwen_runtime / "node",
    ]:
        if candidate.exists():
            return candidate
    return None


def _which_runtime_executable(name: str, variants: list[str]) -> Path | None:
    for candidate in [name, *variants]:
        resolved = shutil.which(candidate)
        if resolved:
            return Path(resolved)
    return None


def _run_version_check(label: str, executable: Path | None, args: list[str], root: Path) -> dict[str, Any]:
    if executable is None:
        return {
            "name": label,
            "status": "missing",
            "version": None,
            "detail": "PATH에서 실행 파일을 찾지 못했습니다.",
            "command": None,
            "path": None,
            "exit_code": None,
        }

    command = _version_command(executable, args)
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=18,
            check=False,
        )
    except Exception as exc:
        return {
            "name": label,
            "status": "failed",
            "version": None,
            "detail": str(exc),
            "command": _command_display(command),
            "path": str(executable),
            "exit_code": None,
        }

    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip())
    return {
        "name": label,
        "status": "ok" if completed.returncode == 0 else "failed",
        "version": _first_output_line(output),
        "detail": output[:1200],
        "command": _command_display(command),
        "path": str(executable),
        "exit_code": completed.returncode,
    }


def _version_command(executable: Path, args: list[str]) -> list[str]:
    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", str(executable), *args]
    return [str(executable), *args]


def _first_output_line(output: str) -> str | None:
    for line in output.splitlines():
        text = line.strip()
        if text:
            return text[:240]
    return None


def _command_display(command: list[str] | None) -> str | None:
    if not command:
        return None
    return " ".join(str(part) for part in command)


def _upsert_project(root: Path, summary: dict[str, Any]) -> str:
    existing = None
    with connect() as conn:
        existing = conn.execute("SELECT id FROM projects WHERE root_path = ?", (str(root),)).fetchone()
        project_id = existing["id"] if existing else str(uuid.uuid4())
        timestamp = now_iso()
        conn.execute(
            """
            INSERT INTO projects(id, name, root_path, summary_json, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(root_path) DO UPDATE SET
                name=excluded.name,
                summary_json=excluded.summary_json,
                updated_at=excluded.updated_at
            """,
            (
                project_id,
                summary["name"],
                str(root),
                json_dumps(summary),
                timestamp,
                timestamp,
            ),
        )
    return project_id


def _get_project(project_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return _project_from_row(row) if row else None


def _require_project(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")
    root = Path(project["root_path"])
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=400, detail="프로젝트 루트가 더 이상 존재하지 않습니다.")
    return project


def _project_from_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["summary"] = json_loads(data.pop("summary_json"), {})
    return data


def _require_session(session_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    session = row_to_dict(row)
    if not session:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")
    return session


def _insert_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    message_id = str(uuid.uuid4())
    created_at = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages(id, session_id, role, content, metadata_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (message_id, session_id, role, content, json_dumps(metadata), created_at),
        )
    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata,
        "created_at": created_at,
    }


def _message_from_row(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = json_loads(data.pop("metadata_json"), {})
    return data


def _recent_history(session_id: str, limit: int = 24) -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _touch_session(session_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (now_iso(), session_id))
