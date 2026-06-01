from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import HTTPException

from .coder_runner import build_qwencode_env
from .config import get_internal_settings
from .db import APP_ROOT, now_iso
from .kk_mcp import ensure_project_qwencode_mcp_settings
from .qwencode_runtime import find_latest_qwencode_runtime, resolve_project_qwen_command, resolve_project_qwen_runtime


CONSOLE_DIR = APP_ROOT / "data" / "ultrawork"
TERMINAL_TAIL_CHARS = 180_000
MAX_RECENT_TEAM_EVENTS = 300
MAX_RECENT_CHAT_EVENTS = 500
# Qwen's Windows paste workaround ignores submit Enter briefly after paste.
QWEN_PASTE_GUARD_SECONDS = 0.62
PTY_WRITE_CHUNK_CHARS = 4096
PASTE_SUBMIT_CHARS_PER_SECOND = 32_000
PASTE_SUBMIT_LINE_SECONDS = 0.002
KNOWN_SUBAGENT_TYPES = (
    "coder-35",
    "explorer-next",
    "tester-35",
    "planner-35",
    "architect-35",
    "reviewer-35",
    "debugger-35",
)


@dataclass
class ConsoleSession:
    id: str
    project_id: str
    project_name: str
    root_path: str
    command: list[str]
    log_path: Path
    team_events_path: Path | None
    team_event_offset: int
    chat_events_dir: Path | None
    chat_events_path: Path | None
    chat_event_offset: int
    chat_started_after: float
    created_at: str
    status: str = "starting"
    mode: str = "pipe"
    started_at: str | None = None
    completed_at: str | None = None
    exit_code: int | None = None
    error: str | None = None
    process: Any = None
    reader_task: asyncio.Task[None] | None = None
    team_task: asyncio.Task[None] | None = None
    chat_task: asyncio.Task[None] | None = None
    queues: set[asyncio.Queue[dict[str, Any]]] = field(default_factory=set)
    recent_team_events: list[dict[str, Any]] = field(default_factory=list)
    recent_chat_events: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    token_usage_event_ids: set[str] = field(default_factory=set)

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "root_path": self.root_path,
            "command": self.command,
            "status": self.status,
            "mode": self.mode,
            "log_path": str(self.log_path),
            "team_events_path": str(self.team_events_path) if self.team_events_path else None,
            "team_events_exists": bool(self.team_events_path and self.team_events_path.exists()),
            "team_events_size": _file_size(self.team_events_path),
            "team_event_offset": self.team_event_offset,
            "chat_events_dir": str(self.chat_events_dir) if self.chat_events_dir else None,
            "chat_events_path": str(self.chat_events_path) if self.chat_events_path else None,
            "chat_events_exists": bool(self.chat_events_path and self.chat_events_path.exists()),
            "chat_events_size": _file_size(self.chat_events_path),
            "chat_event_offset": self.chat_event_offset,
            "token_usage": self.token_usage,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "exit_code": self.exit_code,
            "error": self.error,
        }


class UltraworkConsoleManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ConsoleSession] = {}

    async def start_session(
        self,
        project: dict[str, Any],
        initial_prompt: str | None = None,
        cols: int = 140,
        rows: int = 36,
    ) -> dict[str, Any]:
        settings = get_internal_settings()
        ensure_project_qwencode_mcp_settings(project["root_path"], settings)
        project_runtime = resolve_project_qwen_runtime(project["root_path"])
        preferred_runtime = find_latest_qwencode_runtime()
        if (
            project_runtime
            and preferred_runtime
            and project_runtime.resolve() != preferred_runtime.resolve()
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "프로젝트 qwen.cmd 런타임이 현재 KIWI 우선 런타임과 다릅니다. "
                    "왼쪽 프로젝트 초기화를 다시 실행해 qwen-init으로 qwen.cmd를 재생성하세요. "
                    f"project_runtime={project_runtime}; preferred_runtime={preferred_runtime}"
                ),
            )
        command = resolve_project_qwen_command(project["root_path"])
        if not command:
            raise HTTPException(
                status_code=409,
                detail="프로젝트 루트에 qwen.cmd가 없습니다. 먼저 프로젝트 초기화를 실행해 qwen-init을 완료하세요.",
            )
        if "--approval-mode" not in command and not any(part.startswith("--approval-mode=") for part in command):
            command = [*command, "--approval-mode", "yolo"]
        session_id = str(uuid.uuid4())
        CONSOLE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = CONSOLE_DIR / f"{session_id}.terminal.log"
        team_events_path = _team_events_path(project["root_path"])
        chat_events_dir = _chat_events_dir(project["root_path"])
        team_event_offset = _file_size(team_events_path)
        state = ConsoleSession(
            id=session_id,
            project_id=project["id"],
            project_name=project["name"],
            root_path=project["root_path"],
            command=command,
            log_path=log_path,
            team_events_path=team_events_path,
            team_event_offset=team_event_offset,
            chat_events_dir=chat_events_dir,
            chat_events_path=None,
            chat_event_offset=0,
            chat_started_after=time.time(),
            created_at=now_iso(),
        )
        self._sessions[session_id] = state

        env = build_qwencode_env(settings)
        env["KIWI_ULTRAWORK_CONSOLE"] = "1"
        env["KIWI_ULTRAWORK_FULL_VISIBILITY"] = env.get("KIWI_ULTRAWORK_FULL_VISIBILITY", "0")
        env["QWEN_ULTRAWORK_AGENT_VISIBILITY"] = env.get("QWEN_ULTRAWORK_AGENT_VISIBILITY", "0")
        env["TERM"] = env.get("TERM", "xterm-256color")
        env["COLORTERM"] = env.get("COLORTERM", "truecolor")
        env["FORCE_COLOR"] = env.get("FORCE_COLOR", "1")

        try:
            await self._spawn(state, env, cols, rows)
        except Exception as exc:
            self._sessions.pop(session_id, None)
            raise HTTPException(status_code=500, detail=f"Ultrawork 콘솔 시작 실패: {exc}") from exc

        state.team_task = asyncio.create_task(self._tail_team_events(state))
        state.chat_task = asyncio.create_task(self._tail_chat_events(state))
        await self._broadcast(state, {"type": "status", "session": state.snapshot()})

        if initial_prompt and initial_prompt.strip():
            asyncio.create_task(self._delayed_input(state.id, initial_prompt, 0.8))

        return state.snapshot()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        state = self._sessions.get(session_id)
        return state.snapshot() if state else None

    async def send_input(
        self,
        session_id: str,
        text: str,
        submit: bool = True,
        bracketed_paste: bool = False,
    ) -> dict[str, Any]:
        state = self._require_state(session_id)
        if state.status not in {"running", "starting"}:
            raise HTTPException(status_code=409, detail=f"콘솔이 실행 중이 아닙니다: {state.status}")
        if bracketed_paste:
            await self._write_bracketed_paste(state, text)
        else:
            await self._write_input(state, text)
        if submit:
            delay = _paste_submit_delay(text) if bracketed_paste else 0
            if delay > 0:
                await asyncio.sleep(delay)
            await self._write_enter(state)
        return {"accepted": True}

    async def resize_session(self, session_id: str, cols: int, rows: int) -> dict[str, Any]:
        state = self._require_state(session_id)
        if state.status not in {"running", "starting"}:
            return {"accepted": False, "session": state.snapshot()}
        await self._resize_pty(state, cols=cols, rows=rows)
        return {"accepted": True, "session": state.snapshot()}

    async def stop_session(self, session_id: str) -> dict[str, Any]:
        state = self._require_state(session_id)
        if state.status not in {"running", "starting"}:
            return state.snapshot()
        state.status = "stopping"
        await self._broadcast(state, {"type": "status", "session": state.snapshot()})
        await self._terminate(state)
        return state.snapshot()

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(self.stop_session(session_id) for session_id in list(self._sessions)),
            return_exceptions=True,
        )

    async def stream_events(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        state = self._require_state(session_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        state.queues.add(queue)
        try:
            yield {
                "type": "snapshot",
                "session": state.snapshot(),
                "terminal": _read_tail(state.log_path, TERMINAL_TAIL_CHARS),
                "team_events": state.recent_team_events[-MAX_RECENT_TEAM_EVENTS:],
                "chat_events": state.recent_chat_events[-MAX_RECENT_CHAT_EVENTS:],
            }
            while True:
                event = await queue.get()
                yield event
                if event.get("type") == "done":
                    break
        finally:
            state.queues.discard(queue)

    async def _spawn(
        self,
        state: ConsoleSession,
        env: dict[str, str],
        cols: int,
        rows: int,
    ) -> None:
        if os.name == "nt":
            try:
                from winpty import PtyProcess  # type: ignore

                command_line = _winpty_command_line(state.command)
                state.process = await asyncio.to_thread(
                    PtyProcess.spawn,
                    command_line,
                    cwd=state.root_path,
                    env=env,
                    dimensions=(rows, cols),
                )
                state.mode = "winpty"
                state.status = "running"
                state.started_at = now_iso()
                state.reader_task = asyncio.create_task(self._read_winpty(state))
                return
            except ImportError:
                state.mode = "pipe"

        process = await asyncio.create_subprocess_exec(
            *state.command,
            cwd=state.root_path,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        state.process = process
        state.mode = "pipe"
        state.status = "running"
        state.started_at = now_iso()
        state.reader_task = asyncio.create_task(self._read_pipe(state))

    async def _read_winpty(self, state: ConsoleSession) -> None:
        process = state.process
        exit_code: int | None = None
        try:
            while state.status in {"running", "stopping", "starting"}:
                try:
                    chunk = await asyncio.to_thread(process.read)
                except EOFError:
                    break
                except OSError as exc:
                    await self._record_terminal(state, f"\r\n[KIWI] PTY read failed: {exc}\r\n")
                    break
                if chunk:
                    await self._record_terminal(state, chunk)
                if not process.isalive():
                    break
            exit_code = getattr(process, "exitstatus", None)
        finally:
            await self._finish(state, exit_code)

    async def _read_pipe(self, state: ConsoleSession) -> None:
        process: asyncio.subprocess.Process = state.process
        exit_code: int | None = None
        try:
            assert process.stdout is not None
            async for raw in process.stdout:
                await self._record_terminal(state, raw.decode("utf-8", errors="replace"))
            exit_code = await process.wait()
        finally:
            await self._finish(state, exit_code)

    async def _record_terminal(self, state: ConsoleSession, chunk: str) -> None:
        state.log_path.parent.mkdir(parents=True, exist_ok=True)
        with state.log_path.open("a", encoding="utf-8", errors="replace") as handle:
            handle.write(chunk)
        await self._broadcast(state, {"type": "terminal", "data": chunk})

    async def _tail_team_events(self, state: ConsoleSession) -> None:
        path = state.team_events_path
        if path is None:
            return
        offset = state.team_event_offset
        while state.status in {"starting", "running", "stopping"}:
            try:
                if path.exists():
                    current_size = _file_size(path)
                    if current_size < offset:
                        offset = 0
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        handle.seek(offset)
                        while True:
                            line = handle.readline()
                            if not line:
                                break
                            offset = handle.tell()
                            event = _parse_team_event(line)
                            state.recent_team_events.append(event)
                            state.recent_team_events = state.recent_team_events[-MAX_RECENT_TEAM_EVENTS:]
                            await self._broadcast(state, {"type": "team_event", "event": event})
                state.team_event_offset = offset
            except OSError as exc:
                await self._broadcast(state, {"type": "team_error", "error": str(exc)})
            await asyncio.sleep(0.5)

    async def _tail_chat_events(self, state: ConsoleSession) -> None:
        offset = state.chat_event_offset
        while state.status in {"starting", "running", "stopping"}:
            try:
                if state.chat_events_path is None or not state.chat_events_path.exists():
                    candidate = _find_active_chat_file(
                        state.chat_events_dir,
                        state.root_path,
                        state.chat_started_after,
                    )
                    if candidate:
                        state.chat_events_path = candidate
                        offset = 0
                        state.chat_event_offset = 0
                        await self._broadcast(state, {"type": "status", "session": state.snapshot()})

                path = state.chat_events_path
                if path and path.exists():
                    current_size = _file_size(path)
                    if current_size < offset:
                        offset = 0
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        handle.seek(offset)
                        while True:
                            line = handle.readline()
                            if not line:
                                break
                            offset = handle.tell()
                            for event in _parse_chat_events(line):
                                _accumulate_token_usage(state, event)
                                state.recent_chat_events.append(event)
                                state.recent_chat_events = state.recent_chat_events[-MAX_RECENT_CHAT_EVENTS:]
                                await self._broadcast(
                                    state,
                                    {
                                        "type": "chat_event",
                                        "event": event,
                                        "token_usage": state.token_usage,
                                    },
                                )
                    state.chat_event_offset = offset
            except OSError as exc:
                await self._broadcast(state, {"type": "chat_error", "error": str(exc)})
            await asyncio.sleep(0.5)

    async def _write_input(self, state: ConsoleSession, text: str) -> None:
        if state.mode == "winpty":
            await self._write_winpty_text(state, text)
            return
        process: asyncio.subprocess.Process = state.process
        if process.stdin is None:
            raise HTTPException(status_code=409, detail="콘솔 stdin이 열려 있지 않습니다.")
        for chunk in _chunk_text(text):
            process.stdin.write(chunk.encode("utf-8", errors="replace"))
            await process.stdin.drain()

    async def _write_bracketed_paste(self, state: ConsoleSession, text: str) -> None:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        await self._write_input(state, "\x1b[200~")
        await self._write_input(state, normalized)
        await self._write_input(state, "\x1b[201~")

    async def _write_winpty_text(self, state: ConsoleSession, text: str) -> None:
        # xterm/bracketed paste payloads already carry the intended control
        # characters. Expanding LF to CRLF here can create visible extra line
        # advances in the Windows PTY; submit Enter is sent separately as CR.
        for chunk in _chunk_text(text):
            await asyncio.to_thread(state.process.write, chunk)
            await asyncio.sleep(0)

    async def _write_enter(self, state: ConsoleSession) -> None:
        if state.mode == "winpty":
            await asyncio.to_thread(state.process.write, "\r")
            return
        process: asyncio.subprocess.Process = state.process
        if process.stdin is None:
            raise HTTPException(status_code=409, detail="콘솔 stdin이 열려 있지 않습니다.")
        process.stdin.write(b"\n")
        await process.stdin.drain()

    async def _resize_pty(self, state: ConsoleSession, cols: int, rows: int) -> None:
        process = state.process
        if process is None or state.mode != "winpty":
            return
        for method_name in ("setwinsize", "set_winsize", "resize"):
            method = getattr(process, method_name, None)
            if method is None:
                continue
            try:
                await asyncio.to_thread(method, rows, cols)
                return
            except TypeError:
                try:
                    await asyncio.to_thread(method, cols, rows)
                    return
                except Exception:
                    continue
            except Exception:
                continue

    async def _terminate(self, state: ConsoleSession) -> None:
        process = state.process
        if process is None:
            return
        if state.mode == "winpty":
            await asyncio.to_thread(process.terminate)
            return
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=8)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    async def _finish(self, state: ConsoleSession, exit_code: int | None) -> None:
        if state.status in {"exited", "failed", "stopped"}:
            return
        state.exit_code = exit_code
        state.completed_at = now_iso()
        if state.status == "stopping":
            state.status = "stopped"
        elif exit_code in {0, None}:
            state.status = "exited"
        else:
            state.status = "failed"
        await self._broadcast(state, {"type": "status", "session": state.snapshot()})
        await self._broadcast(state, {"type": "done", "session": state.snapshot()})
        if state.team_task:
            state.team_task.cancel()
        if state.chat_task:
            state.chat_task.cancel()

    async def _delayed_input(self, session_id: str, text: str, delay: float) -> None:
        await asyncio.sleep(delay)
        if session_id in self._sessions:
            await self.send_input(session_id, text, bracketed_paste=True)

    async def _broadcast(self, state: ConsoleSession, event: dict[str, Any]) -> None:
        for queue in state.queues.copy():
            await queue.put(event)

    def _require_state(self, session_id: str) -> ConsoleSession:
        state = self._sessions.get(session_id)
        if state is None:
            raise HTTPException(status_code=404, detail="Ultrawork 콘솔 세션을 찾을 수 없습니다.")
        return state


def _team_events_path(project_root: str | Path | None = None) -> Path | None:
    runtime = resolve_project_qwen_runtime(project_root) or find_latest_qwencode_runtime()
    if runtime is None:
        return None
    return runtime / "portable-runtime" / "team-events.jsonl"


def _chat_events_dir(project_root: str | Path | None = None) -> Path | None:
    runtime = resolve_project_qwen_runtime(project_root) or find_latest_qwencode_runtime()
    if runtime is None or project_root is None:
        return None
    project_id = _sanitize_qwen_cwd(str(project_root))
    return runtime / "portable-runtime" / "projects" / project_id / "chats"


def _winpty_command_line(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def _chunk_text(text: str, size: int = PTY_WRITE_CHUNK_CHARS) -> list[str]:
    if not text:
        return [""]
    return [text[index : index + size] for index in range(0, len(text), size)]


def _paste_submit_delay(text: str) -> float:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return (
        QWEN_PASTE_GUARD_SECONDS
        + (len(normalized) / PASTE_SUBMIT_CHARS_PER_SECOND)
        + (normalized.count("\n") * PASTE_SUBMIT_LINE_SECONDS)
    )


def _file_size(path: Path | None) -> int:
    if path is None:
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _read_tail(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-max_chars:]


def _parse_team_event(line: str) -> dict[str, Any]:
    stripped = line.strip()
    if not stripped:
        return {"raw": ""}
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            parsed["raw"] = stripped
            return parsed
    except json.JSONDecodeError:
        pass
    return {"raw": stripped}


def _accumulate_token_usage(state: ConsoleSession, event: dict[str, Any]) -> None:
    if event.get("kind") != "completion":
        return
    tokens = event.get("tokens")
    if not isinstance(tokens, int) or tokens <= 0:
        return
    event_id = _token_usage_event_id(event)
    if event_id in state.token_usage_event_ids:
        return
    state.token_usage_event_ids.add(event_id)
    agent = _agent_token_key(event.get("agent"))
    state.token_usage[agent] = state.token_usage.get(agent, 0) + tokens


def _token_usage_event_id(event: dict[str, Any]) -> str:
    for key in ("response_id", "prompt_id", "uuid"):
        value = event.get(key)
        if value:
            return f"{key}:{value}"
    return ":".join(
        [
            str(event.get("timestamp") or ""),
            str(event.get("agent") or ""),
            str(event.get("model") or ""),
            str(event.get("tokens") or ""),
        ]
    )


def _agent_token_key(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text == "Qwen3.5-397B" or text.lower() == "kiwi":
        return "kiwi"
    key = text.lower()
    if key == "coder-next" or key.startswith("coder-next-"):
        return "coder-35"
    return key


def _find_active_chat_file(chat_dir: Path | None, project_root: str, started_after: float) -> Path | None:
    if chat_dir is None:
        return None
    try:
        files = sorted(
            (path for path in chat_dir.glob("*.jsonl") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None

    threshold = started_after - 2.0
    for path in files:
        try:
            if path.stat().st_mtime < threshold:
                continue
        except OSError:
            continue
        if _chat_file_matches_project(path, project_root):
            return path
    return None


def _chat_file_matches_project(path: Path, project_root: str) -> bool:
    try:
        first_line = path.open("r", encoding="utf-8", errors="replace").readline()
    except OSError:
        return False
    if not first_line.strip():
        return True
    try:
        first = json.loads(first_line)
    except json.JSONDecodeError:
        return True
    cwd = str(first.get("cwd") or "")
    return _normalize_project_root(cwd) == _normalize_project_root(project_root)


def _parse_chat_events(line: str) -> list[dict[str, Any]]:
    stripped = line.strip()
    if not stripped:
        return []
    try:
        record = json.loads(stripped)
    except json.JSONDecodeError:
        return []
    if not isinstance(record, dict):
        return []

    base = {
        "timestamp": record.get("timestamp"),
        "session_id": record.get("sessionId"),
        "uuid": record.get("uuid"),
        "parent_uuid": record.get("parentUuid"),
        "record_type": record.get("type"),
    }
    record_type = record.get("type")

    if record_type == "user":
        text = _extract_message_text(record.get("message"), omit_ultrawork_system=True)
        if not text:
            return []
        return [{**base, "kind": "user_message", "agent": "user", "content": text}]

    if record_type == "assistant":
        events: list[dict[str, Any]] = []
        agent = _display_agent(record.get("agentName") or record.get("model") or "Kiwi")
        text = _extract_message_text(record.get("message"))
        if text:
            events.append(
                {
                    **base,
                    "kind": "assistant_message",
                    "agent": agent,
                    "content": text,
                    "model": record.get("model"),
                    "tokens": _token_count(record.get("usageMetadata")),
                }
            )
        for call in _extract_function_calls(record.get("message")):
            name = str(call.get("name") or "")
            args = call.get("args") if isinstance(call.get("args"), dict) else {}
            request_id = _call_id(call) or str(record.get("uuid") or "")
            if name == "agent":
                events.append(
                    {
                        **base,
                        "kind": "agent_request",
                        "agent": str(args.get("subagent_type") or "agent"),
                        "request_id": request_id,
                        "pair_id": request_id,
                        "tool_name": name,
                        "title": str(args.get("description") or "Agent request"),
                        "content": str(args.get("prompt") or ""),
                        "tool_input": args,
                    }
                )
            else:
                events.append(
                    {
                        **base,
                        "kind": "tool_request",
                        "agent": agent,
                        "request_id": request_id,
                        "pair_id": request_id,
                        "tool_name": name,
                        "title": name,
                        "content": _compact_json(args),
                        "tool_input": args,
                    }
                )
        return events

    if record_type == "tool_result":
        return _parse_tool_result_record(record, base)

    if record_type == "system" and record.get("subtype") == "ui_telemetry":
        event = ((record.get("systemPayload") or {}).get("uiEvent") or {})
        if isinstance(event, dict):
            parsed = _parse_ui_telemetry_event(event, base)
            return [parsed] if parsed else []

    return []


def _parse_tool_result_record(record: dict[str, Any], base: dict[str, Any]) -> list[dict[str, Any]]:
    result = record.get("toolCallResult") if isinstance(record.get("toolCallResult"), dict) else {}
    display = result.get("resultDisplay") if isinstance(result.get("resultDisplay"), dict) else {}
    agent = str(display.get("subagentName") or "tool")
    status = result.get("status") or display.get("status")

    responses = _extract_function_responses(record.get("message"))
    events: list[dict[str, Any]] = []
    for response in responses:
        name = str(response.get("name") or "")
        payload = response.get("response") if isinstance(response.get("response"), dict) else {}
        if name == "agent":
            content = str(payload.get("output") or payload.get("result") or payload.get("error") or display.get("result") or "")
            request_id = _call_id(response) or str(record.get("parentUuid") or "")
            events.append(
                {
                    **base,
                    "kind": "agent_result",
                    "agent": agent,
                    "request_id": request_id,
                    "pair_id": request_id,
                    "tool_name": name,
                    "status": status,
                    "title": str(display.get("taskDescription") or "Agent result"),
                    "content": content,
                    "error": str(payload.get("error") or "") or None,
                }
            )
        else:
            request_id = _call_id(response) or str(record.get("parentUuid") or "")
            events.append(
                {
                    **base,
                    "kind": "tool_result",
                    "agent": agent,
                    "request_id": request_id,
                    "pair_id": request_id,
                    "tool_name": name,
                    "status": status,
                    "title": name,
                    "content": _compact_json(payload),
                }
            )
    return events


def _parse_ui_telemetry_event(event: dict[str, Any], base: dict[str, Any]) -> dict[str, Any] | None:
    name = str(event.get("event.name") or "")
    agent = _display_agent(event.get("subagent_name") or _agent_from_prompt_id(event.get("prompt_id")) or "Kiwi")
    if name == "qwen-code.api_response":
        content = str(event.get("response_text") or "").strip()
        tokens = _token_count(event)
        if not content and tokens <= 0:
            return None
        return {
            **base,
            "kind": "completion",
            "agent": agent,
            "title": "LLM response",
            "content": content,
            "model": event.get("model"),
            "prompt_id": event.get("prompt_id"),
            "response_id": event.get("response_id"),
            "tokens": tokens,
        }
    if name == "qwen-code.tool_call":
        args = event.get("function_args") if isinstance(event.get("function_args"), dict) else {}
        status = str(event.get("status") or "")
        content = str(event.get("error") or "") if status == "error" else _summarize_tool_args(args)
        return {
            **base,
            "kind": "tool_call",
            "agent": agent,
            "tool_name": event.get("function_name"),
            "status": status,
            "title": str(event.get("function_name") or "tool"),
            "content": content,
            "error": event.get("error"),
            "prompt_id": event.get("prompt_id"),
            "response_id": event.get("response_id"),
            "tool_input": args,
        }
    if name == "qwen-code.api_error":
        return {
            **base,
            "kind": "error",
            "agent": agent,
            "title": "API error",
            "content": str(event.get("error_message") or event.get("error_type") or "API error"),
            "error": event.get("error_message") or event.get("error_type"),
            "model": event.get("model"),
            "prompt_id": event.get("prompt_id"),
            "response_id": event.get("response_id"),
        }
    return None


def _extract_message_text(message: Any, omit_ultrawork_system: bool = False) -> str:
    if not isinstance(message, dict):
        return ""
    parts = message.get("parts")
    if not isinstance(parts, list):
        return ""
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict) or part.get("thought"):
            continue
        text = part.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        if omit_ultrawork_system and text.lstrip().startswith("[Ultrawork team mode active]"):
            continue
        texts.append(text.strip())
    return "\n\n".join(texts).strip()


def _extract_function_calls(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    parts = message.get("parts")
    if not isinstance(parts, list):
        return []
    calls: list[dict[str, Any]] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("functionCall"), dict):
            calls.append(part["functionCall"])
    return calls


def _extract_function_responses(message: Any) -> list[dict[str, Any]]:
    if not isinstance(message, dict):
        return []
    parts = message.get("parts")
    if not isinstance(parts, list):
        return []
    responses: list[dict[str, Any]] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("functionResponse"), dict):
            responses.append(part["functionResponse"])
    return responses


def _call_id(value: dict[str, Any]) -> str:
    for key in ("id", "call_id", "tool_call_id", "toolUseId", "tool_use_id"):
        item = value.get(key)
        if item:
            return str(item)
    return ""


def _token_count(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    for key in ("total_token_count", "totalTokenCount", "total_tokens", "totalTokens"):
        raw = value.get(key)
        if isinstance(raw, (int, float)):
            return max(0, int(raw))
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
    return 0


def _summarize_tool_args(args: dict[str, Any]) -> str:
    for key in ["description", "command", "file_path", "path", "query", "pattern", "prompt"]:
        value = args.get(key)
        if value:
            return str(value)
    return _compact_json(args)


def _compact_json(value: Any) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        text = str(value)
    return text[:4000]


def _agent_from_prompt_id(value: Any) -> str:
    if not isinstance(value, str) or "#" not in value:
        return ""
    parts = value.split("#")
    if len(parts) < 3:
        return ""
    candidate = parts[1]
    for agent_type in KNOWN_SUBAGENT_TYPES:
        if candidate == agent_type or candidate.startswith(f"{agent_type}-"):
            return agent_type
    return candidate


def _display_agent(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Kiwi"
    if text == "Qwen3.5-397B":
        return "Kiwi"
    return text


def _sanitize_qwen_cwd(cwd: str) -> str:
    normalized = cwd.lower() if os.name == "nt" or re.match(r"^[A-Za-z]:[\\/]", cwd) else cwd
    return re.sub(r"[^a-zA-Z0-9]", "-", normalized)


def _normalize_project_root(value: str) -> str:
    normalized = value.replace("/", "\\").rstrip("\\").strip()
    if os.name == "nt" or re.match(r"^[A-Za-z]:[\\/]", value):
        normalized = normalized.lower()
    return normalized
