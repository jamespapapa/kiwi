from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .db import APP_ROOT, now_iso
from .ultrawork_policy import detect_project_profile
from .work_modes import WorkMode, normalize_work_mode, work_mode_definition


PROJECT_INFO_SCHEMA_VERSION = "project-info.v1"
PROJECT_DOCS_ROOT_ENV = "KIWI_AIOPS_DOCS_DIR"
PROJECT_DOCS_DEFAULT_WINDOWS = Path(r"D:\aiops\docs")
PROJECT_DOCS_DEFAULT_POSIX = APP_ROOT.parent / "aiops" / "docs"
PROJECT_INFO_ARTIFACT_DIR = Path("project-info")
PROJECT_INFO_JSON = "project-info.json"
PROJECT_INFO_CONTEXT_MAX_CHARS = 32_000
PROJECT_KNOWLEDGE_DIR = Path("knowledge")
PROJECT_INFO_LEGACY_ARTIFACT_DIR = Path("docs") / "kiwi" / "project-info"
PROJECT_KNOWLEDGE_LEGACY_DIR = Path("docs") / "knowledge"
PROJECT_KNOWLEDGE_REQUIRED_FILES = (
    "00-index.md",
    "01-repository-map.md",
    "02-build-and-runtime.md",
    "03-system-boundaries.md",
    "04-domain-glossary.md",
    "05-api-and-contracts.md",
    "06-data-model.md",
    "06-frontend-css-and-dom.md",
    "07-state-and-data-propagation.md",
    "08-integrations.md",
    "09-security-auth-privacy.md",
    "10-testing-and-quality.md",
    "11-operations-and-deployment.md",
    "12-change-playbooks.md",
    "99-gaps-and-questions.md",
    "_worklog.md",
)
PROJECT_KNOWLEDGE_DETAIL_DIRS = ("apis", "data", "flows", "modules", "decisions")
PROJECT_INFO_ARTIFACT_NAMES = (
    "project-summary",
    "architecture-map",
    "module-responsibility-map",
    "entrypoints",
    "key-flows",
    "api/eai-interface-index",
    "verification-guide",
)


def aiops_docs_root() -> Path:
    configured = os.getenv(PROJECT_DOCS_ROOT_ENV, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        return PROJECT_DOCS_DEFAULT_WINDOWS
    return PROJECT_DOCS_DEFAULT_POSIX.resolve()


def project_docs_key(root: Path | str) -> str:
    project_root = Path(root).expanduser().resolve()
    profile = detect_project_profile(project_root)
    raw = profile.key if profile else project_root.name
    key = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-_").lower()
    return key or "generic"


def project_docs_root(root: Path | str) -> Path:
    return aiops_docs_root() / project_docs_key(root)


def project_info_artifact_dir(root: Path | str) -> Path:
    return project_docs_root(root) / PROJECT_INFO_ARTIFACT_DIR


def project_knowledge_dir(root: Path | str) -> Path:
    return project_docs_root(root) / PROJECT_KNOWLEDGE_DIR


def project_docs_display_path(path: Path) -> str:
    return path.as_posix()


def project_docs_reading_hint(root: Path | str) -> str:
    key = project_docs_key(root)
    docs_root = project_docs_display_path(aiops_docs_root() / key)
    return (
        f"Project docs root: `{docs_root}`. "
        f"Read `{docs_root}/knowledge/00-index.md` first when present. "
        f"Read optional `{docs_root}/project-info/` summaries only if that central directory exists."
    )

IGNORE_DIRS = {
    ".git",
    ".next",
    ".idea",
    ".vscode",
    ".venv",
    ".qwen",
    "venv",
    "__pycache__",
    "build",
    "dist",
    "target",
    "node_modules",
    "portable-runtime",
    "coverage",
    "chrome",
    "chromedriver",
    "offline",
}

TEXT_SUFFIXES = {
    ".cmd",
    ".css",
    ".gradle",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".less",
    ".md",
    ".properties",
    ".py",
    ".scss",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}

BUILD_AND_CONFIG_FILES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "requirements.txt",
    "pyproject.toml",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.ts",
    "vue.config.js",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

ENTRYPOINT_PATTERNS = (
    re.compile(r"\bnew\s+Router\b|\broutes\s*:", re.IGNORECASE),
    re.compile(r"\bcreateRouter\b|\bRouterModule\.forRoot\b", re.IGNORECASE),
    re.compile(r"@(Get|Post|Put|Delete|Patch)?Mapping\b|@RequestMapping\b"),
    re.compile(r"@(app|router)\.(get|post|put|delete|patch)\b"),
    re.compile(r"\bFastAPI\s*\("),
    re.compile(r"\bReactDOM\.createRoot\b|\bcreateApp\s*\("),
)

API_PATTERNS = (
    re.compile(r"\baxios\.(get|post|put|delete|patch)\s*\(", re.IGNORECASE),
    re.compile(r"\bfetch\s*\(", re.IGNORECASE),
    re.compile(r"@(Get|Post|Put|Delete|Patch)?Mapping\b|@RequestMapping\b"),
    re.compile(r"\bRestTemplate\b|\bWebClient\b|\bFeignClient\b"),
    re.compile(r"\bEAI\b|eai[-_A-Za-z0-9]*|service[-_ ]?id", re.IGNORECASE),
)

FLOW_PATTERNS = (
    re.compile(r"\bpath\s*:\s*['\"]"),
    re.compile(r"\bname\s*:\s*['\"]"),
    re.compile(r"\bmethods\s*:\s*\{|\bcomputed\s*:\s*\{|\bwatch\s*:\s*\{"),
    re.compile(r"\bcontroller\b|\bservice\b|\bmapper\b", re.IGNORECASE),
    re.compile(r"\bsubmit\b|\bsave\b|\bload\b|\bfetch\b|\bclaim\b", re.IGNORECASE),
)


def analyze_project_info(root: Path | str, write: bool = False) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    files = _collect_project_files(project_root)
    profile = detect_project_info_profile(project_root)
    artifact_dir = project_info_artifact_dir(project_root)
    artifacts = _build_artifacts(project_root, files, profile)
    source_manifest = _build_source_manifest(project_root, files)
    bundle: dict[str, Any] = {
        "schema_version": PROJECT_INFO_SCHEMA_VERSION,
        "generated_at": now_iso(),
        "project_name": project_root.name,
        "root_path": str(project_root),
        "project_docs_root": project_docs_display_path(project_docs_root(project_root)),
        "project_docs_key": project_docs_key(project_root),
        "artifact_dir": project_docs_display_path(artifact_dir),
        "profile": profile,
        "artifact_order": list(PROJECT_INFO_ARTIFACT_NAMES),
        "artifacts": artifacts,
        "analysis_log": _analysis_log_for_profile(profile),
        "source_manifest": source_manifest,
    }
    errors = validate_project_info_bundle(project_root, bundle)
    bundle["validation"] = {"ok": not errors, "errors": errors}
    if write:
        if errors:
            raise ValueError("Project Info Layer validation failed before write: " + "; ".join(errors[:8]))
        write_project_info_bundle(project_root, bundle)
    return bundle


def write_project_info_bundle(root: Path | str, bundle: dict[str, Any]) -> None:
    project_root = Path(root).expanduser().resolve()
    artifact_dir = _artifact_dir(project_root)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / PROJECT_INFO_JSON).write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for artifact_name in PROJECT_INFO_ARTIFACT_NAMES:
        artifact = bundle["artifacts"][artifact_name]
        artifact_path = artifact_dir / f"{artifact_name}.md"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_artifact_markdown(bundle, artifact_name, artifact),
            encoding="utf-8",
        )


def load_project_info_bundle(root: Path | str) -> dict[str, Any] | None:
    path = _artifact_dir(Path(root).expanduser().resolve()) / PROJECT_INFO_JSON
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def describe_project_info_status(root: Path | str, work_mode: WorkMode | str = "ultrawork") -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    mode = normalize_work_mode(str(work_mode))
    bundle = load_project_info_bundle(project_root)
    if bundle is None:
        return _missing_project_info_status(mode, project_root)
    validation_errors = validate_project_info_bundle(project_root, bundle)
    stale = collect_project_info_stale_inputs(project_root, bundle)
    return _loaded_project_info_status(bundle, mode, validation_errors, stale)


def load_project_info_context(
    root: Path | str,
    work_mode: WorkMode | str = "ultrawork",
    max_chars: int = PROJECT_INFO_CONTEXT_MAX_CHARS,
) -> str:
    project_root = Path(root).expanduser().resolve()
    mode = normalize_work_mode(str(work_mode))
    knowledge_status = _project_knowledge_status(project_root, mode)
    bundle = load_project_info_bundle(project_root)
    if bundle is None:
        status = _missing_project_info_status(mode, project_root)
        lines = [
            "# Project Info Layer",
            "",
            f"- Work mode: {work_mode_definition(mode).label}",
            "- Status: missing",
            "- Profile: missing",
            f"- Artifact path: {status['artifact_path']}",
            f"- Action: {status['action']}",
            "",
            "## Required reading",
            *_bullet_lines(status["required_reading"]),
            "",
            *_render_project_knowledge_context(knowledge_status),
            "",
            "## Target files/domain hints",
            "- Project Info Layer is missing. Do not infer a default architecture or domain map; refresh Project Info first.",
        ]
        return "\n".join(lines).strip() + "\n"

    validation_errors = validate_project_info_bundle(project_root, bundle)
    stale = collect_project_info_stale_inputs(project_root, bundle)
    status = _loaded_project_info_status(bundle, mode, validation_errors, stale)
    implementation_agent = str(status.get("profile", {}).get("implementation_agent", "coder-35"))
    if mode == "fast":
        implementation_agent = "FAST direct mode"
    lines = [
        "# Project Info Layer",
        "",
        f"- Work mode: {work_mode_definition(mode).label}",
        f"- Status: {status['status']}",
        f"- Schema: {bundle.get('schema_version')}",
        f"- Generated at: {bundle.get('generated_at')}",
        f"- Artifact dir: {bundle.get('artifact_dir')}",
        f"- Profile: {bundle.get('profile', {}).get('key', 'generic')}",
        (
            f"- Execution owner: {implementation_agent}"
            if mode == "fast"
            else f"- Implementation agent: {implementation_agent}"
        ),
        f"- Stale: {str(stale.get('is_stale')).lower()}",
    ]
    if validation_errors:
        lines.append("- Validation errors: " + "; ".join(validation_errors[:5]))
    if stale.get("is_stale"):
        changed = ", ".join(item["path"] for item in stale.get("changed", [])[:8])
        added = ", ".join(item["path"] for item in stale.get("added", [])[:8])
        missing = ", ".join(item["path"] for item in stale.get("missing", [])[:8])
        lines.extend(
            [
                f"- Changed inputs: {changed or '(none)'}",
                f"- Added inputs: {added or '(none)'}",
                f"- Missing inputs: {missing or '(none)'}",
                "- Action: Project Info refresh required before relying on shared project facts.",
            ]
        )
    lines.append("")
    lines.extend(
        [
            "## Required reading",
            *_bullet_lines(status["required_reading"]),
            "",
            *_render_project_knowledge_context(knowledge_status),
            "",
            "## Target files/domain hints",
            *_bullet_lines([*status["target_hints"], *status["domain_hints"]]),
            "",
        ]
    )

    artifacts = bundle.get("artifacts", {})
    for artifact_name in PROJECT_INFO_ARTIFACT_NAMES:
        artifact = artifacts.get(artifact_name, {})
        artifact_summary = str(artifact.get("summary") or "").strip()
        if mode == "fast":
            artifact_summary = _redact_fast_only_project_info(artifact_summary)
        lines.extend(
            [
                f"## {artifact_name}",
                "",
                artifact_summary,
                "",
            ]
        )
        for item in artifact.get("items", [])[:12]:
            title = str(item.get("title") or "")
            summary = str(item.get("summary") or "")
            if mode == "fast":
                title = _redact_fast_only_project_info(title)
                summary = _redact_fast_only_project_info(summary)
            evidence_text = "; ".join(_format_evidence_short(evidence) for evidence in item.get("evidence", [])[:4])
            lines.append(f"- {title}: {summary}")
            lines.append(f"  Evidence: {evidence_text}")
        lines.append("")

    text = "\n".join(lines).strip() + "\n"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Project Info Layer context truncated]\n"


def assert_project_info_loadable_for_work_modes(root: Path | str) -> None:
    project_root = Path(root).expanduser().resolve()
    bundle = load_project_info_bundle(project_root)
    if bundle is None:
        raise AssertionError("Project Info Layer bundle is missing")
    errors = validate_project_info_bundle(project_root, bundle)
    if errors:
        raise AssertionError("Project Info Layer bundle is invalid: " + "; ".join(errors[:8]))
    for mode in ("fast", "ultrawork", "superpowers"):
        context = load_project_info_context(project_root, mode)
        if "Project Info Layer" not in context or "project-summary" not in context or "Evidence:" not in context:
            raise AssertionError(f"Project Info Layer is not loadable for {mode}")


