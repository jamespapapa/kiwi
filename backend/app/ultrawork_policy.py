from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, NamedTuple

from .db import APP_ROOT


AGENT_PROMPTS_DIR = APP_ROOT / "docs" / "ultrawork-agents"
TASK_SIZES = ("xsmall", "small", "medium", "large", "xlarge")


class ProjectProfile(NamedTuple):
    key: str
    label: str
    developer_agent: str
    prompt_file: str
    activation_note: str


DCP_FRONT_PROFILE = ProjectProfile(
    key="dcp-front",
    label="DCP Front",
    developer_agent="dcp-front-developer",
    prompt_file="dcp-front-developer.md",
    activation_note="Vue 2 dcp-front 작업이므로 DCP 프론트 전용 개발자를 사용한다.",
)

DCP_BACKEND_PROFILE = ProjectProfile(
    key="dcp-services",
    label="DCP Services",
    developer_agent="dcp-backend-developer",
    prompt_file="dcp-backend-developer.md",
    activation_note="dcp-services 또는 하위 모듈 작업이므로 DCP 백엔드 전용 개발자를 사용한다.",
)

DRT_FRONT_PROFILE = ProjectProfile(
    key="drt-front",
    label="DRT Front",
    developer_agent="drt-front-developer",
    prompt_file="drt-front-developer.md",
    activation_note="DRT 고객용 Vue 3/Vite 프론트 작업이므로 DRT 프론트 전용 개발자를 사용한다.",
)

DRT_API_PROFILE = ProjectProfile(
    key="drt-api",
    label="DRT API",
    developer_agent="drt-backend-developer",
    prompt_file="drt-backend-developer.md",
    activation_note="DRT API Spring Boot/MyBatis 작업이므로 DRT 백엔드 전용 개발자를 사용한다.",
)

DRT_CMS_PROFILE = ProjectProfile(
    key="drt-cms",
    label="DRT CMS",
    developer_agent="drt-cms-backend-developer",
    prompt_file="drt-cms-backend-developer.md",
    activation_note="DRT CMS 통합 관리자 작업이다. target path/요구사항이 frontend면 drt-cms-front-developer, backend/API/DB면 drt-cms-backend-developer를 사용한다.",
)


def detect_project_profile(project: dict[str, Any] | Path | str) -> ProjectProfile | None:
    root = _project_root(project)
    if root is None:
        return None
    name = root.name.lower()
    normalized_path = root.as_posix().lower()
    parts = {part.lower() for part in root.parts}

    if name in {"dcp-front", "dcp-front-develop"} or "dcp-front" in normalized_path:
        return DCP_FRONT_PROFILE
    if _looks_like_dcp_front(root):
        return DCP_FRONT_PROFILE

    if name in {"drt-cms", "drt-cms-main"} or "drt-cms" in normalized_path or _looks_like_drt_cms(root):
        return DRT_CMS_PROFILE
    if name in {"drt-front", "drt-front-main"} or "drt-front" in normalized_path or _looks_like_drt_front(root):
        return DRT_FRONT_PROFILE
    if name in {"drt-api", "drt-api-main"} or "drt-api" in normalized_path or _looks_like_drt_api(root):
        return DRT_API_PROFILE

    if (
        name in {"dcp-services", "dcp-services-mevelop"}
        or "dcp-services" in normalized_path
        or "dcp-services-mevelop" in parts
    ):
        return DCP_BACKEND_PROFILE
    if _looks_like_dcp_services_root(root) or _looks_like_dcp_services_module(root):
        return DCP_BACKEND_PROFILE
    return None


def build_ultrawork_policy(
    project: dict[str, Any] | Path | str,
    intent: dict[str, Any] | None = None,
    selected_task_size: str | None = None,
    selected_task_size_reason: str | None = None,
) -> dict[str, Any]:
    profile = detect_project_profile(project)
    user_size = _normalize_task_size(selected_task_size)
    if not user_size:
        raise ValueError("selected_task_size is required; KIWI no longer auto-estimates t-shirt sizing.")
    size = user_size
    reason = selected_task_size_reason or f"사용자 선택값 `{user_size}`을 최종 source of truth로 사용한다."
    developer_agent, prompt_file, activation_note = _implementation_for_profile(profile, intent, _project_root(project))
    return {
        "task_size": size,
        "task_size_reason": reason,
        "task_size_source": "user",
        "selected_task_size": user_size or "",
        "selected_task_size_reason": selected_task_size_reason or "",
        "recommended_task_size": None,
        "recommended_task_size_reason": "",
        "mode": _mode_for_size(size),
        "profile_key": profile.key if profile else "generic",
        "profile_label": profile.label if profile else "Generic",
        "developer_agent": developer_agent,
        "developer_prompt_file": prompt_file,
        "activation_note": activation_note,
        "subagents": _subagents_for_size(size, developer_agent),
    }


