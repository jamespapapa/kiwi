from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .db import now_iso
from .security import safe_join


IGNORE_DIRS = {
    ".git",
    ".next",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "target",
    "out",
    ".venv",
    "venv",
    "__pycache__",
}

KEY_FILES = [
    "package.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "README.md",
    "next.config.js",
    "next.config.ts",
    "vite.config.ts",
    "src/main.ts",
    "src/main.tsx",
    "src/App.tsx",
    "app/page.tsx",
    "pages/index.tsx",
]


def analyze_project(root: Path) -> dict[str, Any]:
    tree = _collect_tree(root)
    key_files = [file for file in KEY_FILES if (root / file).exists()]
    package_info = _read_package_json(root / "package.json")
    stack = _detect_stack(root, key_files, package_info)
    commands = _detect_commands(root, package_info)
    docs = _collect_docs(root)

    return {
        "root_path": str(root),
        "name": root.name,
        "analyzed_at": now_iso(),
        "stack": stack,
        "key_files": key_files,
        "tree": tree,
        "commands": commands,
        "docs": docs,
        "risks": _detect_risks(root),
    }


def write_initial_kiwi(root: Path, summary: dict[str, Any], extra_notes: str | None = None) -> None:
    docs_dir = safe_join(root, "docs")
    decisions_dir = safe_join(root, "docs", "decisions")
    docs_dir.mkdir(exist_ok=True)
    decisions_dir.mkdir(parents=True, exist_ok=True)

    architecture_path = safe_join(root, "docs", "architecture.md")
    decision_path = safe_join(root, "docs", "decisions", "0001-kiwi-local-runtime.md")

    architecture_path.write_text(_render_architecture_doc(summary), encoding="utf-8")
    if not decision_path.exists():
        decision_path.write_text(_render_decision_doc(summary), encoding="utf-8")

    kiwi_path = safe_join(root, "KIWI.md")
    block = _render_kiwi_block(summary, extra_notes)
    if kiwi_path.exists():
        current = kiwi_path.read_text(encoding="utf-8", errors="ignore")
        kiwi_path.write_text(_upsert_managed_block(current, block), encoding="utf-8")
    else:
        kiwi_path.write_text(_render_new_kiwi(summary, block), encoding="utf-8")


def load_project_context(root: Path, max_chars: int) -> str:
    kiwi_path = root / "KIWI.md"
    if not kiwi_path.exists():
        return "KIWI.md가 아직 없습니다."
    text = kiwi_path.read_text(encoding="utf-8", errors="ignore")
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[KIWI context truncated]"


def append_work_log(root: Path, title: str, summary: str) -> None:
    kiwi_path = safe_join(root, "KIWI.md")
    if not kiwi_path.exists():
        return
    stamp = now_iso()
    entry = f"\n\n### {stamp} - {title}\n\n{summary.strip()}\n"
    text = kiwi_path.read_text(encoding="utf-8", errors="ignore")
    if "## 작업 로그" not in text:
        text += "\n\n## 작업 로그\n"
    text += entry
    kiwi_path.write_text(text, encoding="utf-8")


def _collect_tree(root: Path, max_items: int = 360, max_depth: int = 4) -> list[str]:
    items: list[str] = []

    def walk(path: Path, depth: int) -> None:
        if len(items) >= max_items or depth > max_depth:
            return
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return
        for child in children:
            if len(items) >= max_items:
                break
            rel = child.relative_to(root).as_posix()
            if child.is_dir() and child.name in IGNORE_DIRS:
                continue
            items.append(rel + ("/" if child.is_dir() else ""))
            if child.is_dir():
                walk(child, depth + 1)

    walk(root, 1)
    return items


def _read_package_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _detect_stack(root: Path, key_files: list[str], package_info: dict[str, Any] | None) -> list[str]:
    stack: list[str] = []
    deps = {}
    if package_info:
        deps.update(package_info.get("dependencies", {}))
        deps.update(package_info.get("devDependencies", {}))
    if "next" in deps or "next.config.ts" in key_files or "next.config.js" in key_files:
        stack.append("Next.js")
    if "react" in deps:
        stack.append("React")
    if "typescript" in deps or (root / "tsconfig.json").exists():
        stack.append("TypeScript")
    if (root / "pom.xml").exists():
        stack.append("Maven")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        stack.append("Gradle")
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists():
        stack.append("Python")
    if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists():
        stack.append("Docker")
    return stack or ["Unclassified"]


def _detect_commands(root: Path, package_info: dict[str, Any] | None) -> list[dict[str, str]]:
    commands: list[dict[str, str]] = []
    if package_info:
        scripts = package_info.get("scripts", {})
        for name in ["dev", "build", "test", "lint", "typecheck"]:
            if name in scripts:
                commands.append({"name": name, "command": f"npm run {name}"})
    if (root / "pom.xml").exists():
        commands.extend(
            [
                {"name": "maven-test", "command": "mvn test"},
                {"name": "maven-package", "command": "mvn package"},
            ]
        )
    if (root / "requirements.txt").exists():
        commands.append({"name": "python-tests", "command": "python -m pytest"})
    return commands


