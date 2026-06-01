from __future__ import annotations

import os
import re
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]


def resolve_qwencode_command(configured_command: str, project_root: str | Path | None = None) -> list[str]:
    command = configured_command.strip()
    if command and command.lower() not in {"auto", "qwencode"}:
        return _command_to_exec(command)

    project_command = find_project_qwen_command(project_root)
    if project_command:
        return _command_to_exec(str(project_command))

    runtime = find_latest_qwencode_runtime()
    if runtime:
        return _command_to_exec(str(runtime / "run-qwen.cmd"))

    return ["qwencode"]


def resolve_project_qwen_command(project_root: str | Path | None) -> list[str] | None:
    project_command = find_project_qwen_command(project_root)
    if not project_command:
        return None
    return _command_to_exec(str(project_command))


def resolve_project_qwen_runtime(project_root: str | Path | None) -> Path | None:
    project_command = find_project_qwen_command(project_root)
    if not project_command:
        return None

    runtime = _runtime_from_project_command(project_command)
    if runtime:
        return runtime

    return find_latest_qwencode_runtime()


def resolve_qwen_init_command() -> list[str] | None:
    runtime = find_latest_qwencode_runtime()
    if not runtime:
        return None
    qwen_init = runtime / "qwen-init.cmd"
    if not qwen_init.exists():
        return None
    return _command_to_exec(str(qwen_init))


def find_project_qwen_command(project_root: str | Path | None) -> Path | None:
    if project_root is None:
        return None
    root = Path(project_root)
    for name in ["qwen.cmd", "qwencode.cmd"]:
        candidate = root / name
        if candidate.exists():
            return candidate.resolve()
    return None


def find_latest_qwencode_runtime() -> Path | None:
    candidates: list[Path] = []
    env_runtime = os.getenv("KIWI_QWENCODE_RUNTIME_DIR", "").strip()
    if env_runtime:
        candidates.append(Path(env_runtime))

    if os.name == "nt":
        default_qwencode_runtime = Path(r"D:\aiops\qwencode")
        if _is_qwen_runtime(default_qwencode_runtime):
            ensure_qwencode_runtime_policy(default_qwencode_runtime)
            return default_qwencode_runtime.resolve()

    search_roots = [
        APP_ROOT / "vendor",
        APP_ROOT / "vendor" / "qwen-runtime",
        APP_ROOT.parent / "deliverables",
        APP_ROOT.parent.parent / "deliverables",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        if _is_qwen_runtime(root):
            candidates.append(root)
        candidates.extend(path for path in root.glob("qwen-code-offline-*") if path.is_dir())

    valid = []
    for path in candidates:
        if _is_qwen_runtime(path):
            ensure_qwencode_runtime_policy(path)
            valid.append(path.resolve())
    if not valid:
        return None
    return sorted(valid, key=_runtime_sort_key, reverse=True)[0]


def _runtime_from_project_command(project_command: Path) -> Path | None:
    try:
        text = project_command.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    matches = re.findall(r'"([^"]*run-qwen\.cmd)"|(?:call\s+)([^\s"]*run-qwen\.cmd)', text, flags=re.IGNORECASE)
    for quoted, bare in matches:
        command = (quoted or bare).strip()
        if not command:
            continue
        command = os.path.expandvars(command)
        path = Path(command)
        if not path.is_absolute():
            path = project_command.parent / path
        runtime = path.parent
        if _is_qwen_runtime(runtime):
            return runtime.resolve()
    return None


def _is_qwen_runtime(path: Path) -> bool:
    return (path / "run-qwen.cmd").exists() and (path / "app" / "cli.js").exists()


def ensure_qwencode_runtime_policy(path: Path) -> None:
    """Patch the selected Qwen runtime in place so aiops/qwencode remains source of truth."""
    _patch_runtime_text_file(path / "scripts" / "write-runtime-config.js")
    _patch_runtime_text_file(path / "scripts" / "team-log-lib.js")
    _remove_generated_legacy_agents(path)


def _patch_runtime_text_file(path: Path, patch_activation_message: bool = False) -> None:
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    updated = _normalize_runtime_agent_names(text)
    if updated == text:
        return
    try:
        path.write_text(updated, encoding="utf-8")
    except OSError:
        return


def _normalize_runtime_agent_names(text: str) -> str:
    text = re.sub(r"(?<!qwen3-)coder-next", "coder-35", text)
    return re.sub(r"(?<!Qwen3-)Coder-Next", "Coder-35", text)


def _remove_generated_legacy_agents(path: Path) -> None:
    agents_dir = path / "extensions" / "ultrawork" / "agents"
    for name in [
        "-".join(["coder", "next"]) + ".md",
    ]:
        try:
            (agents_dir / name).unlink(missing_ok=True)
        except OSError:
            continue


def _runtime_sort_key(path: Path) -> tuple[int, tuple[int, ...], float, str]:
    name = path.name.lower()
    version_match = re.search(r"(\d+(?:\.\d+)+)", name)
    version = tuple(int(part) for part in version_match.group(1).split(".")) if version_match else (0,)
    win11_score = 1 if "win11" in name else 0
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0
    return (win11_score, version, mtime, name)


def _command_to_exec(command: str) -> list[str]:
    path = Path(command)
    if path.is_dir() and (path / "run-qwen.cmd").exists():
        path = path / "run-qwen.cmd"
        command = str(path)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", command]
    return [command]
