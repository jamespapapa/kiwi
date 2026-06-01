from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
BUILD = ROOT / "build"
OUT_DIR = BUILD / "offline"
BUNDLE_NAME = "kiwi-offline-win11-py313"
BUNDLE_ROOT = OUT_DIR / BUNDLE_NAME
ORCHESTRATOR_API_BASE_URL = "https://api.t.drt.samsunglife.kr/llmproxy/v1"
CODER_API_BASE_URL = "https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1"
ORCHESTRATOR_MODEL = "Qwen3.5-397B"
CODER_MODEL = "qwen3-coder-next"
QWEN35_MAX_TOKENS = "16384"
CODER_MAX_TOKENS = "16384"
MODEL_CONTEXT_WINDOW = "262144"
NODE_MAX_OLD_SPACE_MB = "8192"
PYWINPTY_REQUIREMENT = "pywinpty>=3.0.3"


SOURCE_INCLUDE = [
    ".env.example",
    ".gitignore",
    "KIWI.md",
    "README.md",
    "app",
    "backend",
    "docs",
    "fonts",
    "next-env.d.ts",
    "next.config.ts",
    "package-lock.json",
    "package.json",
    "public",
    "scripts",
    "tsconfig.json",
]

SOURCE_EXCLUDE_DIRS = {
    ".git",
    ".next",
    ".venv",
    "build",
    "data",
    "node_modules",
    "__pycache__",
}


def main() -> int:
    runtime = find_latest_qwen_runtime()
    if runtime is None:
        print("ERROR: ../deliverables 아래에서 qwen-code-offline-* 런타임을 찾지 못했습니다.", file=sys.stderr)
        return 1

    print(f"Using Qwen runtime: {runtime}")
    reset_dir(BUNDLE_ROOT)
    copy_source(BUNDLE_ROOT)
    copy_qwen_runtime(runtime, BUNDLE_ROOT / "vendor" / "qwen-runtime")
    download_python_wheels(BUNDLE_ROOT / "vendor" / "python-wheelhouse")
    populate_npm_cache(BUNDLE_ROOT / "vendor" / "npm-cache")
    write_bundle_scripts(BUNDLE_ROOT)
    write_manifest(BUNDLE_ROOT, runtime)

    zip_path = OUT_DIR / f"{BUNDLE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    zip_dir(BUNDLE_ROOT, zip_path)
    sha_path = zip_path.with_suffix(".zip.sha256")
    digest = sha256_file(zip_path)
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    print(f"Wrote {zip_path}")
    print(f"Wrote {sha_path}")
    return 0


def find_latest_qwen_runtime() -> Path | None:
    explicit_runtime = os.getenv("KIWI_QWEN_RUNTIME_SOURCE", "").strip()
    if explicit_runtime:
        candidate = Path(explicit_runtime).expanduser().resolve()
        if is_qwen_runtime(candidate):
            return candidate
        print(f"ERROR: KIWI_QWEN_RUNTIME_SOURCE is not a Qwen runtime: {candidate}", file=sys.stderr)
        return None

    deliverables = PARENT / "deliverables"
    candidates = [path for path in deliverables.glob("qwen-code-offline-*") if is_qwen_runtime(path)]
    if not candidates:
        return None
    return sorted(candidates, key=runtime_sort_key, reverse=True)[0].resolve()


def is_qwen_runtime(path: Path) -> bool:
    return path.is_dir() and (path / "run-qwen.cmd").exists() and (path / "app" / "cli.js").exists()


def runtime_sort_key(path: Path) -> tuple[int, tuple[int, ...], float, str]:
    name = path.name.lower()
    version_match = re.search(r"(\d+(?:\.\d+)+)", name)
    version = tuple(int(part) for part in version_match.group(1).split(".")) if version_match else (0,)
    win11_score = 1 if "win11" in name else 0
    return (win11_score, version, path.stat().st_mtime, name)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_source(target_root: Path) -> None:
    for item in SOURCE_INCLUDE:
        src = ROOT / item
        dst = target_root / item
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst, ignore=ignore_source)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def ignore_source(_dir: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in SOURCE_EXCLUDE_DIRS or name.endswith(".pyc") or name == "tsconfig.tsbuildinfo":
            ignored.add(name)
    return ignored


def copy_qwen_runtime(src: Path, dst: Path) -> None:
    print("Copying Qwen runtime...")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("portable-runtime", "*.log"))
    write_qwen_runtime_config(dst)
    patch_qwen_runtime_policy(dst)


