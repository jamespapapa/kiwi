from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .work_modes import WorkMode


class PublicSettings(BaseModel):
    api_base_url: str = "https://api.t.drt.samsunglife.kr/llmproxy/v1"
    coder_api_base_url: str = "https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1"
    orchestrator_model: str = "Qwen3.5-397B"
    coder_model: str = "qwen3-coder-next"
    qwencode_command: str = "qwen.cmd"
    dangerous_mode: bool = True
    request_timeout_seconds: int = 180
    max_context_chars: int = 262_144
    kk_docs_mcp_enabled: bool = True
    kk_docs_mcp_url: str = "http://100.254.193.25:3007/mcp"
    kk_code_analysis_mcp_enabled: bool = False
    kk_code_analysis_mcp_url: str = ""
    kk_mcp_token_set: bool = False
    api_key_set: bool = False


class SettingsUpdate(BaseModel):
    api_base_url: str | None = None
    coder_api_base_url: str | None = None
    api_key: str | None = None
    orchestrator_model: str | None = None
    coder_model: str | None = None
    qwencode_command: str | None = None
    dangerous_mode: bool | None = None
    request_timeout_seconds: int | None = Field(default=None, ge=15, le=1800)
    max_context_chars: int | None = Field(default=None, ge=8_000, le=262_144)
    kk_docs_mcp_enabled: bool | None = None
    kk_docs_mcp_url: str | None = Field(default=None, max_length=1000)
    kk_code_analysis_mcp_enabled: bool | None = None
    kk_code_analysis_mcp_url: str | None = Field(default=None, max_length=1000)
    kk_mcp_token: str | None = Field(default=None, max_length=2000)


class InternalSettings(PublicSettings):
    api_key: str = ""
    kk_mcp_token: str = ""


class FolderPickResponse(BaseModel):
    path: str | None = None
    cancelled: bool = False
    error: str | None = None


class ProjectInitializeRequest(BaseModel):
    path: str
    extra_notes: str | None = None


class ProjectSummary(BaseModel):
    id: str
    name: str
    root_path: str
    summary: dict[str, Any]
    created_at: str
    updated_at: str


class SessionCreateRequest(BaseModel):
    project_id: str
    title: str = "Main Session"


class ChatRequest(BaseModel):
    session_id: str
    project_id: str
    message: str


class PromptBuilderMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class PromptBuilderRequest(BaseModel):
    project_id: str
    message: str
    work_mode: WorkMode = "ultrawork"
    task_size: str | None = Field(default=None, pattern="^(xsmall|small|medium|large|xlarge)$")
    history: list[PromptBuilderMessage] = Field(default_factory=list)


class CoderRunRequest(BaseModel):
    session_id: str
    project_id: str
    prompt: str


class CancelRunResponse(BaseModel):
    cancelled: bool


class UltraworkSessionStartRequest(BaseModel):
    project_id: str
    work_mode: WorkMode = "ultrawork"
    initial_prompt: str | None = None
    task_size: str | None = Field(default=None, pattern="^(xsmall|small|medium|large|xlarge)$")
    task_size_reason: str | None = Field(default=None, max_length=1000)
    cols: int = Field(default=160, ge=80, le=500)
    rows: int = Field(default=44, ge=20, le=160)


class UltraworkInputRequest(BaseModel):
    text: str
    submit: bool = True
    bracketed_paste: bool = False
    task_size: str | None = Field(default=None, pattern="^(xsmall|small|medium|large|xlarge)$")
    task_size_reason: str | None = Field(default=None, max_length=1000)


class UltraworkResizeRequest(BaseModel):
    cols: int = Field(default=160, ge=80, le=500)
    rows: int = Field(default=44, ge=20, le=160)
