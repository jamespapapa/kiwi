#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRACKETED_PASTE_START = "\x1b[200~"
BRACKETED_PASTE_END = "\x1b[201~"
CODEX_MODEL = "gpt-5.4-mini"


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 5 local qwencode shim")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--variant", choices=["basic", "codex"], default="basic")
    args = parser.parse_args()

    runtime = Path(args.runtime).expanduser().resolve()
    project = Path(args.project).expanduser().resolve()
    shim_dir = project / ".kiwi-shim"
    shim_dir.mkdir(parents=True, exist_ok=True)
    team_events = runtime / "portable-runtime" / "team-events.jsonl"
    team_events.parent.mkdir(parents=True, exist_ok=True)

    stdout_log = shim_dir / f"{args.variant}-stdout.log"
    stdin_log = shim_dir / f"{args.variant}-stdin.log"
    codex_log = shim_dir / "codex-call.json"

    def write_stdout(text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()
        with stdout_log.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")

    write_stdout(f"KIWI_PHASE5_SHIM_READY variant={args.variant} project={project}\n")
    append_team_event(
        team_events,
        event="SubagentStart",
        agent_type="Kiwi",
        tool_name="agent",
        tool_input={
            "subagent_type": "explorer-35",
            "description": "Phase 5 shim startup event",
            "prompt": "Verify that Agent Timeline renders structured team events.",
            "path": str(project),
        },
    )

    codex_called = False
    buffer = ""
    stdin_fd = sys.stdin.fileno()
    while True:
        ready, _, _ = select.select([stdin_fd], [], [], 0.5)
        if not ready:
            continue
        raw = os.read(stdin_fd, 8192)
        if not raw:
            break
        buffer += raw.decode("utf-8", errors="replace")
        if should_handle_buffer(buffer):
            submitted = buffer
            buffer = ""
            clean = clean_prompt(submitted)
            if not clean:
                continue
            with stdin_log.open("a", encoding="utf-8") as handle:
                handle.write("=== KIWI SHIM SUBMISSION ===\n")
                handle.write(clean)
                handle.write("\n")
            write_stdout("KIWI_SHIM_PROMPT_BEGIN\n")
            write_stdout(clean)
            write_stdout("\nKIWI_SHIM_PROMPT_END\n")
            append_team_event(
                team_events,
                event="PreToolUse",
                agent_type="Kiwi",
                tool_name="agent",
                tool_input={
                    "subagent_type": "coder-35",
                    "description": "Phase 5 shim received console prompt",
                    "prompt": clean[:1800],
                    "command": "phase5_qwen_shim receive-prompt",
                    "path": str(project),
                },
            )
            append_team_event(
                team_events,
                event="PostToolUse",
                agent_type="coder-35",
                tool_name="agent",
                tool_input={
                    "subagent_type": "coder-35",
                    "description": "Phase 5 shim prompt echo complete",
                    "prompt": "Prompt was echoed to stdout and shim logs.",
                    "file_path": str(stdin_log),
                },
            )
            if args.variant == "codex" and not codex_called:
                codex_called = True
                result = run_codex(project, clean)
                append_jsonl(codex_log, result)
                write_stdout("KIWI_CODEX_BACKED_SHIM_BEGIN\n")
                if result["returncode"] != 0:
                    write_stdout(result["stderr"][-4000:])
                    write_stdout(result["stdout"][-4000:])
                    write_stdout("\nKIWI_CODEX_BACKED_SHIM_FAILED\n")
                    return result["returncode"] or 1
                write_stdout(result["last_message"] or result["stdout"])
                write_stdout("\nKIWI_CODEX_BACKED_SHIM_END\n")
                append_team_event(
                    team_events,
                    event="PostToolUse",
                    agent_type="coder-35",
                    tool_name="agent",
                    tool_input={
                        "subagent_type": "coder-35",
                        "description": "Codex-backed shim completed one real model call",
                        "prompt": result["last_message"][:1800],
                        "command": "codex exec -m gpt-5.4-mini",
                        "file_path": str(codex_log),
                    },
                )

    write_stdout("KIWI_PHASE5_SHIM_EXIT\n")
    return 0


def should_handle_buffer(buffer: str) -> bool:
    if BRACKETED_PASTE_START in buffer:
        return BRACKETED_PASTE_END in buffer
    return "\n" in buffer


def clean_prompt(text: str) -> str:
    return (
        text.replace(BRACKETED_PASTE_START, "")
        .replace(BRACKETED_PASTE_END, "")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def append_team_event(
    path: Path,
    *,
    event: str,
    agent_type: str,
    tool_name: str,
    tool_input: dict[str, Any],
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "agent_type": agent_type,
        "agent_id": f"phase5-{agent_type.lower()}",
        "tool_name": tool_name,
        "decision": "allow",
        "reason": "phase5 local shim evidence",
        "cwd": str(Path.cwd()),
        "tool_input": tool_input,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def run_codex(project: Path, prompt: str) -> dict[str, Any]:
    codex = shutil.which("codex")
    if not codex:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": [],
            "returncode": 127,
            "stdout": "",
            "stderr": "codex executable not found",
            "last_message": "",
        }

    help_text = subprocess.run(
        [codex, "exec", "--help"],
        cwd=str(project),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    ).stdout
    output_path = project / ".kiwi-shim" / "codex-last-message.txt"
    command = [codex, "exec", "-m", CODEX_MODEL]
    help_supports_ephemeral = "--ephemeral" in help_text
    if help_supports_ephemeral:
        command.append("--ephemeral")
    if "--sandbox" in help_text:
        command.extend(["--sandbox", "read-only"])
    if "--skip-git-repo-check" in help_text:
        command.append("--skip-git-repo-check")
    if "--ignore-rules" in help_text:
        command.append("--ignore-rules")
    if "--output-last-message" in help_text:
        command.extend(["--output-last-message", str(output_path)])
    command.append(
        "Reply with exactly this marker and no extra prose: "
        "KIWI_CODEX_BACKED_SHIM_OK. "
        "You are validating that the KIWI Phase 5 qwen.cmd shim can call Codex once."
    )

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(project),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    try:
        last_message = output_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        last_message = ""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "last_message": last_message,
        "help_supports_ephemeral": help_supports_ephemeral,
    }


if __name__ == "__main__":
    raise SystemExit(main())