def write_qwen_runtime_config(runtime_root: Path) -> None:
    env_cmd = f"""
@echo off

rem KIWI fixed Samsung Life routing.
set "QWEN35_API_KEY=sk-local-qwen35"
set "QWEN35_BASE_URL={ORCHESTRATOR_API_BASE_URL}"
set "QWEN35_MODEL={ORCHESTRATOR_MODEL}"

set "CODER_API_KEY=sk-local-coder"
set "CODER_BASE_URL={CODER_API_BASE_URL}"
set "CODER_MODEL={CODER_MODEL}"

set "NODE_TLS_REJECT_UNAUTHORIZED=0"
set "NODE_OPTIONS=--max-old-space-size={NODE_MAX_OLD_SPACE_MB} %NODE_OPTIONS%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "LC_ALL=C.UTF-8"
set "LANG=C.UTF-8"
set "QWEN35_TEMPERATURE=0.2"
set "CODER_TEMPERATURE=0"
set "QWEN35_MAX_TOKENS={QWEN35_MAX_TOKENS}"
set "CODER_MAX_TOKENS={CODER_MAX_TOKENS}"
set "QWEN35_CONTEXT_WINDOW={MODEL_CONTEXT_WINDOW}"
set "CODER_CONTEXT_WINDOW={MODEL_CONTEXT_WINDOW}"
set "QWEN35_EXTRA_BODY_JSON="
set "CODER_EXTRA_BODY_JSON="
set "QWEN_TEAM_LOG=1"
set "QWEN_ULTRAWORK_AGENT_VISIBILITY=0"
set "KIWI_KK_DOCS_MCP_ENABLED=1"
set "KIWI_KK_DOCS_MCP_URL=http://100.254.193.25:3007/mcp"
set "KIWI_KK_CODE_ANALYSIS_MCP_ENABLED=0"
set "KIWI_KK_CODE_ANALYSIS_MCP_URL="
set "KIWI_KK_MCP_TOKEN="
""".strip() + "\n"
    for relative in [
        Path("config") / "env.cmd",
        Path("config") / "env.cmd.example",
        Path("templates") / "project" / ".qwen" / "env.cmd",
    ]:
        path = runtime_root / relative
        if path.exists():
            write_crlf(path, env_cmd)