def estimate_task_size(intent: dict[str, Any]) -> tuple[str, str]:
    explicit = _normalize_task_size(intent.get("task_size") or intent.get("tshirt_size"))
    explicit_reason = str(intent.get("task_size_reason") or intent.get("sizing_reason") or "").strip()

    text = " ".join(
        [
            str(intent.get("task_summary") or ""),
            str(intent.get("task_type") or ""),
            json.dumps(intent.get("target_files", []), ensure_ascii=False),
            json.dumps(intent.get("risk_flags", []), ensure_ascii=False),
            json.dumps(intent.get("search_queries", []), ensure_ascii=False),
        ]
    ).lower()
    target_count = len(intent.get("target_files", [])) if isinstance(intent.get("target_files"), list) else 0
    risk_count = len(intent.get("risk_flags", [])) if isinstance(intent.get("risk_flags"), list) else 0
    high_risk_terms = [
        "cross-module",
        "fullstack",
        "migration",
        "security",
        "auth",
        "redis",
        "eai",
        "session",
        "gateway",
        "배포",
        "보안",
        "인증",
        "권한",
        "개인정보",
        "금융",
        "거래",
        "전체",
        "아키텍처",
    ]
    medium_terms = [
        "api",
        "store",
        "datastore",
        "route",
        "router",
        "modal",
        "component",
        "controller",
        "service",
        "mapper",
        "테스트",
        "검증",
        "화면",
        "흐름",
        "batch",
        "job",
        "scheduler",
        "배치",
        "잡",
        "스케줄",
        "구조",
        "파악",
    ]
    xsmall_terms = ["오타", "문구", "주석", "한 줄", "one-line", "typo", "readme", "간단"]

    high_hits = sum(1 for term in high_risk_terms if term in text)
    medium_hits = sum(1 for term in medium_terms if term in text)
    xsmall_hits = sum(1 for term in xsmall_terms if term in text)

    if high_hits >= 3 or target_count >= 8 or risk_count >= 5:
        heuristic = ("xlarge", "cross-module/보안/데이터 위험 신호 또는 후보 파일 수가 많다.")
    elif high_hits >= 1 or target_count >= 4 or risk_count >= 3:
        heuristic = ("large", "영향 범위가 넓거나 데이터/API/세션 위험 신호가 있다.")
    elif medium_hits >= 2 or target_count >= 2 or risk_count >= 1:
        heuristic = ("medium", "여러 파일 또는 화면/API/store 흐름 확인이 필요하다.")
    elif xsmall_hits and target_count <= 1:
        heuristic = ("xsmall", "단일 파일 수준의 단순 수정 가능성이 높다.")
    else:
        heuristic = ("small", "작업은 구체적이지만 약간의 탐색과 focused verification이 필요하다.")

    if not explicit:
        return heuristic
    if _size_rank(heuristic[0]) >= _size_rank("medium") and _size_rank(heuristic[0]) > _size_rank(explicit):
        return heuristic[0], f"의도 분석은 `{explicit}`였지만 {heuristic[1]}"
    return explicit, explicit_reason or "의도 분석 모델이 산정한 규모를 사용한다."


def render_tshirt_section(policy: dict[str, Any]) -> list[str]:
    size = str(policy.get("task_size") or "medium")
    mode_label = "superpowers 규모 실행 모드" if str(policy.get("work_mode") or "") == "superpowers" else "ultrawork 운영 모드"
    return [
        "## 티셔츠 사이징",
        f"- 사용자 선택: `{size}`",
        "- 최종 source of truth: 사용자 선택값을 따른다.",
        f"- 선택 근거: {policy.get('task_size_reason') or '사용자가 선택한 규모다.'}",
        f"- {mode_label}: {policy.get('mode') or _mode_for_size(size)}",
        f"- 프로젝트 프로필: {policy.get('profile_label') or 'Generic'}",
        f"- 구현 담당 agent: `{policy.get('developer_agent') or 'coder-35'}`",
        "- 시작 시 이 사이징 결과와 그에 맞는 계획을 사용자에게 먼저 보고한다.",
    ]


