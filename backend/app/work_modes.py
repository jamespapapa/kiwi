from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


WorkMode = Literal["fast", "ultrawork", "superpowers"]
TaskSize = Literal["xsmall", "small", "medium", "large", "xlarge"]
TASK_SIZES: tuple[TaskSize, ...] = ("xsmall", "small", "medium", "large", "xlarge")
DEFAULT_TASK_SIZE: TaskSize = "medium"


@dataclass(frozen=True)
class WorkModeDefinition:
    key: WorkMode
    label: str
    prefix: str
    aliases: tuple[str, ...]
    summary: str
    activation: str


WORK_MODE_DEFINITIONS: dict[WorkMode, WorkModeDefinition] = {
    "fast": WorkModeDefinition(
        key="fast",
        label="FAST/lightwork",
        prefix="lightwork",
        aliases=("lightwork", "fast", "lw"),
        summary="짧고 명확한 작업을 Kiwi가 직접 처리하는 경량 모드.",
        activation=(
            "FAST/lightwork mode: keep the work in the main Kiwi session, make the smallest "
            "direct change, use `todo_write` tool for planning, do not produce a size report, "
            "and run focused verification."
        ),
    ),
    "ultrawork": WorkModeDefinition(
        key="ultrawork",
        label="ultrawork",
        prefix="ultrawork",
        aliases=("ultrawork", "ulw"),
        summary="티셔츠 사이징에 따라 explorer/planner/architect/developer/reviewer를 조율하는 팀 모드.",
        activation=(
            "ultrawork mode: report t-shirt sizing first, then coordinate Qwen subagents "
            "according to the selected size and project profile."
        ),
    ),
    "superpowers": WorkModeDefinition(
        key="superpowers",
        label="superpowers",
        prefix="superpowers",
        aliases=("superpowers", "spw"),
        summary="Qwen extension skills를 먼저 활용하고 필요하면 ultrawork 팀 루프로 확장하는 고강도 모드.",
        activation=(
            "superpowers mode: invoke relevant Qwen extension skills first, then use the "
            "ultrawork agent loop only after the skill-driven context is loaded."
        ),
    ),
}

WORK_MODE_ALIASES: dict[str, WorkMode] = {
    alias: definition.key for definition in WORK_MODE_DEFINITIONS.values() for alias in definition.aliases
}
TEAM_MODE_PREFIXES = ("ultrawork", "ulw", "superpowers", "spw")


def normalize_work_mode(value: str | None) -> WorkMode:
    text = str(value or "").strip().lower()
    if text in WORK_MODE_DEFINITIONS:
        return text  # type: ignore[return-value]
    return WORK_MODE_ALIASES.get(text, "ultrawork")


def normalize_task_size(value: str | None) -> TaskSize | None:
    text = str(value or "").strip().lower()
    if text in TASK_SIZES:
        return text  # type: ignore[return-value]
    return None


def split_sized_work_mode_trigger(trigger: str | None) -> tuple[str, TaskSize | None]:
    text = str(trigger or "").strip().lower()
    match = re.match(r"^(ultrawork|ulw|superpowers|spw)_(xsmall|small|medium|large|xlarge)$", text)
    if match:
        return match.group(1), match.group(2)  # type: ignore[return-value]
    return text, None


def work_mode_definition(mode: str | None) -> WorkModeDefinition:
    return WORK_MODE_DEFINITIONS[normalize_work_mode(mode)]


def detect_work_mode_trigger(text: str) -> tuple[str, WorkMode] | None:
    detected = detect_work_mode_trigger_with_size(text)
    if not detected:
        return None
    trigger, mode, _task_size = detected
    return trigger, mode


def detect_work_mode_trigger_with_size(text: str) -> tuple[str, WorkMode, TaskSize | None] | None:
    match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_-]*)(?:\s*(?:\r?\n|$))", text or "")
    if not match:
        return None
    trigger = match.group(1).strip().lower()
    base_trigger, task_size = split_sized_work_mode_trigger(trigger)
    mode = WORK_MODE_ALIASES.get(base_trigger)
    if mode is None:
        return None
    return trigger, mode, task_size


def strip_work_mode_trigger(text: str) -> str:
    detected = detect_work_mode_trigger(text)
    if not detected:
        return text.strip()
    match = re.match(r"^\s*[A-Za-z][A-Za-z0-9_-]*(?:\s*(?:\r?\n|$))", text or "")
    if not match:
        return text.strip()
    return text[match.end() :].lstrip("\r\n")


def prefix_for_work_mode(mode: str | None, task_size: str | None = None) -> str:
    definition = work_mode_definition(mode)
    normalized_size = normalize_task_size(task_size)
    if definition.key in {"ultrawork", "superpowers"} and normalized_size:
        return f"{definition.prefix}_{normalized_size}"
    return definition.prefix


def ensure_work_mode_prefix(text: str, mode: str | None, task_size: str | None = None) -> str:
    definition = work_mode_definition(mode)
    detected = detect_work_mode_trigger(text)
    if detected and detected[1] == definition.key:
        return text
    return f"{prefix_for_work_mode(definition.key, task_size)}\n\n{text.strip()}".strip()


def render_work_mode_lock_lines(mode: str | None, task_size: str | None = None) -> list[str]:
    definition = work_mode_definition(mode)
    activation_prefix = prefix_for_work_mode(definition.key, task_size)
    return [
        "## KIWI work mode lock",
        f"- Session work mode: `{definition.key}` ({definition.label})",
        f"- Activation prefix: `{activation_prefix}`",
        "- This mode is locked for the current console session after first activation.",
        "- If the user later sends another work-mode prefix, KIWI blocks it with 409; start a new console session to change mode.",
        f"- Runtime policy: {definition.activation}",
    ]


def render_work_mode_runtime_policy() -> list[str]:
    return [
        "- `lightwork`/`fast`/`lw`: FAST mode. Kiwi works directly, keeps the change narrow, and runs focused verification.",
        "- `ultrawork_<size>`/`ulw_<size>`: team mode. `<size>` is one of xsmall, small, medium, large, xlarge and is the user-selected source of truth.",
        "- `superpowers_<size>`/`spw_<size>`: skill-first mode. `<size>` is one of xsmall, small, medium, large, xlarge and is the user-selected source of truth.",
        f"- Plain `ultrawork`/`ulw` and `superpowers`/`spw` default to `{DEFAULT_TASK_SIZE}` when no explicit size is provided.",
        "- Once any work-mode prefix activates a Qwen session, later prefixes must not change the active mode in that session.",
    ]