def _collect_docs(root: Path) -> list[str]:
    docs: list[str] = []
    for candidate in ["README.md", "KIWI.md"]:
        if (root / candidate).exists():
            docs.append(candidate)
    docs_dir = root / "docs"
    if docs_dir.exists():
        for path in sorted(docs_dir.rglob("*.md"))[:80]:
            docs.append(path.relative_to(root).as_posix())
    return docs


def _detect_risks(root: Path) -> list[str]:
    risks: list[str] = []
    if not (root / ".git").exists():
        risks.append("Git 저장소가 아니므로 변경 추적과 diff 검토가 제한됩니다.")
    if not (root / "README.md").exists():
        risks.append("README.md가 없어 프로젝트 목적과 실행 방법이 코드에서만 추론됩니다.")
    return risks


def _render_new_kiwi(summary: dict[str, Any], block: str) -> str:
    return (
        f"# KIWI.md - {summary['name']} 프로젝트 지도\n\n"
        "이 파일은 KIWI 에이전트가 장기 기억으로 계속 참고하는 메인 지도입니다. "
        "상세 문서는 `docs/` 아래에 두고, 이 파일에는 현재 구조와 문서 인덱스를 유지합니다.\n\n"
        f"{block}\n"
    )


def _render_kiwi_block(summary: dict[str, Any], extra_notes: str | None) -> str:
    stack = ", ".join(summary.get("stack", []))
    key_files = "\n".join(f"- `{item}`" for item in summary.get("key_files", [])) or "- 확인된 핵심 파일 없음"
    docs = "\n".join(f"- `{item}`" for item in ["docs/architecture.md", "docs/decisions/0001-kiwi-local-runtime.md"])
    commands = "\n".join(
        f"- `{item['command']}` ({item['name']})" for item in summary.get("commands", [])
    ) or "- 자동 감지된 명령 없음"
    risks = "\n".join(f"- {item}" for item in summary.get("risks", [])) or "- 현재 기록된 위험 없음"
    tree = "\n".join(f"- `{item}`" for item in summary.get("tree", [])[:120]) or "- 파일 없음"
    notes = f"\n\n### 사용자 메모\n\n{extra_notes.strip()}\n" if extra_notes else ""

    return (
        "<!-- KIWI:MAP:START -->\n"
        "## 프로젝트 지도\n\n"
        f"- 프로젝트명: `{summary['name']}`\n"
        f"- 루트 경로: `{summary['root_path']}`\n"
        f"- 분석 시각: `{summary['analyzed_at']}`\n"
        f"- 감지 스택: {stack}\n\n"
        "### 핵심 파일\n\n"
        f"{key_files}\n\n"
        "### 실행/검증 명령 후보\n\n"
        f"{commands}\n\n"
        "### 문서 인덱스\n\n"
        f"{docs}\n\n"
        "### 구조 스냅샷\n\n"
        f"{tree}\n\n"
        "### 주의사항\n\n"
        f"{risks}"
        f"{notes}\n"
        "<!-- KIWI:MAP:END -->"
    )


def _upsert_managed_block(current: str, block: str) -> str:
    start = "<!-- KIWI:MAP:START -->"
    end = "<!-- KIWI:MAP:END -->"
    if start in current and end in current:
        before = current.split(start, 1)[0].rstrip()
        after = current.split(end, 1)[1].lstrip()
        return f"{before}\n\n{block}\n\n{after}".rstrip() + "\n"
    return current.rstrip() + "\n\n" + block + "\n"


def _render_architecture_doc(summary: dict[str, Any]) -> str:
    stack = ", ".join(summary.get("stack", []))
    key_files = "\n".join(f"- `{item}`" for item in summary.get("key_files", [])) or "- 확인된 핵심 파일 없음"
    return (
        f"# Architecture - {summary['name']}\n\n"
        "## 현재 해석\n\n"
        f"- 루트: `{summary['root_path']}`\n"
        f"- 감지 스택: {stack}\n\n"
        "## 핵심 파일\n\n"
        f"{key_files}\n\n"
        "## KIWI 운영 메모\n\n"
        "- 상세 설계가 확정되면 이 문서에 보강합니다.\n"
        "- 메인 지도와 문서 인덱스는 `KIWI.md`에서 관리합니다.\n"
    )


def _render_decision_doc(summary: dict[str, Any]) -> str:
    return (
        "# ADR 0001 - KIWI 장기 기억 구조\n\n"
        "## 결정\n\n"
        "`KIWI.md`를 메인 지도 파일로 사용하고, 상세 문서는 `docs/` 아래에 추가합니다.\n\n"
        "## 이유\n\n"
        "바이브코딩 세션이 길어질수록 현재 구조, 실행 명령, 결정사항, 주의사항을 "
        "한 곳에서 빠르게 회수할 수 있어야 합니다.\n\n"
        "## 적용 대상\n\n"
        f"- 프로젝트: `{summary['name']}`\n"
        f"- 루트: `{summary['root_path']}`\n"
    )