def render_subagent_contract(policy: dict[str, Any]) -> list[str]:
    size = str(policy.get("task_size") or "small")
    developer = str(policy.get("developer_agent") or "coder-35")
    profile_note = str(policy.get("activation_note") or "").strip()
    lines = [
        "Kiwi는 먼저 사용자 선택 티셔츠 사이징 결과, 선택 근거, 규모별 실행 계획을 한국어로 보고한다.",
    ]
    if profile_note:
        lines.append(profile_note)

    if size == "xsmall":
        lines.extend(
            [
                "xsmall 모드: subagent를 호출하지 않는다. Kiwi가 직접 읽기/수정/검증을 짧게 수행한다.",
                "xsmall에서도 수정 전 대상 파일과 변경 의도를 한 줄로 확인하고, 검증은 가능한 가장 작은 명령만 실행한다.",
                "중간에 영향 범위가 넓어지면 현재 세션에서 임의로 size를 바꾸지 말고 더 큰 사이즈로 새 콘솔을 시작하라고 보고한다.",
            ]
        )
        return lines

    lines.append("파일 위치가 불명확하면 explorer-35에 짧은 read-only 탐색만 맡긴다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.")

    if size == "small":
        lines.extend(
            [
                f"small 모드: 구현이 필요하면 `{developer}` 1회 위임을 기본으로 하고, planner/architect는 생략한다.",
                "small 모드에서 reviewer-35는 공유 파일, 테스트 실패, 보안/데이터 변경이 있을 때만 호출한다.",
            ]
        )
    elif size == "medium":
        lines.extend(
            [
                f"medium 모드: explorer-35 탐색 후 `{developer}`가 한두 개의 좁은 slice를 구현한다.",
                "medium 모드에서는 구현 결과마다 reviewer-35가 diff와 검증 근거를 확인한다.",
                "데이터/API/store/공유 모듈 위험이 보이면 architect-35를 짧게 호출한다.",
            ]
        )
    else:
        lines.extend(
            [
                "large/xlarge 모드: planner-35가 요구사항과 수용조건을 정리하고 architect-35가 영향 범위와 변경 순서를 검토한다.",
                f"구현은 `{developer}`가 담당한다. Kiwi는 큰 변경을 여러 repair slice로 나누어 위임한다.",
                "각 구현 결과 뒤 reviewer-35 리뷰를 필수로 수행하고, 실패/수정 루프 전 debugger-35가 root cause와 교정 전략을 정리한다.",
                "검증 명령 실행과 결과 해석이 필요하면 tester-35를 사용한다.",
            ]
        )
        if size == "xlarge":
            lines.append("xlarge 모드: phase별 계획, phase별 리뷰, 최종 통합 리뷰를 분리하고 동시 구현은 파일 ownership이 분리될 때만 허용한다.")

    lines.extend(
        [
            f"`{developer}` 위임에는 Objective, Scope, Files/ownership, Required reading, Mandatory workflow, Exact steps, Exact Edit Protocol, Non-goals, Verification, Required response, failure 시 stop-and-return-to-Kiwi 규칙을 포함한다.",
            "Mandatory workflow는 scope 확인 -> 현재 파일 read -> impact map -> 작은 수정 -> focused verification -> evidence 보고 순서로 쓴다.",
            "Exact Edit Protocol은 edit 직전 target range read_file, `@file` 참조나 prompt-attached file content는 edit tool read gate를 만족하지 않으므로 현재 세션에서 read_file을 먼저 호출, latest read_file 출력에서 old_string 복사, 같은 파일 edit 성공 후 snippet stale 처리, 삭제/교체가 1줄이든 N줄이든 any N-line deletion/replacement 기준으로 변경 대상만 포함한 smallest exact current span을 old_string으로 사용, 보존할 boundary/context 라인이 old_string에 포함되면 new_string에도 그대로 보존하고 아니면 span에서 제외, edit_no_occurrence_found 후 같은/더 큰 old_string 재시도 금지, 2회 실패 시 Kiwi/debugger 반환, PowerShell regex/Set-Content 우회 금지를 요구한다.",
            "File path precision도 위임 계약에 포함한다: 파일 경로는 이전 tool 출력이나 사용자 메시지에서 문자 그대로 복사하고, 한글 파일명을 재타이핑하거나 `-`/`_` 주변에 공백을 넣지 않으며, `File not found. Did you mean: <경로>` 힌트를 받으면 제안 경로를 그대로 사용해 1회 재시도하고, 큰 파일은 read_file offset/limit으로 나눠 읽는다.",
            "Required response는 scope confirmed/stop reason, files read, files changed, impact map, verification, remaining risks/exact question을 요구한다.",
            f"`{developer}`가 같은 파일/slice에서 edit를 2번 실패하면 3번째 edit 또는 shell rewrite를 시도하지 말고 현재 파일 상태와 실패한 old_string을 Kiwi/debugger로 반환한다.",
            "진행 중 애매하거나 사용자 판단이 필요하면 일반 텍스트 질문 대신 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다.",
        ]
    )
    return lines


