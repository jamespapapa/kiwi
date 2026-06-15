from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import APP_ROOT
from .ultrawork_policy import detect_project_profile


FAST_SYSTEM_PROMPTS_DIR = APP_ROOT / "docs" / "fast-system-prompts"
FAST_PROFILE_PROMPT_FILES = {
    "dcp-front": "fast-system-prompt.dcp-front.md",
    "dcp-services": "fast-system-prompt.dcp-services.md",
    "generic": "fast-system-prompt.generic.md",
}
RUNTIME_SECTION = "## Runtime Injection Summary"
HUMAN_REVIEW_SECTION = "## Human-Review Final Prompt"


@dataclass(frozen=True)
class FastSystemPrompt:
    profile_key: str
    source_path: Path
    source_relpath: str
    runtime_summary: str
    human_prompt: str
    full_text: str


def detect_fast_prompt_profile(project: dict[str, Any] | Path | str | None) -> str:
    profile = detect_project_profile(project) if project is not None else None
    if profile and profile.key in FAST_PROFILE_PROMPT_FILES:
        return profile.key
    return "generic"


def fast_system_prompt_path(profile_key: str) -> Path:
    normalized = profile_key if profile_key in FAST_PROFILE_PROMPT_FILES else "generic"
    return FAST_SYSTEM_PROMPTS_DIR / FAST_PROFILE_PROMPT_FILES[normalized]


def load_fast_system_prompt(
    project: dict[str, Any] | Path | str | None = None,
    profile_key: str | None = None,
) -> FastSystemPrompt:
    normalized = profile_key if profile_key in FAST_PROFILE_PROMPT_FILES else detect_fast_prompt_profile(project)
    source = fast_system_prompt_path(normalized)
    try:
        full_text = source.read_text(encoding="utf-8")
    except OSError:
        normalized = "generic"
        source = fast_system_prompt_path(normalized)
        full_text = source.read_text(encoding="utf-8")
    runtime_summary = _extract_section(full_text, RUNTIME_SECTION, HUMAN_REVIEW_SECTION)
    human_prompt = _extract_section(full_text, HUMAN_REVIEW_SECTION, None)
    return FastSystemPrompt(
        profile_key=normalized,
        source_path=source,
        source_relpath=source.relative_to(APP_ROOT).as_posix(),
        runtime_summary=runtime_summary.strip(),
        human_prompt=human_prompt.strip(),
        full_text=full_text.strip(),
    )


def render_fast_runtime_injection(
    project: dict[str, Any] | Path | str | None = None,
    max_chars: int = 8000,
) -> str:
    prompt = load_fast_system_prompt(project)
    lines = [
        "## FAST System Prompt Runtime Summary",
        f"- FAST system prompt source: `{prompt.source_relpath}`",
        f"- Profile: `{prompt.profile_key}`",
        "",
        prompt.runtime_summary,
    ]
    text = "\n".join(lines).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[FAST system prompt runtime summary truncated]"


def _extract_section(text: str, start: str, end: str | None) -> str:
    start_index = text.find(start)
    if start_index < 0:
        return ""
    body_start = start_index + len(start)
    if end is None:
        return text[body_start:].strip()
    end_index = text.find(end, body_start)
    if end_index < 0:
        return text[body_start:].strip()
    return text[body_start:end_index].strip()
