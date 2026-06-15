from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .db import now_iso
from .qwencode_runtime import (
    find_latest_qwencode_runtime,
    find_project_qwen_command,
    resolve_project_qwen_runtime,
    resolve_qwen_init_command,
)
from .ultrawork_policy import detect_project_profile


POM_NS = {"m": "http://maven.apache.org/POM/4.0.0"}
QWEN_RUNTIMES_DIR = "runtimes"
NODE_RUNTIME = "node"
NODE10_RUNTIME = "node10"
JAVA17_RUNTIME = "java"
JAVA8_RUNTIME = "java8"
MAVEN_RUNTIME = "maven3.6.3"
TOMCAT9_RUNTIME = "tomcat9"


def collect_project_runtime(root: Path, qwen_harness: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = detect_project_profile(root)
    project_key = profile.key if profile else _guess_project_key(root)
    qwen = _collect_qwen_runtime(root, qwen_harness or {})
    components = _detect_components(root, project_key)
    _attach_backend_toolchain(components, qwen)
    _attach_frontend_toolchain(components, qwen)
    items = _collect_tool_versions(root, qwen, components)
    requirements = _collect_requirements(project_key, components, items, qwen)
    actions = _collect_actions(project_key, components, items, qwen)

    return {
        "checked_at": now_iso(),
        "cwd": str(root),
        "project_key": project_key,
        "project_label": profile.label if profile else project_key,
        "items": items,
        "requirements": requirements,
        "components": components,
        "actions": actions,
        "qwen": qwen,
    }


def launch_project_runtime_action(root: Path, action_id: str, runtime_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    runtime = runtime_checks or collect_project_runtime(root)
    actions = runtime.get("actions") if isinstance(runtime, dict) else []
    action = next((item for item in actions or [] if item.get("id") == action_id), None)
    if not isinstance(action, dict):
        raise ValueError(f"unknown runtime action: {action_id}")
    if action.get("status") == "unavailable":
        raise ValueError(str(action.get("detail") or f"runtime action is unavailable: {action_id}"))

    cwd = Path(str(action.get("cwd") or root)).resolve()
    command = str(action.get("command") or "").strip()
    if not command:
        raise ValueError(f"runtime action has no command: {action_id}")
    if root.resolve() not in [cwd, *cwd.parents]:
        raise ValueError("runtime action cwd is outside the selected project root")

    terminal = _open_new_terminal(cwd, command, title=f"KIWI {action.get('label') or action_id}")
    return {
        "status": "launched",
        "action": action,
        "terminal": terminal,
        "command": command,
        "cwd": str(cwd),
    }


def _detect_components(root: Path, project_key: str) -> dict[str, Any]:
    backend = _detect_backend_component(root, project_key)
    frontend = _detect_frontend_component(root, project_key)
    playwright = _detect_playwright_component(frontend)
    return {
        "backend": backend,
        "frontend": frontend,
        "playwright": playwright,
    }


def _detect_backend_component(root: Path, project_key: str) -> dict[str, Any] | None:
    if project_key == "dcp-front" or project_key == "drt-front":
        return None
    if project_key == "drt-cms":
        if root.name.lower() == "frontend" and (root / "package.json").exists():
            return None
        backend_root = root / "backend" if (root / "backend" / "pom.xml").exists() else root
        root_pom = backend_root / "pom.xml"
        return _backend_from_pom(backend_root, root_pom, project_key)
    return _backend_from_pom(_find_maven_work_root(root, project_key), _find_maven_reactor_pom(root, project_key), project_key)


def _backend_from_pom(work_root: Path | None, root_pom: Path | None, project_key: str) -> dict[str, Any] | None:
    if not work_root or not root_pom or not root_pom.exists():
        return None
    modules = _pom_modules(root_pom)
    properties = _pom_properties(root_pom)
    spring_boot = _has_text(root_pom, "spring-boot-maven-plugin") or _has_java_main(work_root)
    java_required = _required_java(project_key, properties)
    component: dict[str, Any] = {
        "type": "backend",
        "cwd": str(work_root),
        "pom": str(root_pom),
        "java_required": java_required,
        "maven_required": "3.x",
        "project_key": project_key,
        "packaging": _pom_packaging(root_pom),
        "artifact_id": _pom_text(root_pom, "artifactId"),
        "modules": modules,
        "spring_boot": spring_boot,
    }
    if project_key == "dcp-services":
        component["dcp_core"] = _collect_dcp_core_status(work_root, modules)
        component["tomcat_required"] = "9.0.115"
        component["deployable_modules"] = _dcp_web_modules(work_root, modules)
        component["tomcat_deploy_module"] = _default_dcp_tomcat_module(work_root, modules)
        component["tomcat_deploy_context"] = component["tomcat_deploy_module"]
    return component


def _detect_frontend_component(root: Path, project_key: str) -> dict[str, Any] | None:
    package_dir = _find_frontend_package_dir(root, project_key)
    if not package_dir:
        return None
    package_path = package_dir / "package.json"
    package = _read_package_json(package_path)
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    package_manager = _package_manager(project_key, package_dir)
    required = _required_node(project_key)
    return {
        "type": "frontend",
        "cwd": str(package_dir),
        "package_json": str(package_path),
        "package_name": package.get("name"),
        "package_manager": package_manager,
        "node_required": required,
        "vue": _dependency_version(package, "vue"),
        "vite": _dependency_version(package, "vite"),
        "scripts": scripts,
        "script_summary": {key: scripts.get(key) for key in ["serve", "serve:local", "dev", "start", "build", "test:e2e"] if key in scripts},
    }


def _detect_playwright_component(frontend: dict[str, Any] | None) -> dict[str, Any]:
    qwen_runtime = find_latest_qwencode_runtime()
    qwen_node = _find_qwen_tool(qwen_runtime, "node", NODE_RUNTIME) or _which_runtime_executable("node", ["node.exe", "node"])
    qwen_npx = _find_qwen_tool(qwen_runtime, "npx", NODE_RUNTIME) or _which_runtime_executable("npx", ["npx.cmd", "npx.bat", "npx"])
    if not frontend:
        return {
            "status": "not_applicable",
            "qwencode_node": str(qwen_node) if qwen_node else None,
            "detail": "프론트엔드 package.json이 없어 Playwright 실행 대상을 만들 수 없습니다.",
        }
    cwd = Path(str(frontend["cwd"]))
    local_playwright = _local_bin(cwd, "playwright")
    return {
        "status": "ready" if qwen_node else "missing_node",
        "cwd": str(cwd),
        "qwencode_node": str(qwen_node) if qwen_node else None,
        "qwencode_npx": str(qwen_npx) if qwen_npx else None,
        "local_playwright": str(local_playwright) if local_playwright else None,
        "command": _playwright_command(cwd, qwen_npx, local_playwright),
        "detail": "qwencode Node 22 런타임으로 Playwright를 실행합니다. 브라우저 서버는 별도 프론트 실행 액션으로 먼저 띄우세요.",
    }


def _attach_frontend_toolchain(components: dict[str, Any], qwen: dict[str, Any]) -> None:
    frontend = components.get("frontend")
    if not isinstance(frontend, dict):
        return
    runtime = Path(qwen["runtime_dir"]) if qwen.get("runtime_dir") else None
    required = str(frontend.get("node_required") or "")
    node_folder = NODE10_RUNTIME if required == "10" else NODE_RUNTIME
    managed_node = _find_qwen_tool(runtime, "node", node_folder)
    managed_npm = _find_qwen_tool(runtime, "npm", node_folder)
    managed_npx = _find_qwen_tool(runtime, "npx", node_folder)
    managed_yarn = _find_qwen_tool(runtime, "yarn", node_folder)
    managed_runtime_dir = _runtime_dir(runtime, node_folder) if runtime else None
    managed_runtime_present = bool(managed_runtime_dir and managed_runtime_dir.exists())
    path_fallback_allowed = not (required == "10" and managed_runtime_present)
    node = managed_node or (_which_runtime_executable("node", ["node.exe", "node"]) if path_fallback_allowed else None)
    npm = managed_npm or (_which_runtime_executable("npm", ["npm.cmd", "npm.bat", "npm"]) if path_fallback_allowed else None)
    npx = managed_npx or (_which_runtime_executable("npx", ["npx.cmd", "npx.bat", "npx"]) if path_fallback_allowed else None)
    yarn = managed_yarn or (_which_runtime_executable("yarn", ["yarn.cmd", "yarn.bat", "yarn"]) if path_fallback_allowed else None)
    frontend["node_runtime_folder"] = _runtime_relative(node_folder)
    frontend["node_runtime_dir"] = str(managed_runtime_dir) if managed_runtime_dir else None
    frontend["node_runtime_present"] = managed_runtime_present
    frontend["managed_node_runtime"] = bool(managed_node)
    frontend["node_executable"] = str(node) if node else None
    frontend["npm_executable"] = str(npm) if npm else None
    frontend["npx_executable"] = str(npx) if npx else None
    frontend["managed_npm_executable"] = str(managed_npm) if managed_npm else None
    frontend["managed_npx_executable"] = str(managed_npx) if managed_npx else None
    frontend["managed_yarn_executable"] = str(managed_yarn) if managed_yarn else None
    frontend["yarn_executable"] = str(yarn) if yarn else None


def _attach_backend_toolchain(components: dict[str, Any], qwen: dict[str, Any]) -> None:
    backend = components.get("backend")
    if not isinstance(backend, dict):
        return
    runtime = Path(qwen["runtime_dir"]) if qwen.get("runtime_dir") else None
    java_required = str(backend.get("java_required") or "")
    java_folder = JAVA8_RUNTIME if java_required == "8" else JAVA17_RUNTIME
    managed_java = _find_qwen_tool(runtime, "java", java_folder, subdir="bin")
    managed_maven = _find_qwen_tool(runtime, "mvn", MAVEN_RUNTIME, subdir="bin")
    managed_tomcat = _find_qwen_tool(runtime, "catalina", TOMCAT9_RUNTIME, subdir="bin")
    java_home = _runtime_dir(runtime, java_folder) if managed_java else None
    maven_home = _runtime_dir(runtime, MAVEN_RUNTIME) if managed_maven else None
    tomcat_home = _runtime_dir(runtime, TOMCAT9_RUNTIME) if managed_tomcat else None
    backend["java_runtime_folder"] = _runtime_relative(java_folder)
    backend["java_runtime_dir"] = str(_runtime_dir(runtime, java_folder)) if runtime else None
    backend["maven_runtime_folder"] = _runtime_relative(MAVEN_RUNTIME)
    backend["maven_runtime_dir"] = str(_runtime_dir(runtime, MAVEN_RUNTIME)) if runtime else None
    backend["managed_java_runtime"] = bool(managed_java)
    backend["managed_maven_runtime"] = bool(managed_maven)
    backend["tomcat_runtime_folder"] = _runtime_relative(TOMCAT9_RUNTIME)
    backend["tomcat_runtime_dir"] = str(_runtime_dir(runtime, TOMCAT9_RUNTIME)) if runtime else None
    backend["managed_tomcat_runtime"] = bool(managed_tomcat)
    backend["java_home"] = str(java_home) if java_home else None
    backend["maven_home"] = str(maven_home) if maven_home else None
    backend["tomcat_home"] = str(tomcat_home) if tomcat_home else None
    backend["java_executable"] = str(managed_java) if managed_java else None
    backend["maven_executable"] = str(managed_maven) if managed_maven else None
    backend["tomcat_executable"] = str(managed_tomcat) if managed_tomcat else None


def _collect_tool_versions(root: Path, qwen: dict[str, Any], components: dict[str, Any]) -> list[dict[str, Any]]:
    qwen_runtime = Path(qwen["runtime_dir"]) if qwen.get("runtime_dir") else None
    backend = components.get("backend") if isinstance(components.get("backend"), dict) else {}
    frontend = components.get("frontend") if isinstance(components.get("frontend"), dict) else {}
    backend_java = _path_from_optional(backend.get("java_executable") if isinstance(backend, dict) else None)
    backend_maven = _path_from_optional(backend.get("maven_executable") if isinstance(backend, dict) else None)
    backend_tomcat = _path_from_optional(backend.get("tomcat_executable") if isinstance(backend, dict) else None)
    frontend_node = _path_from_optional(frontend.get("node_executable") if isinstance(frontend, dict) else None)
    frontend_npm = _path_from_optional(frontend.get("npm_executable") if isinstance(frontend, dict) else None)
    frontend_yarn = _path_from_optional(frontend.get("yarn_executable") if isinstance(frontend, dict) else None)
    backend_env = _backend_runtime_env(backend) if isinstance(backend, dict) else {}
    frontend_env = _frontend_runtime_env(frontend) if isinstance(frontend, dict) else {}
    items: list[dict[str, Any]] = []
    if backend:
        java_executable = backend_java or _which_runtime_executable("java", ["java.exe", "java"])
        maven_executable = backend_maven or _which_runtime_executable("mvn", ["mvn.cmd", "mvn.bat", "mvn.exe", "mvn"])
        items.append(_run_version_check("Java", java_executable, ["-version"], root, env=backend_env if backend_java else None))
        items.append(_run_version_check("Maven", maven_executable, ["-version"], root, env=backend_env if backend_maven else None))
        if backend.get("tomcat_required"):
            items.append(_run_version_check("Tomcat", backend_tomcat, ["version"], root, env=backend_env if backend_tomcat else None))
    if frontend:
        package_manager = str(frontend.get("package_manager") or "npm")
        required_node = str(frontend.get("node_required") or "")
        managed_node_runtime_present = bool(frontend.get("node_runtime_present"))
        path_fallback_allowed = not (required_node == "10" and managed_node_runtime_present)
        node_executable = frontend_node
        if node_executable is None and path_fallback_allowed:
            node_executable = _find_qwen_tool(qwen_runtime, "node", NODE_RUNTIME) or _which_runtime_executable("node", ["node.exe", "node"])
        items.append(
            _run_version_check(
                "Node",
                node_executable,
                ["--version"],
                _version_check_cwd(node_executable, root),
                env=frontend_env if frontend_env else None,
            )
        )
        if package_manager == "yarn":
            yarn_executable = frontend_yarn or (_which_runtime_executable("yarn", ["yarn.cmd", "yarn.bat", "yarn"]) if path_fallback_allowed else None)
            items.append(_collect_yarn_runtime_check(frontend, yarn_executable))
        else:
            npm_executable = frontend_npm or (_which_runtime_executable("npm", ["npm.cmd", "npm.bat", "npm"]) if path_fallback_allowed else None)
            items.append(
                _run_version_check(
                    "Npm",
                    npm_executable,
                    ["--version"],
                    _version_check_cwd(npm_executable, root),
                    env=frontend_env if frontend_env else None,
                )
            )
    return items


def _collect_requirements(
    project_key: str,
    components: dict[str, Any],
    items: list[dict[str, Any]],
    qwen: dict[str, Any],
) -> list[dict[str, Any]]:
    by_name = {str(item.get("name")): item for item in items}
    requirements: list[dict[str, Any]] = []
    backend = components.get("backend")
    frontend = components.get("frontend")

    if backend:
        java_required = str(backend.get("java_required") or "")
        requirements.append(_java_requirement(by_name.get("Java"), java_required))
        requirements.append(_tool_requirement(by_name.get("Maven"), "Maven", "qwencode runtimes/maven3.6.3 or PATH mvn available"))
        if project_key == "dcp-services":
            dcp_core = backend.get("dcp_core") or {}
            requirements.append(
                {
                    "id": "dcp-core-reactor",
                    "name": "DCP core reactor",
                    "expected": "root POM includes dcp-core and modules depend on local reactor artifact",
                    "actual": dcp_core.get("summary"),
                    "status": "ok" if dcp_core.get("ok") else "error",
                    "detail": dcp_core.get("detail"),
                }
            )
            requirements.append(_tomcat_requirement(by_name.get("Tomcat"), backend))

    if frontend:
        requirements.append(_node_requirement(by_name.get("Node"), str(frontend.get("node_required") or "")))
        pm = str(frontend.get("package_manager") or "")
        requirements.append(_tool_requirement(by_name.get("Yarn") if pm == "yarn" else by_name.get("Npm"), pm, f"{pm} available"))

    requirements.append(
        {
            "id": "qwen-node-playwright",
            "name": "Playwright Node",
            "expected": "qwencode bundled Node 22",
            "actual": qwen.get("runtime_dir") or "not found",
            "status": "ok" if (components.get("playwright") or {}).get("qwencode_node") else "warn",
            "detail": "Playwright 테스트는 project Node와 분리해서 qwencode Node 런타임으로 실행합니다.",
        }
    )
    return requirements


def _collect_actions(
    project_key: str,
    components: dict[str, Any],
    items: list[dict[str, Any]],
    qwen: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    backend = components.get("backend")
    frontend = components.get("frontend")
    maven_ok = _item_ok(items, "Maven")
    java_item = _find_item(items, "Java")
    node_item = _find_item(items, "Node")

    if backend:
        cwd = str(backend["cwd"])
        backend_ready = maven_ok and _java_matches(java_item, str(backend.get("java_required") or ""))
        for goal in ["clean", "compile", "test"]:
            command = _backend_maven_command(backend, goal)
            actions.append(
                _action(
                    f"maven-{goal}",
                    f"mvn {goal}",
                    cwd,
                    command,
                    enabled=backend_ready,
                    detail="Maven과 프로젝트 요구 JDK 버전이 맞아야 실행할 수 있습니다.",
                )
            )
        if project_key == "dcp-services":
            tomcat_ready = backend_ready and _item_ok(items, "Tomcat")
            actions.append(
                _action(
                    "backend-run",
                    "tomcat deploy/run",
                    cwd,
                    _dcp_tomcat_deploy_command(backend),
                    enabled=tomcat_ready,
                    detail=(
                        "dcp-services는 Spring Boot 직접 실행이 아니라 runtimes/tomcat9에 dcp-gateway exploded webapp을 배포한 뒤 catalina run으로 실행합니다."
                        if tomcat_ready
                        else f"Tomcat 9 runtime이 필요합니다: {backend.get('tomcat_runtime_dir') or _runtime_relative(TOMCAT9_RUNTIME)}"
                    ),
                )
            )
        elif backend.get("spring_boot"):
            run_command = _backend_maven_command(backend, "spring-boot:run")
            actions.append(
                _action(
                    "backend-run",
                    "backend run",
                    cwd,
                    run_command,
                    enabled=backend_ready,
                    detail="Spring Boot Maven plugin/main class 기반 실행입니다.",
                )
            )
        else:
            actions.append(
                _action(
                    "backend-run",
                    "backend run",
                    cwd,
                    "mvn spring-boot:run",
                    enabled=False,
                    detail="이 백엔드는 직접 실행 가능한 Spring Boot main/plugin을 감지하지 못했습니다. clean/compile/test를 우선 사용하세요.",
                )
            )

    if frontend:
        cwd = str(frontend["cwd"])
        pm = str(frontend["package_manager"] or "npm")
        pm_command = _frontend_package_command(frontend, pm)
        scripts = frontend.get("scripts") if isinstance(frontend.get("scripts"), dict) else {}
        dev_script = _frontend_dev_script(project_key, scripts)
        build_script = _first_existing_script(scripts, ["build:local", "build"])
        test_script = _first_existing_script(scripts, ["test:e2e", "test"])
        pm_ok = _node_matches(node_item, str(frontend.get("node_required") or "")) and (
            _item_ok(items, "Yarn") if pm == "yarn" else _item_ok(items, "Npm")
        )
        if pm == "yarn":
            actions.append(
                _action(
                    "frontend-install",
                    "yarn install --offline",
                    cwd,
                    f"{pm_command} install --offline",
                    enabled=pm_ok,
                    detail="Yarn lockfile 기준으로 오프라인 의존성을 설치합니다. 상태 체크가 아니라 사용자가 실행하는 액션입니다.",
                )
            )
        if dev_script:
            actions.append(_action("frontend-run", "frontend run", cwd, _frontend_script_command(pm_command, pm, dev_script), enabled=pm_ok))
        if build_script:
            actions.append(_action("frontend-build", "frontend build", cwd, _frontend_script_command(pm_command, pm, build_script), enabled=pm_ok))
        if test_script:
            actions.append(_action("frontend-test", "frontend test", cwd, _frontend_script_command(pm_command, pm, test_script), enabled=pm_ok))

    playwright = components.get("playwright") or {}
    if playwright.get("command"):
        actions.append(
            _action(
                "playwright-test",
                "playwright test",
                str(playwright.get("cwd") or frontend.get("cwd") if frontend else "."),
                str(playwright["command"]),
                enabled=bool(playwright.get("command")),
                detail="프론트 dev server를 먼저 실행한 뒤 새 터미널에서 Playwright를 실행합니다.",
            )
        )
    return actions


def _collect_qwen_runtime(root: Path, qwen_harness: dict[str, Any]) -> dict[str, Any]:
    qwen_init_command = resolve_qwen_init_command()
    project_command = find_project_qwen_command(root)
    project_qwen_runtime = resolve_project_qwen_runtime(root)
    preferred_qwen_runtime = find_latest_qwencode_runtime()
    qwen_runtime = project_qwen_runtime or preferred_qwen_runtime
    runtime_mismatch = bool(
        project_command
        and preferred_qwen_runtime
        and (not project_qwen_runtime or project_qwen_runtime.resolve() != preferred_qwen_runtime.resolve())
    )
    qwen_runtime = preferred_qwen_runtime if runtime_mismatch and preferred_qwen_runtime else (project_qwen_runtime or preferred_qwen_runtime)
    return {
        "harness_status": qwen_harness.get("status"),
        "harness_reason": qwen_harness.get("reason") or qwen_harness.get("error"),
        "qwen_init_command": _command_display(qwen_init_command),
        "qwen_init_available": bool(qwen_init_command),
        "project_command": str(project_command) if project_command else None,
        "project_command_exists": bool(project_command),
        "runtime_dir": str(qwen_runtime) if qwen_runtime else None,
        "runtime_source": "preferred" if runtime_mismatch and preferred_qwen_runtime else ("project" if project_qwen_runtime else ("preferred" if preferred_qwen_runtime else None)),
        "project_runtime_dir": str(project_qwen_runtime) if project_qwen_runtime else None,
        "preferred_runtime_dir": str(preferred_qwen_runtime) if preferred_qwen_runtime else None,
        "runtime_mismatch": runtime_mismatch,
    }


def _find_maven_work_root(root: Path, project_key: str) -> Path | None:
    if project_key == "dcp-services":
        return _find_dcp_services_root(root)
    if (root / "pom.xml").exists():
        return root
    for parent in root.parents:
        if (parent / "pom.xml").exists():
            return parent
    return None


def _find_maven_reactor_pom(root: Path, project_key: str) -> Path | None:
    work_root = _find_maven_work_root(root, project_key)
    if work_root and (work_root / "pom.xml").exists():
        return work_root / "pom.xml"
    return None


def _find_dcp_services_root(root: Path) -> Path | None:
    candidates = [root, *root.parents]
    for candidate in candidates:
        pom = candidate / "pom.xml"
        if pom.exists() and "dcp-core" in _pom_modules(pom):
            return candidate
    return root if (root / "pom.xml").exists() else None


def _find_frontend_package_dir(root: Path, project_key: str) -> Path | None:
    if project_key == "dcp-services" or project_key == "drt-api":
        return None
    if (root / "package.json").exists():
        return root
    if project_key == "drt-front":
        for relative in ["dev", "ui", "public"]:
            if (root / relative / "package.json").exists():
                return root / relative
    if project_key == "drt-cms":
        if root.name.lower() == "backend" and (root / "pom.xml").exists():
            return None
        if (root / "frontend" / "package.json").exists():
            return root / "frontend"
    for candidate in sorted(root.glob("*/package.json")):
        return candidate.parent
    return None


def _collect_dcp_core_status(root: Path, modules: list[str]) -> dict[str, Any]:
    core_module_ok = "dcp-core" in modules and (root / "dcp-core" / "pom.xml").exists()
    missing_refs: list[str] = []
    ref_modules: list[str] = []
    for module in modules:
        if module == "dcp-core":
            continue
        pom = root / module / "pom.xml"
        if not pom.exists():
            missing_refs.append(f"{module}: missing pom")
            continue
        deps = _pom_dependencies(pom)
        if any(dep.get("artifactId") == "dcp-core" for dep in deps):
            ref_modules.append(module)
        else:
            missing_refs.append(module)
    ok = core_module_ok and not missing_refs
    return {
        "ok": ok,
        "core_module_present": core_module_ok,
        "referencing_modules": ref_modules,
        "missing_references": missing_refs,
        "summary": f"dcp-core module={'yes' if core_module_ok else 'no'}, refs={len(ref_modules)}, missing={len(missing_refs)}",
        "detail": (
            "Maven reactor가 dcp-core local module을 포함하고, 각 dcp-* 모듈이 dcp-core artifact를 참조합니다."
            if ok
            else f"dcp-core local reactor 확인 필요: {', '.join(missing_refs[:12])}"
        ),
    }


def _dcp_web_modules(root: Path, modules: list[str]) -> list[str]:
    return [module for module in modules if module != "dcp-core" and (root / module / "webapp").exists()]


def _default_dcp_tomcat_module(root: Path, modules: list[str]) -> str:
    candidates = _dcp_web_modules(root, modules)
    for preferred in ["dcp-gateway", "dcp-insurance"]:
        if preferred in candidates:
            return preferred
    return candidates[0] if candidates else "dcp-gateway"


def _required_java(project_key: str, properties: dict[str, str]) -> str:
    if project_key == "dcp-services":
        return "8"
    if project_key in {"drt-api", "drt-cms"}:
        return properties.get("java.version") or "17"
    return properties.get("java.version") or ""


def _required_node(project_key: str) -> str:
    if project_key == "dcp-front":
        return "10"
    if project_key in {"drt-front", "drt-cms"}:
        return ">=20"
    return ""


def _package_manager(project_key: str, package_dir: Path) -> str:
    if project_key == "dcp-front":
        return "npm"
    if project_key in {"drt-front", "drt-cms"}:
        return "yarn"
    if (package_dir / "yarn.lock").exists():
        return "yarn"
    return "npm"


def _run_version_check(label: str, executable: Path | None, args: list[str], root: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    if executable is None:
        return {
            "name": label,
            "status": "missing",
            "version": None,
            "detail": "PATH에서 실행 파일을 찾지 못했습니다.",
            "command": None,
            "path": None,
            "cwd": str(root),
            "exit_code": None,
        }

    command = _version_command(executable, args)
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            env={**os.environ, **env} if env else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=18,
            check=False,
        )
    except Exception as exc:
        return {
            "name": label,
            "status": "failed",
            "version": None,
            "detail": str(exc),
            "command": _command_display(command),
            "path": str(executable),
            "cwd": str(root),
            "exit_code": None,
        }

    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part and part.strip())
    return {
        "name": label,
        "status": "ok" if completed.returncode == 0 else "failed",
        "version": _first_output_line(output),
        "detail": output[:1200],
        "command": _command_display(command),
        "path": str(executable),
        "cwd": str(root),
        "exit_code": completed.returncode,
        "major": _parse_major_version(output),
    }


def _collect_yarn_runtime_check(frontend: dict[str, Any], executable: Path | None) -> dict[str, Any]:
    cwd = Path(str(frontend.get("cwd") or "."))
    yarn_lock = cwd / "yarn.lock"
    yarnrc = cwd / ".yarnrc"
    offline_mirror = _yarn_offline_mirror(cwd)
    version = _bundled_yarn_version(executable) or _package_manager_yarn_version(frontend) or "Yarn classic offline runner"
    details = [
        "네트워크를 막기 위해 런타임 체크에서는 `yarn --version`을 실행하지 않습니다.",
        f"cwd={cwd}",
        f"yarn.lock={'yes' if yarn_lock.exists() else 'no'}",
        f".yarnrc={'yes' if yarnrc.exists() else 'no'}",
    ]
    if offline_mirror:
        details.append(f"offline mirror={offline_mirror} ({'exists' if offline_mirror.exists() else 'missing'})")
    if executable and _looks_like_corepack_yarn(executable):
        details.append("Corepack yarn shim detected; bundled qwencode should provide runtimes/node/yarn.cmd classic wrapper.")
    if executable is None:
        return {
            "name": "Yarn",
            "status": "missing",
            "version": None,
            "detail": "PATH와 qwencode runtimes/node에서 yarn 실행 파일을 찾지 못했습니다.",
            "command": None,
            "path": None,
            "exit_code": None,
            "cwd": str(cwd),
        }
    return {
        "name": "Yarn",
        "status": "ok",
        "version": version,
        "detail": "\n".join(details),
        "command": "offline metadata check; yarn --version intentionally skipped",
        "path": str(executable),
        "exit_code": 0,
        "major": _parse_major_version(version) or 1,
        "cwd": str(cwd),
        "offline_mirror": str(offline_mirror) if offline_mirror else None,
    }


def _package_manager_yarn_version(frontend: dict[str, Any]) -> str | None:
    package_path = Path(str(frontend.get("package_json") or ""))
    package = _read_package_json(package_path) if package_path.exists() else {}
    manager = package.get("packageManager")
    if isinstance(manager, str) and manager.lower().startswith("yarn@"):
        return manager.split("@", 1)[1]
    return None


def _bundled_yarn_version(executable: Path | None) -> str | None:
    if executable is None:
        return None
    candidates = [
        executable.parent / "node_modules" / "yarn" / "package.json",
        executable.parent.parent / "node_modules" / "yarn" / "package.json",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        package = _read_package_json(candidate)
        version = package.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    return None


def _yarn_offline_mirror(cwd: Path) -> Path | None:
    yarnrc = cwd / ".yarnrc"
    if not yarnrc.exists():
        return None
    try:
        text = yarnrc.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r'^\s*yarn-offline-mirror\s+["\']?([^"\'\r\n]+)', text, flags=re.MULTILINE)
    if not match:
        return None
    return (cwd / match.group(1).strip()).resolve()


def _looks_like_corepack_yarn(executable: Path) -> bool:
    normalized = str(executable).replace("\\", "/").lower()
    return "/corepack/" in normalized or normalized.endswith("/corepack/dist/yarn.js")


def _backend_runtime_env(backend: dict[str, Any]) -> dict[str, str]:
    env: dict[str, str] = {}
    path_entries: list[str] = []
    java_home = str(backend.get("java_home") or "").strip()
    maven_home = str(backend.get("maven_home") or "").strip()
    tomcat_home = str(backend.get("tomcat_home") or "").strip()
    if java_home:
        env["JAVA_HOME"] = java_home
        path_entries.append(str(Path(java_home) / "bin"))
    if maven_home:
        env["MAVEN_HOME"] = maven_home
        path_entries.append(str(Path(maven_home) / "bin"))
    if tomcat_home:
        env["CATALINA_HOME"] = tomcat_home
        env["CATALINA_BASE"] = tomcat_home
        path_entries.append(str(Path(tomcat_home) / "bin"))
    if path_entries:
        env["PATH"] = os.pathsep.join([*path_entries, os.environ.get("PATH", "")])
    return env


def _frontend_runtime_env(frontend: dict[str, Any]) -> dict[str, str]:
    path_entries: list[str] = []
    for key in ["node_executable", "npm_executable", "npx_executable", "yarn_executable"]:
        value = str(frontend.get(key) or "").strip()
        if not value:
            continue
        parent = str(Path(value).parent)
        if parent and parent not in path_entries:
            path_entries.append(parent)
    runtime_dir = str(frontend.get("node_runtime_dir") or "").strip()
    if runtime_dir and runtime_dir not in path_entries:
        path_entries.append(runtime_dir)
    if not path_entries:
        return {}
    return {"PATH": os.pathsep.join([*path_entries, os.environ.get("PATH", "")])}


def _version_check_cwd(executable: Path | None, fallback: Path) -> Path:
    if executable is not None and executable.parent.exists():
        return executable.parent
    return fallback


def _backend_maven_command(backend: dict[str, Any], goal: str) -> str:
    mvn = _quote_command_path(str(backend.get("maven_executable") or "mvn"))
    java_home = str(backend.get("java_home") or "").strip()
    maven_home = str(backend.get("maven_home") or "").strip()
    if os.name == "nt":
        parts: list[str] = []
        path_entries: list[str] = []
        if java_home:
            parts.append(f'set "JAVA_HOME={java_home}"')
            path_entries.append(r"%JAVA_HOME%\bin")
        if maven_home:
            parts.append(f'set "MAVEN_HOME={maven_home}"')
            path_entries.append(r"%MAVEN_HOME%\bin")
        if path_entries:
            parts.append(f'set "PATH={";".join(path_entries)};%PATH%"')
        parts.append(f"{mvn} {goal}")
        return " && ".join(parts)

    env_parts: list[str] = []
    path_entries = []
    if java_home:
        env_parts.append(f"JAVA_HOME={sh_quote(java_home)}")
        path_entries.append(str(Path(java_home) / "bin"))
    if maven_home:
        env_parts.append(f"MAVEN_HOME={sh_quote(maven_home)}")
        path_entries.append(str(Path(maven_home) / "bin"))
    if path_entries:
        env_parts.append(f"PATH={sh_quote(os.pathsep.join(path_entries))}:$PATH")
    env_prefix = " ".join(env_parts)
    command = f"{mvn} {goal}"
    return f"{env_prefix} {command}".strip()


def _dcp_tomcat_deploy_command(backend: dict[str, Any]) -> str:
    module = str(backend.get("tomcat_deploy_module") or "dcp-gateway")
    context = str(backend.get("tomcat_deploy_context") or module)
    java_home = str(backend.get("java_home") or "").strip()
    maven_home = str(backend.get("maven_home") or "").strip()
    tomcat_home = str(backend.get("tomcat_home") or "").strip()
    mvn = _quote_command_path(str(backend.get("maven_executable") or "mvn"))
    catalina = _quote_command_path(str(backend.get("tomcat_executable") or _default_catalina_path(tomcat_home)))
    deploy_path = str(Path(tomcat_home) / "webapps" / context) if tomcat_home else f"webapps/{context}"
    maven_goal = f"{mvn} -pl {module} -am clean install -Ddeploy-phase=local -Ddeploy-path={_quote_command_path(deploy_path)}"
    catalina_goal = f"{catalina} run"

    if os.name == "nt":
        parts: list[str] = []
        path_entries: list[str] = []
        if java_home:
            parts.append(f'set "JAVA_HOME={java_home}"')
            path_entries.append(r"%JAVA_HOME%\bin")
        if maven_home:
            parts.append(f'set "MAVEN_HOME={maven_home}"')
            path_entries.append(r"%MAVEN_HOME%\bin")
        if tomcat_home:
            parts.append(f'set "CATALINA_HOME={tomcat_home}"')
            parts.append(f'set "CATALINA_BASE={tomcat_home}"')
            path_entries.append(r"%CATALINA_HOME%\bin")
        if path_entries:
            parts.append(f'set "PATH={";".join(path_entries)};%PATH%"')
        parts.extend([maven_goal, catalina_goal])
        return " && ".join(parts)

    exports: list[str] = []
    path_entries = []
    if java_home:
        exports.append(f"export JAVA_HOME={sh_quote(java_home)}")
        path_entries.append(str(Path(java_home) / "bin"))
    if maven_home:
        exports.append(f"export MAVEN_HOME={sh_quote(maven_home)}")
        path_entries.append(str(Path(maven_home) / "bin"))
    if tomcat_home:
        exports.append(f"export CATALINA_HOME={sh_quote(tomcat_home)}")
        exports.append(f"export CATALINA_BASE={sh_quote(tomcat_home)}")
        path_entries.append(str(Path(tomcat_home) / "bin"))
    if path_entries:
        exports.append(f"export PATH={sh_quote(os.pathsep.join(path_entries))}:$PATH")
    prefix = "; ".join(exports)
    return f"{prefix}; {maven_goal} && {catalina_goal}" if prefix else f"{maven_goal} && {catalina_goal}"


def _default_catalina_path(tomcat_home: str) -> str:
    if not tomcat_home:
        return "catalina"
    name = "catalina.bat" if os.name == "nt" else "catalina.sh"
    return str(Path(tomcat_home) / "bin" / name)


def _java_requirement(item: dict[str, Any] | None, expected_major: str) -> dict[str, Any]:
    major = item.get("major") if item else None
    ok = str(major) == str(expected_major)
    return {
        "id": "java-version",
        "name": "Java",
        "expected": f"Java {expected_major}",
        "actual": item.get("version") if item else "not found",
        "status": "ok" if ok else "error",
        "detail": "백엔드 Maven 빌드용 JDK 버전입니다.",
    }


def _node_requirement(item: dict[str, Any] | None, expected: str) -> dict[str, Any]:
    major = item.get("major") if item else None
    if expected.startswith(">="):
        ok = isinstance(major, int) and major >= int(expected[2:])
    else:
        ok = str(major) == expected
    return {
        "id": "node-version",
        "name": "Node",
        "expected": f"Node {expected}",
        "actual": item.get("version") if item else "not found",
        "status": "ok" if ok else "error",
        "detail": "프로젝트 dev/build 스크립트용 Node 버전입니다. Playwright는 별도 qwencode Node를 사용합니다.",
    }


def _tool_requirement(item: dict[str, Any] | None, name: str, expected: str) -> dict[str, Any]:
    ok = bool(item and item.get("status") == "ok")
    return {
        "id": f"{name.lower()}-available",
        "name": name,
        "expected": expected,
        "actual": item.get("version") if item else "not found",
        "status": "ok" if ok else "warn",
        "detail": item.get("path") if item else "실행 파일을 찾지 못했습니다.",
    }


def _tomcat_requirement(item: dict[str, Any] | None, backend: dict[str, Any]) -> dict[str, Any]:
    ok = bool(item and item.get("status") == "ok")
    return {
        "id": "tomcat9-runtime",
        "name": "Tomcat 9",
        "expected": "Tomcat 9.0.115 under qwencode runtimes/tomcat9",
        "actual": item.get("version") if item else "not found",
        "status": "ok" if ok else "error",
        "detail": backend.get("tomcat_runtime_dir") or "D:/aiops/qwencode/runtimes/tomcat9",
    }


def _action(action_id: str, label: str, cwd: str, command: str, enabled: bool, detail: str = "") -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "cwd": cwd,
        "command": command,
        "terminal": True,
        "status": "ready" if enabled else "unavailable",
        "detail": detail,
    }


def _open_new_terminal(cwd: Path, command: str, title: str) -> dict[str, Any]:
    if os.name == "nt":
        script_path = _write_windows_runtime_action_script(cwd, command)
        subprocess.Popen(
            ["cmd.exe", "/d", "/s", "/c", "start", title, "cmd.exe", "/d", "/s", "/k", str(script_path)],
            cwd=str(cwd),
        )
        return {"type": "windows-cmd", "title": title, "script": str(script_path)}
    if sys.platform == "darwin":
        script_command = f"cd {sh_quote(str(cwd))} && {command}"
        script = f'tell application "Terminal"\n  do script {json.dumps(script_command)}\n  activate\nend tell'
        subprocess.Popen(["osascript", "-e", script], cwd=str(cwd))
        return {"type": "mac-terminal", "title": title}
    terminal = shutil.which("x-terminal-emulator") or shutil.which("gnome-terminal") or shutil.which("konsole")
    if terminal:
        subprocess.Popen([terminal, "-e", f"sh -lc {sh_quote(f'cd {sh_quote(str(cwd))} && {command}; exec sh')}"], cwd=str(cwd))
        return {"type": "linux-terminal", "title": title}
    raise RuntimeError("새 터미널을 열 수 없습니다. Windows Terminal, macOS Terminal, 또는 x-terminal-emulator가 필요합니다.")


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _playwright_command(cwd: Path, qwen_npx: Path | None, local_playwright: Path | None) -> str | None:
    if local_playwright:
        return f'"{local_playwright}" test'
    if qwen_npx:
        return f'"{qwen_npx}" playwright test'
    return None


def _find_qwen_tool(runtime: Path | None, name: str, folder: str = NODE_RUNTIME, subdir: str | None = None) -> Path | None:
    if runtime is None:
        return None
    suffixes = [".cmd", ".exe", "", ".bat", ".sh"] if os.name == "nt" else ["", ".sh", ".cmd", ".exe", ".bat"]
    base = _runtime_dir(runtime, folder)
    if subdir:
        base = base / subdir
    for search_base in _runtime_tool_search_bases(base, folder, subdir):
        for suffix in suffixes:
            candidate = search_base / f"{name}{suffix}"
            if _is_runnable_candidate(candidate):
                return candidate
    if folder == NODE_RUNTIME and subdir is None and name in {"yarn", "yarnpkg", "corepack"}:
        for shim_base in [base / "node_modules" / "corepack" / "shims", base / "node_modules" / "corepack" / "shims" / "nodewin"]:
            for suffix in suffixes:
                candidate = shim_base / f"{name}{suffix}"
                if _is_runnable_candidate(candidate):
                    return candidate
    return None


def _runtime_tool_search_bases(base: Path, folder: str, subdir: str | None) -> list[Path]:
    bases = [base]
    if folder != NODE10_RUNTIME or subdir is not None or not base.exists():
        return bases
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.lower() in {"node_modules", "npm-cache"}:
            continue
        bases.append(child)
        bin_dir = child / "bin"
        if bin_dir.is_dir():
            bases.append(bin_dir)
    return bases


def _runtime_dir(runtime: Path | None, folder: str) -> Path:
    if runtime is None:
        return Path(QWEN_RUNTIMES_DIR) / folder
    return runtime / QWEN_RUNTIMES_DIR / folder


def _runtime_relative(folder: str) -> str:
    return f"{QWEN_RUNTIMES_DIR}/{folder}"


def _path_from_optional(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.exists() else None


def _is_runnable_candidate(path: Path) -> bool:
    if not path.exists() or path.is_dir():
        return False
    if os.name == "nt":
        return True
    return os.access(path, os.X_OK)


def _frontend_package_command(frontend: dict[str, Any], package_manager: str) -> str:
    if package_manager == "npm":
        npm = str(frontend.get("managed_npm_executable") or "").strip()
        return _quote_command_path(npm) if npm else "npm"
    if package_manager == "yarn":
        yarn = str(frontend.get("managed_yarn_executable") or "").strip()
        return _quote_command_path(yarn) if yarn else "yarn"
    return package_manager


def _frontend_dev_script(project_key: str, scripts: dict[str, Any]) -> str | None:
    if project_key == "drt-front" and "start" in scripts:
        return "start"
    return _first_existing_script(scripts, ["serve:local", "serve", "dev", "start"])


def _frontend_script_command(package_command: str, package_manager: str, script: str) -> str:
    if package_manager == "yarn" and script == "start":
        return f"{package_command} start"
    return f"{package_command} run {script}"


def _write_windows_runtime_action_script(cwd: Path, command: str) -> Path:
    action_dir = Path(__file__).resolve().parents[2] / "data" / "runtime-actions"
    action_dir.mkdir(parents=True, exist_ok=True)
    script_path = action_dir / f"kiwi-runtime-action-{uuid.uuid4().hex}.cmd"
    script_path.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                f'cd /d "{cwd}"',
                command,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def _quote_command_path(value: str) -> str:
    if not value:
        return value
    if re.search(r"[\s()&^%$!`'\";]", value):
        return f'"{value}"'
    return value


def _which_runtime_executable(name: str, variants: list[str]) -> Path | None:
    for candidate in [name, *variants]:
        resolved = shutil.which(candidate)
        if resolved:
            return Path(resolved)
    return None


def _version_command(executable: Path, args: list[str]) -> list[str]:
    if os.name == "nt" and executable.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", str(executable), *args]
    return [str(executable), *args]


def _item_ok(items: list[dict[str, Any]], name: str) -> bool:
    return any(item.get("name") == name and item.get("status") == "ok" for item in items)


def _find_item(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("name") == name), None)


def _java_matches(item: dict[str, Any] | None, expected: str) -> bool:
    if not expected:
        return bool(item and item.get("status") == "ok")
    return bool(item and str(item.get("major")) == expected)


def _node_matches(item: dict[str, Any] | None, expected: str) -> bool:
    if not item or item.get("status") != "ok":
        return False
    major = item.get("major")
    if expected.startswith(">="):
        return isinstance(major, int) and major >= int(expected[2:])
    if expected:
        return str(major) == expected
    return True


def _first_existing_script(scripts: dict[str, Any], names: list[str]) -> str | None:
    for name in names:
        if name in scripts:
            return name
    return None


def _first_output_line(output: str) -> str | None:
    for line in output.splitlines():
        text = line.strip()
        if text:
            return text[:240]
    return None


def _parse_major_version(output: str) -> int | None:
    match = re.search(r'version "?(\d+)(?:\.(\d+))?', output, re.IGNORECASE) or re.search(r"\bv?(\d+)\.(\d+)", output)
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    if major == 1 and minor:
        return minor
    return major


def _command_display(command: list[str] | None) -> str | None:
    if not command:
        return None
    return " ".join(str(part) for part in command)


def _read_package_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _dependency_version(package: dict[str, Any], name: str) -> str | None:
    for section in ["dependencies", "devDependencies"]:
        deps = package.get(section)
        if isinstance(deps, dict) and name in deps:
            return str(deps[name])
    return None


def _local_bin(cwd: Path, name: str) -> Path | None:
    for candidate in [cwd / "node_modules" / ".bin" / name, cwd / "node_modules" / ".bin" / f"{name}.cmd"]:
        if candidate.exists():
            return candidate
    return None


def _has_java_main(root: Path) -> bool:
    for path in list(root.glob("src/main/java/**/*.java"))[:2000]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "@SpringBootApplication" in text and "public static void main" in text:
            return True
    return False


def _has_text(path: Path, needle: str) -> bool:
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _pom_tree(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None


def _pom_text(path: Path, tag: str) -> str | None:
    root = _pom_tree(path)
    if root is None:
        return None
    value = root.findtext(f"m:{tag}", namespaces=POM_NS) or root.findtext(f"m:parent/m:{tag}", namespaces=POM_NS)
    return value.strip() if value else None


def _pom_packaging(path: Path) -> str | None:
    root = _pom_tree(path)
    if root is None:
        return None
    return (root.findtext("m:packaging", namespaces=POM_NS) or "jar").strip()


def _pom_modules(path: Path) -> list[str]:
    root = _pom_tree(path)
    if root is None:
        return []
    modules = [node.text.strip() for node in root.findall("m:modules/m:module", POM_NS) if node.text and node.text.strip()]
    for profile in root.findall("m:profiles/m:profile", POM_NS):
        for node in profile.findall("m:modules/m:module", POM_NS):
            if node.text and node.text.strip() and node.text.strip() not in modules:
                modules.append(node.text.strip())
    return modules


def _pom_properties(path: Path) -> dict[str, str]:
    root = _pom_tree(path)
    if root is None:
        return {}
    props = root.find("m:properties", POM_NS)
    if props is None:
        return {}
    result: dict[str, str] = {}
    for child in list(props):
        tag = child.tag.rsplit("}", 1)[-1]
        if child.text and child.text.strip():
            result[tag] = child.text.strip()
    return result


def _pom_dependencies(path: Path) -> list[dict[str, str]]:
    root = _pom_tree(path)
    if root is None:
        return []
    deps: list[dict[str, str]] = []
    for dep in root.findall(".//m:dependency", POM_NS):
        deps.append(
            {
                "groupId": (dep.findtext("m:groupId", namespaces=POM_NS) or "").strip(),
                "artifactId": (dep.findtext("m:artifactId", namespaces=POM_NS) or "").strip(),
                "version": (dep.findtext("m:version", namespaces=POM_NS) or "").strip(),
            }
        )
    return deps


def _guess_project_key(root: Path) -> str:
    name = root.name.lower()
    if "dcp-front" in name:
        return "dcp-front"
    if "dcp-services" in name:
        return "dcp-services"
    if "drt-front" in name:
        return "drt-front"
    if "drt-api" in name:
        return "drt-api"
    if "drt-cms" in name:
        return "drt-cms"
    return "generic"