def render_qwencode_tool_cheatsheet() -> list[str]:
    return [
        "툴 스키마가 확실하지 않으면 먼저 해당 툴 사용법/schema를 로드한 뒤 정확한 파라미터명으로 호출한다.",
        "`todo_write`: 계획 작성과 상태 갱신에 필수다. 표시명이나 MCP-prefixed alias가 아니라 실제 호출명 `todo_write`만 사용한다.",
        "`read_file`: 존재 확인 후 절대 `file_path`로 읽는다. 파일 경로는 손으로 다시 타이핑하지 말고 이전 tool 출력(list_directory/glob/grep_search/read_file)이나 사용자 메시지에서 문자 그대로 복사한다. 특히 한글 파일명에서 `-`/`_` 주변에 공백을 임의로 넣지 않는다. `File not found. Did you mean: <경로>` 힌트를 받으면 제안 경로를 그대로 사용해 1회 재시도한다. 디렉터리 경로도 동일하다: 중간 디렉터리를 추측해 만들지 말고 부모를 먼저 list한다. 큰 파일은 offset/limit으로 범위를 나눠 읽는다.",
        "`write_file`: 새 파일 또는 의도적 전체 교체에만 쓴다. 긴 문서/파일을 한 번의 write_file로 쓰면 max_tokens 절단으로 잘린 파일이 생길 수 있다. 먼저 골격과 첫 섹션만 write_file로 만들고, 나머지는 섹션 단위로 edit append 한다.",
        "`edit`: edit 직전 target range를 읽고 latest read_file 출력에서 `old_string`을 그대로 복사한다. `@file` 참조나 prompt-attached file content는 edit tool read gate를 만족하지 않으므로 현재 세션에서 `read_file`을 먼저 호출해야 한다. edit 성공 후 같은 파일의 이전 snippet은 stale이다. 삭제/교체가 1줄이든 N줄이든 any N-line deletion/replacement 기준으로 변경 대상만 포함한 smallest exact current span을 `old_string`으로 쓴다. 보존할 boundary/context 라인이 `old_string`에 포함되면 `new_string`에도 그대로 보존하고, 아니면 span에서 제외한다. `edit_no_occurrence_found` 후 같은/더 큰 `old_string` 재시도와 PowerShell regex/Set-Content 우회는 금지다.",
        "`ask_user_question`: 호출 직전에 사용법/schema를 먼저 로드하고, `questions`를 문자열이 아니라 질문 객체 배열로 준다. 일반 텍스트 질문이나 MCP-prefixed alias를 쓰지 않는다.",
    ]


def _project_root(project: dict[str, Any] | Path | str) -> Path | None:
    if isinstance(project, dict):
        raw = project.get("root_path")
    else:
        raw = project
    if raw is None:
        return None
    try:
        return Path(str(raw)).expanduser().resolve()
    except OSError:
        return Path(str(raw)).expanduser()


def _looks_like_dcp_front(root: Path) -> bool:
    package_json = root / "package.json"
    if not package_json.exists():
        return False
    try:
        package_text = package_json.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return (
        '"vue"' in package_text
        and '"vuex"' in package_text
        and (root / "src" / "views" / "mo" / "mysamsunglife").exists()
        and (root / "src" / "store" / "modules" / "com" / "DataStore.js").exists()
    )


def _looks_like_dcp_services_root(root: Path) -> bool:
    pom = root / "pom.xml"
    if not pom.exists():
        return False
    try:
        text = pom.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return False
    return all(module in text for module in ["<module>dcp-core</module>", "<module>dcp-gateway</module>", "<module>dcp-insurance</module>"])


def _looks_like_dcp_services_module(root: Path) -> bool:
    if not (root / "pom.xml").exists():
        return False
    if re.match(r"^dcp-[a-z0-9-]+$", root.name.lower()) and (root / "src" / "main").exists():
        return True
    for parent in root.parents:
        if parent.name.lower() in {"dcp-services", "dcp-services-mevelop"}:
            return True
        if _looks_like_dcp_services_root(parent):
            return True
    return False


def _looks_like_drt_front(root: Path) -> bool:
    candidates = [root, root / "dev", root / "ui"]
    for base in candidates:
        package_json = base / "package.json"
        if not package_json.exists():
            continue
        text = _read_lower(package_json)
        if (
            '"vue"' in text
            and '"vite"' in text
            and (base / "src" / "router" / "index.ts").exists()
            and (base / "src" / "module" / "DrtHttpClient.ts").exists()
        ):
            return True
    return False


