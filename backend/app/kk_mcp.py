from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import httpx


DOCS_SERVER_NAME = "kk-docs"
CODE_SERVER_NAME = "kk-code-analysis"


class KkMcpClient:
    def __init__(self, settings: Any):
        self.settings = settings
        self.url = str(getattr(settings, "kk_docs_mcp_url", "") or "").strip()
        self.token = str(getattr(settings, "kk_mcp_token", "") or "").strip()

    async def search_documents(self, queries: list[str], limit: int = 5) -> list[dict[str, Any]]:
        if not getattr(self.settings, "kk_docs_mcp_enabled", False) or not self.url:
            return []

        clean_queries = []
        for query in queries:
            text = str(query or "").strip()
            if text and text not in clean_queries:
                clean_queries.append(text)
            if len(clean_queries) >= 5:
                break

        results: list[dict[str, Any]] = []
        for query in clean_queries:
            results.append(await self._call_search(query, limit=limit))
        return results

    async def _call_search(self, query: str, limit: int) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "kk_search",
                "arguments": {
                    "query": query,
                    "limit": limit,
                },
            },
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(90.0),
                verify=False,
                trust_env=False,
            ) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            return {"query": query, "ok": False, "error": str(exc), "results": []}

        if body.get("error"):
            return {"query": query, "ok": False, "error": body["error"], "results": []}

        structured = ((body.get("result") or {}).get("structuredContent") or {})
        raw_results = structured.get("results") if isinstance(structured, dict) else []
        if not isinstance(raw_results, list):
            raw_results = []

        compact_results = [_compact_search_result(item) for item in raw_results[:limit] if isinstance(item, dict)]
        return {
            "query": query,
            "ok": True,
            "endpoint": self.url,
            "candidate_counts": structured.get("candidate_counts", {}) if isinstance(structured, dict) else {},
            "elapsed_ms": structured.get("elapsed_ms") if isinstance(structured, dict) else None,
            "results": compact_results,
        }


def ensure_project_qwencode_mcp_settings(project_root: str | Path, settings: Any) -> Path:
    root = Path(project_root)
    qwen_dir = root / ".qwen"
    qwen_dir.mkdir(parents=True, exist_ok=True)
    settings_path = qwen_dir / "settings.json"

    data: dict[str, Any] = {}
    if settings_path.exists():
        try:
            parsed = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            data = {}

    mcp_servers = data.get("mcpServers")
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}

    docs_enabled = bool(getattr(settings, "kk_docs_mcp_enabled", False))
    docs_url = str(getattr(settings, "kk_docs_mcp_url", "") or "").strip()
    if docs_enabled and docs_url:
        mcp_servers[DOCS_SERVER_NAME] = _mcp_server_config(
            docs_url,
            getattr(settings, "kk_mcp_token", ""),
            include_tools=["kk_search", "kk_get_document", "kk_list_topics"],
        )
    else:
        mcp_servers.pop(DOCS_SERVER_NAME, None)

    code_enabled = bool(getattr(settings, "kk_code_analysis_mcp_enabled", False))
    code_url = str(getattr(settings, "kk_code_analysis_mcp_url", "") or "").strip()
    if code_enabled and code_url:
        mcp_servers[CODE_SERVER_NAME] = _mcp_server_config(code_url, getattr(settings, "kk_mcp_token", ""))
    else:
        mcp_servers.pop(CODE_SERVER_NAME, None)

    data["mcpServers"] = mcp_servers
    tools = data.get("tools")
    if not isinstance(tools, dict):
        tools = {}
    tools["approvalMode"] = "yolo"
    tools.pop("sandbox", None)
    data["tools"] = tools
    ui = data.get("ui")
    if not isinstance(ui, dict):
        ui = {}
    ui["compactMode"] = True
    ui["useTerminalBuffer"] = False
    data["ui"] = ui
    settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return settings_path


def _mcp_server_config(url: str, token: str | None = None, include_tools: list[str] | None = None) -> dict[str, Any]:
    config: dict[str, Any] = {
        "httpUrl": url,
        "timeout": 600000,
        "trust": True,
    }
    if include_tools:
        config["includeTools"] = include_tools
    if token:
        config["headers"] = {"Authorization": f"Bearer {str(token).strip()}"}
    return config


def _compact_search_result(item: dict[str, Any]) -> dict[str, Any]:
    content = str(item.get("content") or "")
    return {
        "document_id": item.get("document_id"),
        "chunk_id": item.get("chunk_id"),
        "title": item.get("title"),
        "topic": item.get("topic"),
        "source_type": item.get("source_type"),
        "heading": item.get("heading"),
        "link": item.get("link"),
        "score": item.get("score"),
        "confidence": item.get("confidence"),
        "content": content[:1800],
    }