def _missing_project_info_status(mode: WorkMode, root: Path | str | None = None) -> dict[str, Any]:
    artifact_dir = project_docs_display_path(
        project_info_artifact_dir(root) if root is not None else aiops_docs_root() / "<project-key>" / PROJECT_INFO_ARTIFACT_DIR
    )
    return {
        "status": "missing",
        "work_mode": work_mode_definition(mode).label,
        "profile": {"key": "missing", "label": "Project Info missing"},
        "artifact_dir": artifact_dir,
        "artifact_path": f"{artifact_dir}/{PROJECT_INFO_JSON}",
        "stale": {
            "schema_stale": False,
            "is_stale": False,
            "changed": [],
            "missing": [],
            "added": [],
        },
        "required_reading": [
            "D:/aiops/docs/<project-key>/knowledge/00-index.md (read first when present)",
            f"{artifact_dir}/ (optional Project Info directory; read only if it exists)",
            "Run Project Info refresh before relying on generated Project Info summaries.",
        ],
        "target_hints": [],
        "domain_hints": [],
        "action": "Project Info Layer missing: use central knowledge docs and current files now; run Project Info refresh before relying on generated summaries.",
    }


def _loaded_project_info_status(
    bundle: dict[str, Any],
    mode: WorkMode,
    validation_errors: list[str],
    stale: dict[str, Any],
) -> dict[str, Any]:
    raw_profile = bundle.get("profile", {})
    profile = {
        "key": str(raw_profile.get("key") or "generic"),
        "label": str(raw_profile.get("label") or raw_profile.get("key") or "generic"),
    }
    if mode == "fast":
        profile["execution_owner"] = "FAST direct mode"
    else:
        profile["implementation_agent"] = str(raw_profile.get("implementation_agent") or "coder-35")

    if validation_errors:
        status = "invalid"
        action = "Project Info validation failed; run Project Info refresh before relying on shared project facts."
    elif stale.get("is_stale"):
        status = "stale"
        action = "Project Info refresh required before relying on changed, added, or missing tracked inputs."
    else:
        status = "ready"
        action = "Use the summarized Project Info Layer as starting context, then verify against current files."

    project_root = Path(str(bundle.get("root_path") or ".")).expanduser()
    knowledge_status = _project_knowledge_status(project_root, mode)
    return {
        "status": status,
        "work_mode": work_mode_definition(mode).label,
        "schema_version": bundle.get("schema_version"),
        "generated_at": bundle.get("generated_at"),
        "profile": profile,
        "artifact_dir": bundle.get("artifact_dir") or PROJECT_INFO_ARTIFACT_DIR.as_posix(),
        "artifact_path": f"{bundle.get('artifact_dir') or PROJECT_INFO_ARTIFACT_DIR.as_posix()}/{PROJECT_INFO_JSON}",
        "stale": stale,
        "validation_errors": validation_errors[:8],
        "required_reading": _project_info_required_reading(bundle),
        "project_knowledge": knowledge_status,
        "target_hints": _project_info_target_hints(bundle),
        "domain_hints": _project_info_domain_hints(bundle, mode),
        "action": action,
    }


def _project_info_required_reading(bundle: dict[str, Any], limit: int = 12) -> list[str]:
    artifact_dir = str(bundle.get("artifact_dir") or PROJECT_INFO_ARTIFACT_DIR.as_posix()).rstrip("/")
    required: list[str] = []
    root_path = str(bundle.get("root_path") or "").strip()
    if root_path:
        required.extend(_project_knowledge_required_reading(Path(root_path), limit=6))
    else:
        required.append("D:/aiops/docs/<project-key>/knowledge/00-index.md (read first when present)")
    required.extend(f"{artifact_dir}/{artifact_name}.md (optional Project Info summary)" for artifact_name in PROJECT_INFO_ARTIFACT_NAMES)
    required.append(f"{artifact_dir}/{PROJECT_INFO_JSON} metadata only; do not paste the full JSON into prompts.")
    return required[:limit]


def _project_knowledge_status(project_root: Path, mode: WorkMode) -> dict[str, Any]:
    root = project_root.expanduser().resolve()
    knowledge_root = project_knowledge_dir(root)
    index = knowledge_root / "00-index.md"
    display_path = project_docs_display_path(knowledge_root)
    if not index.exists():
        return {
            "status": "missing",
            "path": display_path,
            "profile": "missing",
            "version": "missing",
            "required_reading": [f"{display_path}/00-index.md (missing)"],
            "detail_dirs": [],
            "action": f"Project knowledge pack is optional but recommended for DRT/DCP work; install it under {display_path} when available.",
        }
    metadata = _safe_project_knowledge_metadata(index)
    return {
        "status": "ready",
        "path": display_path,
        "profile": metadata.get("profile") or "unknown",
        "version": metadata.get("kiwi_knowledge_pack_version") or metadata.get("version") or "unknown",
        "required_reading": _project_knowledge_required_reading(root),
        "detail_dirs": _project_knowledge_detail_docs(root),
        "action": "Read this seed knowledge pack before broad analysis, then verify every claim against current files and Project Info evidence.",
    }


def _project_knowledge_required_reading(project_root: Path, limit: int = 14) -> list[str]:
    root = project_root.expanduser().resolve()
    knowledge_root = project_knowledge_dir(root)
    display_root = project_docs_display_path(knowledge_root)
    if not knowledge_root.exists():
        return []
    required: list[str] = []
    for filename in PROJECT_KNOWLEDGE_REQUIRED_FILES:
        path = knowledge_root / filename
        if path.exists():
            required.append(f"{display_root}/{filename}")
            if len(required) >= limit:
                return required
    return required


def _project_knowledge_detail_docs(project_root: Path, limit: int = 12) -> list[str]:
    root = project_root.expanduser().resolve()
    knowledge_root = project_knowledge_dir(root)
    display_root = project_docs_display_path(knowledge_root)
    details: list[str] = []
    for dirname in PROJECT_KNOWLEDGE_DETAIL_DIRS:
        for path in sorted((knowledge_root / dirname).glob("*.md")):
            details.append(f"{display_root}/{dirname}/{path.name}")
            if len(details) >= limit:
                return details
    return details


def _safe_project_knowledge_metadata(index_path: Path) -> dict[str, str]:
    try:
        text = index_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    _, _, rest = text.partition("\n")
    front_matter, sep, _body = rest.partition("\n---")
    if not sep:
        return {}
    metadata: dict[str, str] = {}
    for raw_line in front_matter.splitlines():
        key, sep, value = raw_line.partition(":")
        if not sep:
            continue
        key = key.strip()
        if key not in {"kiwi_knowledge_pack_version", "version", "profile", "source_reference"}:
            continue
        metadata[key] = value.strip().strip('"').strip("'")
    return metadata


def _render_project_knowledge_context(status: dict[str, Any]) -> list[str]:
    lines = [
        "## Project Knowledge Pack",
        f"- Status: {status.get('status')}",
        f"- Path: {status.get('path')}",
        f"- Version: {status.get('version')}",
        f"- Profile: {status.get('profile')}",
        f"- Action: {status.get('action')}",
        "- Rule: treat the central knowledge pack as seed project knowledge; current repository files and Project Info evidence remain the source of truth.",
        "- Do not paste full knowledge-pack files into prompts. Read only the relevant docs and cite path evidence.",
        "### Knowledge reading",
        *_bullet_lines([str(item) for item in status.get("required_reading", [])[:14]]),
    ]
    details = [str(item) for item in status.get("detail_dirs", [])[:12]]
    if details:
        lines.extend(["", "### Knowledge detail docs", *_bullet_lines(details)])
    return lines


def _project_info_target_hints(bundle: dict[str, Any], limit: int = 14) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for artifact in bundle.get("artifacts", {}).values():
        for item in artifact.get("items", []):
            for evidence in item.get("evidence", []):
                path = str(evidence.get("path") or "").strip()
                if not path or path in seen:
                    continue
                seen.add(path)
                symbol = str(evidence.get("symbol") or evidence.get("name") or "").strip()
                hint = f"{path}" + (f" ({symbol})" if symbol else "")
                hints.append(hint[:260])
                if len(hints) >= limit:
                    return hints
    return hints or ["No target file hints were extracted; search current files before editing."]


def _project_info_domain_hints(bundle: dict[str, Any], mode: WorkMode, limit: int = 14) -> list[str]:
    hints: list[str] = []
    seen: set[str] = set()
    for artifact_name in PROJECT_INFO_ARTIFACT_NAMES:
        artifact = bundle.get("artifacts", {}).get(artifact_name, {})
        for item in artifact.get("items", []):
            title = str(item.get("title") or "").strip()
            kind = str(item.get("kind") or "").strip()
            summary = str(item.get("summary") or "").strip()
            if mode == "fast":
                summary = _redact_fast_only_project_info(summary)
                title = _redact_fast_only_project_info(title)
                kind = _redact_fast_only_project_info(kind)
            hint = f"{artifact_name}: {kind}: {title} - {summary}"[:300]
            key = hint.lower()
            if not title or key in seen:
                continue
            seen.add(key)
            hints.append(hint)
            if len(hints) >= limit:
                return hints
    return hints or ["No domain hints were extracted; treat Project Info as incomplete and search current files."]


def _bullet_lines(items: list[Any]) -> list[str]:
    lines = []
    for item in items:
        text = str(item).strip()
        if text:
            lines.append(f"- {text}")
    return lines or ["- (none)"]


def collect_project_info_stale_inputs(root: Path | str, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    if bundle is None:
        bundle = load_project_info_bundle(project_root) or {}
    files = _collect_project_files(project_root)
    current = _build_source_manifest(project_root, files)
    previous = bundle.get("source_manifest") if isinstance(bundle, dict) else {}
    if not isinstance(previous, dict):
        previous = {}

    changed: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []

    for rel, old_meta in sorted(previous.items()):
        new_meta = current.get(rel)
        if new_meta is None:
            missing.append({"path": rel, "reason": "tracked input no longer exists"})
            continue
        if _manifest_signature(old_meta) != _manifest_signature(new_meta):
            changed.append({"path": rel, "reason": "tracked input content changed"})

    for rel in sorted(set(current) - set(previous)):
        added.append({"path": rel, "reason": "new stale-relevant input"})

    schema_stale = bundle.get("schema_version") != PROJECT_INFO_SCHEMA_VERSION
    return {
        "schema_stale": schema_stale,
        "is_stale": bool(schema_stale or changed or missing or added),
        "changed": changed,
        "missing": missing,
        "added": added,
        "tracked_count": len(previous),
        "current_count": len(current),
    }


def validate_project_info_bundle(root: Path | str, bundle: dict[str, Any]) -> list[str]:
    project_root = Path(root).expanduser().resolve()
    errors: list[str] = []
    if bundle.get("schema_version") != PROJECT_INFO_SCHEMA_VERSION:
        errors.append("schema_version mismatch")

    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, dict):
        return errors + ["artifacts must be an object"]

    for artifact_name in PROJECT_INFO_ARTIFACT_NAMES:
        artifact = artifacts.get(artifact_name)
        if not isinstance(artifact, dict):
            errors.append(f"{artifact_name}: missing artifact")
            continue
        items = artifact.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{artifact_name}: missing items")
            continue
        for index, item in enumerate(items):
            item_id = str(item.get("id") or f"item-{index}") if isinstance(item, dict) else f"item-{index}"
            if not isinstance(item, dict):
                errors.append(f"{artifact_name}.{item_id}: item must be an object")
                continue
            evidence_list = item.get("evidence")
            if not isinstance(evidence_list, list) or not evidence_list:
                errors.append(f"{artifact_name}.{item_id}: missing evidence")
                continue
            for evidence_index, evidence in enumerate(evidence_list):
                errors.extend(_validate_evidence(project_root, artifact_name, item_id, evidence_index, evidence))
    return errors


def detect_project_info_profile(root: Path | str) -> dict[str, Any]:
    project_root = Path(root).expanduser().resolve()
    policy_profile = detect_project_profile(project_root)
    evidence: list[dict[str, Any]] = []
    key = policy_profile.key if policy_profile else "generic"
    label = policy_profile.label if policy_profile else "Generic"
    implementation_agent = policy_profile.developer_agent if policy_profile else "coder-35"

    if key == "dcp-front":
        evidence.extend(_dcp_front_profile_evidence(project_root))
    elif key == "dcp-services":
        evidence.extend(_dcp_services_profile_evidence(project_root))
    elif key == "drt-front":
        evidence.extend(_drt_front_profile_evidence(project_root))
    elif key == "drt-api":
        evidence.extend(_drt_api_profile_evidence(project_root))
    elif key == "drt-cms":
        evidence.extend(_drt_cms_profile_evidence(project_root))
    if not evidence:
        evidence.append(_fallback_evidence(project_root, "profile", "Project profile fallback evidence."))

    return {
        "key": key,
        "label": label,
        "implementation_agent": implementation_agent,
        "evidence": evidence,
    }