def _looks_like_drt_api(root: Path) -> bool:
    pom = root / "pom.xml"
    if not pom.exists():
        return False
    text = _read_lower(pom)
    return (
        "<artifactid>drt-api</artifactid>" in text
        or (root / "src" / "main" / "java" / "com" / "samsunglife" / "drt" / "api" / "Application.java").exists()
    )


def _looks_like_drt_cms(root: Path) -> bool:
    if (root / "frontend" / "package.json").exists() and (root / "backend" / "pom.xml").exists():
        return True
    pom = root / "pom.xml"
    if pom.exists() and "<artifactid>drt-cms-parent</artifactid>" in _read_lower(pom):
        return True
    package_json = root / "package.json"
    if package_json.exists() and '"edirect"' in _read_lower(package_json) and (root / "src" / "router").exists():
        return True
    if (
        (root / "src" / "main" / "java" / "com" / "samsunglife" / "drt" / "cms").exists()
        or (root / "backend" / "src" / "main" / "java" / "com" / "samsunglife" / "drt" / "cms").exists()
    ):
        return True
    for parent in root.parents:
        if parent.name.lower() in {"drt-cms", "drt-cms-main"}:
            return True
        if (parent / "frontend" / "package.json").exists() and (parent / "backend" / "pom.xml").exists():
            return True
    return False


def _implementation_for_profile(
    profile: ProjectProfile | None,
    intent: dict[str, Any] | None,
    root: Path | None,
) -> tuple[str, str, str]:
    if profile is None:
        return "coder-35", "", "특화 프로젝트가 아니므로 기본 coder-35를 사용한다."
    if profile.key != "drt-cms":
        return profile.developer_agent, profile.prompt_file, profile.activation_note
    if _drt_cms_prefers_frontend(root, intent):
        return (
            "drt-cms-front-developer",
            "drt-cms-front-developer.md",
            "DRT CMS frontend/Quasar 관리자 화면 작업이므로 DRT CMS 프론트 전용 개발자를 사용한다.",
        )
    return (
        "drt-cms-backend-developer",
        "drt-cms-backend-developer.md",
        "DRT CMS backend/Spring 관리자 API 작업이므로 DRT CMS 백엔드 전용 개발자를 사용한다.",
    )


def _drt_cms_prefers_frontend(root: Path | None, intent: dict[str, Any] | None) -> bool:
    if root is not None:
        if root.name.lower() == "frontend":
            return True
        if (root / "package.json").exists() and (root / "src" / "router").exists():
            return True
    text_parts: list[str] = []
    if isinstance(intent, dict):
        for key in ("task_summary", "task_type", "target_files", "search_queries", "risk_flags"):
            value = intent.get(key)
            text_parts.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value or ""))
    text = " ".join(text_parts).lower()
    frontend_terms = [
        "frontend/",
        "src/views/",
        "src/router/",
        "src/services/",
        ".vue",
        "quasar",
        "ag-grid",
        "pinia",
        "화면",
        "버튼",
        "모달",
        "그리드",
    ]
    backend_terms = [
        "backend/",
        "src/main/java",
        "src/main/resources",
        ".java",
        ".xml",
        "controller",
        "service",
        "repository",
        "mybatis",
        "api",
        "db",
        "sql",
    ]
    return sum(1 for term in frontend_terms if term in text) > sum(1 for term in backend_terms if term in text)


def _read_lower(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").lower()
    except OSError:
        return ""


def _normalize_task_size(value: Any) -> str:
    size = str(value or "").strip().lower()
    return size if size in TASK_SIZES else ""


def _mode_for_size(size: str) -> str:
    return {
        "xsmall": "solo",
        "small": "light",
        "medium": "balanced",
        "large": "full",
        "xlarge": "full-phased",
    }.get(size, "light")


def _size_rank(size: str) -> int:
    try:
        return TASK_SIZES.index(size)
    except ValueError:
        return TASK_SIZES.index("small")


def _subagents_for_size(size: str, developer_agent: str) -> list[str]:
    if size == "xsmall":
        return []
    if size == "small":
        return ["explorer-35", developer_agent, "reviewer-35"]
    if size == "medium":
        return ["explorer-35", developer_agent, "architect-35", "reviewer-35"]
    return ["planner-35", "architect-35", "explorer-35", developer_agent, "reviewer-35", "debugger-35", "tester-35"]