def patch_qwen_runtime_policy(runtime_root: Path) -> None:
    cli_path = runtime_root / "app" / "cli.js"
    if cli_path.exists():
        cli = cli_path.read_text(encoding="utf-8", errors="replace")
        cli_changed = False
        if "agent_type: typeof subagentNameContext" not in cli:
            cli = cli.replace(
                """          tool_input: toolInput,
          tool_use_id: toolUseId
        },""",
                """          tool_input: toolInput,
          tool_use_id: toolUseId,
          agent_type: typeof subagentNameContext !== "undefined" && subagentNameContext?.getStore ? subagentNameContext.getStore() : void 0
        },""",
                1,
            )
            cli = cli.replace(
                "async firePreToolUseEvent(toolName, toolInput, toolUseId, permissionMode, signal) {",
                "async firePreToolUseEvent(toolName, toolInput, toolUseId, permissionMode, agentType, signal) {",
                2,
            )
            cli = cli.replace(
                """          tool_input: toolInput,
          tool_use_id: toolUseId
        };""",
                """          tool_input: toolInput,
          tool_use_id: toolUseId,
          agent_type: agentType
        };""",
                1,
            )
            cli = cli.replace(
                """          toolUseId,
          permissionMode,
          signal
        );""",
                """          toolUseId,
          permissionMode,
          agentType,
          signal
        );""",
                1,
            )
            cli = cli.replace(
                """                      input["tool_use_id"] || "",
                      input["permission_mode"] ?? "default" /* Default */,
                      signal
                    );""",
                """                      input["tool_use_id"] || "",
                      input["permission_mode"] ?? "default" /* Default */,
                      input["agent_type"] || "",
                      signal
                    );""",
                1,
            )
            cli_changed = True
        old_visibility_default = """      try {
        const runtimeDir = process.env.QWEN_RUNTIME_DIR || path23.join(process.env.QWEN_BUNDLE_ROOT || process.cwd(), "portable-runtime");
        const state = JSON.parse(fs31.readFileSync(path23.join(runtimeDir, "ultrawork-state.json"), "utf8"));
        const sessionId = this.config.getSessionId?.();
        const cwd = this.config.getWorkingDir?.();
        return Boolean(
          sessionId && state.sessions?.[`session:${sessionId}`]?.active || cwd && state.sessions?.[`cwd:${cwd}`]?.active || state.sessions?.fallback?.active
        );
      } catch {
        return false;
      }"""
        if old_visibility_default in cli:
            cli = cli.replace(old_visibility_default, "      return false;", 1)
            cli_changed = True
        if "skipLoopDetection: settings.model?.skipLoopDetection ?? false" in cli:
            cli = cli.replace(
                "skipLoopDetection: settings.model?.skipLoopDetection ?? false",
                "skipLoopDetection: settings.model?.skipLoopDetection ?? true",
                1,
            )
            cli_changed = True
        if "buildSubagentContextOverride(runtimeContext, config2)" not in cli:
            cli = cli.replace(
                "          const subagentContext = await this.buildSubagentContextOverride(runtimeContext);",
                "          const subagentContext = await this.buildSubagentContextOverride(runtimeContext, config2);",
                1,
            )
            cli = cli.replace(
                """      async buildSubagentContextOverride(runtimeContext) {
        const subagentContext = Object.create(runtimeContext);
        if (!hasRebuiltToolRegistry(runtimeContext)) {""",
                """      async buildSubagentContextOverride(runtimeContext, config2) {
        const subagentContext = Object.create(runtimeContext);
        const subagentName = String(config2?.name || "").trim().toLowerCase();
        if (["planner-35", "architect-35", "reviewer-35", "debugger-35", "tester-35", "explorer-next"].includes(subagentName)) {
          subagentContext.fileReadCacheDisabled = true;
        }
        if (!hasRebuiltToolRegistry(runtimeContext)) {""",
                1,
            )
            cli_changed = True
        if cli_changed:
            cli_path.write_text(cli, encoding="utf-8")

    policy_path = runtime_root / "scripts" / "orchestration-policy.js"
    if not policy_path.exists():
        return
    policy = policy_path.read_text(encoding="utf-8", errors="replace")
    policy = normalize_runtime_agent_names(policy)
    policy = policy.replace("tester-next", "tester-35")
    policy_path.write_text(policy, encoding="utf-8")

    config_path = runtime_root / "scripts" / "write-runtime-config.js"
    if config_path.exists():
        config = config_path.read_text(encoding="utf-8", errors="replace")
        config = normalize_runtime_agent_names(config)
        if 'fs.rmSync(path.join(qwenHome, "extensions", "ultrawork", "agents")' not in config:
            config = config.replace(
                '  removeFileIfExists(path.join(qwenHome, "QWEN.md"));\n',
                '  removeFileIfExists(path.join(qwenHome, "QWEN.md"));\n'
                '  fs.rmSync(path.join(qwenHome, "extensions", "ultrawork", "agents"), { recursive: true, force: true });\n',
                1,
            )
        old_description = (
            "keeps Kiwi orchestration-only, enforces "
            + "Qwen3.5 "
            + "consultation before "
            + "code-changing work, and blocks mutation by read-only agents."
        )
        config = config.replace(
            old_description,
            "keeps Kiwi orchestration-only and blocks mutation by read-only agents.",
        )
        config = config.replace(
            'name: "Qwen3-Coder-Next Coder / Tester / Explorer"',
            'name: "Qwen3-Coder-Next Explorer"',
        )
        config = config.replace(
            'writeText(path.join(extensionDir, "agents", "coder-35.md"), agent(\n    coderModel,',
            'writeText(path.join(extensionDir, "agents", "coder-35.md"), agent(\n    qwen35Model,',
        )
        config = config.replace(
            'writeText(path.join(extensionDir, "agents", "tester-35.md"), agent(\n    coderModel,',
            'writeText(path.join(extensionDir, "agents", "tester-35.md"), agent(\n    qwen35Model,',
        )
        config = config.replace(
            'writeText(path.join(extensionDir, "agents", "explorer-next.md"), agent(\n    qwen35Model,',
            'writeText(path.join(extensionDir, "agents", "explorer-next.md"), agent(\n    coderModel,',
        )
        config = config.replace(
            "^(agent|task|AskUserQuestion|ask_user_question|TodoWrite|todo_write|edit|write_file|save_memory|run_shell_command)$",
            "^(agent|Agent|task|Task|AskUserQuestion|ask_user_question|TodoWrite|todo_write|Edit|edit|Replace|replace|ApplyPatch|apply_patch|Write|write|WriteFile|write_file|SaveMemory|save_memory|Shell|run_shell_command)$",
        )
        if "skipLoopDetection: false" in config:
            config = config.replace("skipLoopDetection: false", "skipLoopDetection: true")
        elif "skipLoopDetection: true" not in config:
            config = config.replace(
                """    model: {
      name: qwen35Model
    },""",
                """    model: {
      name: qwen35Model,
      skipLoopDetection: true
    },""",
                1,
            )
        config_path.write_text(config, encoding="utf-8")

    team_log_path = runtime_root / "scripts" / "team-log-lib.js"
    if team_log_path.exists():
        team_log = team_log_path.read_text(encoding="utf-8", errors="replace")
        team_log = normalize_runtime_agent_names(team_log)
        team_log_path.write_text(team_log, encoding="utf-8")

    for relative in [Path("README.md")]:
        doc_path = runtime_root / relative
        if doc_path.exists():
            doc = doc_path.read_text(encoding="utf-8", errors="replace")
            doc = normalize_runtime_agent_names(doc).replace("tester-next", "tester-35")
            doc_path.write_text(doc, encoding="utf-8")


