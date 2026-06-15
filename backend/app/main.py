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
from .project_info import (
    analyze_project_info,
    collect_project_info_stale_inputs,
    load_project_info_bundle,
    project_info_artifact_dir,
)
from .project_runtime import collect_project_runtime, launch_project_runtime_action
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
from .work_modes import normalize_work_mode


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


def validate_prompt_builder_task_size(work_mode: str, task_size: str | None) -> None:
    normalized = normalize_work_mode(work_mode)
    if normalized == "fast":
        if task_size:
            raise HTTPException(status_code=422, detail="FAST/lightwork Prompt Builder request must not include task_size.")
    return


def validate_initial_prompt_task_size(work_mode: str, initial_prompt: str | None, task_size: str | None) -> None:
    normalized = normalize_work_mode(work_mode)
    if normalized == "fast":
        if task_size:
            raise HTTPException(status_code=422, detail="FAST/lightwork initial_prompt request must not include task_size.")
        return
    return


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
    summary["project_info"] = _project_info_initialize_status(root)
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


@app.get("/api/projects/{project_id}/project-info")
def get_project_info(project_id: str) -> dict[str, Any]:
    project = _require_project(project_id)
    root = Path(project["root_path"])
    bundle = load_project_info_bundle(root)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Project Info Layer 산출물이 없습니다. 프로젝트 초기화 또는 refresh를 먼저 실행하세요.")
    return {"bundle": bundle, "stale": collect_project_info_stale_inputs(root, bundle)}


@app.post("/api/projects/{project_id}/project-info/refresh")
def refresh_project_info(project_id: str) -> dict[str, Any]:
    project = _require_project(project_id)
    root = Path(project["root_path"])
    bundle = analyze_project_info(root, write=True)
    summary = dict(project.get("summary") or {})
    summary["project_info"] = bundle
    _upsert_project(root, summary)
    return {"bundle": bundle, "stale": collect_project_info_stale_inputs(root, bundle)}


@app.post("/api/projects/{project_id}/runtime/check")
def refresh_project_runtime(project_id: str) -> dict[str, Any]:
    project = _require_project(project_id)
    root = Path(project["root_path"])
    summary = dict(project.get("summary") or {})
    qwen_harness = summary.get("qwen_harness") if isinstance(summary.get("qwen_harness"), dict) else {}
    runtime_checks = _collect_runtime_checks(root, qwen_harness)
    summary["runtime_checks"] = runtime_checks
    _upsert_project(root, summary)
    return {"runtime_checks": runtime_checks, "project": _get_project(project_id)}