def _build_artifacts(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    builders = {
        "project-summary": _artifact_project_summary,
        "architecture-map": _artifact_architecture_map,
        "module-responsibility-map": _artifact_module_responsibility_map,
        "entrypoints": _artifact_entrypoints,
        "key-flows": _artifact_key_flows,
        "api/eai-interface-index": _artifact_api_eai_interface_index,
        "verification-guide": _artifact_verification_guide,
    }
    artifacts = {name: builders[name](root, files, profile) for name in PROJECT_INFO_ARTIFACT_NAMES}
    if profile.get("key") == "dcp-front":
        _enhance_dcp_front_artifacts(root, files, artifacts)
    elif profile.get("key") == "dcp-services":
        _enhance_dcp_services_artifacts(root, files, artifacts)
    elif profile.get("key") == "drt-front":
        _enhance_drt_front_artifacts(root, files, artifacts)
    elif profile.get("key") == "drt-api":
        _enhance_drt_api_artifacts(root, files, artifacts)
    elif profile.get("key") == "drt-cms":
        _enhance_drt_cms_artifacts(root, files, artifacts)
    return artifacts


def _artifact_project_summary(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    stack = _detect_stack(root)
    key_config = _existing(paths=BUILD_AND_CONFIG_FILES, files=files)
    items = [
        {
            "id": "project-profile",
            "title": "Project profile",
            "summary": f"{profile['key']} profile maps implementation work to {profile['implementation_agent']}.",
            "evidence": profile["evidence"],
        },
        {
            "id": "detected-stack",
            "title": "Detected stack",
            "summary": ", ".join(stack) if stack else "No known stack marker was detected.",
            "evidence": _evidence_for_paths(root, key_config[:6], "stack", "Build or package descriptor used for stack detection."),
        },
        {
            "id": "source-footprint",
            "title": "Source footprint",
            "summary": f"{len(files)} text/project files were scanned outside generated directories.",
            "evidence": [_fallback_evidence(root, "source-footprint", "Representative file from deterministic project scan.")],
        },
    ]
    return _artifact("Project Summary", "Basic project identity, profile, stack, and scan boundary.", items)


def _artifact_architecture_map(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    del profile
    top_dirs = _top_level_directories(files)
    items: list[dict[str, Any]] = []
    for directory in top_dirs[:10]:
        representative = _first_file_under(files, directory + "/")
        if representative is None:
            continue
        items.append(
            {
                "id": _slug(f"dir-{directory}"),
                "title": directory,
                "summary": _directory_responsibility(directory),
                "evidence": [_evidence(root, representative, None, directory, "Representative file under this architecture area.")],
            }
        )
    if not items:
        items.append(_fallback_item(root, "architecture-map", "No top-level source directory was detected."))
    return _artifact("Architecture Map", "Top-level areas and their evidence-backed responsibilities.", items)


def _artifact_module_responsibility_map(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    source_roots = [prefix for prefix in ("app", "pages", "src", "backend", "public") if any(f == prefix or f.startswith(prefix + "/") for f in files)]
    for prefix in source_roots:
        children = _child_directories(files, prefix)
        if children:
            for child in children[:8]:
                representative = _first_file_under(files, f"{prefix}/{child}/")
                if representative:
                    path = f"{prefix}/{child}"
                    items.append(
                        {
                            "id": _slug(path),
                            "title": path,
                            "summary": _directory_responsibility(path),
                            "evidence": [_evidence(root, representative, None, path, "Representative file for module responsibility.")],
                        }
                    )
        else:
            representative = _first_file_under(files, prefix + "/")
            if representative:
                items.append(
                    {
                        "id": _slug(prefix),
                        "title": prefix,
                        "summary": _directory_responsibility(prefix),
                        "evidence": [_evidence(root, representative, None, prefix, "Representative source root file.")],
                    }
                )

    maven_modules = _maven_modules(root)
    for module in maven_modules[:20]:
        items.append(
            {
                "id": _slug(f"maven-{module['name']}"),
                "title": module["name"],
                "summary": "Maven module declared by the root pom.xml.",
                "evidence": [module["evidence"]],
            }
        )

    if profile["key"] == "dcp-front":
        datastore = "src/store/modules/com/DataStore.js"
        if datastore in files:
            items.append(
                {
                    "id": "dcp-front-datastore",
                    "title": "DCP front DataStore",
                    "summary": "Shared Vuex/DataStore carrier for DCP front flows.",
                    "evidence": [_evidence(root, datastore, _line_for_pattern(root / datastore, r"state|mutations|export"), "DataStore", "DCP front profile marker and shared state module.")],
                }
            )

    if not items:
        items.append(_fallback_item(root, "module-responsibility-map", "No module roots were detected."))
    return _artifact("Module Responsibility Map", "Module roots, Maven modules, and DCP-specific shared carriers.", items)


def _artifact_entrypoints(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    del profile
    matches = _pattern_matches(root, files, ENTRYPOINT_PATTERNS, limit=40)
    preferred_files = [
        "app/page.tsx",
        "pages/index.tsx",
        "src/main.js",
        "src/main.ts",
        "src/main.tsx",
        "src/router/index.js",
        "src/router/index.ts",
        "backend/app/main.py",
    ]
    for rel in preferred_files:
        if rel in files and not any(match["path"] == rel for match in matches):
            matches.insert(0, {"path": rel, "line": 1, "text": Path(root / rel).read_text(encoding="utf-8", errors="ignore").splitlines()[0] if (root / rel).exists() else rel})

    items = [
        {
            "id": _slug(f"entry-{match['path']}-{match.get('line', 1)}"),
            "title": match["path"],
            "summary": "Potential runtime or route entrypoint detected from framework markers.",
            "evidence": [_evidence(root, match["path"], match.get("line"), _symbol_from_text(match.get("text", "")) or "entrypoint", "Framework entrypoint marker.")],
        }
        for match in _dedupe_matches(matches)[:16]
    ]
    if not items:
        items.append(_fallback_item(root, "entrypoints", "No framework entrypoint marker was detected."))
    return _artifact("Entrypoints", "Detected route, app, controller, or framework entrypoints.", items)


def _artifact_key_flows(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    matches = _pattern_matches(root, files, FLOW_PATTERNS, limit=80)
    route_matches = [match for match in matches if "path" in match.get("text", "")]
    action_matches = [match for match in matches if match not in route_matches]
    selected = route_matches[:8] + action_matches[:8]
    items = [
        {
            "id": _slug(f"flow-{match['path']}-{match.get('line', 1)}"),
            "title": _flow_title(match),
            "summary": "Candidate user or backend flow marker. Expand in detailed docs before implementation decisions.",
            "evidence": [_evidence(root, match["path"], match.get("line"), _symbol_from_text(match.get("text", "")) or "flow-marker", "Route/action/service marker used to seed flow analysis.")],
        }
        for match in _dedupe_matches(selected)
    ]
    if profile["key"] == "dcp-front":
        dcp_routes = [match for match in route_matches if "mysamsunglife" in match["path"].lower() or "claim" in match.get("text", "").lower()]
        for match in dcp_routes[:4]:
            items.insert(
                0,
                {
                    "id": _slug(f"dcp-front-flow-{match['path']}-{match.get('line', 1)}"),
                    "title": "DCP front route flow seed",
                    "summary": "DCP front route/view marker for later route -> view -> store -> API flow tracing.",
                    "evidence": [_evidence(root, match["path"], match.get("line"), "dcp-front-flow", "DCP front route or claim marker.")],
                },
            )
    if not items:
        items.append(_fallback_item(root, "key-flows", "No route/action flow marker was detected."))
    return _artifact("Key Flows", "Route, action, controller, and service markers that seed later flow documents.", items[:18])


def _artifact_api_eai_interface_index(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    del profile
    matches = _pattern_matches(root, files, API_PATTERNS, limit=120)
    items = [
        {
            "id": _slug(f"interface-{match['path']}-{match.get('line', 1)}"),
            "title": _api_title(match),
            "summary": "API, controller mapping, client call, or EAI marker detected by deterministic scan.",
            "evidence": [_evidence(root, match["path"], match.get("line"), _symbol_from_text(match.get("text", "")) or "interface", "API/EAI interface marker.")],
        }
        for match in _dedupe_matches(matches)[:24]
    ]
    if not items:
        items.append(_fallback_item(root, "api/eai-interface-index", "No API/EAI marker was detected."))
    return _artifact("API/EAI Interface Index", "Interface markers for frontend API clients, backend controllers, and EAI/external calls.", items)


def _artifact_verification_guide(root: Path, files: list[str], profile: dict[str, Any]) -> dict[str, Any]:
    del profile
    items: list[dict[str, Any]] = []
    package = _read_json(root / "package.json")
    if isinstance(package, dict):
        scripts = package.get("scripts", {})
        if isinstance(scripts, dict):
            for script_name in ("typecheck", "lint", "test", "build", "dev"):
                if script_name in scripts:
                    items.append(
                        {
                            "id": _slug(f"npm-{script_name}"),
                            "title": f"npm run {script_name}",
                            "summary": f"Package script command: {scripts[script_name]}",
                            "evidence": [_evidence(root, "package.json", _line_for_pattern(root / "package.json", rf'"{re.escape(script_name)}"\s*:'), script_name, "package.json script entry.")],
                        }
                    )
    if "pom.xml" in files:
        items.append(
            {
                "id": "maven-package",
                "title": "mvn package",
                "summary": "Maven build candidate because pom.xml exists at project root.",
                "evidence": [_evidence(root, "pom.xml", _line_for_pattern(root / "pom.xml", r"<project|<modules|<artifactId>"), "pom.xml", "Root Maven descriptor.")],
            }
        )
    if "build.gradle" in files or "build.gradle.kts" in files:
        gradle_file = "build.gradle" if "build.gradle" in files else "build.gradle.kts"
        items.append(
            {
                "id": "gradle-build",
                "title": "gradle build",
                "summary": "Gradle build candidate because a Gradle build file exists.",
                "evidence": [_evidence(root, gradle_file, _line_for_pattern(root / gradle_file, r"plugins|dependencies|tasks"), gradle_file, "Gradle build descriptor.")],
            }
        )
    test_roots = [path for path in files if "/test/" in path or path.startswith("test/") or path.startswith("tests/")]
    for path in test_roots[:8]:
        items.append(
            {
                "id": _slug(f"test-root-{path}"),
                "title": path,
                "summary": "Test source or fixture path detected.",
                "evidence": [_evidence(root, path, 1, "test", "Representative test path.")],
            }
        )
    if not items:
        items.append(_fallback_item(root, "verification-guide", "No explicit verification command was detected."))
    return _artifact("Verification Guide", "Commands and test roots that can verify future changes.", items)


def _enhance_dcp_front_artifacts(root: Path, files: list[str], artifacts: dict[str, Any]) -> None:
    artifacts["architecture-map"]["items"].extend(
        [
            _kind_item(
                "dcp-front-routing-layer",
                "DCP front routing layer",
                "Vue Router files under src/router bind mobile/PC channel paths to screen components.",
                [_first_evidence(root, files, "src/router/", "routes|path:|component:", "src/router", "Router file used for screen navigation.")],
                "route-view-flow",
                ["dcp-front", "router"],
            ),
            _kind_item(
                "dcp-front-view-layer",
                "DCP front view layer",
                "Screen files under src/views are Vue single-file components; mysamsunglife mobile screens live under src/views/mo/mysamsunglife.",
                [_first_evidence(root, files, "src/views/mo/mysamsunglife/", "<template|name:", "src/views", "Representative mobile screen component.")],
                "screen-role",
                ["dcp-front", "screen"],
            ),
            _kind_item(
                "dcp-front-store-layer",
                "DCP front Vuex store layer",
                "Vuex modules are registered from src/store/index.js and include the shared data module used by long flows.",
                _existing_evidence(
                    root,
                    [
                        ("src/store/index.js", r"DataStore|modules", "store/index.js", "Vuex module registration."),
                        ("src/store/modules/com/DataStore.js", r"export|state|setData|DataStore", "DataStore", "Shared DataStore module."),
                    ],
                ),
                "datastore-flow",
                ["dcp-front", "store"],
            ),
        ]
    )

    screen_items = _dcp_front_screen_items(root, files)
    flow_items = _dcp_front_route_flow_items(root, files)
    component_items = _dcp_front_component_items(root, files)
    datastore_items = _dcp_front_datastore_items(root, files)
    api_items = _dcp_front_api_items(root, files)
    verification_items = _dcp_front_verification_items(root, files)

    artifacts["module-responsibility-map"]["items"].extend(screen_items[:6] + component_items[:4] + datastore_items[:2])
    artifacts["entrypoints"]["items"].extend(flow_items[:10])
    artifacts["key-flows"]["items"].extend(flow_items[:10] + datastore_items + api_items[:6])
    artifacts["api/eai-interface-index"]["items"].extend(api_items[:16])
    artifacts["verification-guide"]["items"].extend(verification_items)
    _dedupe_all_artifacts(artifacts)


def _enhance_dcp_services_artifacts(root: Path, files: list[str], artifacts: dict[str, Any]) -> None:
    module_items = _dcp_services_module_items(root)
    package_items = _dcp_services_package_items(root, files)
    controller_items = _dcp_services_controller_flow_items(root, files)
    repository_items = _dcp_services_repository_items(root, files)
    config_items = _dcp_services_config_items(root, files)
    scheduler_items = _dcp_services_scheduler_items(root, files)
    eai_items = _dcp_services_eai_items(root, files)
    dto_items = _dcp_services_dto_items(root, files)
    verification_items = _dcp_services_verification_items(root, files)

    artifacts["architecture-map"]["items"].extend(module_items[:10] + config_items[:4])
    artifacts["module-responsibility-map"]["items"].extend(module_items + package_items[:18] + repository_items[:6])
    artifacts["entrypoints"]["items"].extend(controller_items[:16] + scheduler_items[:4])
    artifacts["key-flows"]["items"].extend(controller_items[:14] + scheduler_items + dto_items[:8])
    artifacts["api/eai-interface-index"]["items"].extend(eai_items + controller_items[:12] + dto_items[:10])
    artifacts["verification-guide"]["items"].extend(verification_items + config_items[:4])
    _dedupe_all_artifacts(artifacts)


def _dcp_front_screen_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    families = [
        ("insurance/internet", "Insurance internet claim/application mobile screens"),
        ("insurance/give", "Insurance payment/give mobile screens"),
        ("insurance/finds", "Insurance finds mobile screens"),
        ("insurance/chng", "Insurance change mobile screens"),
        ("fund/trading", "Fund trading mobile screens"),
        ("fund/pension", "Fund pension mobile screens"),
        ("fund/transfer", "Fund transfer mobile screens"),
        ("mycontract", "My contract mobile screens"),
    ]
    items: list[dict[str, Any]] = []
    for family, role in families:
        view_prefix = f"src/views/mo/mysamsunglife/{family}/"
        route = f"src/router/mo/mysamsunglife/{family}/route.js"
        views = [rel for rel in files if rel.startswith(view_prefix) and rel.endswith(".vue")][:5]
        evidence: list[dict[str, Any]] = []
        if route in files:
            evidence.append(_evidence(root, route, _line_for_pattern(root / route, r"path:|name:|components:"), family, "Route file for this screen family."))
        for view in views[:3]:
            evidence.append(_evidence(root, view, _line_for_pattern(root / view, r"<template|name:|@exports"), Path(view).stem, "Representative Vue screen file."))
        if evidence:
            items.append(
                _kind_item(
                    f"dcp-front-screen-{family}",
                    family,
                    f"{role}; concrete view files include {', '.join(Path(view).name for view in views[:3])}.",
                    evidence,
                    "screen-role",
                    ["dcp-front", "screen", family],
                    {"view_files": views},
                )
            )
    return items


def _dcp_front_route_flow_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    route_files = [
        rel
        for rel in files
        if rel.startswith("src/router/mo/mysamsunglife/") and rel.endswith("/route.js")
    ][:80]
    priority = sorted(
        route_files,
        key=lambda rel: (
            0 if "insurance/internet" in rel else 1 if "insurance" in rel else 2 if "fund" in rel else 3,
            rel,
        ),
    )
    items: list[dict[str, Any]] = []
    for route in priority[:18]:
        routes = _extract_vue_route_entries(root / route, limit=4)
        if not routes:
            evidence = [_evidence(root, route, _line_for_pattern(root / route, r"path:|components:"), Path(route).parent.name, "Route file with no parsed leaf entry.")]
            summary = f"{route} defines a route family; inspect route entries before changing screens."
            entries: list[dict[str, Any]] = []
        else:
            entries = routes
            first = routes[0]
            evidence = [_evidence(root, route, first.get("line"), first.get("name") or first.get("path") or "route", "Route name/path entry.")]
            view_path = str(first.get("view_path") or "")
            if view_path and (root / view_path).exists():
                evidence.append(_evidence(root, view_path, _line_for_pattern(root / view_path, r"<template|name:|@exports"), Path(view_path).stem, "Vue view component loaded by route entry."))
            summary = f"{route} maps route names such as {', '.join(str(item.get('name') or item.get('path')) for item in routes[:3])} to Vue screen components."
        items.append(
            _kind_item(
                f"dcp-front-route-flow-{route}",
                route,
                summary,
                evidence,
                "route-view-flow",
                ["dcp-front", "router"],
                {"routes": entries},
            )
        )
    return items


def _dcp_front_component_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    candidates = [
        ("src/components/com/base/index.js", r"import|export", "Base component registry"),
        ("src/components/com/base/modal/index.js", r"import|export|Ui.*Modal", "Base modal registry"),
        ("src/components/com/base/modal/UiCommonModal.vue", r"<template|name:", "Common modal component"),
        ("src/components/com/base/loading/Spinner.vue", r"<template|name:", "Common loading spinner"),
        ("src/views/layout/mo/MobileIndexPage.vue", r"<template|name:", "Mobile layout wrapper"),
        ("src/views/layout/mo/MobileMainHeader.vue", r"<template|name:", "Mobile main header"),
    ]
    items: list[dict[str, Any]] = []
    for rel, pattern, title in candidates:
        if rel not in files:
            continue
        items.append(
            _kind_item(
                f"dcp-front-component-{rel}",
                title,
                f"{title} is a shared component/layout file used by screen families.",
                [_evidence(root, rel, _line_for_pattern(root / rel, pattern), Path(rel).stem, "Shared component evidence.")],
                "common-component",
                ["dcp-front", "component"],
            )
        )
    return items


def _dcp_front_datastore_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    evidence = _existing_evidence(
        root,
        [
            ("src/store/index.js", r"DataStore|modules|data", "store data module", "Vuex store registers the data module."),
            ("src/store/modules/com/DataStore.js", r"state|setData|SET|export", "DataStore", "Shared DataStore implementation."),
            ("src/plugins/com/Common.js", r"보험금청구 이어하기 체크|case '1001'|spotLoad|spotSave", "claim continuation", "Common plugin branches claim continuation flow."),
        ],
    )
    if evidence:
        items.append(
            _kind_item(
                "dcp-front-datastore-claim-flow",
                "DataStore and claim continuation flow",
                "The shared Vuex data module is registered as store data, and Common.js contains insurance-claim continuation routing branches.",
                evidence,
                "datastore-flow",
                ["dcp-front", "store", "claim"],
            )
        )
    return items


def _dcp_front_api_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    matches = _pattern_matches(
        root,
        [
            rel
            for rel in files
            if rel.startswith("src/") and rel.endswith((".js", ".vue"))
            and not rel.startswith("src/assets/")
        ],
        (
            re.compile(r"axios\.(get|post|put|delete|patch)\s*\("),
            re.compile(r"(?:this\.|Vue\.)?\$http\.(get|post|put|delete|patch)\s*\("),
        ),
        limit=80,
    )
    items: list[dict[str, Any]] = []
    for match in matches[:24]:
        endpoint = _extract_http_endpoint(match.get("text", ""))
        summary = (
            f"Backend call pattern uses {endpoint} from {match['path']}."
            if endpoint
            else f"Backend call pattern is present in {match['path']}; endpoint is dynamic and must be resolved from nearby variables."
        )
        items.append(
            _kind_item(
                f"dcp-front-api-{match['path']}-{match.get('line')}",
                _api_title(match),
                summary,
                [_evidence(root, match["path"], match.get("line"), endpoint or "dynamic-http-call", "Axios/Vue.$http backend call pattern.")],
                "backend-call-pattern",
                ["dcp-front", "api"],
                {"endpoint": endpoint or "dynamic"},
            )
        )
    return items


def _dcp_front_verification_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    package = _read_json(root / "package.json")
    if isinstance(package, dict) and isinstance(package.get("scripts"), dict):
        for script in ["lint", "test:unit", "test:e2e", "build"]:
            if script in package["scripts"]:
                items.append(
                    _kind_item(
                        f"dcp-front-verification-{script}",
                        f"npm run {script}",
                        f"package.json defines npm run {script} as {package['scripts'][script]}.",
                        [_evidence(root, "package.json", _line_for_pattern(root / "package.json", rf'"{re.escape(script)}"\s*:'), script, "Verification script in package.json.")],
                        "verification-command",
                        ["dcp-front", "verification"],
                        {"command": f"npm run {script}"},
                    )
                )
    for rel in [
        "tools/playwright/playwright.config.js",
        "tools/playwright/tests/insurance-claim-intro.spec.js",
        "tools/playwright/tests/helpers/claimIntro.js",
    ]:
        if rel in files:
            items.append(
                _kind_item(
                    f"dcp-front-playwright-{rel}",
                    rel,
                    "Playwright verification asset for focused browser checks.",
                    [_evidence(root, rel, _line_for_pattern(root / rel, r"test|defineConfig|claim|module\.exports|async"), Path(rel).name, "Playwright verification evidence.")],
                    "verification-command",
                    ["dcp-front", "playwright"],
                )
            )
    return items


def _dcp_services_module_items(root: Path) -> list[dict[str, Any]]:
    modules = _maven_modules(root)
    items: list[dict[str, Any]] = []
    for module in modules[:24]:
        module_pom = f"{module['name']}/pom.xml"
        evidence = [module["evidence"]]
        if (root / module_pom).exists():
            evidence.append(_evidence(root, module_pom, _line_for_pattern(root / module_pom, r"<artifactId>|<packaging>|<dependencies>"), module["name"], "Child Maven module descriptor."))
        items.append(
            _kind_item(
                f"dcp-services-module-{module['name']}",
                module["name"],
                f"{module['name']} is declared as a Maven module in the root pom.xml.",
                evidence,
                "maven-module",
                ["dcp-services", "maven"],
                {"module": module["name"]},
            )
        )
    return items


def _dcp_services_package_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    package_dirs = sorted(
        {
            "/".join(Path(rel).parts[:8])
            for rel in files
            if rel.endswith(".java")
            and len(Path(rel).parts) >= 9
            and Path(rel).parts[1:5] == ("src", "main", "java", "com")
        }
    )
    items: list[dict[str, Any]] = []
    for package_dir in package_dirs[:30]:
        representative = _first_file_under(files, package_dir + "/")
        if not representative:
            continue
        items.append(
            _kind_item(
                f"dcp-services-package-{package_dir}",
                package_dir,
                f"{package_dir} is a Java package area with controller/service/response subpackages discovered from current files.",
                [_evidence(root, representative, _line_for_pattern(root / representative, r"package |class |interface "), package_dir, "Representative Java file for package role.")],
                "package-role",
                ["dcp-services", "package"],
            )
        )
    return items


def _dcp_services_controller_flow_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    controller_files = [
        rel
        for rel in files
        if rel.endswith("Controller.java") and "/src/main/java/" in rel
    ]
    priority = sorted(
        controller_files,
        key=lambda rel: (
            0 if "dcp-insurance" in rel else 1 if "dcp-loan" in rel else 2 if "dcp-product" in rel else 3,
            rel,
        ),
    )
    items: list[dict[str, Any]] = []
    for rel in priority[:28]:
        class_line = _line_for_pattern(root / rel, r"class\s+\w+Controller")
        mapping_line = _line_for_pattern(root / rel, r"@RequestMapping")
        service_line = _line_for_pattern(root / rel, r"private\s+.*Service\s+\w+")
        response_line = _line_for_pattern(root / rel, r"resolveResponse|Response|Res\.class")
        evidence = [
            _evidence(root, rel, class_line, Path(rel).stem, "Controller class."),
            _evidence(root, rel, mapping_line, "RequestMapping", "HTTP endpoint mapping."),
        ]
        if service_line:
            evidence.append(_evidence(root, rel, service_line, "service field", "Controller delegates to service dependency."))
        if response_line:
            evidence.append(_evidence(root, rel, response_line, "response mapping", "Controller maps service result to response DTO."))
        items.append(
            _kind_item(
                f"dcp-services-controller-flow-{rel}",
                Path(rel).stem,
                f"{Path(rel).stem} exposes Spring @RequestMapping endpoints and delegates through service/response patterns in the same file.",
                evidence,
                "controller-service-flow",
                ["dcp-services", "controller"],
            )
        )
    return items


def _dcp_services_repository_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    context_files = [
        rel
        for rel in files
        if rel.endswith("applicationContext-service.xml")
        and "src/main/resources/spring/" in rel
    ]
    for rel in context_files[:12]:
        items.append(
            _kind_item(
                f"dcp-services-repository-{rel}",
                rel,
                "Repository/persistence wiring uses MyBatis SqlSessionTemplate and mapperLocations from applicationContext-service.xml.",
                _existing_evidence(
                    root,
                    [
                        (rel, r"SqlSessionTemplate", "SqlSessionTemplate", "MyBatis repository session template."),
                        (rel, r"mapperLocations", "mapperLocations", "Mapper XML location pattern."),
                    ],
                ),
                "repository-pattern",
                ["dcp-services", "repository", "mybatis"],
            )
        )
    if not items:
        evidence = _first_evidence(root, files, "", "SqlSessionTemplate|mapperLocations|@Repository|Mapper", "repository search", "unknown with searched evidence for repository pattern.")
        items.append(
            _kind_item(
                "dcp-services-repository-unknown",
                "unknown with searched evidence repository pattern",
                "unknown with searched evidence: repository pattern was searched via @Repository/Mapper/SqlSessionTemplate/mapperLocations.",
                [evidence],
                "repository-pattern",
                ["dcp-services", "repository"],
            )
        )
    return items


def _dcp_services_config_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for rel in [
        "pom.xml",
        "dcp-insurance/src/main/resources-env/WEB-INF/local/web.xml",
        "dcp-insurance/src/main/resources-env/WEB-INF/dev/web.xml",
        "dcp-insurance/src/main/resources-env/WEB-INF/stage/web.xml",
        "dcp-insurance/src/main/resources-env/WEB-INF/release/web.xml",
        "dcp-gateway/src/main/resources/spring/applicationContext-service.xml",
    ]:
        if rel not in files:
            continue
        symbol = "profile/config" if "resources-env" in rel or rel == "pom.xml" else "spring service config"
        summary = (
            "Root pom.xml defines Maven profiles and module lists for local/dev/qa/stage/release."
            if rel == "pom.xml"
            else f"{rel} is an environment/profile config file used by the module runtime."
        )
        items.append(
            _kind_item(
                f"dcp-services-config-{rel}",
                rel,
                summary,
                [_evidence(root, rel, _line_for_pattern(root / rel, r"<profile>|<id>|<web-app|<context-param|<bean|<property"), symbol, "Configuration/profile evidence.")],
                "config-profile",
                ["dcp-services", "config"],
            )
        )
    return items


def _dcp_services_scheduler_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    candidates = [
        ("dcp-async/src/main/java/com/samsunglife/dcp/async/process/context/EventProcessSchedule.java", r"class\s+EventProcessSchedule|schedule|Schedule"),
        ("dcp-async/src/main/java/com/samsunglife/dcp/async/process/context/EventProcessScheduleContext.java", r"class\s+EventProcessScheduleContext|schedule|Schedule"),
        ("dcp-async/src/main/java/com/samsunglife/dcp/async/dispatcher/executor/EventProcessorExecutor.java", r"class\s+EventProcessorExecutor|Executor"),
        ("dcp-batch/pom.xml", r"<artifactId>|dcp-batch"),
    ]
    items: list[dict[str, Any]] = []
    for rel, pattern in candidates:
        if rel in files:
            items.append(
                _kind_item(
                    f"dcp-services-scheduler-{rel}",
                    rel,
                    f"scheduler/batch processing evidence is present in {rel}.",
                    [_evidence(root, rel, _line_for_pattern(root / rel, pattern), Path(rel).stem, "scheduler/batch evidence.")],
                    "batch-scheduler",
                    ["dcp-services", "scheduler", "batch"],
                )
            )
    if not items:
        evidence = _first_evidence(root, files, "", "Scheduler|Scheduled|Batch|batch|EventProcessor", "scheduler search", "unknown with searched evidence for batch/scheduler.")
        items.append(
            _kind_item(
                "dcp-services-scheduler-unknown",
                "unknown with searched evidence scheduler",
                "unknown with searched evidence: batch/scheduler terms were searched but no concrete scheduler class was found in scanned files.",
                [evidence],
                "batch-scheduler",
                ["dcp-services", "scheduler"],
            )
        )
    return items


def _dcp_services_eai_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items = _dcp_services_eai_xml_items(root, files)
    service_files = [
        rel
        for rel in files
        if rel.endswith("Service.java") and "/src/main/java/" in rel
    ]
    matches = _pattern_matches(
        root,
        service_files,
        (re.compile(r"\bcallF[0-9A-Z_]+\s*\("), re.compile(r"eaiExecute|generateServiceId|@eaiName|EaiResult")),
        limit=160,
    )
    for match in matches[:32]:
        text = str(match.get("text") or "")
        interface_id = _extract_eai_id(text)
        rel = match["path"]
        evidence = [_evidence(root, rel, match.get("line"), interface_id or Path(rel).stem, "EAI/interface marker.")]
        execute_line = _line_for_pattern(root / rel, r"eaiExecute|generateServiceId|EaiParams")
        if execute_line and execute_line != match.get("line"):
            evidence.append(_evidence(root, rel, execute_line, "eaiExecute", "EAI execution/build path."))
        summary = (
            f"EAI/interface {interface_id} is declared or called in {rel}."
            if interface_id
            else f"unknown with searched evidence: EAI/interface marker found in {rel}, but no literal service id was extracted from the matched line."
        )
        items.append(
            _kind_item(
                f"dcp-services-eai-{rel}-{match.get('line')}",
                interface_id or f"unknown with searched evidence in {Path(rel).stem}",
                summary,
                evidence,
                "eai-interface",
                ["dcp-services", "eai"],
                {"interface_id": interface_id or ""},
            )
        )
    if not items:
        evidence = _first_evidence(root, files, "", "EAI|EaiResult|eaiExecute|serviceId", "EAI search", "unknown with searched evidence for EAI/interface.")
        items.append(
            _kind_item(
                "dcp-services-eai-unknown",
                "unknown with searched evidence EAI/interface",
                "unknown with searched evidence: EAI/interface search ran, but no executable EAI call was extracted.",
                [evidence],
                "eai-interface",
                ["dcp-services", "eai"],
                {"interface_id": ""},
            )
        )
    return items


def _dcp_services_eai_xml_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    eai_xml_files = sorted(rel for rel in files if _is_eai_xml_path(rel))
    service_xml_files = [rel for rel in eai_xml_files if rel.endswith("_service.xml")]
    config_xml_files = [rel for rel in eai_xml_files if rel not in service_xml_files]
    items: list[dict[str, Any]] = []

    for rel in service_xml_files:
        metadata = _extract_eai_xml_metadata(root / rel)
        interface_id = metadata.get("layout_id") or _extract_eai_id_from_filename(rel)
        service_name = metadata.get("service_name") or ""
        transaction_type = metadata.get("transaction_type") or ""
        target_type = metadata.get("target_type") or ""
        parameter_name = metadata.get("parameter_name") or ""
        line = metadata.get("layout_line") or _line_for_pattern(root / rel, r"<layoutId>|<serviceName>|<services")
        summary_parts = [f"EAI XML interface {interface_id} is defined by {rel}"]
        if service_name:
            summary_parts.append(f"serviceName={service_name}")
        if transaction_type:
            summary_parts.append(f"transactionType={transaction_type}")
        if target_type:
            summary_parts.append(f"targetType={target_type}")
        if parameter_name:
            summary_parts.append(f"parameterName={parameter_name}")
        items.append(
            _kind_item(
                f"dcp-services-eai-xml-{rel}",
                interface_id or Path(rel).name,
                "; ".join(summary_parts) + ".",
                [_evidence(root, rel, int(line) if line else 1, interface_id or Path(rel).stem, "EAI service XML layout/interface definition.")],
                "eai-interface",
                ["dcp-services", "eai", "xml"],
                {
                    "interface_id": interface_id,
                    "service_name": service_name,
                    "transaction_type": transaction_type,
                    "target_type": target_type,
                    "parameter_name": parameter_name,
                    "source": "resources/eai XML",
                },
            )
        )

    for rel in config_xml_files:
        config_id = _extract_eai_id_from_filename(rel) or Path(rel).stem
        line = _line_for_pattern(root / rel, r"<[A-Za-z].*>|<Config|<services")
        items.append(
            _kind_item(
                f"dcp-services-eai-xml-config-{rel}",
                config_id,
                f"EAI XML config/resource file {rel} is indexed so stale checks track the EAI runtime metadata set.",
                [_evidence(root, rel, line or 1, config_id, "EAI XML config/resource metadata.")],
                "eai-interface",
                ["dcp-services", "eai", "xml", "config"],
                {
                    "interface_id": config_id,
                    "source": "resources/eai XML",
                },
            )
        )
    return items


def _dcp_services_dto_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    dto_files = [
        rel
        for rel in files
        if rel.endswith(".java")
        and any(part in rel for part in ["/response/", "/request/", "/params/"])
        and "/src/main/java/" in rel
    ]
    items: list[dict[str, Any]] = []
    for rel in dto_files[:28]:
        kind = "response" if "/response/" in rel else "request" if "/request/" in rel else "params"
        items.append(
            _kind_item(
                f"dcp-services-dto-{rel}",
                Path(rel).stem,
                f"{Path(rel).stem} is a {kind} DTO/parameter class used in controller/service request/response flow.",
                [_evidence(root, rel, _line_for_pattern(root / rel, r"class |interface |package "), Path(rel).stem, f"{kind} DTO class.")],
                "dto-flow",
                ["dcp-services", "dto", kind],
            )
        )
    return items


def _dcp_services_verification_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    items = [
        _kind_item(
            "dcp-services-verification-maven-package",
            "mvn package",
            "Root pom.xml is a Maven aggregator; maven.test.skip is set in properties, so package may be compile/package oriented unless profile overrides it.",
            _existing_evidence(
                root,
                [
                    ("pom.xml", r"<packaging>pom</packaging>|<modules>", "Maven aggregator", "Root Maven aggregator."),
                    ("pom.xml", r"<maven\.test\.skip>true</maven\.test\.skip>", "maven.test.skip", "Default test skip property."),
                ],
            ),
            "verification-command",
            ["dcp-services", "verification"],
            {"command": "mvn package"},
        )
    ]
    test = "src/test/java/LibraryTest.java"
    if test in files:
        items.append(
            _kind_item(
                "dcp-services-verification-root-test",
                test,
                "Root test source exists, but module/profile-specific tests must be checked before relying on this as coverage.",
                [_evidence(root, test, _line_for_pattern(root / test, r"class |@Test"), "LibraryTest", "Representative test source.")],
                "verification-command",
                ["dcp-services", "verification"],
            )
        )
    return items


def _enhance_drt_front_artifacts(root: Path, files: list[str], artifacts: dict[str, Any]) -> None:
    prefix = _drt_front_base_prefix(root, files)
    route_items = _drt_vue_route_items(root, files, prefix, "drt-front")
    store_items = _drt_front_store_items(root, files, prefix)
    service_items = _drt_front_service_items(root, files, prefix)
    verification_items = _drt_front_verification_items(root, files, prefix)
    artifacts["architecture-map"]["items"].extend(
        [
            _kind_item(
                "drt-front-vite-shell",
                "DRT front Vite/Vue3 shell",
                "DRT front runs from the Vite Vue3 app under the dev/ui project root, with shared public assets one level above.",
                _existing_evidence(
                    root,
                    [
                        (f"{prefix}package.json", r'"vue"\s*:|"vite"\s*:', "package stack", "Vue3/Vite package descriptor."),
                        (f"{prefix}vite.config.ts", r"publicDir|proxy|defineConfig", "vite config", "Vite publicDir/proxy/build config."),
                        (f"{prefix}src/main.ts", r"createApp|createPinia|router", "main.ts", "Vue app bootstrap."),
                    ],
                ),
                "frontend-shell",
                ["drt-front", "vue3", "vite"],
            )
        ]
    )
    artifacts["module-responsibility-map"]["items"].extend(store_items + service_items[:10])
    artifacts["entrypoints"]["items"].extend(route_items[:16])
    artifacts["key-flows"]["items"].extend(route_items[:10] + store_items + service_items[:8])
    artifacts["api/eai-interface-index"]["items"].extend(service_items[:18])
    artifacts["verification-guide"]["items"].extend(verification_items)
    _dedupe_all_artifacts(artifacts)


def _enhance_drt_api_artifacts(root: Path, files: list[str], artifacts: dict[str, Any]) -> None:
    controller_items = _spring_controller_items(root, files, "drt-api")
    mapper_items = _mybatis_mapper_items(root, files, "drt-api")
    integration_items = _drt_api_integration_items(root, files)
    verification_items = _maven_verification_items(root, files, "drt-api")
    artifacts["architecture-map"]["items"].extend(
        [
            _kind_item(
                "drt-api-spring-boot-runtime",
                "DRT API Spring Boot runtime",
                "DRT API is a Spring Boot jar with drt-core, web, JDBC, Redis/session, Kafka, DynamoDB, and MyBatis dependencies.",
                _existing_evidence(
                    root,
                    [
                        ("pom.xml", r"drt-core|spring-boot-starter-web|spring-session-data-redis|spring-kafka|mybatis-spring-boot-starter", "pom dependencies", "DRT API runtime dependency marker."),
                        ("src/main/java/com/samsunglife/drt/api/Application.java", r"@SpringBootApplication", "Application", "Spring Boot application entrypoint."),
                    ],
                ),
                "backend-runtime",
                ["drt-api", "spring-boot"],
            )
        ]
    )
    artifacts["module-responsibility-map"]["items"].extend(_java_package_role_items(root, files, "src/main/java/com/samsunglife/drt/api", "drt-api") + mapper_items[:10])
    artifacts["entrypoints"]["items"].extend(controller_items[:24])
    artifacts["key-flows"]["items"].extend(controller_items[:18] + integration_items[:8])
    artifacts["api/eai-interface-index"]["items"].extend(controller_items[:18] + mapper_items[:24] + integration_items)
    artifacts["verification-guide"]["items"].extend(verification_items)
    _dedupe_all_artifacts(artifacts)


def _enhance_drt_cms_artifacts(root: Path, files: list[str], artifacts: dict[str, Any]) -> None:
    frontend_routes = _drt_vue_route_items(root, files, "frontend/", "drt-cms")
    frontend_services = _drt_cms_front_service_items(root, files)
    backend_controllers = _spring_controller_items(root, files, "drt-cms")
    backend_mappers = _mybatis_mapper_items(root, files, "drt-cms")
    verification_items = _maven_verification_items(root, files, "drt-cms") + _drt_cms_front_verification_items(root, files)
    artifacts["architecture-map"]["items"].extend(
        [
            _kind_item(
                "drt-cms-integrated-root",
                "DRT CMS integrated admin root",
                "DRT CMS is an integrated admin repository with Maven parent modules for backend and frontend.",
                _existing_evidence(
                    root,
                    [
                        ("pom.xml", r"<module>backend</module>|<module>frontend</module>|drt-cms-parent", "parent pom", "Integrated CMS parent module descriptor."),
                        ("backend/pom.xml", r"drt-cms-backend|spring-boot-starter-security|mybatis", "backend pom", "CMS backend module descriptor."),
                        ("frontend/package.json", r'"quasar"\s*:|"ag-grid|pinia', "frontend package", "CMS frontend Quasar/admin package descriptor."),
                    ],
                ),
                "integrated-admin",
                ["drt-cms", "frontend", "backend"],
            )
        ]
    )
    artifacts["module-responsibility-map"]["items"].extend(
        _java_package_role_items(root, files, "backend/src/main/java/com/samsunglife/drt/cms", "drt-cms")[:18]
        + frontend_services[:12]
        + backend_mappers[:12]
    )
    artifacts["entrypoints"]["items"].extend(frontend_routes[:16] + backend_controllers[:18])
    artifacts["key-flows"]["items"].extend(frontend_routes[:12] + frontend_services[:10] + backend_controllers[:12])
    artifacts["api/eai-interface-index"]["items"].extend(frontend_services[:18] + backend_controllers[:18] + backend_mappers[:24])
    artifacts["verification-guide"]["items"].extend(verification_items)
    _dedupe_all_artifacts(artifacts)


def _drt_front_base_prefix(root: Path, files: list[str]) -> str:
    if "dev/package.json" in files:
        return "dev/"
    if "ui/package.json" in files:
        return "ui/"
    if (root / "package.json").exists():
        return ""
    return "dev/"


def _drt_vue_route_items(root: Path, files: list[str], prefix: str, profile_key: str) -> list[dict[str, Any]]:
    route_files = sorted(rel for rel in files if rel.startswith(f"{prefix}src/router/") and rel.endswith((".ts", ".js")))
    items: list[dict[str, Any]] = []
    for rel in route_files[:28]:
        items.append(
            _kind_item(
                f"{profile_key}-route-{rel}",
                rel,
                f"{rel} is a Vue Router route family/entry file. Trace route -> view -> service/store before changing navigation.",
                [_evidence(root, rel, _line_for_pattern(root / rel, r"createRouter|routes|path:|name:|component:"), "Vue Router", "DRT/CMS route map evidence.")],
                "route-view-flow",
                [profile_key, "router"],
            )
        )
    return items


def _drt_front_store_items(root: Path, files: list[str], prefix: str) -> list[dict[str, Any]]:
    store_files = sorted(rel for rel in files if rel.startswith(f"{prefix}src/store/") and rel.endswith(".ts"))
    items: list[dict[str, Any]] = []
    for rel in store_files[:18]:
        items.append(
            _kind_item(
                f"drt-front-store-{rel}",
                Path(rel).stem,
                f"{Path(rel).stem} is a Pinia store; verify imports and persisted state before changing shared flow state.",
                [_evidence(root, rel, _line_for_pattern(root / rel, r"defineStore|persist|storeToRefs"), Path(rel).stem, "Pinia store evidence.")],
                "store-flow",
                ["drt-front", "pinia", "store"],
            )
        )
    return items


def _drt_front_service_items(root: Path, files: list[str], prefix: str) -> list[dict[str, Any]]:
    service_files = sorted(rel for rel in files if rel.startswith(f"{prefix}src/module/service/") and rel.endswith(".ts"))
    seed_files = [f"{prefix}src/module/DrtHttpClient.ts", f"{prefix}src/module/AgentSseClient.ts"]
    selected = [rel for rel in seed_files if rel in files] + service_files[:32]
    return [
        _kind_item(
            f"drt-front-service-{rel}",
            Path(rel).stem,
            f"{Path(rel).stem} contains DRT frontend API/client logic; verify DrtHttpClient response shape and route/store consumers.",
            [_evidence(root, rel, _line_for_pattern(root / rel, r"axios|fetchAny|fetchAddr|Service|export|SSE|EventSource"), Path(rel).stem, "DRT front service/client evidence.")],
            "frontend-api-client",
            ["drt-front", "service", "api"],
        )
        for rel in selected
    ]


def _drt_front_verification_items(root: Path, files: list[str], prefix: str) -> list[dict[str, Any]]:
    return _package_verification_items(root, files, prefix, "drt-front")


def _spring_controller_items(root: Path, files: list[str], profile_key: str) -> list[dict[str, Any]]:
    controllers = sorted(
        rel
        for rel in files
        if rel.endswith(("Controller.java", "Resource.java"))
        and ("/src/main/java/" in rel or rel.startswith("src/main/java/") or rel.startswith("backend/src/main/java/"))
    )
    items: list[dict[str, Any]] = []
    for rel in controllers[:48]:
        evidence = [
            _evidence(root, rel, _line_for_pattern(root / rel, r"@(RestController|Controller)|class\s+\w+(Controller|Resource)"), Path(rel).stem, "Spring controller/resource class."),
            _evidence(root, rel, _line_for_pattern(root / rel, r"@(RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)"), "mapping", "HTTP mapping annotation."),
        ]
        items.append(
            _kind_item(
                f"{profile_key}-controller-{rel}",
                Path(rel).stem,
                f"{Path(rel).stem} exposes Spring HTTP endpoints. Trace mapped method -> service -> mapper/repository -> DTO before edits.",
                evidence,
                "controller-service-flow",
                [profile_key, "controller", "api"],
            )
        )
    return items


def _mybatis_mapper_items(root: Path, files: list[str], profile_key: str) -> list[dict[str, Any]]:
    mapper_files = sorted(rel for rel in files if rel.endswith(".xml") and ("mapper/" in rel or "mybatis/sql/" in rel))
    java_mappers = sorted(rel for rel in files if rel.endswith("Mapper.java") or rel.endswith("Repository.java"))
    items: list[dict[str, Any]] = []
    for rel in java_mappers[:24]:
        items.append(
            _kind_item(
                f"{profile_key}-java-mapper-{rel}",
                Path(rel).stem,
                f"{Path(rel).stem} is a Java mapper/repository interface/class; pair it with the matching XML before query changes.",
                [_evidence(root, rel, _line_for_pattern(root / rel, r"@Mapper|interface|class"), Path(rel).stem, "Java mapper/repository evidence.")],
                "repository-pattern",
                [profile_key, "mybatis", "repository"],
            )
        )
    for rel in mapper_files[:36]:
        items.append(
            _kind_item(
                f"{profile_key}-xml-mapper-{rel}",
                Path(rel).stem,
                f"{rel} is a MyBatis mapper XML; validate namespace, statement id, DTO fields, and dynamic SQL conditions before edits.",
                [_evidence(root, rel, _line_for_pattern(root / rel, r"<mapper|<select|<insert|<update|<delete"), Path(rel).stem, "MyBatis XML evidence.")],
                "repository-pattern",
                [profile_key, "mybatis", "xml"],
            )
        )
    return items


def _java_package_role_items(root: Path, files: list[str], package_prefix: str, profile_key: str) -> list[dict[str, Any]]:
    package_dirs = sorted(
        {
            "/".join(Path(rel).parts[: min(len(Path(rel).parts), len(Path(package_prefix).parts) + 2)])
            for rel in files
            if rel.startswith(package_prefix + "/") and rel.endswith(".java")
        }
    )
    items: list[dict[str, Any]] = []
    for package_dir in package_dirs[:40]:
        representative = _first_file_under(files, package_dir + "/")
        if representative:
            items.append(
                _kind_item(
                    f"{profile_key}-package-{package_dir}",
                    package_dir,
                    f"{package_dir} is a Java package area. Confirm controller/service/repository/domain roles from current files before implementation.",
                    [_evidence(root, representative, _line_for_pattern(root / representative, r"package |class |interface "), package_dir, "Representative Java package file.")],
                    "package-role",
                    [profile_key, "java-package"],
                )
            )
    return items


def _drt_api_integration_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    matches = _pattern_matches(
        root,
        [rel for rel in files if rel.endswith(".java")],
        (
            re.compile(r"\bRedisTemplate\b|\bRedisUtil\b|@Cacheable|@CacheEvict"),
            re.compile(r"\bKafkaTemplate\b|@KafkaListener"),
            re.compile(r"\bDynamoLogUtil\b|dynamodb", re.IGNORECASE),
            re.compile(r"\bRestTemplate\b|\bWebClient\b|\bHttpClient\b|Client\b"),
        ),
        limit=80,
    )
    return [
        _kind_item(
            f"drt-api-integration-{match['path']}-{match.get('line')}",
            _symbol_from_text(str(match.get("text") or "")) or Path(match["path"]).stem,
            "Integration/cache/client marker detected; verify external contract, profile config, timeout/retry, and masking requirements before edits.",
            [_evidence(root, match["path"], match.get("line"), _symbol_from_text(str(match.get("text") or "")) or "integration", "DRT API integration/cache/client evidence.")],
            "integration",
            ["drt-api", "integration"],
        )
        for match in _dedupe_matches(matches)[:24]
    ]


def _drt_cms_front_service_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    service_files = sorted(rel for rel in files if rel.startswith("frontend/src/services/") and rel.endswith((".ts", ".js")))
    seed_files = [
        "frontend/src/boot/axios.ts",
        "frontend/src/router/routes.ts",
        "frontend/src/components/plugins/grid/nv-grid.vue",
    ]
    selected = [rel for rel in seed_files if rel in files] + service_files[:36]
    return [
        _kind_item(
            f"drt-cms-front-service-{rel}",
            Path(rel).stem,
            f"{rel} participates in CMS admin service/grid/API flow. Pair service/model/view files before changing screen behavior.",
            [_evidence(root, rel, _line_for_pattern(root / rel, r"api\.|axios|class .*Service|GENERIC_API|ag-grid|pagination|export"), Path(rel).stem, "DRT CMS frontend service/grid evidence.")],
            "frontend-api-client",
            ["drt-cms", "frontend", "service", "grid"],
        )
        for rel in selected
    ]


def _package_verification_items(root: Path, files: list[str], prefix: str, profile_key: str) -> list[dict[str, Any]]:
    rel = f"{prefix}package.json"
    package = _read_json(root / rel)
    items: list[dict[str, Any]] = []
    if isinstance(package, dict) and isinstance(package.get("scripts"), dict):
        for script_name in ("lint", "test", "test:e2e", "test:unit", "build", "build:stage", "build:dr", "serve:local", "dev"):
            if script_name in package["scripts"]:
                items.append(
                    _kind_item(
                        f"{profile_key}-verification-{script_name}",
                        f"npm run {script_name}",
                        f"{rel} defines npm run {script_name} as {package['scripts'][script_name]}.",
                        [_evidence(root, rel, _line_for_pattern(root / rel, rf'"{re.escape(script_name)}"\s*:'), script_name, "package.json verification script.")],
                        "verification-command",
                        [profile_key, "verification"],
                        {"command": f"cd {prefix.rstrip('/') or '.'} && npm run {script_name}"},
                    )
                )
    return items


def _drt_cms_front_verification_items(root: Path, files: list[str]) -> list[dict[str, Any]]:
    return _package_verification_items(root, files, "frontend/", "drt-cms")


def _maven_verification_items(root: Path, files: list[str], profile_key: str) -> list[dict[str, Any]]:
    if "pom.xml" not in files:
        return []
    return [
        _kind_item(
            f"{profile_key}-verification-maven",
            "mvn package",
            "Root pom.xml exists; use Maven package/test/profile commands as the backend verification base, then narrow by module/profile when possible.",
            [_evidence(root, "pom.xml", _line_for_pattern(root / "pom.xml", r"<project|<artifactId>|<modules>|<packaging>"), "pom.xml", "Maven verification descriptor.")],
            "verification-command",
            [profile_key, "verification", "maven"],
            {"command": "mvn package"},
        )
    ]


def _kind_item(
    item_id: str,
    title: str,
    summary: str,
    evidence: list[dict[str, Any] | None],
    kind: str,
    tags: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": _slug(item_id),
        "title": title,
        "summary": summary,
        "kind": kind,
        "tags": tags,
        "evidence": [item for item in evidence if isinstance(item, dict) and item.get("path")],
    }
    if extra:
        item.update(extra)
    return item


def _existing_evidence(root: Path, specs: list[tuple[str, str, str, str]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for rel, pattern, symbol, reason in specs:
        if (root / rel).exists():
            evidence.append(_evidence(root, rel, _line_for_pattern(root / rel, pattern), symbol, reason))
    return evidence


def _first_evidence(
    root: Path,
    files: list[str],
    prefix: str,
    pattern: str,
    symbol: str,
    reason: str,
) -> dict[str, Any]:
    compiled = re.compile(pattern)
    candidates = [rel for rel in files if rel.startswith(prefix)] if prefix else list(files)
    for rel in candidates:
        path = root / rel
        if not path.is_file() or Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            if compiled.search(line):
                return _evidence(root, rel, index, symbol, reason)
    if candidates:
        return _evidence(root, candidates[0], _line_for_pattern(root / candidates[0], r"\S") or 1, symbol, reason)
    return _fallback_evidence(root, symbol, reason)


def _dedupe_all_artifacts(artifacts: dict[str, Any]) -> None:
    for artifact in artifacts.values():
        items = artifact.get("items")
        if not isinstance(items, list):
            continue
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or _slug(str(item.get("title") or "item")))
            if item_id in seen:
                continue
            seen.add(item_id)
            item["id"] = item_id
            deduped.append(item)
        artifact["items"] = deduped


def _extract_vue_route_entries(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []

    entries: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        name_match = re.search(r"\bname\s*:\s*['\"]([^'\"]+)['\"]", line)
        if not name_match:
            continue
        window_before = "\n".join(lines[max(0, index - 5) : index])
        window_after = "\n".join(lines[index - 1 : min(len(lines), index + 7)])
        path_match = re.search(r"\bpath\s*:\s*['\"]([^'\"]+)['\"]", window_before)
        view_match = re.search(r"@/views/([^'\"]+?\.vue)", window_after)
        entries.append(
            {
                "line": index,
                "name": name_match.group(1),
                "path": path_match.group(1) if path_match else "",
                "view_path": f"src/views/{view_match.group(1)}" if view_match else "",
            }
        )
        if len(entries) >= limit:
            break
    return entries


def _extract_http_endpoint(text: str) -> str:
    match = re.search(r"['\"](/(?:gw|api|monimo)[^'\"]*)['\"]", text)
    if match:
        return match.group(1)
    match = re.search(r"['\"](/[A-Za-z0-9_./{}-]+)['\"]", text)
    return match.group(1) if match else ""


def _extract_eai_id(text: str) -> str:
    for pattern in [
        r"\bcall(F[0-9A-Z_]+[A-Z0-9_]*)\s*\(",
        r"\blayoutId\s*=\s*['\"]([A-Z0-9_]+)['\"]",
        r"@eaiName\s*\(?\s*['\"]?([A-Z0-9_]+)",
        r"\b(EAF[0-9A-Z_]+)\b",
        r"\b(F[0-9][0-9A-Z_]{5,})\b",
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _is_eai_xml_path(rel: str) -> bool:
    normalized = rel.replace("\\", "/")
    return normalized.endswith(".xml") and (
        normalized.startswith("resources/eai/") or "/resources/eai/" in normalized
    )


def _extract_eai_id_from_filename(rel: str) -> str:
    name = Path(rel).name
    match = re.match(r"([A-Z0-9_]+)_service\.xml$", name, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.match(r"([A-Z0-9_]+)\.xml$", name, flags=re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _extract_eai_xml_metadata(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return {}

    metadata: dict[str, Any] = {}
    tag_map = {
        "layout_id": "layoutId",
        "service_name": "serviceName",
        "service_description": "serviceDescription",
        "transaction_type": "transactionType",
        "target_type": "targetType",
        "parameter_name": "parameterName",
    }
    for index, line in enumerate(lines, start=1):
        for key, tag in tag_map.items():
            if key in metadata:
                continue
            value = _extract_xml_tag_text(line, tag)
            if value:
                metadata[key] = value
                if key == "layout_id":
                    metadata["layout_line"] = index
    return metadata


def _extract_xml_tag_text(line: str, tag: str) -> str:
    match = re.search(rf"<{re.escape(tag)}(?:\s[^>]*)?>(.*?)</{re.escape(tag)}>", line)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _analysis_log_for_profile(profile: dict[str, Any]) -> dict[str, Any]:
    searches = [
        {
            "query": "build descriptors and project profile markers",
            "purpose": "Detect stack, DCP profile, and implementation agent routing.",
            "evidence_policy": "Every emitted claim must point to a project-relative path with line and symbol/name.",
        },
        {
            "query": "entrypoints, route mappings, controllers, API clients, EAI calls",
            "purpose": "Populate Project Info artifacts with implementation-relevant anchors.",
            "evidence_policy": "Fallback evidence is allowed only for explicit negative findings.",
        },
    ]
    key = str(profile.get("key") or "generic")
    if key == "dcp-front":
        searches.extend(
            [
                {
                    "query": "src/router/mo/mysamsunglife/**/route.js",
                    "purpose": "Map Vue Router route names to src/views screen components.",
                },
                {
                    "query": "src/store/index.js src/store/modules/com/DataStore.js src/plugins/com/Common.js",
                    "purpose": "Locate DataStore registration and long-flow continuation state handling.",
                },
                {
                    "query": "axios.* Vue.$http.* tools/playwright",
                    "purpose": "Index backend call patterns and browser verification assets.",
                },
            ]
        )
    elif key == "dcp-services":
        searches.extend(
            [
                {
                    "query": "pom.xml <module> and module pom.xml descriptors",
                    "purpose": "Map Maven module boundaries and build/profile responsibilities.",
                },
                {
                    "query": "*Controller.java *Service.java response/request/params packages",
                    "purpose": "Trace controller-service-response flow anchors.",
                },
                {
                    "query": "applicationContext-service.xml SqlSessionTemplate mapperLocations resources-env scheduler EAI",
                    "purpose": "Index repository wiring, environment profiles, scheduler/batch classes, and EAI interface calls.",
                },
            ]
        )
    elif key == "drt-front":
        searches.extend(
            [
                {
                    "query": "dev/package.json dev/vite.config.ts dev/src/router/** dev/src/store/**",
                    "purpose": "Map DRT customer front Vite/Vue3, route families, Pinia stores, and build/proxy settings.",
                },
                {
                    "query": "dev/src/module/DrtHttpClient.ts dev/src/module/service/**/*.ts dev/src/view/**/*.vue",
                    "purpose": "Trace frontend service calls, response interceptors, views, and domain flows.",
                },
            ]
        )
    elif key == "drt-api":
        searches.extend(
            [
                {
                    "query": "pom.xml Application.java *Controller.java *Service.java *Mapper.java src/main/resources/mapper/**/*.xml",
                    "purpose": "Trace DRT API Spring Boot, controller/service/mapper, Redis/Kafka/Dynamo, and MyBatis boundaries.",
                },
                {
                    "query": "src/main/resources/application-*.properties src/main/resources/*/env.properties plugins templates",
                    "purpose": "Index profile configs, plugin resources, authentication/crypto assets, and template outputs.",
                },
            ]
        )
    elif key == "drt-cms":
        searches.extend(
            [
                {
                    "query": "pom.xml backend/pom.xml frontend/package.json frontend/src/router/**",
                    "purpose": "Map integrated CMS parent, backend/frontend module boundaries, Quasar route families, and build scripts.",
                },
                {
                    "query": "backend/src/main/java/**/rest backend/src/main/java/**/modules backend/src/main/resources/mybatis/sql frontend/src/services frontend/src/views",
                    "purpose": "Trace CMS REST/resource -> service/repository and admin screen -> service/model/grid flows.",
                },
            ]
        )
    return {"searches": searches}


def _artifact(title: str, summary: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": title, "summary": summary, "items": items}


def _collect_project_files(root: Path, max_files: int | None = None) -> list[str]:
    files: list[str] = []
    if not root.exists():
        return files
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if max_files is not None and len(files) >= max_files:
            break
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORE_DIRS for part in rel_parts):
            continue
        if PROJECT_INFO_LEGACY_ARTIFACT_DIR.parts == rel_parts[: len(PROJECT_INFO_LEGACY_ARTIFACT_DIR.parts)]:
            continue
        if PROJECT_KNOWLEDGE_LEGACY_DIR.parts == rel_parts[: len(PROJECT_KNOWLEDGE_LEGACY_DIR.parts)]:
            continue
        if not path.is_file():
            continue
        if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if not path.suffix and path.name not in BUILD_AND_CONFIG_FILES:
            continue
        files.append(path.relative_to(root).as_posix())
    return files


def _build_source_manifest(root: Path, files: list[str]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for rel in files:
        if not _is_stale_relevant(rel):
            continue
        path = root / rel
        try:
            data = path.read_bytes()
        except OSError:
            continue
        manifest[rel] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
    return manifest


def _is_stale_relevant(rel: str) -> bool:
    path = Path(rel)
    name = path.name
    if _is_eai_xml_path(rel):
        return True
    if "/src/main/resources-env/" in rel:
        return True
    if name in BUILD_AND_CONFIG_FILES or rel in BUILD_AND_CONFIG_FILES:
        return True
    if path.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".vue", ".java", ".xml", ".py", ".yml", ".yaml", ".properties"}:
        return rel.startswith("src/") or rel.startswith("backend/") or "/src/" in rel
    if "interface" in name.lower() or "module" in name.lower():
        return True
    return False


def _manifest_signature(meta: Any) -> tuple[Any, Any]:
    if not isinstance(meta, dict):
        return None, None
    return meta.get("sha256"), meta.get("size")


def _detect_stack(root: Path) -> list[str]:
    stack: list[str] = []
    package = _read_json(root / "package.json")
    deps: dict[str, Any] = {}
    if isinstance(package, dict):
        for key in ("dependencies", "devDependencies"):
            value = package.get(key)
            if isinstance(value, dict):
                deps.update(value)
    if "next" in deps or (root / "next.config.ts").exists() or (root / "next.config.js").exists():
        stack.append("Next.js")
    if "react" in deps:
        stack.append("React")
    if "vue" in deps:
        stack.append("Vue")
    if "vuex" in deps:
        stack.append("Vuex")
    if "vite" in deps or (root / "vite.config.ts").exists() or (root / "dev" / "vite.config.ts").exists():
        stack.append("Vite")
    if "pinia" in deps:
        stack.append("Pinia")
    if "quasar" in deps:
        stack.append("Quasar")
    if "axios" in deps:
        stack.append("Axios")
    if "typescript" in deps or (root / "tsconfig.json").exists():
        stack.append("TypeScript")
    if (root / "pom.xml").exists():
        stack.append("Maven")
        pom_text = (root / "pom.xml").read_text(encoding="utf-8", errors="ignore").lower()
        if "spring-boot" in pom_text:
            stack.append("Spring Boot")
        if "mybatis" in pom_text:
            stack.append("MyBatis")
    for package_rel in ("dev/package.json", "frontend/package.json"):
        package = _read_json(root / package_rel)
        package_deps: dict[str, Any] = {}
        if isinstance(package, dict):
            for key in ("dependencies", "devDependencies"):
                value = package.get(key)
                if isinstance(value, dict):
                    package_deps.update(value)
        if "vue" in package_deps and "Vue" not in stack:
            stack.append("Vue")
        if "vite" in package_deps and "Vite" not in stack:
            stack.append("Vite")
        if "pinia" in package_deps and "Pinia" not in stack:
            stack.append("Pinia")
        if "quasar" in package_deps and "Quasar" not in stack:
            stack.append("Quasar")
        if "axios" in package_deps and "Axios" not in stack:
            stack.append("Axios")
        if "typescript" in package_deps and "TypeScript" not in stack:
            stack.append("TypeScript")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        stack.append("Gradle")
    if any((root / rel).exists() for rel in ("requirements.txt", "pyproject.toml", "backend/requirements.txt")):
        stack.append("Python")
    return stack or ["Unclassified"]


def _dcp_front_profile_evidence(root: Path) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    package = root / "package.json"
    if package.exists():
        for symbol, pattern, reason in [
            ("vue", r'"vue"\s*:', "Vue dependency marker for dcp-front."),
            ("vuex", r'"vuex"\s*:', "Vuex dependency marker for dcp-front."),
        ]:
            line = _line_for_pattern(package, pattern)
            if line:
                evidence.append(_evidence(root, "package.json", line, symbol, reason))
    datastore = "src/store/modules/com/DataStore.js"
    if (root / datastore).exists():
        evidence.append(_evidence(root, datastore, _line_for_pattern(root / datastore, r"export|state|mutations"), "DataStore", "DCP front shared state marker."))
    view_marker = _first_file_under(_collect_project_files(root), "src/views/mo/mysamsunglife/")
    if view_marker:
        evidence.append(_evidence(root, view_marker, 1, "mysamsunglife", "DCP front mobile view tree marker."))
    return evidence


def _dcp_services_profile_evidence(root: Path) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    pom = root / "pom.xml"
    if pom.exists():
        for module in ("dcp-core", "dcp-gateway", "dcp-insurance"):
            line = _line_for_pattern(pom, rf"<module>\s*{re.escape(module)}\s*</module>")
            if line:
                evidence.append(_evidence(root, "pom.xml", line, module, "DCP services Maven module marker."))
        if not evidence:
            evidence.append(_evidence(root, "pom.xml", _line_for_pattern(pom, r"<project|<artifactId>"), "pom.xml", "Maven descriptor for dcp-services module."))
    return evidence


def _drt_front_profile_evidence(root: Path) -> list[dict[str, Any]]:
    base = root / "dev" if (root / "dev" / "package.json").exists() else root
    rel_base = "dev/" if base != root else ""
    evidence = _existing_evidence(
        root,
        [
            (f"{rel_base}package.json", r'"vue"\s*:|"vite"\s*:|"pinia"\s*:', "Vue3/Vite/Pinia", "DRT front package stack marker."),
            (f"{rel_base}vite.config.ts", r"defineConfig|proxy|api\.t\.drt", "Vite proxy", "DRT front Vite proxy/build config marker."),
            (f"{rel_base}src/router/index.ts", r"createRouter|routes", "Vue Router", "DRT front route entry marker."),
            (f"{rel_base}src/module/DrtHttpClient.ts", r"axios|DrtHttpResponse|interceptors", "DrtHttpClient", "DRT front HTTP client/interceptor marker."),
        ],
    )
    if not evidence:
        evidence.append(_fallback_evidence(root, "drt-front", "DRT front profile fallback evidence."))
    return evidence


def _drt_api_profile_evidence(root: Path) -> list[dict[str, Any]]:
    evidence = _existing_evidence(
        root,
        [
            ("pom.xml", r"<artifactId>\s*drt-api\s*</artifactId>|drt-core|spring-boot-starter-web", "drt-api pom", "DRT API Maven/Spring Boot marker."),
            ("src/main/java/com/samsunglife/drt/api/Application.java", r"@SpringBootApplication|scanBasePackages", "Application", "DRT API Spring Boot entrypoint marker."),
            ("src/main/resources/mybatis-config.xml", r"<configuration|typeAliases|mappers", "MyBatis config", "DRT API MyBatis config marker."),
        ],
    )
    if not evidence:
        evidence.append(_fallback_evidence(root, "drt-api", "DRT API profile fallback evidence."))
    return evidence


def _drt_cms_profile_evidence(root: Path) -> list[dict[str, Any]]:
    evidence = _existing_evidence(
        root,
        [
            ("pom.xml", r"<artifactId>\s*drt-cms-parent\s*</artifactId>|<module>backend</module>|<module>frontend</module>", "drt-cms parent", "DRT CMS parent Maven module marker."),
            ("backend/pom.xml", r"<artifactId>\s*drt-cms-backend\s*</artifactId>|spring-boot-starter-security|mybatis", "CMS backend", "DRT CMS backend Spring/MyBatis marker."),
            ("frontend/package.json", r'"quasar"\s*:|"ag-grid|pinia|axios', "CMS frontend", "DRT CMS Quasar/admin frontend marker."),
            ("frontend/src/router/routes.ts", r"asyncRouterMap|routes-|Layout", "CMS routes", "DRT CMS admin route map marker."),
        ],
    )
    if not evidence:
        evidence.append(_fallback_evidence(root, "drt-cms", "DRT CMS profile fallback evidence."))
    return evidence


def _maven_modules(root: Path) -> list[dict[str, Any]]:
    pom = root / "pom.xml"
    if not pom.exists():
        return []
    try:
        lines = pom.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    modules: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        match = re.search(r"<module>\s*([^<]+?)\s*</module>", line)
        if match:
            name = match.group(1).strip()
            modules.append({"name": name, "evidence": _evidence(root, "pom.xml", index, name, "Maven module declaration.")})
    return modules


def _pattern_matches(root: Path, files: list[str], patterns: tuple[re.Pattern[str], ...], limit: int) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for rel in files:
        if len(matches) >= limit:
            break
        if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
            continue
        path = root / rel
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            text = line.strip()
            if not text:
                continue
            if text.startswith("//") or text.startswith("/*") or text.startswith("* "):
                continue
            if any(pattern.search(text) for pattern in patterns):
                matches.append({"path": rel, "line": index, "text": text[:240]})
                break
    return matches


def _dedupe_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    result: list[dict[str, Any]] = []
    for match in matches:
        key = (str(match.get("path")), int(match.get("line") or 1))
        if key in seen:
            continue
        seen.add(key)
        result.append(match)
    return result


def _validate_evidence(root: Path, artifact_name: str, item_id: str, index: int, evidence: Any) -> list[str]:
    prefix = f"{artifact_name}.{item_id}.evidence[{index}]"
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return [f"{prefix}: evidence must be an object"]
    rel = str(evidence.get("path") or "").strip()
    if not rel:
        errors.append(f"{prefix}: missing evidence path")
        return errors
    if Path(rel).is_absolute():
        errors.append(f"{prefix}: evidence path must be project-relative")
        candidate = Path(rel)
    else:
        candidate = root / rel
    if not _is_inside(root, candidate):
        errors.append(f"{prefix}: evidence path escapes project root")
    if not candidate.exists():
        errors.append(f"{prefix}: missing evidence path {rel}")
    line = evidence.get("line")
    if line is not None:
        try:
            line_int = int(line)
        except (TypeError, ValueError):
            errors.append(f"{prefix}: evidence line must be an integer")
        else:
            if line_int < 1:
                errors.append(f"{prefix}: evidence line must be positive")
            elif candidate.exists() and candidate.is_file():
                try:
                    line_count = len(candidate.read_text(encoding="utf-8", errors="ignore").splitlines())
                    if line_count and line_int > line_count:
                        errors.append(f"{prefix}: evidence line exceeds file length")
                except OSError:
                    pass
    if not str(evidence.get("symbol") or evidence.get("name") or "").strip():
        errors.append(f"{prefix}: missing evidence symbol/name")
    if not str(evidence.get("reason") or "").strip():
        errors.append(f"{prefix}: missing evidence reason")
    return errors


def _render_artifact_markdown(bundle: dict[str, Any], artifact_name: str, artifact: dict[str, Any]) -> str:
    profile = bundle.get("profile", {})
    lines = [
        "---",
        "kiwi_project_info: true",
        f"schema_version: {bundle.get('schema_version')}",
        f"artifact: {artifact_name}",
        f"project: {json.dumps(bundle.get('project_name', ''), ensure_ascii=False)}",
        f"profile: {json.dumps(profile.get('key', 'generic'), ensure_ascii=False)}",
        f"generated_at: {json.dumps(bundle.get('generated_at', ''), ensure_ascii=False)}",
        "---",
        "",
        f"# {artifact.get('title') or artifact_name}",
        "",
        str(artifact.get("summary") or "").strip(),
        "",
    ]
    for item in artifact.get("items", []):
        lines.extend(
            [
                f"## {item.get('title')}",
                "",
                str(item.get("summary") or "").strip(),
                "",
            ]
        )
        metadata_lines: list[str] = []
        if item.get("kind"):
            metadata_lines.append(f"- Kind: `{_escape_md(str(item.get('kind')))}`")
        if item.get("tags"):
            metadata_lines.append("- Tags: " + ", ".join(f"`{_escape_md(str(tag))}`" for tag in item.get("tags", [])))
        structured_keys = sorted(
            key
            for key in item
            if key not in {"id", "title", "summary", "kind", "tags", "evidence"}
        )
        for key in structured_keys:
            metadata_lines.append(f"- {key}: `{_escape_md(json.dumps(item.get(key), ensure_ascii=False))}`")
        if metadata_lines:
            lines.extend(metadata_lines)
            lines.append("")
        lines.extend(
            [
                "### Evidence",
                "",
                "| Path | Line | Symbol/Name | Reason |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for evidence in item.get("evidence", []):
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{_escape_md(str(evidence.get('path', '')))}`",
                        str(evidence.get("line") or ""),
                        _escape_md(str(evidence.get("symbol") or evidence.get("name") or "")),
                        _escape_md(str(evidence.get("reason") or "")),
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _format_evidence_short(evidence: dict[str, Any]) -> str:
    path = str(evidence.get("path") or "")
    line = evidence.get("line")
    symbol = str(evidence.get("symbol") or evidence.get("name") or "")
    location = f"{path}:{line}" if line else path
    return f"{location} ({symbol})"


def _redact_fast_only_project_info(text: str) -> str:
    redacted = text
    redacted = re.sub(
        r"\b(coder-35|dcp-front-developer|dcp-backend-developer|drt-front-developer|drt-backend-developer|drt-cms-front-developer|drt-cms-backend-developer)\b",
        "FAST direct mode",
        redacted,
    )
    redacted = re.sub(r"\btask_size\b", "work scope", redacted)
    redacted = re.sub(r"\bsubagent\b", "direct helper", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"티셔츠", "작업 범위", redacted)
    redacted = re.sub(r"ultrawork\s*팀", "direct work", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"implementation work", "project work", redacted, flags=re.IGNORECASE)
    redacted = re.sub(r"implementation agent", "project profile", redacted, flags=re.IGNORECASE)
    return redacted


def _artifact_dir(root: Path) -> Path:
    artifact_dir = project_info_artifact_dir(root).resolve()
    docs_root = aiops_docs_root().resolve()
    if not _is_inside(docs_root, artifact_dir):
        raise ValueError("Project Info artifact directory escapes AIOps docs root")
    return artifact_dir


def _is_inside(root: Path | str, candidate: Path | str) -> bool:
    try:
        root_abs = os.path.normcase(os.path.abspath(str(Path(root).resolve())))
        candidate_abs = os.path.normcase(os.path.abspath(str(Path(candidate).resolve())))
        return os.path.commonpath([root_abs, candidate_abs]) == root_abs
    except (OSError, ValueError):
        return False


def _evidence(root: Path, rel: str, line: int | None, symbol: str, reason: str) -> dict[str, Any]:
    path = root / rel
    if line is not None and (not path.exists() or not path.is_file()):
        line = None
    return {
        "path": rel,
        **({"line": int(line)} if line else {}),
        "symbol": symbol,
        "reason": reason,
    }


def _evidence_for_paths(root: Path, paths: list[str], symbol: str, reason: str) -> list[dict[str, Any]]:
    if not paths:
        return [_fallback_evidence(root, symbol, reason)]
    return [_evidence(root, rel, _line_for_pattern(root / rel, r"\S"), symbol, reason) for rel in paths if (root / rel).exists()]


def _fallback_item(root: Path, item_id: str, summary: str) -> dict[str, Any]:
    return {
        "id": _slug(item_id),
        "title": item_id,
        "summary": summary,
        "evidence": [_fallback_evidence(root, item_id, "Representative project file for negative or fallback finding.")],
    }


def _fallback_evidence(root: Path, symbol: str, reason: str) -> dict[str, Any]:
    preferred = [
        "package.json",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "README.md",
        "KIWI.md",
        "app/page.tsx",
        "backend/app/main.py",
        "src/main.js",
        "src/main.ts",
        "src/router/index.js",
    ]
    files = _collect_project_files(root)
    for rel in preferred + files:
        if (root / rel).exists() and (root / rel).is_file():
            return _evidence(root, rel, _line_for_pattern(root / rel, r"\S") or 1, symbol, reason)
    raise ValueError(f"Project Info Layer needs at least one evidence file under {root}")


def _line_for_pattern(path: Path, pattern: str) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    compiled = re.compile(pattern)
    try:
        for index, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if compiled.search(line):
                return index
    except OSError:
        return None
    return None


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _existing(paths: set[str], files: list[str]) -> list[str]:
    file_set = set(files)
    return sorted(path for path in paths if path in file_set)


def _top_level_directories(files: list[str]) -> list[str]:
    dirs = {Path(rel).parts[0] for rel in files if len(Path(rel).parts) > 1}
    preferred = ["app", "pages", "src", "backend", "docs", "public", "scripts"]
    return [item for item in preferred if item in dirs] + sorted(dirs - set(preferred))


def _child_directories(files: list[str], prefix: str) -> list[str]:
    children: set[str] = set()
    for rel in files:
        parts = Path(rel).parts
        if len(parts) >= 3 and parts[0] == prefix:
            children.add(parts[1])
    return sorted(children)


def _first_file_under(files: list[str], prefix: str) -> str | None:
    for rel in files:
        if rel.startswith(prefix):
            return rel
    return None


def _directory_responsibility(path: str) -> str:
    lowered = path.lower()
    if lowered in {"app", "pages"} or "router" in lowered:
        return "Application routing or user-facing page entry area."
    if "view" in lowered or "screen" in lowered:
        return "User-facing screen/view area."
    if "component" in lowered:
        return "Reusable UI component area."
    if "store" in lowered or "datastore" in lowered:
        return "Client or workflow state carrier area."
    if "api" in lowered or "client" in lowered:
        return "API client or interface adapter area."
    if "controller" in lowered:
        return "Backend request handling boundary."
    if "service" in lowered:
        return "Backend business logic or integration service area."
    if "mapper" in lowered or "repository" in lowered:
        return "Persistence or query mapping area."
    if lowered == "backend":
        return "Backend runtime and API service area."
    if lowered == "docs":
        return "Project documentation area."
    if lowered == "scripts":
        return "Developer automation and packaging area."
    if lowered == "public":
        return "Static asset area."
    return "Project area identified by directory structure; expand with local evidence before implementation."


def _symbol_from_text(text: str) -> str:
    for pattern in [
        r"name\s*:\s*['\"]([^'\"]+)",
        r"path\s*:\s*['\"]([^'\"]+)",
        r"(?:function|class|def)\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"@(?:Get|Post|Put|Delete|Patch)?Mapping\s*\(([^)]*)\)",
        r"axios\.(get|post|put|delete|patch)",
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()[:120] or "symbol"
    return ""


def _flow_title(match: dict[str, Any]) -> str:
    symbol = _symbol_from_text(str(match.get("text") or ""))
    return f"{symbol or 'flow marker'} in {match['path']}"


def _api_title(match: dict[str, Any]) -> str:
    symbol = _symbol_from_text(str(match.get("text") or ""))
    return f"{symbol or 'interface marker'} in {match['path']}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug[:120] or "item"


def _escape_md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