def normalize_runtime_agent_names(text: str) -> str:
    text = re.sub(r"(?<!qwen3-)coder-next", "coder-35", text)
    return re.sub(r"(?<!Qwen3-)Coder-Next", "Coder-35", text)


def download_python_wheels(dest: Path) -> None:
    print("Downloading Windows Python 3.13 wheelhouse...")
    reset_dir(dest)
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "-r",
            str(ROOT / "backend" / "requirements.txt"),
            "--dest",
            str(dest),
            "--only-binary=:all:",
            "--platform",
            "win_amd64",
            "--python-version",
            "3.13",
            "--implementation",
            "cp",
            "--abi",
            "cp313",
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            PYWINPTY_REQUIREMENT,
            "--dest",
            str(dest),
            "--only-binary=:all:",
            "--platform",
            "win_amd64",
            "--python-version",
            "3.13",
            "--implementation",
            "cp",
            "--abi",
            "cp313",
        ]
    )


def populate_npm_cache(dest: Path) -> None:
    print("Populating npm offline cache...")
    reset_dir(dest)
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    urls = []
    for package in lock.get("packages", {}).values():
        resolved = package.get("resolved") if isinstance(package, dict) else None
        if isinstance(resolved, str) and resolved.startswith("http"):
            urls.append(resolved)
    for url in sorted(set(urls)):
        run(["npm", "cache", "add", url, "--cache", str(dest)])


def write_bundle_scripts(target_root: Path) -> None:
    (target_root / "bin").mkdir(parents=True, exist_ok=True)
    write_crlf(
        target_root / "bin" / "qwencode.cmd",
        r"""
@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
call "%ROOT%\vendor\qwen-runtime\run-qwen.cmd" %*
exit /b %ERRORLEVEL%
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "install-offline.cmd",
        r"""
@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PATH=%ROOT%\vendor\qwen-runtime\node;%PATH%"
set "PYTHON_CMD=python"

py -3.13 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3.13"

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.13.x is required. Install Python 3.13.5 and make it available as python or py -3.13.
  exit /b 1
)

