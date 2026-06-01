from __future__ import annotations

import os
from typing import Any

from .db import connect
from .models import InternalSettings, PublicSettings, SettingsUpdate


ORCHESTRATOR_API_BASE_URL = "https://api.t.drt.samsunglife.kr/llmproxy/v1"
CODER_API_BASE_URL = "https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1"
ORCHESTRATOR_MODEL = "Qwen3.5-397B"
CODER_MODEL = "qwen3-coder-next"

DEFAULTS: dict[str, Any] = {
    "api_base_url": ORCHESTRATOR_API_BASE_URL,
    "coder_api_base_url": CODER_API_BASE_URL,
    "api_key": "",
    "orchestrator_model": ORCHESTRATOR_MODEL,
    "coder_model": CODER_MODEL,
    "qwencode_command": "qwen.cmd",
    "dangerous_mode": True,
    "request_timeout_seconds": 180,
    "max_context_chars": 262_144,
    "kk_docs_mcp_enabled": True,
    "kk_docs_mcp_url": os.getenv("KIWI_KK_DOCS_MCP_URL", "http://100.254.193.25:3007/mcp"),
    "kk_code_analysis_mcp_enabled": False,
    "kk_code_analysis_mcp_url": os.getenv("KIWI_KK_CODE_ANALYSIS_MCP_URL", ""),
    "kk_mcp_token": os.getenv("KIWI_KK_MCP_TOKEN", ""),
}

LOCKED_SETTINGS = {
    "api_base_url",
    "coder_api_base_url",
    "api_key",
    "orchestrator_model",
    "coder_model",
    "qwencode_command",
}
CONFIGURABLE_SETTINGS = set(DEFAULTS) - LOCKED_SETTINGS


def _coerce(key: str, value: str) -> Any:
    if key == "dangerous_mode":
        return value.lower() == "true"
    if key in {"kk_docs_mcp_enabled", "kk_code_analysis_mcp_enabled"}:
        return value.lower() == "true"
    if key in {"request_timeout_seconds", "max_context_chars"}:
        return int(value)
    return value


def get_internal_settings() -> InternalSettings:
    data = dict(DEFAULTS)
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        if row["key"] in CONFIGURABLE_SETTINGS:
            data[row["key"]] = _coerce(row["key"], row["value"])
    # KIWI ultrawork runs in YOLO mode by policy. Older local SQLite settings may
    # still contain dangerous_mode=false, so force the effective runtime value.
    data["dangerous_mode"] = True
    return InternalSettings(**data, api_key_set=bool(data.get("api_key")))


def get_public_settings() -> PublicSettings:
    internal = get_internal_settings()
    return PublicSettings(
        api_base_url=internal.api_base_url,
        coder_api_base_url=internal.coder_api_base_url,
        orchestrator_model=internal.orchestrator_model,
        coder_model=internal.coder_model,
        qwencode_command=internal.qwencode_command,
        dangerous_mode=internal.dangerous_mode,
        request_timeout_seconds=internal.request_timeout_seconds,
        max_context_chars=internal.max_context_chars,
        kk_docs_mcp_enabled=internal.kk_docs_mcp_enabled,
        kk_docs_mcp_url=internal.kk_docs_mcp_url,
        kk_code_analysis_mcp_enabled=internal.kk_code_analysis_mcp_enabled,
        kk_code_analysis_mcp_url=internal.kk_code_analysis_mcp_url,
        kk_mcp_token_set=bool(internal.kk_mcp_token),
        api_key_set=bool(internal.api_key),
    )


def update_settings(payload: SettingsUpdate) -> PublicSettings:
    updates = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if key in CONFIGURABLE_SETTINGS
    }
    with connect() as conn:
        for key, value in updates.items():
            if value is None:
                continue
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
    return get_public_settings()