@app.post("/api/projects/{project_id}/runtime/actions/{action_id}")
def run_project_runtime_action(project_id: str, action_id: str) -> dict[str, Any]:
    project = _require_project(project_id)
    root = Path(project["root_path"])
    summary = project.get("summary") if isinstance(project.get("summary"), dict) else {}
    runtime_checks = summary.get("runtime_checks") if isinstance(summary.get("runtime_checks"), dict) else None
    try:
        return launch_project_runtime_action(root, action_id, runtime_checks)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    validate_prompt_builder_task_size(payload.work_mode, payload.task_size)
    history = [item.model_dump() for item in payload.history][-12:]
    run = await prompt_builder.start_run(project, payload.message, history, payload.work_mode, payload.task_size)
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
    validate_initial_prompt_task_size(payload.work_mode, payload.initial_prompt, payload.task_size)
    session = await console.start_session(
        project,
        work_mode=payload.work_mode,
        initial_prompt=payload.initial_prompt,
        task_size=payload.task_size,
        task_size_reason=payload.task_size_reason,
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
        task_size=payload.task_size,
        task_size_reason=payload.task_size_reason,
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


def _project_info_initialize_status(root: Path) -> dict[str, Any]:
    absolute_path = project_info_artifact_dir(root) / "project-info.json"
    artifact_path = absolute_path
    if not absolute_path.exists():
        return {
            "status": "missing",
            "artifact_dir": str(project_info_artifact_dir(root)),
            "artifact_path": artifact_path.as_posix(),
            "action": "Project Info Layer 산출물이 없습니다. 필요할 때 Project Info refresh를 실행하세요.",
            "init_fast_path": True,
        }

    bundle = load_project_info_bundle(root)
    if bundle is None:
        return {
            "status": "invalid",
            "artifact_path": artifact_path.as_posix(),
            "action": "Project Info Layer JSON을 읽을 수 없습니다. Project Info refresh를 다시 실행하세요.",
            "init_fast_path": True,
        }

    raw_profile = bundle.get("profile", {}) if isinstance(bundle.get("profile"), dict) else {}
    return {
        "status": "ready",
        "schema_version": bundle.get("schema_version"),
        "generated_at": bundle.get("generated_at"),
        "artifact_dir": bundle.get("artifact_dir") or "D:/aiops/docs/<project-key>/project-info",
        "artifact_path": artifact_path.as_posix(),
        "profile": {
            "key": raw_profile.get("key") or "generic",
            "label": raw_profile.get("label") or raw_profile.get("key") or "generic",
            "implementation_agent": raw_profile.get("implementation_agent") or "coder-35",
        },
        "stale": {"is_stale": False, "unchecked_during_initialize": True},
        "action": "초기화에서는 기존 Project Info 상태만 확인했습니다. 최신화가 필요하면 Project Info refresh를 실행하세요.",
        "init_fast_path": True,
    }


def _ensure_qwen_project_harness(root: Path) -> dict[str, Any]:
    existing = find_project_qwen_command(root)
    preferred_runtime = find_latest_qwencode_runtime()
    project_runtime = resolve_project_qwen_runtime(root) if existing else None
    runtime_mismatch = bool(
        existing
        and preferred_runtime
        and (not project_runtime or project_runtime.resolve() != preferred_runtime.resolve())
    )
    qwen_assets_stale = _project_qwen_assets_stale(root, project_runtime or preferred_runtime)
    if existing and not runtime_mismatch and not qwen_assets_stale:
        return {
            "status": "exists",
            "command": str(existing),
            "project_runtime_dir": str(project_runtime) if project_runtime else None,
            "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
            "project_skills_status": "ready",
            "project_agents_status": "ready",
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
            "status": "mismatch" if runtime_mismatch else ("qwen_assets_stale" if qwen_assets_stale else "skipped"),
            "reason": (
                "프로젝트 qwen.cmd 런타임이 없거나 현재 우선 런타임과 다릅니다. "
                "Windows 폐쇄망에서 프로젝트 초기화를 다시 실행하면 qwen-init이 하네스를 재생성합니다."
                if runtime_mismatch
                else (
                    "프로젝트 .qwen/skills 또는 .qwen/agents가 현재 qwencode runtime template과 다릅니다. "
                    "Windows 폐쇄망에서 프로젝트 초기화를 다시 실행하면 qwen-init이 superpowers skills와 KIWI agents를 재생성합니다."
                    if qwen_assets_stale
                    else "qwen-init.cmd is Windows-only; it will run during Windows offline initialization."
                )
            ),
            "command": command,
            "project_command": str(existing) if existing else None,
            "project_runtime_dir": str(project_runtime) if project_runtime else None,
            "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
            "project_skills_status": "stale" if qwen_assets_stale else "ready",
            "project_agents_status": "stale" if qwen_assets_stale else "ready",
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
    preferred_runtime = find_latest_qwencode_runtime()
    succeeded = completed.returncode == 0 and project_command
    status = "failed"
    if succeeded:
        if runtime_mismatch:
            status = "reset"
        elif qwen_assets_stale:
            status = "qwen_assets_refreshed"
        else:
            status = "succeeded"
    return {
        "status": status,
        "exit_code": completed.returncode,
        "command": command,
        "project_command": str(project_command) if project_command else None,
        "previous_project_command": str(existing) if existing else None,
        "previous_project_runtime_dir": str(project_runtime) if project_runtime else None,
        "preferred_runtime_dir": str(preferred_runtime) if preferred_runtime else None,
        "project_skills_status": "ready" if succeeded else ("stale" if qwen_assets_stale else "unknown"),
        "project_agents_status": "ready" if succeeded else ("stale" if qwen_assets_stale else "unknown"),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def _project_superpowers_skills_stale(root: Path, runtime: Path | None) -> bool:
    required = ["kiwi-superpowers", "using-superpowers"]
    project_skills = root / ".qwen" / "skills"
    for skill in required:
        project_skill = project_skills / skill / "SKILL.md"
        if not project_skill.exists():
            return True
        if runtime is None:
            continue
        template_skill = runtime / "templates" / "project" / ".qwen" / "skills" / skill / "SKILL.md"
        if not template_skill.exists():
            continue
        try:
            if project_skill.read_text(encoding="utf-8", errors="replace") != template_skill.read_text(
                encoding="utf-8", errors="replace"
            ):
                return True
        except OSError:
            return True
    return False


def _project_qwen_assets_stale(root: Path, runtime: Path | None) -> bool:
    if _project_superpowers_skills_stale(root, runtime):
        return True
    required_agents = [
        "coder-35",
        "dcp-front-developer",
        "dcp-backend-developer",
        "drt-front-developer",
        "drt-backend-developer",
        "drt-cms-front-developer",
        "drt-cms-backend-developer",
    ]
    project_agents = root / ".qwen" / "agents"
    for agent in required_agents:
        project_agent = project_agents / f"{agent}.md"
        if not project_agent.exists():
            return True
        if runtime is None:
            continue
        template_agent = runtime / "templates" / "project" / ".qwen" / "agents" / f"{agent}.md"
        if not template_agent.exists():
            continue
        try:
            if project_agent.read_text(encoding="utf-8", errors="replace") != template_agent.read_text(
                encoding="utf-8", errors="replace"
            ):
                return True
        except OSError:
            return True
    return False


def _collect_runtime_checks(root: Path, qwen_harness: dict[str, Any]) -> dict[str, Any]:
    return collect_project_runtime(root, qwen_harness)


def _find_qwen_node(qwen_runtime: Path | None) -> Path | None:
    if qwen_runtime is None:
        return None
    for candidate in [
        qwen_runtime / "runtimes" / "node" / "node.exe",
        qwen_runtime / "runtimes" / "node" / "node",
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