%PYTHON_CMD% --version
if not exist "%ROOT%\.venv" (
  %PYTHON_CMD% -m venv "%ROOT%\.venv"
)

"%ROOT%\.venv\Scripts\python.exe" -m pip install --no-index --find-links "%ROOT%\vendor\python-wheelhouse" -r "%ROOT%\backend\requirements.txt"
if errorlevel 1 exit /b %ERRORLEVEL%

"%ROOT%\.venv\Scripts\python.exe" -m pip install --no-index --find-links "%ROOT%\vendor\python-wheelhouse" pywinpty
if errorlevel 1 exit /b %ERRORLEVEL%

"%ROOT%\vendor\qwen-runtime\node\npm.cmd" ci --offline --cache "%ROOT%\vendor\npm-cache"
if errorlevel 1 exit /b %ERRORLEVEL%

"%ROOT%\vendor\qwen-runtime\node\npm.cmd" run build
if errorlevel 1 exit /b %ERRORLEVEL%

echo.
echo KIWI offline install complete.
echo Run start-kiwi.cmd.
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "start-kiwi.cmd",
        r"""
@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PATH=%ROOT%\bin;%ROOT%\vendor\qwen-runtime\node;%PATH%"
if "%KIWI_QWENCODE_RUNTIME_DIR%"=="" (
  if exist "D:\aiops\qwencode\run-qwen.cmd" (
    set "KIWI_QWENCODE_RUNTIME_DIR=D:\aiops\qwencode"
  )
)
set "NEXT_PUBLIC_KIWI_API_URL=http://localhost:8787"

if not exist "%ROOT%\.venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run install-offline.cmd first.
  exit /b 1
)

start "KIWI Backend" cmd /k "%ROOT%\run-backend.cmd"
start "KIWI Web" cmd /k "%ROOT%\run-web.cmd"
echo KIWI backend: http://localhost:8787
echo KIWI web:     http://localhost:3000
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "run-backend.cmd",
        r"""
@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PATH=%ROOT%\bin;%ROOT%\vendor\qwen-runtime\node;%PATH%"
if "%KIWI_QWENCODE_RUNTIME_DIR%"=="" (
  if exist "D:\aiops\qwencode\run-qwen.cmd" (
    set "KIWI_QWENCODE_RUNTIME_DIR=D:\aiops\qwencode"
  )
)
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir "%ROOT%\backend" --host 127.0.0.1 --port 8787
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "run-web.cmd",
        r"""
@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PATH=%ROOT%\vendor\qwen-runtime\node;%PATH%"
set "NEXT_PUBLIC_KIWI_API_URL=http://localhost:8787"
cd /d "%ROOT%"

if not exist "%ROOT%\node_modules\next" (
  echo [ERROR] node_modules not found. Run install-offline.cmd first.
  exit /b 1
)

if not exist "%ROOT%\.next\BUILD_ID" (
  echo [INFO] Next production build not found. Building with offline npm cache...
  "%ROOT%\vendor\qwen-runtime\node\npm.cmd" run build
  if errorlevel 1 exit /b %ERRORLEVEL%
)

"%ROOT%\vendor\qwen-runtime\node\npm.cmd" run start
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "verify-offline.cmd",
        r"""
@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PATH=%ROOT%\bin;%ROOT%\vendor\qwen-runtime\node;%PATH%"
if "%KIWI_QWENCODE_RUNTIME_DIR%"=="" (
  if exist "D:\aiops\qwencode\run-qwen.cmd" (
    set "KIWI_QWENCODE_RUNTIME_DIR=D:\aiops\qwencode"
  )
)

"%ROOT%\.venv\Scripts\python.exe" -c "from app.main import app; from app.qwencode_runtime import find_latest_qwencode_runtime; print(app.title); print(find_latest_qwencode_runtime())"
if errorlevel 1 exit /b %ERRORLEVEL%

"%ROOT%\vendor\qwen-runtime\node\npm.cmd" run typecheck
if errorlevel 1 exit /b %ERRORLEVEL%

