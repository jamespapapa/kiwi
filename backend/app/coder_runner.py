from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import HTTPException

from .config import get_internal_settings
from .db import APP_ROOT, connect, json_dumps, now_iso, row_to_dict
from .kk_mcp import ensure_project_qwencode_mcp_settings
from .project_analyzer import append_work_log
from .qwencode_runtime import resolve_qwencode_command
from .qwen_client import QwenClient


RUNS_DIR = APP_ROOT / "data" / "runs"


class CoderRunManager:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    async def start_run(self, session_id: str, project: dict[str, Any], prompt: str) -> dict[str, Any]:
        settings = get_internal_settings()
        ensure_project_qwencode_mcp_settings(project["root_path"], settings)
        run_id = str(uuid.uuid4())
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = RUNS_DIR / f"{run_id}.log"
        command = _build_qwencode_command(
            settings.qwencode_command,
            settings.coder_model,
            prompt,
            project["root_path"],
        )
        created_at = now_iso()

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO coder_runs(
                    id, session_id, project_id, prompt, command_json, status, log_path,
                    created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, 'queued', ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    project["id"],
                    prompt,
                    json_dumps(command),
                    str(log_path),
                    created_at,
                    created_at,
                ),
            )

        asyncio.create_task(self._run_process(run_id, project, command, log_path, settings))
        run = self.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=500, detail="coder run 생성에 실패했습니다.")
        return run

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            row = conn.execute("SELECT * FROM coder_runs WHERE id = ?", (run_id,)).fetchone()
        run = row_to_dict(row)
        if not run:
            return None
        run["command"] = json.loads(run.pop("command_json"))
        return run

    async def cancel_run(self, run_id: str) -> bool:
        process = self._processes.get(run_id)
        if not process or process.returncode is not None:
            return False
        process.terminate()
        await self._broadcast(run_id, {"type": "status", "status": "cancelling"})
        return True

    async def stream_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.setdefault(run_id, set()).add(queue)
        try:
            run = self.get_run(run_id)
            if run:
                yield {"type": "snapshot", "run": run, "log": _read_log_tail(run.get("log_path", ""))}
            while True:
                event = await queue.get()
                yield event
                if event.get("type") == "done":
                    break
        finally:
            self._queues.get(run_id, set()).discard(queue)

    async def _run_process(
        self,
        run_id: str,
        project: dict[str, Any],
        command: list[str],
        log_path: Path,
        settings: Any,
    ) -> None:
        root_path = project["root_path"]
        await self._set_run_status(run_id, "running", started_at=now_iso())
        await self._broadcast(run_id, {"type": "status", "status": "running", "command": command})

        log_lines: list[str] = []
        exit_code: int | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=root_path,
                env=build_qwencode_env(settings),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self._processes[run_id] = process
            with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
                assert process.stdout is not None
                async for raw_line in process.stdout:
                    line = raw_line.decode("utf-8", errors="replace")
                    log_file.write(line)
                    log_file.flush()
                    log_lines.append(line)
                    if len(log_lines) > 800:
                        log_lines = log_lines[-800:]
                    await self._broadcast(run_id, {"type": "log", "data": line})
                exit_code = await process.wait()
        except FileNotFoundError:
            exit_code = 127
            message = "qwencode 명령을 찾을 수 없습니다. 설정의 qwencode command와 PATH를 확인하세요.\n"
            log_path.write_text(message, encoding="utf-8")
            await self._broadcast(run_id, {"type": "log", "data": message})
        except Exception as exc:  # pragma: no cover - defensive runtime guard.
            exit_code = 1
            message = f"coder run failed: {exc}\n"
            with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
                log_file.write(message)
            await self._broadcast(run_id, {"type": "log", "data": message})
        finally:
            self._processes.pop(run_id, None)

        status = "succeeded" if exit_code == 0 else "failed"
        await self._set_run_status(run_id, status, exit_code=exit_code, completed_at=now_iso())
        await self._broadcast(run_id, {"type": "status", "status": status, "exit_code": exit_code})

        review = await self._review_run(run_id, project, "".join(log_lines[-240:]))
        if review:
            await self._broadcast(run_id, {"type": "review", "data": review})
        await self._broadcast(run_id, {"type": "done", "status": status, "exit_code": exit_code})

    async def _review_run(self, run_id: str, project: dict[str, Any], log_tail: str) -> str:
        diff = await _git_diff(project["root_path"])
        settings = get_internal_settings()
        qwen = QwenClient(settings)
        prompt = (
            "qwencode 실행 결과를 리뷰하라. 사용자가 바로 이해할 수 있게 한국어로 요약하고, "
            "문제가 있으면 후속 조치를 제안하라. 중요한 변경이면 KIWI.md 작업 로그에 남길 한 문장도 포함하라.\n\n"
            f"Run ID: {run_id}\n\n"
            f"Log tail:\n{log_tail[-12000:]}\n\n"
            f"Git diff:\n{diff[-50000:]}"
        )
        try:
            review = await qwen.chat(
                [
                    {"role": "system", "content": "You are Kiwi Reviewer. Use Korean. Be concrete."},
                    {"role": "user", "content": prompt},
                ],
                model=settings.orchestrator_model,
                temperature=0.1,
            )
        except Exception as exc:
            review = f"리뷰 모델 호출에 실패했습니다: {exc}"

        with connect() as conn:
            run = conn.execute("SELECT session_id FROM coder_runs WHERE id = ?", (run_id,)).fetchone()
            if run:
                conn.execute(
                    """
                    INSERT INTO messages(id, session_id, role, content, metadata_json, created_at)
                    VALUES(?, ?, 'assistant', ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        run["session_id"],
                        review,
                        json_dumps({"type": "coder_review", "run_id": run_id}),
                        now_iso(),
                    ),
                )
        if diff.strip():
            append_work_log(Path(project["root_path"]), "qwencode 실행 리뷰", review[:1200])
        return review

    async def _set_run_status(
        self,
        run_id: str,
        status: str,
        exit_code: int | None = None,
        started_at: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        with connect() as conn:
            conn.execute(
                """
                UPDATE coder_runs
                SET status = ?,
                    exit_code = COALESCE(?, exit_code),
                    started_at = COALESCE(?, started_at),
                    completed_at = COALESCE(?, completed_at),
                    updated_at = ?
                WHERE id = ?
                """,
                (status, exit_code, started_at, completed_at, now_iso(), run_id),
            )

    async def _broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        queues = self._queues.get(run_id, set()).copy()
        for queue in queues:
            await queue.put(event)


def _build_qwencode_command(
    command: str,
    model: str,
    prompt: str,
    project_root: str | Path | None = None,
) -> list[str]:
    parts = resolve_qwencode_command(command, project_root)
    return [*parts, "--model", model, "--prompt", prompt, "--approval-mode", "yolo"]


def build_qwencode_env(settings: Any) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "QWEN35_BASE_URL": settings.api_base_url,
            "CODER_BASE_URL": settings.coder_api_base_url,
            "QWEN35_API_KEY": settings.api_key or "sk-local-qwen35",
            "CODER_API_KEY": settings.api_key or "sk-local-coder",
            "QWEN35_MODEL": settings.orchestrator_model,
            "CODER_MODEL": settings.coder_model,
            "QWEN35_TEMPERATURE": "0.2",
            "CODER_TEMPERATURE": "0",
            "QWEN35_MAX_TOKENS": "16384",
            "CODER_MAX_TOKENS": "16384",
            "QWEN35_CONTEXT_WINDOW": "262144",
            "CODER_CONTEXT_WINDOW": "262144",
            "QWEN_TEAM_LOG": "1",
            "QWEN_TELEMETRY_ENABLED": "0",
            "KIWI_KK_DOCS_MCP_ENABLED": "1" if getattr(settings, "kk_docs_mcp_enabled", False) else "0",
            "KIWI_KK_DOCS_MCP_URL": getattr(settings, "kk_docs_mcp_url", ""),
            "KIWI_KK_CODE_ANALYSIS_MCP_ENABLED": "1" if getattr(settings, "kk_code_analysis_mcp_enabled", False) else "0",
            "KIWI_KK_CODE_ANALYSIS_MCP_URL": getattr(settings, "kk_code_analysis_mcp_url", ""),
            "KIWI_KK_MCP_TOKEN": getattr(settings, "kk_mcp_token", ""),
            "NODE_TLS_REJECT_UNAUTHORIZED": env.get("NODE_TLS_REJECT_UNAUTHORIZED", "0"),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "LC_ALL": env.get("LC_ALL", "C.UTF-8"),
            "LANG": env.get("LANG", "C.UTF-8"),
        }
    )
    heap_option = "--max-old-space-size=8192"
    node_options = env.get("NODE_OPTIONS", "").strip()
    if heap_option not in node_options:
        env["NODE_OPTIONS"] = f"{heap_option} {node_options}".strip()
    return env


def _read_log_tail(path: str, max_chars: int = 80_000) -> str:
    if not path:
        return ""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-max_chars:]


async def _git_diff(root_path: str) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            root_path,
            "diff",
            "--",
            ".",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
    except FileNotFoundError:
        return "git command not found"
    output = stdout.decode("utf-8", errors="replace")
    if process.returncode != 0:
        return stderr.decode("utf-8", errors="replace")
    return output