echo Offline verification passed.
""".strip()
        + "\n",
    )
    write_crlf(
        target_root / "OFFLINE_INSTALL.md",
        rf"""
# KIWI Offline Install

## 포함물

- `vendor/python-wheelhouse`: Windows x64, Python 3.13(cp313)용 Python wheels
- `vendor/npm-cache`: `package-lock.json` 기반 npm 오프라인 캐시
- `vendor/qwen-runtime`: `D:\aiops\qwencode`가 없을 때 사용하는 fallback Qwen Code 오프라인 런타임
- `bin/qwencode.cmd`: fallback runtime의 `vendor/qwen-runtime/run-qwen.cmd` 래퍼

## 설치

1. Windows 11에 Python 3.13.5를 설치하고 `python`이 PATH에서 실행되게 한다.
2. 압축을 푼 폴더에서 실행한다.

```cmd
install-offline.cmd
```

## 실행

```cmd
start-kiwi.cmd
```

- Web: `http://localhost:3000`
- Backend: `http://localhost:8787`
- `.next` production build가 없으면 `run-web.cmd`가 시작 전에 오프라인 캐시로 `npm run build`를 한 번 수행한다.

## 설정

OpenAI-compatible API Base, API Key, 모델명은 삼성생명 폐쇄망 기준으로 고정되어 있다.

Windows에서 `D:\aiops\qwencode\run-qwen.cmd`가 있으면 KIWI는 이 기존 runtime을 우선 사용한다.
해당 경로가 없을 때만 번들 내부 `vendor/qwen-runtime`을 fallback으로 사용한다.

프로젝트 초기화는 현재 우선 runtime의 `qwen-init.cmd <project-path>`로 프로젝트 루트에 `qwen.cmd`를 만든다.
Ultrawork Console은 프로젝트 루트의 `qwen.cmd`를 실행하며, `qwen.cmd`가 없거나 다른 runtime을 가리키면 콘솔 시작을 중단한다.
runtime mismatch가 보이면 프로젝트 초기화를 다시 실행해 `qwen.cmd`를 현재 우선 runtime 기준으로 재생성한다.

- Orchestrator: `{ORCHESTRATOR_API_BASE_URL}`, `{ORCHESTRATOR_MODEL}`
- Explorer-next: `{CODER_API_BASE_URL}`, `{CODER_MODEL}`
- Context window: `{MODEL_CONTEXT_WINDOW}`
- Output max tokens: Qwen3.5 `{QWEN35_MAX_TOKENS}`, Explorer `{CODER_MAX_TOKENS}`
- Terminal agent visibility: `QWEN_ULTRAWORK_AGENT_VISIBILITY=0`
""".strip()
        + "\n",
    )


def write_manifest(target_root: Path, runtime: Path) -> None:
    manifest = {
        "name": BUNDLE_NAME,
        "python": "3.13.x win_amd64 cp313",
        "qwenRuntime": runtime.name,
        "qwenRuntimeSource": str(runtime),
        "orchestratorApiBaseUrl": ORCHESTRATOR_API_BASE_URL,
        "orchestratorModel": ORCHESTRATOR_MODEL,
        "coderApiBaseUrl": CODER_API_BASE_URL,
        "coderModel": CODER_MODEL,
        "modelContextWindow": int(MODEL_CONTEXT_WINDOW),
        "qwen35MaxTokens": int(QWEN35_MAX_TOKENS),
        "coderMaxTokens": int(CODER_MAX_TOKENS),
        "nodeMaxOldSpaceMb": int(NODE_MAX_OLD_SPACE_MB),
        "qwenUltraworkAgentVisibility": False,
        "pythonRuntimeWheels": ["backend/requirements.txt", PYWINPTY_REQUIREMENT],
    }
    (target_root / "bundle-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def zip_dir(src: Path, zip_path: Path) -> None:
    print("Creating zip...")
    with ZipFile(zip_path, "w", ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src.parent))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_crlf(path: Path, content: str) -> None:
    path.write_text(content.replace("\n", "\r\n"), encoding="utf-8")


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    raise SystemExit(main())
