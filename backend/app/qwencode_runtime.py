from __future__ import annotations

import os
import json
import re
import shutil
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[2]
AGENT_PROMPTS_DIR = APP_ROOT / "docs" / "ultrawork-agents"
FAST_SYSTEM_PROMPTS_DIR = APP_ROOT / "docs" / "fast-system-prompts"
SUPERPOWERS_SKILLS_DIR = APP_ROOT / "docs" / "superpowers-skills"
SUPERPOWERS_POLICY_SOURCE = APP_ROOT / "docs" / "superpowers-runtime-policy.md"
RUNTIME_POLICY_SOURCE = APP_ROOT / "docs" / "ultrawork-runtime-policy.md"
POLICY_BLOCK_START = "<!-- KIWI:ULTRAWORK_POLICY:START -->"
POLICY_BLOCK_END = "<!-- KIWI:ULTRAWORK_POLICY:END -->"


def resolve_qwencode_command(configured_command: str, project_root: str | Path | None = None) -> list[str]:
    command = configured_command.strip()
    if command and command.lower() not in {"auto", "qwencode"}:
        return _command_to_exec(command)

    project_command = find_project_qwen_command(project_root)
    if project_command:
        return _command_to_exec(str(project_command))

    runtime = find_latest_qwencode_runtime()
    if runtime:
        return _command_to_exec(str(runtime / "run-qwen.cmd"))

    return ["qwencode"]


def resolve_project_qwen_command(project_root: str | Path | None) -> list[str] | None:
    project_command = find_project_qwen_command(project_root)
    if not project_command:
        return None
    return _command_to_exec(str(project_command))


def resolve_project_qwen_runtime(project_root: str | Path | None) -> Path | None:
    project_command = find_project_qwen_command(project_root)
    if not project_command:
        return None

    return _runtime_from_project_command(project_command)


def resolve_qwen_init_command() -> list[str] | None:
    runtime = find_latest_qwencode_runtime()
    if not runtime:
        return None
    qwen_init = runtime / "qwen-init.cmd"
    if not qwen_init.exists():
        return None
    return _command_to_exec(str(qwen_init))


def find_project_qwen_command(project_root: str | Path | None) -> Path | None:
    if project_root is None:
        return None
    root = Path(project_root)
    for name in ["qwen.cmd", "qwencode.cmd"]:
        candidate = root / name
        if candidate.exists():
            return candidate.resolve()
    return None


def find_latest_qwencode_runtime() -> Path | None:
    candidates: list[Path] = []

    if os.name == "nt":
        default_qwencode_runtime = Path(r"D:\aiops\qwencode")
        if _is_qwen_runtime(default_qwencode_runtime):
            ensure_qwencode_runtime_policy(default_qwencode_runtime)
            return default_qwencode_runtime.resolve()

    env_runtime = os.getenv("KIWI_QWENCODE_RUNTIME_DIR", "").strip()
    if env_runtime and _is_qwen_runtime(Path(env_runtime)):
        runtime = Path(env_runtime)
        ensure_qwencode_runtime_policy(runtime)
        return runtime.resolve()

    vendor_runtime = APP_ROOT / "vendor" / "qwen-runtime"
    if _is_qwen_runtime(vendor_runtime):
        ensure_qwencode_runtime_policy(vendor_runtime)
        return vendor_runtime.resolve()

    search_roots = [
        APP_ROOT / "vendor",
        APP_ROOT.parent / "deliverables",
        APP_ROOT.parent.parent / "deliverables",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        if _is_qwen_runtime(root):
            candidates.append(root)
        candidates.extend(path for path in root.glob("qwen-code-offline-*") if path.is_dir())

    valid = []
    for path in candidates:
        if _is_qwen_runtime(path):
            ensure_qwencode_runtime_policy(path)
            valid.append(path.resolve())
    if not valid:
        return None
    return sorted(valid, key=_runtime_sort_key, reverse=True)[0]


def _runtime_from_project_command(project_command: Path) -> Path | None:
    try:
        text = project_command.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    matches = re.findall(r'"([^"]*run-qwen\.cmd)"|(?:call\s+)([^\s"]*run-qwen\.cmd)', text, flags=re.IGNORECASE)
    for quoted, bare in matches:
        command = (quoted or bare).strip()
        if not command:
            continue
        command = os.path.expandvars(command)
        path = Path(command)
        if not path.is_absolute():
            path = project_command.parent / path
        runtime = path.parent
        if _is_qwen_runtime(runtime):
            return runtime.resolve()
    return None


def _is_qwen_runtime(path: Path) -> bool:
    return (path / "run-qwen.cmd").exists() and (path / "app" / "cli.js").exists()


def ensure_qwencode_runtime_policy(path: Path) -> None:
    """Patch the selected Qwen runtime in place so aiops/qwencode remains source of truth."""
    _normalize_qwencode_runtime_layout(path)
    _patch_qwen_runtime_launchers(path)
    _patch_qwen_init_script(path)
    _patch_runtime_text_file(
        path / "app" / "cli.js",
        patch_core_tool_examples=True,
        patch_cli_hooks=True,
        patch_edit_tool_guidance=True,
        patch_console_input=True,
    )
    chunks_dir = path / "app" / "chunks"
    if chunks_dir.exists():
        for chunk in sorted(chunks_dir.glob("*.js")):
            _patch_runtime_text_file(chunk, patch_cli_hooks=True, patch_edit_tool_guidance=True)
    _patch_qwen35_vision_runtime(path)
    _patch_runtime_text_file(path / "scripts" / "ultrawork-activate.js", patch_work_mode_activation=True)
    _patch_runtime_text_file(path / "scripts" / "write-runtime-config.js", patch_custom_agents=True)
    _patch_runtime_text_file(path / "scripts" / "team-log-lib.js", patch_activation_message=True, patch_work_mode_state=True)
    _patch_runtime_text_file(path / "scripts" / "orchestration-policy.js", patch_work_mode_policy=True)
    _patch_qwen_settings_files(path)
    _remove_generated_legacy_agents(path)
    _install_kiwi_fast_system_prompts(path)
    _install_kiwi_ultrawork_agents(path)
    _install_kiwi_ultrawork_policy(path)
    _install_kiwi_superpowers_extension(path)


def _patch_qwen_runtime_launchers(path: Path) -> None:
    for relative in [Path("run-qwen.cmd"), Path("run-qwen-split.cmd")]:
        launcher_path = path / relative
        if not launcher_path.exists():
            continue
        try:
            text = launcher_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        updated = _rewrite_qwen_node_runtime_paths(text)
        anchor = 'set "NODE_TLS_REJECT_UNAUTHORIZED=0"\n'
        if "KIWI forced no sandbox for Windows closed-network runtime" not in updated and anchor in updated:
            updated = updated.replace(
                anchor,
                anchor
                + "rem KIWI forced no sandbox for Windows closed-network runtime.\n"
                + 'set "QWEN_SANDBOX=0"\n'
                + 'set "SANDBOX="\n',
                1,
            )
        project_asset_sync = (
            'rem KIWI syncs bundled project skills and agents into existing qwen projects.\n'
            'if exist "%ROOT%\\templates\\project\\.qwen\\skills" if exist "%CD%\\.qwen" (\n'
            '  robocopy "%ROOT%\\templates\\project\\.qwen\\skills" "%CD%\\.qwen\\skills" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul\n'
            '  if errorlevel 8 exit /b %ERRORLEVEL%\n'
            ')\n'
            'if exist "%ROOT%\\templates\\project\\.qwen\\agents" if exist "%CD%\\.qwen" (\n'
            '  robocopy "%ROOT%\\templates\\project\\.qwen\\agents" "%CD%\\.qwen\\agents" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul\n'
            '  if errorlevel 8 exit /b %ERRORLEVEL%\n'
            ')\n'
        )
        updated = re.sub(
            r"rem KIWI syncs bundled project skills(?: and agents)? into existing qwen projects\.\r?\n"
            r"if exist \"%ROOT%\\templates\\project\\.qwen\\skills\" if exist \"%CD%\\.qwen\" \(\r?\n"
            r"  robocopy \"%ROOT%\\templates\\project\\.qwen\\skills\" \"%CD%\\.qwen\\skills\" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul\r?\n"
            r"  if errorlevel 8 exit /b %ERRORLEVEL%\r?\n"
            r"\)\r?\n"
            r"(?:if exist \"%ROOT%\\templates\\project\\.qwen\\agents\" if exist \"%CD%\\.qwen\" \(\r?\n"
            r"  robocopy \"%ROOT%\\templates\\project\\.qwen\\agents\" \"%CD%\\.qwen\\agents\" /E /NFL /NDL /NJH /NJS /NC /NS /NP >nul\r?\n"
            r"  if errorlevel 8 exit /b %ERRORLEVEL%\r?\n"
            r"\)\r?\n)?",
            lambda _match: project_asset_sync,
            updated,
            count=1,
        )
        if "KIWI syncs bundled project skills and agents into existing qwen projects" not in updated:
            updated = updated.replace(
                '"%ROOT%\\runtimes\\node\\node.exe" "%ROOT%\\app\\cli.js" --auth-type openai %*',
                project_asset_sync + '"%ROOT%\\runtimes\\node\\node.exe" "%ROOT%\\app\\cli.js" --auth-type openai %*',
                1,
            )
        updated = re.sub(
            r"\r?\nrem KIWI forced yolo approval for Windows closed-network runtime\.\r?\n"
            r'"%ROOT%\\runtimes\\node\\node\.exe" "%ROOT%\\app\\cli\.js" --auth-type openai %\* --approval-mode yolo',
            lambda _match: '\n"%ROOT%\\runtimes\\node\\node.exe" "%ROOT%\\app\\cli.js" --auth-type openai %*',
            updated,
            count=1,
        )
        updated = updated.replace(
            '"%ROOT%\\runtimes\\node\\node.exe" "%ROOT%\\app\\cli.js" --auth-type openai %* --approval-mode yolo',
            '"%ROOT%\\runtimes\\node\\node.exe" "%ROOT%\\app\\cli.js" --auth-type openai %*',
        )
        if updated == text:
            continue
        try:
            launcher_path.write_text(updated, encoding="utf-8")
        except OSError:
            continue


def _normalize_qwencode_runtime_layout(path: Path) -> None:
    runtimes = path / "runtimes"
    node_runtime = runtimes / "node"
    legacy_node = path / "node"
    try:
        runtimes.mkdir(parents=True, exist_ok=True)
        if legacy_node.exists() and not node_runtime.exists():
            shutil.move(str(legacy_node), str(node_runtime))
        elif legacy_node.exists() and node_runtime.exists():
            shutil.rmtree(legacy_node)
    except OSError:
        return


def _rewrite_qwen_node_runtime_paths(text: str) -> str:
    return (
        text.replace("%ROOT%\\node\\", "%ROOT%\\runtimes\\node\\")
        .replace("%ROOT%\\node;", "%ROOT%\\runtimes\\node;")
        .replace("%~dp0node\\", "%~dp0runtimes\\node\\")
    )


def _patch_qwen_init_script(path: Path) -> None:
    init_path = path / "scripts" / "qwen-init.ps1"
    if not init_path.exists():
        return
    try:
        text = init_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    updated = text
    if "function Copy-TemplateDirectory" not in updated:
        updated = updated.replace(
            """function Write-Cmd {
  param(
    [string]$RelativePath,
    [string]$Content
  )
""",
            """function Copy-TemplateDirectory {
  param(
    [string]$TemplateRelativePath,
    [string]$TargetRelativePath
  )

  $Source = Join-Path (Join-Path $Root "templates\\project") $TemplateRelativePath
  if (!(Test-Path -LiteralPath $Source -PathType Container)) {
    return
  }
  $Destination = Join-Path $Target $TargetRelativePath
  if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }
  $DestinationParent = Split-Path -Parent $Destination
  if (![string]::IsNullOrWhiteSpace($DestinationParent)) {
    New-Item -ItemType Directory -Force -Path $DestinationParent | Out-Null
  }
  Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
  Write-Host "[OK] Created $TargetRelativePath"
}

function Write-Cmd {
  param(
    [string]$RelativePath,
    [string]$Content
  )
""",
            1,
        )
    if '".qwen\\skills"' not in updated:
        updated = updated.replace(
            '  ".qwen\\env.cmd",\n',
            '  ".qwen\\env.cmd",\n  ".qwen\\skills",\n',
            1,
        )
    if '".qwen\\agents"' not in updated:
        updated = updated.replace(
            '  ".qwen\\skills",\n',
            '  ".qwen\\skills",\n  ".qwen\\agents",\n',
            1,
        )
    if 'Copy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"' not in updated:
        updated = updated.replace(
            'Copy-Template ".qwen\\env.cmd" ".qwen\\env.cmd"\n',
            'Copy-Template ".qwen\\env.cmd" ".qwen\\env.cmd"\nCopy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"\n',
            1,
        )
    if 'Copy-TemplateDirectory ".qwen\\agents" ".qwen\\agents"' not in updated:
        updated = updated.replace(
            'Copy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"\n',
            'Copy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"\nCopy-TemplateDirectory ".qwen\\agents" ".qwen\\agents"\n',
            1,
        )
    if updated != text:
        try:
            init_path.write_text(updated, encoding="utf-8")
        except OSError:
            return


def _patch_runtime_text_file(
    path: Path,
    patch_activation_message: bool = False,
    patch_cli_hooks: bool = False,
    patch_custom_agents: bool = False,
    patch_core_tool_examples: bool = False,
    patch_edit_tool_guidance: bool = False,
    patch_work_mode_activation: bool = False,
    patch_work_mode_state: bool = False,
    patch_work_mode_policy: bool = False,
    patch_console_input: bool = False,
) -> None:
    if not path.exists():
        return
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    updated = _normalize_runtime_agent_names(text)
    if patch_cli_hooks:
        updated = _patch_qwen_cli_hooks(updated)
    if patch_console_input:
        updated = _patch_console_paste_guard(updated)
    if patch_activation_message:
        updated = _patch_ultrawork_activation_message(updated)
    if patch_custom_agents:
        updated = _patch_write_runtime_config_custom_agents(updated)
    if patch_core_tool_examples:
        updated = _patch_core_tool_prompt_examples(updated)
    if patch_edit_tool_guidance:
        updated = _patch_edit_tool_failure_guidance(updated)
    if patch_work_mode_activation:
        updated = _patch_work_mode_activation_script(updated)
    if patch_work_mode_state:
        updated = _patch_work_mode_state_script(updated)
    if patch_work_mode_policy:
        updated = _patch_work_mode_policy_script(updated)
    if updated == text:
        return
    try:
        path.write_text(updated, encoding="utf-8")
    except OSError:
        return


def _patch_qwen35_vision_runtime(path: Path) -> None:
    candidates = [
        path / "scripts" / "write-runtime-config.js",
        path / "app" / "cli.js",
    ]
    chunks_dir = path / "app" / "chunks"
    if chunks_dir.exists():
        candidates.extend(sorted(chunks_dir.glob("*.js")))
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
            updated = _patch_qwen35_vision_text(text)
            if updated != text:
                candidate.write_text(updated, encoding="utf-8")
        except OSError:
            continue


def _apply_qwen_console_ui_defaults(data: dict[str, Any]) -> None:
    ui = data.get("ui")
    if not isinstance(ui, dict):
        ui = {}
    ui["compactMode"] = True
    ui["useTerminalBuffer"] = False
    data["ui"] = ui


def _patch_qwen_settings_files(path: Path) -> None:
    for settings_path in [
        path / "portable-user" / ".qwen" / "settings.json",
        path / "templates" / "project" / ".qwen" / "settings.json",
    ]:
        if not settings_path.exists():
            continue
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        tools = data.get("tools")
        if not isinstance(tools, dict):
            tools = {}
        tools["approvalMode"] = "yolo"
        tools.pop("sandbox", None)
        data["tools"] = tools
        _apply_qwen_console_ui_defaults(data)
        try:
            settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            continue


def _patch_qwen35_vision_text(text: str) -> str:
    text = text.replace(
        """    extra_body: extraBodyEnv("QWEN35_EXTRA_BODY_JSON")
  });""",
        """    extra_body: extraBodyEnv("QWEN35_EXTRA_BODY_JSON"),
    modalities: { image: true },
    splitToolMedia: true
  });""",
    )
    text = text.replace(
        """  // Qwen3.5-Plus, Qwen3.6-Plus: image + video support
  [/^qwen3\\.5-plus/, { image: true, video: true }],""",
        """  // Qwen3.5-Plus, Qwen3.6-Plus: image + video support
  [/^qwen3\\.5-plus/, { image: true, video: true }],
  // Samsung Life Qwen3.5-397B is served as image-capable in the closed network.
  [/^qwen3\\.5-397b(?:-a17b)?/, { image: true }],""",
    )
    return text


def _normalize_runtime_agent_names(text: str) -> str:
    text = re.sub(r"(?<!qwen3-)coder-next", "coder-35", text)
    return re.sub(r"(?<!Qwen3-)Coder-Next", "Coder-35", text)


def _patch_qwen_cli_hooks(text: str) -> str:
    """Carry subagent identity into Qwen hook payloads and keep subagent approval yolo."""
    agent_type_expr = 'String(this.config?.name || this.config?.getName?.() || this.config?.getSubagentName?.() || this.config?.getAgentName?.() || "")'
    if "function normalizeKiwiToolName(name)" not in text:
        text = text.replace(
            "      const functionResponses = [];\n      let hitBoundary = false;",
            """      function normalizeKiwiToolName(name) {
        const value = String(name || "").trim();
        const compact = value.toLowerCase().replace(/[^a-z0-9]/g, "");
        if (compact === "todowrite" || compact === "mcptodowrite") return "todo_write";
        if (compact === "askuserquestion" || compact === "mcpaskuserquestion") return "ask_user_question";
        return value;
      }
      const functionResponses = [];
      let hitBoundary = false;""",
        )
    text = text.replace(
        '        const name3 = fc.name ?? "";\n        const args2 = fc.args ?? {};',
        """        const rawName = fc.name ?? "";
        const name3 = normalizeKiwiToolName(rawName);
        if (name3 !== rawName) fc.name = name3;
        const args2 = fc.args ?? {};""",
    )
    text = text.replace(
        "function parseApprovalModeValue(value) {\n  const normalized = value.trim().toLowerCase();",
        "function parseApprovalModeValue(value) {\n"
        "  if (Array.isArray(value)) value = value[value.length - 1];\n"
        "  if (typeof value !== \"string\") value = String(value ?? \"\");\n"
        "  const normalized = value.trim().toLowerCase();",
    )
    text = text.replace(
        'const agentApprovalMode = agentApprovalModes.get(agentId) ?? "default" /* DEFAULT */;',
        'const agentApprovalMode = agentApprovalModes.get(agentId) ?? "yolo" /* YOLO */;',
    )
    text = text.replace(
        "const permissionMode = String(approvalMode);\n      if (hooksEnabledForTool && messageBusForTool) {",
        "const permissionMode = String(approvalMode);\n"
        f"      const agentTypeForHooks = {agent_type_expr};\n"
        "      if (hooksEnabledForTool && messageBusForTool) {",
    )
    text = text.replace(
        """          toolUseId,
          permissionMode,
          abortSignal
        );""",
        """          toolUseId,
          permissionMode,
          agentTypeForHooks,
          abortSignal
        );""",
    )
    text = text.replace(
        "async function firePreToolUseHook(messageBus, toolName, toolInput, toolUseId, permissionMode, signal) {",
        "async function firePreToolUseHook(messageBus, toolName, toolInput, toolUseId, permissionMode, agentType, signal) {",
    )
    text = text.replace(
        """        input: {
          permission_mode: permissionMode,
          tool_name: toolName,""",
        """        input: {
          permission_mode: permissionMode,
          agent_type: agentType || void 0,
          tool_name: toolName,""",
    )
    text = re.sub(
        r"(async function firePostToolUseHook\(messageBus, toolName, toolInput, toolResponse, toolUseId, permissionMode, signal\) \{.*?input: \{\n\s*permission_mode: permissionMode,\n)\s*agent_type: agentType \|\| void 0,\n",
        r"\1",
        text,
        flags=re.DOTALL,
    )
    text = text.replace(
        """          toolUseId,
          permissionMode
        ),""",
        """          toolUseId,
          permissionMode,
          String(this.config?.name || this.config?.getName?.() || this.config?.getSubagentName?.() || this.config?.getAgentName?.() || "")
        ),""",
    )
    return text


def _patch_ultrawork_activation_message(text: str) -> str:
    text = text.replace(
        "Then continue immediately with the required `agent` tool call in the same turn. Do not stop after this announcement.",
        "Then, before any `agent` tool call, call `todo_write` tool and report the user-selected t-shirt size (`xsmall|small|medium|large|xlarge`), ultrawork mode, role composition, and short Korean plan. Do not use MCP-prefixed aliases for core tools. Do not call explorer-35, planner-35, architect-35, coder-35, reviewer-35, debugger-35, or tester-35 until after that sizing report.",
    )
    anchor = "- Before doing substantive work, Kiwi must call `todo_write` tool with ordered steps, the current in-progress item, and completion/verification conditions. Keep the visible Korean plan consistent with the todo list."
    schema_guard = "- Tool schema hint: if a tool schema is uncertain, load/check that tool's usage first; common traps are absolute `read_file.file_path`, `ask_user_question.questions` as an array, and exact `edit.old_string`. For edit, `@file` references or prompt-attached file content do not count as a tool read; call `read_file` in this session for the target file/range immediately before editing, then copy the smallest exact current N-line span from that latest `read_file`. After a successful edit the old snippet is stale; on `edit_no_occurrence_found`, reread and retry once smaller, then stop instead of using PowerShell regex/Set-Content."
    project_info_guard = "- Central docs guard: project docs live under `D:/aiops/docs/<project-key>/`. Read `knowledge/00-index.md` first when present. Read optional Project Info Layer `project-info/` only from that absolute central root if it exists. Never try project-relative `docs/<project-key>/...` or `docs/kiwi/project-info/...` paths."
    path_guard = "- File path guard: copy file paths character-for-character from prior tool output (list_directory/glob/grep_search/read_file) or the user message. Never re-type Korean file names and never insert spaces around `-`/`_`. If a tool answers `File not found. Did you mean: <path>`, retry once with exactly that suggested path. Read large files in offset/limit slices instead of whole-file reads."
    schema_line = f'    "{schema_guard}",'
    project_info_line = f'    "{project_info_guard}",'
    path_line = f'    "{path_guard}",'
    anchor_line = f'    "{anchor}",'
    if anchor_line in text:
        additions = []
        if schema_guard not in text:
            additions.append(schema_line)
        if project_info_guard not in text:
            additions.append(project_info_line)
        if path_guard not in text:
            additions.append(path_line)
        if additions:
            return text.replace(anchor_line, "\n".join([*additions, anchor_line]), 1)
    return text


def _patch_work_mode_activation_script(text: str) -> str:
    new = """function triggerFromPrompt(prompt) {
  const line = firstLine(prompt);
  if (line === "ultrawork" || line === "ulw") return line;
  if (line === "lightwork" || line === "fast" || line === "lw") return line;
  if (line === "superpowers" || line === "spw") return line;
  if (/^(ultrawork|ulw|superpowers|spw)_(xsmall|small|medium|large|xlarge)$/.test(line)) return line;
  return "";
}"""
    updated = re.sub(r"function triggerFromPrompt\(prompt\) \{\n.*?\n\}", new, text, count=1, flags=re.DOTALL)
    if "teamModeContext(trigger, input.prompt || \"\", input)" not in updated:
        updated = updated.replace(
            "additionalContext: teamModeContext(trigger, input.prompt || \"\")",
            "additionalContext: teamModeContext(trigger, input.prompt || \"\", input)",
        )
        updated = updated.replace(
            "additionalContext: teamModeContext(trigger)",
            "additionalContext: teamModeContext(trigger, input.prompt || \"\", input)",
        )
        updated = updated.replace("function writeOutput(active, trigger) {", "function writeOutput(active, trigger, input = {}) {", 1)
        updated = updated.replace("writeOutput(true, trigger);", "writeOutput(true, trigger, input);", 1)
        updated = updated.replace("writeOutput(active, \"\");", "writeOutput(active, \"\", input);", 1)
    return updated


def _patch_work_mode_state_script(text: str) -> str:
    if "function activeWorkMode(input)" not in text:
        helper = r'''
function workModeFromTrigger(trigger) {
  const value = String(trigger || "").trim().toLowerCase();
  const base = value.replace(/_(xsmall|small|medium|large|xlarge)$/, "");
  if (base === "lightwork" || base === "fast" || base === "lw") return "fast";
  if (base === "superpowers" || base === "spw") return "superpowers";
  if (base === "ultrawork" || base === "ulw") return "ultrawork";
  return "";
}

function sessionState(input) {
  const state = readState();
  return state.sessions[sessionKey(input)] || null;
}

function selectedTaskSizeFromPrompt(prompt) {
  const text = String(prompt || "");
  const first = text.trim().split(/\r?\n/, 1)[0]?.trim().toLowerCase() || "";
  const triggerMatch = first.match(/^(ultrawork|ulw|superpowers|spw)_(xsmall|small|medium|large|xlarge)$/);
  if (triggerMatch) return triggerMatch[2].toLowerCase();
  const match = text.match(/사용자\s*선택:\s*`?(xsmall|small|medium|large|xlarge)`?/i)
    || text.match(/selected[_\s-]*task[_\s-]*size\s*[:=]\s*`?(xsmall|small|medium|large|xlarge)`?/i);
  return match ? match[1].toLowerCase() : "medium";
}

function activeWorkMode(input) {
  const state = sessionState(input);
  if (!state?.active) return "";
  return state.mode || workModeFromTrigger(state.trigger) || "";
}

function activeTaskSize(input) {
  const state = sessionState(input);
  if (!state?.active) return "";
  return state.selected_task_size || "medium";
}

function projectDocsKey(input) {
  const raw = String(input?.cwd || process.cwd?.() || "").replace(/\\/g, "/").toLowerCase();
  const parts = raw.split("/").filter(Boolean);
  const joined = parts.join("/");
  const base = (parts[parts.length - 1] || "").replace(/(?:-develop|-mevelop|-main)$/, "");
  if (joined.includes("dcp-front")) return "dcp-front";
  if (joined.includes("dcp-services")) return "dcp-services";
  if (joined.includes("drt-cms")) return "drt-cms";
  if (joined.includes("drt-front")) return "drt-front";
  if (joined.includes("drt-api")) return "drt-api";
  if (/^dcp-[a-z0-9._-]+$/.test(base) && base !== "dcp-front") return "dcp-services";
  const sanitized = base.replace(/[^a-z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "");
  if (sanitized === "dcp") return "dcp-services";
  return sanitized || "generic";
}

function projectDocsRoot(input) {
  return `D:/aiops/docs/${projectDocsKey(input)}`;
}

function projectKnowledgeIndex(input) {
  return `${projectDocsRoot(input)}/knowledge/00-index.md`;
}

function projectInfoRoot(input) {
  return `${projectDocsRoot(input)}/project-info`;
}

function projectRoot(input) {
  return String(input?.cwd || process.cwd?.() || "").replace(/\\/g, "/").replace(/\/$/, "");
}

function projectSkillPath(input, skillName) {
  return `${projectRoot(input)}/.qwen/skills/${skillName}/SKILL.md`;
}

function qwencodeSkillPath(skillName) {
  return `D:/aiops/qwencode/portable-user/.qwen/skills/${skillName}/SKILL.md`;
}

function superpowersPolicyPath() {
  return "D:/aiops/qwencode/portable-user/.qwen/extensions/superpowers/SUPERPOWERS_POLICY.md";
}

function superpowersSkillRuntimeLine(input) {
  return `Local Superpowers Skills: call the built-in skill tool with skill="kiwi-superpowers", then skill="using-superpowers". These skill names are parameters to the skill tool, not standalone tool names. If the skill tool reports unavailable or unknown skill, read ${projectSkillPath(input, "kiwi-superpowers")} and ${projectSkillPath(input, "using-superpowers")} with read_file; if either file is absent, read ${qwencodeSkillPath("kiwi-superpowers")} and ${qwencodeSkillPath("using-superpowers")}. If both locations are absent, read fallback policy ${superpowersPolicyPath()} and report the install gap once.`;
}

function projectDocsRuntimeLine(input) {
  const key = projectDocsKey(input);
  const root = projectDocsRoot(input);
  return `Resolved Project Docs: project_key=${key}; central root=${root}; first read ${root}/knowledge/00-index.md when present. Never use project-relative docs/<project-key>/ paths or a parent key such as D:/aiops/docs/dcp.`;
}

function workModeContextLine(mode, input = {}) {
  if (mode === "fast") return `Active KIWI work mode: FAST/lightwork. Kiwi works directly, keeps the change narrow, runs focused verification, and uses ${projectKnowledgeIndex(input)} when present.`;
  if (mode === "superpowers") return `Active KIWI work mode: superpowers. Use central docs at ${projectKnowledgeIndex(input)} first, then invoke local superpowers with the built-in skill tool.`;
  return `Active KIWI work mode: ultrawork. Report the user-selected t-shirt size first, coordinate registered Qwen subagents, and use central docs at ${projectKnowledgeIndex(input)} when present.`;
}

'''
        text = text.replace("function activateTeamMode(input, trigger) {", helper + "function activateTeamMode(input, trigger) {", 1)

    if "function selectedTaskSizeFromPrompt(prompt)" not in text and "function activeWorkMode(input)" in text:
        text = text.replace(
            "function activeWorkMode(input) {\n",
            """function selectedTaskSizeFromPrompt(prompt) {
  const text = String(prompt || "");
  const first = text.trim().split(/\\r?\\n/, 1)[0]?.trim().toLowerCase() || "";
  const triggerMatch = first.match(/^(ultrawork|ulw|superpowers|spw)_(xsmall|small|medium|large|xlarge)$/);
  if (triggerMatch) return triggerMatch[2].toLowerCase();
  const match = text.match(/사용자\\s*선택:\\s*`?(xsmall|small|medium|large|xlarge)`?/i)
    || text.match(/selected[_\\s-]*task[_\\s-]*size\\s*[:=]\\s*`?(xsmall|small|medium|large|xlarge)`?/i);
  return match ? match[1].toLowerCase() : "medium";
}

function activeWorkMode(input) {
""",
            1,
        )
    if "function activeTaskSize(input)" not in text and "function workModeContextLine(mode" in text:
        text = text.replace(
            "function workModeContextLine(mode",
            """function activeTaskSize(input) {
  const state = sessionState(input);
  if (!state?.active) return "";
  return state.selected_task_size || "medium";
}

function workModeContextLine(mode""",
            1,
        )
    if "function projectDocsKey(input)" not in text and "function workModeContextLine(mode" in text:
        text = text.replace(
            "function workModeContextLine(mode",
            """function projectDocsKey(input) {
  const raw = String(input?.cwd || process.cwd?.() || "").replace(/\\\\/g, "/").toLowerCase();
  const parts = raw.split("/").filter(Boolean);
  const joined = parts.join("/");
  const base = (parts[parts.length - 1] || "").replace(/(?:-develop|-mevelop|-main)$/, "");
  if (joined.includes("dcp-front")) return "dcp-front";
  if (joined.includes("dcp-services")) return "dcp-services";
  if (joined.includes("drt-cms")) return "drt-cms";
  if (joined.includes("drt-front")) return "drt-front";
  if (joined.includes("drt-api")) return "drt-api";
  if (/^dcp-[a-z0-9._-]+$/.test(base) && base !== "dcp-front") return "dcp-services";
  const sanitized = base.replace(/[^a-z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "");
  if (sanitized === "dcp") return "dcp-services";
  return sanitized || "generic";
}

function projectDocsRoot(input) {
  return `D:/aiops/docs/${projectDocsKey(input)}`;
}

function projectKnowledgeIndex(input) {
  return `${projectDocsRoot(input)}/knowledge/00-index.md`;
}

function projectInfoRoot(input) {
  return `${projectDocsRoot(input)}/project-info`;
}

function projectDocsRuntimeLine(input) {
  const key = projectDocsKey(input);
  const root = projectDocsRoot(input);
  return `Resolved Project Docs: project_key=${key}; central root=${root}; first read ${root}/knowledge/00-index.md when present. Never use project-relative docs/<project-key>/ paths or a parent key such as D:/aiops/docs/dcp.`;
}

function workModeContextLine(mode""",
            1,
        )

    text = re.sub(
        r"function workModeFromTrigger\(trigger\) \{\n.*?\n\}",
        lambda _match: """function workModeFromTrigger(trigger) {
  const value = String(trigger || "").trim().toLowerCase();
  const base = value.replace(/_(xsmall|small|medium|large|xlarge)$/, "");
  if (base === "lightwork" || base === "fast" || base === "lw") return "fast";
  if (base === "superpowers" || base === "spw") return "superpowers";
  if (base === "ultrawork" || base === "ulw") return "ultrawork";
  return "";
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"function selectedTaskSizeFromPrompt\(prompt\) \{\n.*?\n\}",
        lambda _match: """function selectedTaskSizeFromPrompt(prompt) {
  const text = String(prompt || "");
  const first = text.trim().split(/\\r?\\n/, 1)[0]?.trim().toLowerCase() || "";
  const triggerMatch = first.match(/^(ultrawork|ulw|superpowers|spw)_(xsmall|small|medium|large|xlarge)$/);
  if (triggerMatch) return triggerMatch[2].toLowerCase();
  const match = text.match(/사용자\\s*선택:\\s*`?(xsmall|small|medium|large|xlarge)`?/i)
    || text.match(/selected[_\\s-]*task[_\\s-]*size\\s*[:=]\\s*`?(xsmall|small|medium|large|xlarge)`?/i);
  return match ? match[1].toLowerCase() : "medium";
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"function activeTaskSize\(input\) \{\n.*?\n\}",
        lambda _match: """function activeTaskSize(input) {
  const state = sessionState(input);
  if (!state?.active) return "";
  return state.selected_task_size || "medium";
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"function activeWorkMode\(input\) \{\n.*?\n\}",
        lambda _match: """function activeWorkMode(input) {
  const state = sessionState(input);
  if (!state?.active) return "";
  return state.mode || workModeFromTrigger(state.trigger) || "";
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"function projectDocsKey\(input\) \{\n.*?\nfunction projectDocsRuntimeLine\(input\) \{\n.*?\n\}",
        lambda _match: """function projectDocsKey(input) {
  const raw = String(input?.cwd || process.cwd?.() || "").replace(/\\\\/g, "/").toLowerCase();
  const parts = raw.split("/").filter(Boolean);
  const joined = parts.join("/");
  const base = (parts[parts.length - 1] || "").replace(/(?:-develop|-mevelop|-main)$/, "");
  if (joined.includes("dcp-front")) return "dcp-front";
  if (joined.includes("dcp-services")) return "dcp-services";
  if (joined.includes("drt-cms")) return "drt-cms";
  if (joined.includes("drt-front")) return "drt-front";
  if (joined.includes("drt-api")) return "drt-api";
  if (/^dcp-[a-z0-9._-]+$/.test(base) && base !== "dcp-front") return "dcp-services";
  const sanitized = base.replace(/[^a-z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "");
  if (sanitized === "dcp") return "dcp-services";
  return sanitized || "generic";
}

function projectDocsRoot(input) {
  return `D:/aiops/docs/${projectDocsKey(input)}`;
}

function projectKnowledgeIndex(input) {
  return `${projectDocsRoot(input)}/knowledge/00-index.md`;
}

function projectInfoRoot(input) {
  return `${projectDocsRoot(input)}/project-info`;
}

function projectRoot(input) {
  return String(input?.cwd || process.cwd?.() || "").replace(/\\\\/g, "/").replace(/\\/$/, "");
}

function projectSkillPath(input, skillName) {
  return `${projectRoot(input)}/.qwen/skills/${skillName}/SKILL.md`;
}

function qwencodeSkillPath(skillName) {
  return `D:/aiops/qwencode/portable-user/.qwen/skills/${skillName}/SKILL.md`;
}

function superpowersPolicyPath() {
  return "D:/aiops/qwencode/portable-user/.qwen/extensions/superpowers/SUPERPOWERS_POLICY.md";
}

function superpowersSkillRuntimeLine(input) {
  return `Local Superpowers Skills: call the built-in skill tool with skill="kiwi-superpowers", then skill="using-superpowers". These skill names are parameters to the skill tool, not standalone tool names. If the skill tool reports unavailable or unknown skill, read ${projectSkillPath(input, "kiwi-superpowers")} and ${projectSkillPath(input, "using-superpowers")} with read_file; if either file is absent, read ${qwencodeSkillPath("kiwi-superpowers")} and ${qwencodeSkillPath("using-superpowers")}. If both locations are absent, read fallback policy ${superpowersPolicyPath()} and report the install gap once.`;
}

function projectDocsRuntimeLine(input) {
  const key = projectDocsKey(input);
  const root = projectDocsRoot(input);
  return `Resolved Project Docs: project_key=${key}; central root=${root}; first read ${root}/knowledge/00-index.md when present. Never use project-relative docs/<project-key>/ paths or a parent key such as D:/aiops/docs/dcp.`;
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"function workModeContextLine\(mode(?:, input = \{\})?\) \{\n.*?\n\}",
        lambda _match: """function workModeContextLine(mode, input = {}) {
  if (mode === "fast") return `Active KIWI work mode: FAST/lightwork. Kiwi works directly, keeps the change narrow, runs focused verification, and uses ${projectKnowledgeIndex(input)} when present.`;
  if (mode === "superpowers") return `Active KIWI work mode: superpowers. Use central docs at ${projectKnowledgeIndex(input)} first, then invoke local superpowers with the built-in skill tool.`;
  return `Active KIWI work mode: ultrawork. Report the user-selected t-shirt size first, coordinate registered Qwen subagents, and use central docs at ${projectKnowledgeIndex(input)} when present.`;
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )

    old_activate = """function activateTeamMode(input, trigger) {
  const state = readState();
  const key = sessionKey(input);
  state.sessions[key] = {
    active: true,
    trigger,
    cwd: input.cwd || null,
    session_id: input.session_id || null,
    activated_at: new Date().toISOString()
  };
  writeState(state);
}"""
    new_activate = """function activateTeamMode(input, trigger) {
  const state = readState();
  const key = sessionKey(input);
  const requestedMode = workModeFromTrigger(trigger);
  const selectedTaskSize = requestedMode === "fast" ? "" : selectedTaskSizeFromPrompt(input?.prompt);
  const existing = state.sessions[key];
  if (existing?.active) {
    const lockedMode = existing.mode || workModeFromTrigger(existing.trigger);
    state.sessions[key] = {
      ...existing,
      active: true,
      mode: lockedMode,
      selected_task_size: existing.selected_task_size || selectedTaskSize || null,
      mode_locked: true,
      rejected_trigger: lockedMode !== requestedMode ? trigger : existing.rejected_trigger,
      updated_at: new Date().toISOString()
    };
    writeState(state);
    return;
  }
  state.sessions[key] = {
    active: true,
    trigger,
    mode: requestedMode,
    selected_task_size: selectedTaskSize || null,
    mode_locked: true,
    cwd: input.cwd || null,
    session_id: input.session_id || null,
    activated_at: new Date().toISOString()
  };
  writeState(state);
}"""
    if old_activate in text:
        text = text.replace(old_activate, new_activate, 1)

    if "workModeContextLine(workModeFromTrigger(trigger), input)" not in text:
        text = text.replace(
            '"[Ultrawork team mode active]",\n    `${triggerLine}`.trim(),',
            '"[Ultrawork team mode active]",\n    workModeContextLine(workModeFromTrigger(trigger), input),\n    projectDocsRuntimeLine(input),\n    `${triggerLine}`.trim(),',
            1,
        )
    text = _replace_team_mode_context(text)
    lock_line = "- Work mode lock: once lightwork, ultrawork, or superpowers activates this session, do not change mode from a later prompt prefix; ask the user to start a new console session instead."
    if lock_line not in text:
        text = text.replace(
            '"Planning protocol:",',
            f'"Work mode protocol:",\n    "{lock_line}",\n    "- lightwork/fast/lw: direct focused work, no subagents.",\n    "- ultrawork_<size>/ulw_<size>: user-selected t-shirt sizing and Qwen subagent orchestration; plain ultrawork/ulw defaults to medium.",\n    "- superpowers_<size>/spw_<size>: invoke local superpowers with the built-in skill tool, then use ultrawork agents as needed; plain superpowers/spw defaults to medium.",\n    "",\n    "Planning protocol:",',
            1,
        )
    if "activeTaskSize" not in text.split("module.exports = ", 1)[-1]:
        text = text.replace(
            "  isTeamModeActive,\n",
            "  isTeamModeActive,\n  activeWorkMode,\n  activeTaskSize,\n",
            1,
        )
    elif "activeWorkMode" not in text.split("module.exports = ", 1)[-1]:
        text = text.replace(
            "  isTeamModeActive,\n",
            "  isTeamModeActive,\n  activeWorkMode,\n",
            1,
        )
    return text


def _replace_team_mode_context(text: str) -> str:
    replacement = r'''function fastModeContext(trigger, input = {}) {
  const triggerLine = trigger ? ` The first line "${trigger}" is a mode switch; ignore it as task content.` : "";
  const activationReport = trigger
    ? "- On this first response after activation, tell the user in Korean: `FAST/lightwork 모드 활성화했습니다. Kiwi가 직접 계획, 실행, 검증하겠습니다.` In the same first turn, call `todo_write` tool with the direct plan before any file read, edit, or shell command."
    : "- FAST/lightwork mode is already active; do not repeat the activation announcement unless the user asks.";
  return [
    "[KIWI FAST/lightwork mode active]",
    workModeContextLine("fast", input),
    projectDocsRuntimeLine(input),
    `${triggerLine}`.trim(),
    "",
    "Your name is Kiwi. You are the main Qwen3.5 worker for this direct session: clarify the goal, inspect only the necessary files, make the smallest direct change, verify narrowly, and report concrete evidence.",
    "",
    "FAST system prompt source:",
    "- dcp-front: docs/fast-system-prompts/fast-system-prompt.dcp-front.md",
    "- dcp-services: docs/fast-system-prompts/fast-system-prompt.dcp-services.md",
    "- generic: docs/fast-system-prompts/fast-system-prompt.generic.md",
    `- Use the profile-matching source as the direct-work contract. Read central docs at ${projectKnowledgeIndex(input)} when present, optionally read ${projectInfoRoot(input)}/ only if it exists, verify current files, make a minimal diff, run focused verification, and stop and ask on ambiguity.`,
    "",
    "FAST/lightwork direct protocol:",
    `- Central Project Docs: project_key=${projectDocsKey(input)}; root ${projectDocsRoot(input)}. Read ${projectKnowledgeIndex(input)} first when present. Project Info Layer summaries are optional at ${projectInfoRoot(input)}/ only; never try project-relative docs/<project-key>/... or docs/kiwi/project-info/... paths.`,
    `- Project Knowledge Pack: use the relevant ${projectDocsRoot(input)}/knowledge/* docs as seed knowledge only; verify every claim against current files before editing.`,
    "- If Project Info Layer is missing or stale, tell the user Project Info refresh is needed and continue from current files. Do not invent a default project overview.",
    "- Do not paste full project-info.json or full EAI markdown into prompts; use summary artifacts and targeted evidence paths only.",
    "- FAST/lightwork has no size report. Never estimate or report work scale in this mode.",
    "- Before doing substantive work, call `todo_write` tool with ordered steps, the current in-progress item, and completion/verification conditions. For a tiny task, one item is enough.",
    "- Keep the scope narrow. Do not broaden the task or turn it into delegated workflow inside this session.",
    "- Do not use the registered `agent` delegation mechanism in FAST/lightwork. If a denial from that mechanism appears, treat it as confirmation of the active direct-work policy, continue directly, and do not claim a mode conflict.",
    "- Read the current files before editing. Prefer a minimal diff that follows repository-local conventions.",
    "- Run focused verification when available. If verification cannot run, report why and provide a concrete fallback check.",
    "- If the work turns broad, risky, or cross-module, stop and tell the user to start a new console session in a stronger work mode.",
    "",
    "User-visible reporting protocol:",
    activationReport,
    "- Keep the main terminal concise: todo_write-backed plan, action, verification, and blockers only.",
    "",
    "User question protocol:",
    "- If user input, permission, confirmation, a blocking clarification, or a human-visible choice is needed, do not ask as plain prose.",
    "- Before calling `ask_user_question`, first load/check the tool usage or schema for `ask_user_question` and verify the exact `questions` array shape.",
    "- Then call the native `ask_user_question` tool in the same turn. `questions` must be an array of 1-3 question objects; each object needs `header`, `id`, `question`, and 2-3 `options` with `label` and `description`.",
    "- If `ask_user_question` is unavailable after checking its usage/schema, explicitly say the tool is unavailable and ask the shortest plain-text fallback question.",
    "",
    "Tool use precision:",
    "- Actual callable names are `todo_write` and `ask_user_question`. Display names and MCP-prefixed aliases are not callable names.",
    "- If a tool schema is uncertain, load/check that tool's usage first. Common traps: absolute `read_file.file_path`, `ask_user_question.questions` as an array, exact `edit.old_string`. For edit, `@file` references and prompt-attached file content do not satisfy the edit tool read gate; call `read_file` in this session for the exact target range before the first edit.",
    "- File path precision: copy file and directory paths character-for-character from prior tool output (list_directory/glob/grep_search/read_file) or the user message. Never re-type Korean file names, never insert spaces around `-`/`_`, and never invent intermediate directories; list the parent directory first. If a tool answers `File not found. Did you mean: <path>`, retry once with exactly that suggested path. Read large files in offset/limit slices instead of whole-file reads.",
    "",
    "Safety:",
    "- Do not modify deployment, secrets, certificates, release scripts, or infrastructure-critical files without explicit user confirmation.",
    "- Mention verification commands and residual risk in the final answer."
  ].filter(Boolean).join("\n");
}

function superpowersXsmallContext(trigger, prompt, input = {}) {
  const triggerLine = trigger ? ` The first line "${trigger}" is a mode switch; ignore it as task content.` : "";
  const activationReport = trigger
    ? `- On this first response after activation, tell the user in Korean: \`superpowers xsmall 모드 활성화했습니다. 중앙 프로젝트 문서와 superpowers skill tool을 사용한 뒤 Kiwi direct work로 처리하겠습니다.\` Then read ${projectKnowledgeIndex(input)} when present. Then call the built-in skill tool as specified by the Local Superpowers Skills line.`
    : "- Superpowers xsmall mode is already active; do not repeat the activation announcement unless the user asks.";
  return [
    "[KIWI superpowers xsmall mode active]",
    workModeContextLine("superpowers", input),
    projectDocsRuntimeLine(input),
    `${triggerLine}`.trim(),
    "",
    "Your name is Kiwi. You are the main Qwen3.5 worker for this direct superpowers session.",
    "Kiwi direct work is allowed for selected task_size `xsmall`: read the current files, make the smallest direct change, and run focused verification.",
    "",
    "Superpowers xsmall skill-first protocol:",
    `- Central project docs root is ${projectDocsRoot(input)}. Read ${projectKnowledgeIndex(input)} first when present. Read optional Project Info Layer only from ${projectInfoRoot(input)}/ if it exists.`,
    "- Never try project-relative `docs/<project-key>/...` or `docs/kiwi/project-info/...` paths for central docs.",
    superpowersSkillRuntimeLine(input),
    "- This skill-tool gate applies to every superpowers size, including large and xlarge.",
    "- Use skill tool for `kiwi-superpowers` and `using-superpowers` before broad analysis or delegation. Do not call tools named `kiwi-superpowers` or `using-superpowers`.",
    "- Before substantive work, call `todo_write` tool with ordered steps, the current in-progress item, and completion/verification conditions.",
    "- Build a compact impact map before editing: entrypoint, producer, carrier, persistence/cache/session, downstream consumer, verification surface.",
    "- The selected task_size is `xsmall`; do not call subagents for xsmall and do not delegate implementation.",
    "- If the impact map shows shared files, API/storage risk, or cross-module work, stop and ask the user to start a new non-xsmall superpowers or ultrawork session.",
    "",
    "User-visible reporting protocol:",
    activationReport,
    "- Keep the main terminal concise: todo_write-backed plan, action, verification, and blockers only.",
    "",
    "User question protocol:",
    "- If user input, permission, confirmation, a blocking clarification, or a human-visible choice is needed, do not ask as plain prose.",
    "- Before calling `ask_user_question`, first load/check the tool usage or schema for `ask_user_question` and verify the exact `questions` array shape.",
    "- Then call the native `ask_user_question` tool in the same turn. `questions` must be an array of 1-3 question objects; each object needs `header`, `id`, `question`, and 2-3 `options` with `label` and `description`.",
    "- If `ask_user_question` is unavailable after checking its usage/schema, explicitly say the tool is unavailable and ask the shortest plain-text fallback question.",
    "",
    "Tool use precision:",
    "- Actual callable names are `todo_write` and `ask_user_question`. Display names and MCP-prefixed aliases are not callable names.",
    "- If a tool schema is uncertain, load/check that tool's usage first. Common traps: absolute `read_file.file_path`, `ask_user_question.questions` as an array, exact `edit.old_string`. For edit, `@file` references and prompt-attached file content do not satisfy the edit tool read gate; call `read_file` in this session for the exact target range before the first edit.",
    "- File path precision: copy file and directory paths character-for-character from prior tool output (list_directory/glob/grep_search/read_file) or the user message. Never re-type Korean file names, never insert spaces around `-`/`_`, and never invent intermediate directories; list the parent directory first. If a tool answers `File not found. Did you mean: <path>`, retry once with exactly that suggested path. Read large files in offset/limit slices instead of whole-file reads.",
    "",
    "Safety:",
    "- Do not modify deployment, secrets, certificates, release scripts, or infrastructure-critical files without explicit user confirmation.",
    "- Mention verification commands and residual risk in the final answer."
  ].filter(Boolean).join("\n");
}

function teamModeContext(trigger, prompt = "", input = {}) {
  const mode = workModeFromTrigger(trigger) || activeWorkMode(input);
  if (mode === "fast") return fastModeContext(trigger, input);
  if (mode === "superpowers" && (selectedTaskSizeFromPrompt(prompt) === "xsmall" || activeTaskSize(input) === "xsmall")) return superpowersXsmallContext(trigger, prompt, input);
  const triggerLine = trigger ? ` The first line "${trigger}" is a mode switch; ignore it as task content.` : "";
  const activationReport = trigger
    ? mode === "superpowers"
      ? `- On this first response after activation, tell the user in Korean: \`superpowers 모드 활성화했습니다. 중앙 프로젝트 문서와 superpowers skill tool을 사용한 뒤 필요한 경우에만 위임 루프로 확장하겠습니다.\` Then read ${projectKnowledgeIndex(input)} when present. Then call the built-in skill tool as specified by the Local Superpowers Skills line.`
      : "- On this first response after activation, tell the user in Korean: `ultrawork 모드 활성화했습니다. 사용자 선택 티셔츠 사이즈를 먼저 보고하고, 규모에 맞게 Qwen subagent 팀을 조율하겠습니다.` Then report the selected t-shirt size before any `agent` tool call."
    : "- Team work mode is already active; do not repeat the activation announcement unless the user asks.";
  return [
    mode === "superpowers" ? "[KIWI superpowers mode active]" : "[Ultrawork team mode active]",
    workModeContextLine(mode, input),
    projectDocsRuntimeLine(input),
    `${triggerLine}`.trim(),
    "",
    "Your name is Kiwi. You are the main Qwen3.5 orchestrator and accountable PM: clarify the goal, consult specialists, plan the work, coordinate agents, resolve conflicts, drive verification, and keep looping until the user's request is genuinely complete or a real blocker must be reported.",
    "Kiwi should delegate code edits, refactors, test creation, and file-changing shell commands through the registered `agent` tool with the selected implementation subagent in team modes. Runtime hooks treat this as an advisory rule because Qwen can omit or drift subagent identity in PreToolUse payloads.",
    "Qwen3.5 non-mutating agents are planner-35, architect-35, reviewer-35, debugger-35, explorer-35, and tester-35. They analyze, plan, review, debug, explore, and verify, but they must not edit files.",
    "coder-35 is the default Qwen3.5 implementation agent. Specialized implementation agents include dcp-front-developer, dcp-backend-developer, drt-front-developer, drt-backend-developer, drt-cms-front-developer, and drt-cms-backend-developer when selected by project profile. Implementation agents own code mutation; all other agents remain read-only except tester-35 may run non-mutating verification commands.",
    "Agents do not need a separate queue or side process. Run collaboration through normal Qwen Code subagent calls: Kiwi sends a brief, receives feedback, then applies or relays the relevant points.",
    "Kiwi may run multiple subagents in parallel when their questions or ownership scopes are independent. Kiwi must prevent conflicts by assigning clear responsibilities, file/path ownership, and expected outputs before parallel work starts.",
    "",
    "Work mode protocol:",
    "- Work mode lock: once lightwork, ultrawork, or superpowers activates this session, do not change mode from a later prompt prefix; ask the user to start a new console session instead.",
    "- ultrawork_<size>/ulw_<size>: report the user-selected t-shirt size first and coordinate Qwen subagents according to that size. Plain ultrawork/ulw defaults to medium.",
    `- superpowers_<size>/spw_<size>: read ${projectKnowledgeIndex(input)} when present, invoke local superpowers with the built-in skill tool, and treat SUPERPOWERS_POLICY.md plus loaded skills as the source of truth before delegated execution. Plain superpowers/spw defaults to medium.`,
    `- Central Project Docs: project_key=${projectDocsKey(input)}; root ${projectDocsRoot(input)}. Read ${projectKnowledgeIndex(input)} first. Read project-info summaries only from ${projectInfoRoot(input)}/ if they exist. Never try project-relative docs/<project-key>/... or docs/kiwi/project-info/... paths.`,
    `- Project Knowledge Pack: use relevant ${projectDocsRoot(input)}/knowledge/* docs as seed knowledge before broad analysis; verify against current files.`,
    "- If Project Info Layer missing or stale, report that Project Info refresh is needed and keep current-file verification as the source of truth.",
    "- Do not paste full project-info.json or full EAI markdown into prompts; use summary artifacts and targeted evidence paths only.",
    "",
    ...(mode === "superpowers" ? [
      "Superpowers skill-first protocol:",
      superpowersSkillRuntimeLine(input),
      "- This skill-tool gate applies to every superpowers size, including large and xlarge.",
      "- First tool actions after this activation: call the built-in skill tool for `kiwi-superpowers`, then `using-superpowers`, then a task-specific skill when applicable.",
      "- Do not call `todo_write`, read broad repository files, implement, or call `agent` until the skill tool has been called for `kiwi-superpowers` and `using-superpowers`, or the fallback policy file has been read.",
      "- Do not call tools named `kiwi-superpowers` or `using-superpowers`; call the built-in skill tool with those values in its skill parameter.",
      "- The superpowers policy and skill are the source of truth for this mode; delegated agents are available only after the skill-first impact map is complete.",
      "- The selected task_size from the prefix or KIWI UI is the source of truth for role composition.",
    "- For front-end implementation slices with visible UI impact, load the `verifying-frontend-with-playwright` skill with the built-in skill tool before any completion claim: capture the changed screen with the bundled Playwright runtime, read the screenshot with read_file (Qwen3.5 image input is enabled through provider modalities), and verify the rendered change. If the serving adapter rejects image media, report DOM/CSS/text evidence plus the screenshot path for human review.",
      ""
    ] : []),
    "Planning protocol:",
    "- Before substantive work or any `agent` tool call, Kiwi must call `todo_write` tool with ordered steps, the current in-progress item, and completion/verification conditions.",
    "- Before any `agent` tool call, Kiwi must report the selected t-shirt size (`xsmall|small|medium|large|xlarge`), the selected work mode, role composition, and a short Korean execution plan consistent with the todo list.",
    "- Do not call explorer-35, planner-35, architect-35, coder-35, reviewer-35, debugger-35, tester-35, dcp-front-developer, dcp-backend-developer, drt-front-developer, drt-backend-developer, drt-cms-front-developer, or drt-cms-backend-developer until after that sizing report.",
    "- The visible plan must include ordered steps, the current in-progress step, and the acceptance/verification condition for completion.",
    "- `todo_write` tool is mandatory for planning and status updates; if the tool is unavailable, explicitly report that and keep a visible fallback plan.",
    "- After each subagent result or major decision, update the plan status before continuing: mark completed items, identify the next in-progress item, and revise the plan if the facts changed.",
    "- The final answer must map the completed work back to the plan and explicitly mention verification results or remaining blockers.",
    "",
    "User-visible reporting protocol:",
    activationReport,
    "- When you need a subagent, call the registered `agent` tool immediately. Do not merely write `[Ultrawork 요청] ...` as text and stop. KIWI records actual agent requests in Agent Chat and tool/policy events in Agent Timeline.",
    "- After every subagent result, use the returned result to decide the next action. Do not duplicate the full result unless you need to explain a decision, conflict, rejection, or follow-up.",
    "- Do not emit periodic progress messages. Keep the main terminal quiet while subagents run.",
    "- If launching multiple agents in parallel, make each `agent` prompt self-contained and clearly scoped.",
    "- Do not hide subagent instructions, questions, answers, disagreements, or rejected advice from the user. The user must be able to observe what was asked and what came back through KIWI Agent Chat/Timeline or your concise decision notes.",
    "",
    "User question protocol:",
    "- If user input, permission, confirmation, a blocking clarification, or a human-visible choice is needed, do not ask as plain prose.",
    "- Before calling `ask_user_question`, first load/check the tool usage or schema for `ask_user_question` and verify the exact `questions` array shape.",
    "- Then call the native `ask_user_question` tool in the same turn. `questions` must be an array of 1-3 question objects; each object needs `header`, `id`, `question`, and 2-3 `options` with `label` and `description`.",
    "- If `ask_user_question` is unavailable after checking its usage/schema, explicitly say the tool is unavailable and ask the shortest plain-text fallback question.",
    "",
    "Critical subagent invocation rule:",
    "- Subagent names are not tool names. Never call tools named planner-35, architect-35, reviewer-35, debugger-35, explorer-35, tester-35, coder-35, dcp-front-developer, dcp-backend-developer, drt-front-developer, drt-backend-developer, drt-cms-front-developer, or drt-cms-backend-developer.",
    "- To launch a subagent, use the registered tool named `agent` (displayed as Agent/Task) and pass the subagent name in `subagent_type`.",
    "- Required `agent` parameters are `description` and `prompt`; set `subagent_type` exactly to the desired agent name.",
    "",
    "For implementation tasks, run the smallest practical team loop:",
    "1. `xsmall` stays in Kiwi direct handling after the sizing report; do not call subagents for xsmall.",
    "2. `small` uses the implementation agent when a clear code slice exists; planner-35 and architect-35 are optional.",
    "3. Use planner-35 when requirements, acceptance criteria, ownership boundaries, or execution order need clarification.",
    "4. Use architect-35 when the work is complex, ambiguous, cross-module, security-sensitive, data-affecting, high-blast-radius, or front-end layout/CSS sensitive.",
    "5. Use explorer-35 for short targeted repository context when file or symbol locations are unclear. Run several explorer-35 calls in parallel only for independent questions.",
    "6. Integrate each implementation result, but do not finalize and do not launch another implementation loop until reviewer-35 has reviewed that result.",
    "7. Use tester-35 for Qwen3.5 verification review or non-mutating verification commands when code changes need an independent check.",
    "8. Use debugger-35 before asking for a fix after reviewer/tester findings, failed verification, failed edits, repeated tool-call failures, or unclear runtime symptoms.",
    "",
    "Delegation rules:",
    "- Kiwi, planner-35, architect-35, reviewer-35, debugger-35, explorer-35, and tester-35 must remain read-only for direct file mutation.",
    "- Prefer the selected implementation agent for edits, file writes, memory writes, and mutating shell commands in team modes. DCP/DRT/CMS implementation agents are included when selected by project profile. The hook does not hard-deny mutation solely from missing/mismatched identity.",
    "- reviewer-35 is mandatory after every implementation result except xsmall direct work.",
    "- debugger-35 is mandatory before a revision/fix loop when the previous loop produced a failure, reviewer/tester finding, failed edit, or repeated tool-call problem.",
    "- Parallelize independent subagent work when it reduces latency, but never create overlapping file ownership without first resolving the ownership boundary.",
    "",
    "Implementation work order contract:",
    "- Every implementation prompt must include Objective, Scope, Files/ownership, Relevant guidance if any, Exact implementation steps, Exact Edit Protocol, Non-goals, Verification command or fallback, Exploration budget, and Expected response format.",
    "- Keep implementation jobs small and bounded. If a coding task is broad, split it into sequential or parallel slices with non-overlapping files instead of sending one vague large task.",
    "- Reuse-first: for publishing, mockup, and UI revision work, modify the existing screens, components, and styles in place. Do not create a new view/component file or a parallel mock screen unless the work order explicitly names the new file path. Existing bottom sheets, confirm dialogs, and shared flows must be reused as-is.",
    "- Tell the implementation agent to first inspect the target files, then edit in small batches, then run focused verification.",
    "- Exact Edit Protocol: read the target range immediately before every edit; `@file` references and prompt-attached file content are not enough for edit, so the current session must call `read_file` for the target file/range first; copy old_string only from the latest read_file output; reread after each successful edit to the same file; for any N-line deletion/replacement use the smallest exact current span that contains only the changed lines, adding neighboring context only if needed for uniqueness; if preserved boundary/context lines are included in old_string, copy them unchanged into new_string, otherwise exclude them from the span; on edit_no_occurrence_found do not retry the same/larger old_string, reread and retry once smaller, then stop; do not use PowerShell regex/Set-Content or full-file shell rewrites as an edit-mismatch workaround.",
    "- File path precision: copy file and directory paths character-for-character from prior tool output (list_directory/glob/grep_search/read_file) or the user message. Never re-type Korean file names, never insert spaces around `-`/`_`, and never invent intermediate directories; list the parent directory first. If a tool answers `File not found. Did you mean: <path>`, retry once with exactly that suggested path. Read large files in offset/limit slices instead of whole-file reads.",
    "",
    "Safety:",
    "- Actual callable names are `todo_write` and `ask_user_question`. Display names and MCP-prefixed aliases are not callable names.",
    "- Do not modify deployment, secrets, certificates, release scripts, or infrastructure-critical files without explicit user confirmation.",
    "- Prefer minimal diffs and repository-local conventions.",
    "- Mention verification commands and residual risk in the final answer."
  ].filter(Boolean).join("\n");
}'''
    if "function fastModeContext(trigger" in text:
        updated = re.sub(
            r"function fastModeContext\(trigger(?:, [^)]*)?\) \{.*?\n\}\n\nfunction truncate",
            lambda _: replacement + "\n\nfunction truncate",
            text,
            count=1,
            flags=re.DOTALL,
        )
        if updated != text:
            return updated
    return re.sub(
        r"function teamModeContext\(trigger(?:, [^)]*)?\) \{.*?\n\}\n\nfunction truncate",
        lambda _: replacement + "\n\nfunction truncate",
        text,
        count=1,
        flags=re.DOTALL,
    )


def _patch_work_mode_policy_script(text: str) -> str:
    if 'activeWorkMode, activeTaskSize, logHookEvent' not in text:
        text = text.replace(
            'const { isTeamModeActive, logHookEvent } = require("./team-log-lib");',
            'const { isTeamModeActive, activeWorkMode, activeTaskSize, logHookEvent } = require("./team-log-lib");',
            1,
        )
        text = text.replace(
            'const { isTeamModeActive, activeWorkMode, logHookEvent } = require("./team-log-lib");',
            'const { isTeamModeActive, activeWorkMode, activeTaskSize, logHookEvent } = require("./team-log-lib");',
            1,
        )
    if "function isSkillTool(toolName)" not in text:
        text = text.replace(
            """function isAgentTool(toolName) {
  const name = normalize(toolName).replace(/[\\s-]/g, "_");
  return ["agent", "task"].includes(name);
}""",
            """function isAgentTool(toolName) {
  const name = normalize(toolName).replace(/[\\s-]/g, "_");
  return ["agent", "task"].includes(name);
}

function isSkillTool(toolName) {
  const name = normalize(toolName).replace(/[\\s-]/g, "_");
  return ["skill"].includes(name);
}""",
            1,
        )
    if "function isImplementationAgent(agentType)" not in text:
        text = text.replace(
            """function isCoderAgent(agentType) {
  return normalize(agentType).startsWith("coder-35");
}""",
            """const IMPLEMENTATION_AGENTS = [
  "coder-35",
  "dcp-front-developer",
  "dcp-backend-developer",
  "drt-front-developer",
  "drt-backend-developer",
  "drt-cms-front-developer",
  "drt-cms-backend-developer"
];

function isImplementationAgent(agentType) {
  const name = normalize(agentType);
  return IMPLEMENTATION_AGENTS.some((agent) => name.startsWith(agent));
}

function inferAgentType(input) {
  const direct = [
    input?.agent_type,
    input?.agentType,
    input?.subagent_type,
    input?.subagentType,
    input?.subagent_name,
    input?.subagentName,
    input?.agent_name,
    input?.agentName,
    input?.config_name,
    input?.configName
  ];
  for (const value of direct) {
    const normalized = normalize(value);
    if (normalized) return normalized;
  }
  const ids = [
    input?.prompt_id,
    input?.promptId,
    input?.conversation_id,
    input?.conversationId,
    input?.request_id,
    input?.requestId,
    input?.session_id,
    input?.sessionId
  ].map((value) => normalize(value)).filter(Boolean);
  for (const id of ids) {
    for (const agent of IMPLEMENTATION_AGENTS) {
      if (
        id === agent ||
        id.includes(`#${agent}`) ||
        id.includes(`${agent}#`) ||
        id.includes(`${agent}-`) ||
        id.includes(`${agent}_`)
      ) {
        return agent;
      }
    }
  }
  return "";
}

function isMainKiwi(agentType) {
  return !normalize(agentType);
}""",
            1,
        )
    elif "function inferAgentType(input)" not in text:
        text = text.replace(
            "function isMainKiwi(agentType) {",
            """const IMPLEMENTATION_AGENTS = [
  "coder-35",
  "dcp-front-developer",
  "dcp-backend-developer",
  "drt-front-developer",
  "drt-backend-developer",
  "drt-cms-front-developer",
  "drt-cms-backend-developer"
];

function inferAgentType(input) {
  const direct = [
    input?.agent_type,
    input?.agentType,
    input?.subagent_type,
    input?.subagentType,
    input?.subagent_name,
    input?.subagentName,
    input?.agent_name,
    input?.agentName,
    input?.config_name,
    input?.configName
  ];
  for (const value of direct) {
    const normalized = normalize(value);
    if (normalized) return normalized;
  }
  const ids = [
    input?.prompt_id,
    input?.promptId,
    input?.conversation_id,
    input?.conversationId,
    input?.request_id,
    input?.requestId,
    input?.session_id,
    input?.sessionId
  ].map((value) => normalize(value)).filter(Boolean);
  for (const id of ids) {
    for (const agent of IMPLEMENTATION_AGENTS) {
      if (
        id === agent ||
        id.includes(`#${agent}`) ||
        id.includes(`${agent}#`) ||
        id.includes(`${agent}-`) ||
        id.includes(`${agent}_`)
      ) {
        return agent;
      }
    }
  }
  return "";
}

function isMainKiwi(agentType) {""",
            1,
        )
    text = text.replace("const canMutate = isCoderAgent(agentType);", "const canMutate = isImplementationAgent(agentType);")
    text = text.replace("const agentType = normalize(input.agent_type);", "const agentType = inferAgentType(input);")
    text = text.replace(
        "  const text = normalize(command);\n  if (!text) return false;",
        "  let text = normalize(command);\n  if (!text) return false;\n  text = text.replace(/\\s+\\d?>\\s*(nul|\\/dev\\/null)\\b/g, \"\");",
    )
    if "  const mode = activeWorkMode(input);" not in text:
        text = text.replace(
            "  const active = isTeamModeActive(input);",
            "  const active = isTeamModeActive(input);\n  const mode = activeWorkMode(input);",
            1,
        )
    if "  const taskSize = activeTaskSize(input);" not in text:
        text = text.replace(
            "  const mode = activeWorkMode(input);",
            "  const mode = activeWorkMode(input);\n  const taskSize = activeTaskSize(input);",
            1,
        )
    marker = 'mode === "superpowers" && taskSize === "xsmall" && isMainKiwi(agentType)'
    if marker not in text:
        text = text.replace(
            """  if (isAgentTool(toolName)) {
    writeDecision(
      "allow",
      "Allowed by team orchestration policy.",
      undefined,
      input
    );
    return;
  }""",
            """  if (mode === "fast" && isAgentTool(toolName)) {
    writeDecision(
      "deny",
      "FAST/lightwork mode is locked to direct Kiwi work.",
      "Start a new console session in a stronger work mode if this task needs delegated execution.",
      input
    );
    return;
  }

  if (mode === "fast") {
    writeDecision("allow", "Allowed by FAST/lightwork direct-work policy.", undefined, input);
    return;
  }

  if (mode === "superpowers" && isSkillTool(toolName)) {
    writeDecision("allow", "Allowed by superpowers skill-first policy.", undefined, input);
    return;
  }

  if (mode === "superpowers" && activeTaskSize(input) === "xsmall" && isAgentTool(toolName)) {
    writeDecision(
      "deny",
      "Superpowers xsmall mode is Kiwi direct work and must not delegate agents.",
      "If this task needs delegated execution, start a new superpowers session with selected task_size small or larger.",
      input
    );
    return;
  }

  if (mode === "superpowers" && activeTaskSize(input) === "xsmall" && isMainKiwi(agentType)) {
    writeDecision("allow", "Allowed by superpowers xsmall Kiwi direct-work policy.", undefined, input);
    return;
  }

  if (isAgentTool(toolName)) {
    writeDecision(
      "allow",
      "Allowed by team orchestration policy.",
      undefined,
      input
    );
    return;
  }""",
            1,
        )
        text = text.replace("activeTaskSize(input) === \"xsmall\"", "taskSize === \"xsmall\"", 2)
    text = text.replace(
        "Only a coder-35 worker may edit files or write memory in Ultrawork mode.",
        "Only the selected implementation agent may edit files or write memory in Ultrawork/superpowers team mode.",
    )
    text = text.replace(
        "Kiwi, Qwen3.5 consultant agents, tester, and explorer are intentionally read-only for direct file mutation. Use the registered `agent` tool with subagent_type `coder-35` and pass a concrete work order.",
        "Kiwi, Qwen3.5 consultant agents, tester, and explorer are intentionally read-only for direct file mutation in non-xsmall team modes. Use the registered `agent` tool with the selected implementation agent. DCP/DRT/CMS implementation agents are allowed when selected by project profile.",
    )
    text = text.replace(
        "Mutating shell commands are allowed only from a coder-35 worker in Ultrawork mode.",
        "Mutating shell commands are allowed only from the selected implementation agent in Ultrawork/superpowers team mode.",
    )
    text = text.replace(
        "Kiwi may run orchestration and read-only diagnostics, and tester-35 may run verification commands. File-changing shell commands must be delegated through the registered `agent` tool with subagent_type `coder-35`.",
        "Kiwi may run orchestration and read-only diagnostics in non-xsmall team modes, and tester-35 may run verification commands. File-changing shell commands must be delegated through the registered `agent` tool with the selected implementation agent, including DCP/DRT/CMS implementation agents when selected by project profile.",
    )
    text = text.replace(
        "Kiwi must not directly edit files, write memory, or run mutating shell commands in team modes. Kiwi's job is orchestration and decision-making. Code edits, refactors, test creation, and file-changing shell commands must be delegated through the registered `agent` tool with the selected implementation subagent.",
        "Kiwi should delegate code edits, refactors, test creation, and file-changing shell commands through the registered `agent` tool with the selected implementation subagent in team modes. Runtime hooks treat this as an advisory rule because Qwen can omit or drift subagent identity in PreToolUse payloads.",
    )
    text = text.replace(
        "- Only the selected implementation agent may edit files, write files, write memory, or run mutating shell commands in team modes. DCP/DRT/CMS implementation agents are included when selected by project profile.",
        "- Prefer the selected implementation agent for edits, file writes, memory writes, and mutating shell commands in team modes. DCP/DRT/CMS implementation agents are included when selected by project profile. The hook does not hard-deny mutation solely from missing/mismatched identity.",
    )
    text = text.replace(
        "DCP implementation agents dcp-front-developer and dcp-backend-developer are allowed when selected by project profile.",
        "DCP/DRT/CMS implementation agents are allowed when selected by project profile.",
    )
    text = text.replace(
        "including DCP implementation agents when selected by project profile.",
        "including DCP/DRT/CMS implementation agents when selected by project profile.",
    )
    text = re.sub(
        r"function isImplementationAgent\(agentType\) \{\n.*?\n\}",
        lambda _match: """function isImplementationAgent(agentType) {
  const name = normalize(agentType);
  return IMPLEMENTATION_AGENTS.some((agent) => name.startsWith(agent));
}""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    if "function isKnownReadOnlyAgent(agentType)" not in text and "function isMainKiwi(agentType)" in text:
        text = text.replace(
            "function isMainKiwi(agentType) {",
            """function isKnownReadOnlyAgent(agentType) {
  const name = normalize(agentType);
  return [
    "planner-35",
    "architect-35",
    "reviewer-35",
    "debugger-35",
    "explorer-35",
    "tester-35"
  ].some((agent) => name.startsWith(agent));
}

function isMainKiwi(agentType) {""",
            1,
        )
    text = text.replace(
        "const canMutate = isImplementationAgent(agentType) || !agentType;",
        "const canMutate = isImplementationAgent(agentType);",
    )
    text = text.replace(
        "if (isWriteTool(toolName) && isKnownReadOnlyAgent(agentType)) {",
        "if (isWriteTool(toolName) && !canMutate) {",
    )
    text = text.replace(
        "if (looksMutatingShell(command) && isKnownReadOnlyAgent(agentType)) {",
        "if (looksMutatingShell(command) && !canMutate) {",
    )
    text = re.sub(
        r"\n  if \(isWriteTool\(toolName\) && !agentType\) \{\n"
        r"    writeDecision\(\n"
        r"      \"allow\",\n"
        r"      \"Allowed by implementation fallback because Qwen did not expose subagent identity to this hook\.\",\n"
        r"      undefined,\n"
        r"      input\n"
        r"    \);\n"
        r"    return;\n"
        r"  \}\n",
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"\n    if \(looksMutatingShell\(command\) && !agentType\) \{\n"
        r"      writeDecision\(\n"
        r"        \"allow\",\n"
        r"        \"Allowed by implementation fallback because Qwen did not expose subagent identity to this hook\.\",\n"
        r"        undefined,\n"
        r"        input\n"
        r"      \);\n"
        r"      return;\n"
        r"    \n?}",
        "",
        text,
        count=1,
    )
    text = re.sub(
        r"""\n  if \(isWriteTool\(toolName\) && !canMutate\) \{\n    writeDecision\(\n      "deny",\n      "Only the selected implementation agent may edit files or write memory in Ultrawork/superpowers team mode\.",\n      ".*?",\n      input\n    \);\n    return;\n  \n?\}\n""",
        """
  if (isWriteTool(toolName) && !canMutate) {
    writeDecision(
      "allow",
      "Allowed by advisory mutation policy; Qwen subagent identity may be missing or drifted.",
      "Prefer the selected implementation agent for writes, including DCP/DRT/CMS implementation agents when selected by project profile. If this is a planner/reviewer/tester/explorer action, stop and delegate the implementation slice instead of editing directly.",
      input
    );
    return;
  }
""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"""\n    if \(looksMutatingShell\(command\) && !canMutate\) \{\n      writeDecision\(\n        "deny",\n        "Mutating shell commands are allowed only from the selected implementation agent in Ultrawork/superpowers team mode\.",\n        ".*?",\n        input\n      \);\n      return;\n    \n?\}""",
        """
    if (looksMutatingShell(command) && !canMutate) {
      writeDecision(
        "allow",
        "Allowed by advisory mutation policy; Qwen subagent identity may be missing or drifted.",
        "Prefer the selected implementation agent for mutating shell commands, including DCP/DRT/CMS implementation agents when selected by project profile. If this is a planner/reviewer/tester/explorer action, stop and delegate the implementation slice instead of changing files directly.",
        input
      );
      return;
    }""",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"""\n  if \(isTesterAgent\(agentType\) && isWriteTool\(toolName\)\) \{\n    writeDecision\("deny", "tester-35 verifies and reports\. Test-file edits must be delegated to coder-35\.", undefined, input\);\n    return;\n  \n?\}\n""",
        """
  if (isTesterAgent(agentType) && isWriteTool(toolName)) {
    writeDecision(
      "allow",
      "Allowed by advisory tester policy; tester identity is not enforced as a hard write blocker.",
      "tester-35 should normally verify and report. If implementation is needed, delegate the implementation slice to the selected developer agent.",
      input
    );
    return;
  }
""",
        text,
        count=1,
    )
    return text


def _patch_core_tool_prompt_examples(text: str) -> str:
    replacements = {
        "[tool_call: ${ToolNames.GLOB} for path 'tests/test_auth.py']": "[tool_call: ${ToolNames.GLOB} for pattern 'tests/test_auth.py']",
        "[tool_call: ${ToolNames.READ_FILE} for path '": "[tool_call: ${ToolNames.READ_FILE} for file_path '",
        "[tool_call: ${ToolNames.WRITE_FILE} for path '": "[tool_call: ${ToolNames.WRITE_FILE} for file_path '",
        "[tool_call: ${ToolNames.EDIT} for path 'src/auth.py' replacing old content with new content]": "[tool_call: ${ToolNames.EDIT} for file_path '/path/to/project/src/auth.py' replacing old_string with new_string]",
        "<function=${ToolNames.GLOB}>\n<parameter=path>\ntests/test_auth.py\n</parameter>": "<function=${ToolNames.GLOB}>\n<parameter=pattern>\ntests/test_auth.py\n</parameter>",
        "<function=${ToolNames.READ_FILE}>\n<parameter=path>": "<function=${ToolNames.READ_FILE}>\n<parameter=file_path>",
        '<function=${ToolNames.EDIT}>\n<parameter=path>\nsrc/auth.py\n</parameter>': '<function=${ToolNames.EDIT}>\n<parameter=file_path>\n/path/to/project/src/auth.py\n</parameter>',
        "<function=${ToolNames.WRITE_FILE}>\n<parameter=path>\n/path/to/someFile.test.ts\n</parameter>\n</function>": "<function=${ToolNames.WRITE_FILE}>\n<parameter=file_path>\n/path/to/someFile.test.ts\n</parameter>\n<parameter=content>\n(test file content)\n</parameter>\n</function>",
        "<parameter=old_content>": "<parameter=old_string>",
        "</parameter>\n<parameter=new_content>": "</parameter>\n<parameter=new_string>",
        '{"name": "${ToolNames.READ_FILE}", "arguments": {"path":': '{"name": "${ToolNames.READ_FILE}", "arguments": {"file_path":',
        '{"name": "${ToolNames.GLOB}", "arguments": {"path": "tests/test_auth.py"}}': '{"name": "${ToolNames.GLOB}", "arguments": {"pattern": "tests/test_auth.py"}}',
        '{"name": "${ToolNames.EDIT}", "arguments": {"path": "src/auth.py", "old_content": "(old code content)", "new_content": "(new code content)"}}': '{"name": "${ToolNames.EDIT}", "arguments": {"file_path": "/path/to/project/src/auth.py", "old_string": "(exact old code content)", "new_string": "(exact new code content)"}}',
        '{"name": "${ToolNames.WRITE_FILE}", "arguments": {"path": "/path/to/someFile.test.ts"}}': '{"name": "${ToolNames.WRITE_FILE}", "arguments": {"file_path": "/path/to/someFile.test.ts", "content": "(test file content)"}}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _patch_edit_tool_description(text: str) -> str:
    replacements = {
        "This tool requires providing significant context around the change to ensure precise targeting. Always use the ${ReadFileTool.Name} tool to examine the file's current content before attempting a text replacement.": "This tool requires the smallest exact current span that uniquely identifies the intended change. Always use the ${ReadFileTool.Name} tool in the current session to examine the file's current content before attempting a text replacement. Prompt-attached file content, including @file references, does not satisfy this tool's read gate.",
        "This tool requires the smallest exact current span that uniquely identifies the intended change. Always use the ${ReadFileTool.Name} tool to examine the file's current content before attempting a text replacement.": "This tool requires the smallest exact current span that uniquely identifies the intended change. Always use the ${ReadFileTool.Name} tool in the current session to examine the file's current content before attempting a text replacement. Prompt-attached file content, including @file references, does not satisfy this tool's read gate.",
        "**Important:** If ANY of the above are not satisfied, the tool will fail. CRITICAL for `old_string`: Must uniquely identify the single instance to change. Include at least 3 lines of context BEFORE and AFTER the target text, matching whitespace and indentation precisely. If this string matches multiple locations, or does not match exactly, the tool will fail.": "**Important:** If ANY of the above are not satisfied, the tool will fail. CRITICAL for `old_string`: Must uniquely identify the single instance to change. Use the smallest exact current span that occurs once. For N-line deletion or replacement, prefer exactly those N current lines; add minimal surrounding context only when needed for uniqueness. If this string matches multiple locations, or does not match exactly, the tool will fail.",
        "The exact literal text to replace, preferably unescaped. For single replacements (default), include at least 3 lines of context BEFORE and AFTER the target text, matching whitespace and indentation precisely. If this string is not the exact literal text (i.e. you escaped it) or does not match exactly, the tool will fail.": "The exact literal text to replace, preferably unescaped. Use the smallest exact current span that occurs once. For N-line deletion or replacement, prefer exactly those N current lines; add minimal surrounding context only when needed for uniqueness. If this string is not the exact literal text (i.e. you escaped it) or does not match exactly, the tool will fail.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


KIWI_EDIT_WS_REPAIR_HELPER = r'''
function kiwiCollapseLineForMatch(value) {
  return normalizeBasicCharacters(value).replace(/\s+/g, "");
}
__name(kiwiCollapseLineForMatch, "kiwiCollapseLineForMatch");
function kiwiMergePreservedLines(oldLines, newLines, fileWindowLines) {
  const rows = oldLines.length;
  const cols = newLines.length;
  if (rows === 0 || cols === 0 || rows * cols > 400000) {
    return newLines.slice();
  }
  const width = cols + 1;
  const dp = new Int32Array((rows + 1) * width);
  for (let i = 1; i <= rows; i++) {
    for (let j = 1; j <= cols; j++) {
      dp[i * width + j] = oldLines[i - 1] === newLines[j - 1]
        ? dp[(i - 1) * width + (j - 1)] + 1
        : Math.max(dp[(i - 1) * width + j], dp[i * width + (j - 1)]);
    }
  }
  const merged = newLines.slice();
  let i = rows;
  let j = cols;
  while (i > 0 && j > 0) {
    if (oldLines[i - 1] === newLines[j - 1] && dp[i * width + j] === dp[(i - 1) * width + (j - 1)] + 1) {
      merged[j - 1] = fileWindowLines[i - 1];
      i -= 1;
      j -= 1;
    } else if (dp[(i - 1) * width + j] >= dp[i * width + (j - 1)]) {
      i -= 1;
    } else {
      j -= 1;
    }
  }
  return merged;
}
__name(kiwiMergePreservedLines, "kiwiMergePreservedLines");
function kiwiWhitespaceTolerantRepair(fileContent, oldString, newString) {
  if (fileContent === null || fileContent === void 0 || oldString === "" || fileContent.includes(oldString)) {
    return null;
  }
  const oldParts = kiwiSplitEditLines(oldString);
  const newParts = kiwiSplitEditLines(newString);
  if (oldParts.lines.length === 0) {
    return null;
  }
  const collapsedOld = oldParts.lines.map(kiwiCollapseLineForMatch);
  if (collapsedOld.join("").length < 8) {
    return null;
  }
  const fileLines = fileContent.split("\n");
  if (collapsedOld.length > fileLines.length) {
    return null;
  }
  const collapsedFile = fileLines.map(kiwiCollapseLineForMatch);
  let matchIndex = -1;
  let matchCount = 0;
  outer: for (let i = 0; i <= collapsedFile.length - collapsedOld.length; i++) {
    for (let p = 0; p < collapsedOld.length; p++) {
      if (collapsedFile[i + p] !== collapsedOld[p]) {
        continue outer;
      }
    }
    matchCount += 1;
    if (matchCount > 1) {
      return null;
    }
    matchIndex = i;
  }
  if (matchCount !== 1) {
    return null;
  }
  const windowLines = fileLines.slice(matchIndex, matchIndex + collapsedOld.length);
  const canIncludeTrailing = matchIndex + collapsedOld.length < fileLines.length;
  const includeTrailing = oldParts.trailingNewline && canIncludeTrailing;
  const removedTrailing = oldParts.trailingNewline && !canIncludeTrailing;
  const windowSlice = kiwiJoinEditLines(windowLines, includeTrailing);
  if (windowSlice === "" || countOccurrences(fileContent, windowSlice) !== 1) {
    return null;
  }
  const mergedNewLines = kiwiMergePreservedLines(oldParts.lines, newParts.lines, windowLines);
  const repairedNew = kiwiJoinEditLines(mergedNewLines, newParts.trailingNewline && !removedTrailing);
  return { oldString: windowSlice, newString: repairedNew };
}
__name(kiwiWhitespaceTolerantRepair, "kiwiWhitespaceTolerantRepair");'''

KIWI_EDIT_SPAN_INSERT_V1 = """      const kiwiSafeSpan = kiwiDeriveSafeEditSpan(currentContent, finalOldString, finalNewString);
      if (kiwiSafeSpan !== null) {
        finalOldString = kiwiSafeSpan.oldString;
        finalNewString = kiwiSafeSpan.newString;
      }
      occurrences = countOccurrences(currentContent, finalOldString);"""

KIWI_EDIT_SPAN_INSERT_V2 = """      let kiwiSafeSpan = kiwiDeriveSafeEditSpan(currentContent, finalOldString, finalNewString);
      if (kiwiSafeSpan === null) {
        kiwiSafeSpan = kiwiWhitespaceTolerantRepair(currentContent, finalOldString, finalNewString);
      }
      if (kiwiSafeSpan !== null) {
        finalOldString = kiwiSafeSpan.oldString;
        finalNewString = kiwiSafeSpan.newString;
      }
      occurrences = countOccurrences(currentContent, finalOldString);"""


def _patch_edit_tool_span_repair(text: str) -> str:
    if "kiwiDeriveSafeEditSpan" in text:
        if "kiwiWhitespaceTolerantRepair" not in text:
            text = text.replace(
                '__name(kiwiDeriveSafeEditSpan, "kiwiDeriveSafeEditSpan");',
                '__name(kiwiDeriveSafeEditSpan, "kiwiDeriveSafeEditSpan");' + KIWI_EDIT_WS_REPAIR_HELPER,
                1,
            )
            text = text.replace(KIWI_EDIT_SPAN_INSERT_V1, KIWI_EDIT_SPAN_INSERT_V2, 1)
        return text
    helper_anchor = '__name(maybeAugmentOldStringForDeletion, "maybeAugmentOldStringForDeletion");'
    helper = r'''
function kiwiSplitEditLines(text) {
  const lines = text.split("\n");
  const trailingNewline = text.endsWith("\n");
  if (trailingNewline && lines.at(-1) === "") {
    lines.pop();
  }
  return { lines, trailingNewline };
}
__name(kiwiSplitEditLines, "kiwiSplitEditLines");
function kiwiJoinEditLines(lines, includeTrailingNewline) {
  if (lines.length === 0) {
    return "";
  }
  const joined = lines.join("\n");
  return includeTrailingNewline ? `${joined}
` : joined;
}
__name(kiwiJoinEditLines, "kiwiJoinEditLines");
function kiwiCommonPrefixLineCount(left, right) {
  const limit = Math.min(left.length, right.length);
  let count = 0;
  while (count < limit && left[count] === right[count]) {
    count++;
  }
  return count;
}
__name(kiwiCommonPrefixLineCount, "kiwiCommonPrefixLineCount");
function kiwiCommonSuffixLineCount(left, right, prefixCount) {
  const limit = Math.min(left.length, right.length) - prefixCount;
  let count = 0;
  while (count < limit && left[left.length - 1 - count] === right[right.length - 1 - count]) {
    count++;
  }
  return count;
}
__name(kiwiCommonSuffixLineCount, "kiwiCommonSuffixLineCount");
function kiwiDeriveSafeEditSpan(fileContent, oldString, newString) {
  if (fileContent === null || oldString === "" || fileContent.includes(oldString)) {
    return null;
  }
  const oldParts = kiwiSplitEditLines(oldString);
  const newParts = kiwiSplitEditLines(newString);
  const prefixCount = kiwiCommonPrefixLineCount(oldParts.lines, newParts.lines);
  const suffixCount = kiwiCommonSuffixLineCount(oldParts.lines, newParts.lines, prefixCount);
  const oldCoreLines = oldParts.lines.slice(prefixCount, oldParts.lines.length - suffixCount);
  const newCoreLines = newParts.lines.slice(prefixCount, newParts.lines.length - suffixCount);
  if (oldCoreLines.length === 0 || oldCoreLines.every((line) => normalizeBasicCharacters(line).trim() === "")) {
    return null;
  }
  const oldCoreHasFollowingLine = prefixCount + oldCoreLines.length < oldParts.lines.length || oldParts.trailingNewline;
  const newCoreHasFollowingLine = prefixCount + newCoreLines.length < newParts.lines.length || newParts.trailingNewline;
  const oldCore = kiwiJoinEditLines(oldCoreLines, oldCoreHasFollowingLine);
  const newCore = kiwiJoinEditLines(newCoreLines, newCoreLines.length > 0 && newCoreHasFollowingLine);
  if (normalizeBasicCharacters(oldCore).trim().length < 4) {
    return null;
  }
  const canonicalOld = findMatchedSlice(fileContent, oldCore);
  if (canonicalOld === null) {
    return null;
  }
  if (countOccurrences(fileContent, canonicalOld.slice) !== 1) {
    return null;
  }
  return {
    oldString: canonicalOld.slice,
    newString: adjustNewStringForTrailingLine(newCore, canonicalOld.removedTrailingFinalEmptyLine)
  };
}
__name(kiwiDeriveSafeEditSpan, "kiwiDeriveSafeEditSpan");
function kiwiCollapseLineForMatch(value) {
  return normalizeBasicCharacters(value).replace(/\s+/g, "");
}
__name(kiwiCollapseLineForMatch, "kiwiCollapseLineForMatch");
function kiwiMergePreservedLines(oldLines, newLines, fileWindowLines) {
  const rows = oldLines.length;
  const cols = newLines.length;
  if (rows === 0 || cols === 0 || rows * cols > 400000) {
    return newLines.slice();
  }
  const width = cols + 1;
  const dp = new Int32Array((rows + 1) * width);
  for (let i = 1; i <= rows; i++) {
    for (let j = 1; j <= cols; j++) {
      dp[i * width + j] = oldLines[i - 1] === newLines[j - 1]
        ? dp[(i - 1) * width + (j - 1)] + 1
        : Math.max(dp[(i - 1) * width + j], dp[i * width + (j - 1)]);
    }
  }
  const merged = newLines.slice();
  let i = rows;
  let j = cols;
  while (i > 0 && j > 0) {
    if (oldLines[i - 1] === newLines[j - 1] && dp[i * width + j] === dp[(i - 1) * width + (j - 1)] + 1) {
      merged[j - 1] = fileWindowLines[i - 1];
      i -= 1;
      j -= 1;
    } else if (dp[(i - 1) * width + j] >= dp[i * width + (j - 1)]) {
      i -= 1;
    } else {
      j -= 1;
    }
  }
  return merged;
}
__name(kiwiMergePreservedLines, "kiwiMergePreservedLines");
function kiwiWhitespaceTolerantRepair(fileContent, oldString, newString) {
  if (fileContent === null || fileContent === void 0 || oldString === "" || fileContent.includes(oldString)) {
    return null;
  }
  const oldParts = kiwiSplitEditLines(oldString);
  const newParts = kiwiSplitEditLines(newString);
  if (oldParts.lines.length === 0) {
    return null;
  }
  const collapsedOld = oldParts.lines.map(kiwiCollapseLineForMatch);
  if (collapsedOld.join("").length < 8) {
    return null;
  }
  const fileLines = fileContent.split("\n");
  if (collapsedOld.length > fileLines.length) {
    return null;
  }
  const collapsedFile = fileLines.map(kiwiCollapseLineForMatch);
  let matchIndex = -1;
  let matchCount = 0;
  outer: for (let i = 0; i <= collapsedFile.length - collapsedOld.length; i++) {
    for (let p = 0; p < collapsedOld.length; p++) {
      if (collapsedFile[i + p] !== collapsedOld[p]) {
        continue outer;
      }
    }
    matchCount += 1;
    if (matchCount > 1) {
      return null;
    }
    matchIndex = i;
  }
  if (matchCount !== 1) {
    return null;
  }
  const windowLines = fileLines.slice(matchIndex, matchIndex + collapsedOld.length);
  const canIncludeTrailing = matchIndex + collapsedOld.length < fileLines.length;
  const includeTrailing = oldParts.trailingNewline && canIncludeTrailing;
  const removedTrailing = oldParts.trailingNewline && !canIncludeTrailing;
  const windowSlice = kiwiJoinEditLines(windowLines, includeTrailing);
  if (windowSlice === "" || countOccurrences(fileContent, windowSlice) !== 1) {
    return null;
  }
  const mergedNewLines = kiwiMergePreservedLines(oldParts.lines, newParts.lines, windowLines);
  const repairedNew = kiwiJoinEditLines(mergedNewLines, newParts.trailingNewline && !removedTrailing);
  return { oldString: windowSlice, newString: repairedNew };
}
__name(kiwiWhitespaceTolerantRepair, "kiwiWhitespaceTolerantRepair");'''
    if helper_anchor in text:
        text = text.replace(helper_anchor, f"{helper_anchor}\n{helper}", 1)
    text = text.replace(
        "      occurrences = countOccurrences(currentContent, finalOldString);",
        """      let kiwiSafeSpan = kiwiDeriveSafeEditSpan(currentContent, finalOldString, finalNewString);
      if (kiwiSafeSpan === null) {
        kiwiSafeSpan = kiwiWhitespaceTolerantRepair(currentContent, finalOldString, finalNewString);
      }
      if (kiwiSafeSpan !== null) {
        finalOldString = kiwiSafeSpan.oldString;
        finalNewString = kiwiSafeSpan.newString;
      }
      occurrences = countOccurrences(currentContent, finalOldString);""",
        1,
    )
    return text


def _patch_console_paste_guard(text: str) -> str:
    """Let KIWI console submit Enter bypass Qwen's Windows paste-enter guard.

    Qwen 0.17 swallows the return key while `recentPasteTime` is set (500ms after
    each paste event) when `pasteWorkaround` is on (always true on win32). KIWI
    sends bracketed-paste text followed by a deliberate submit CR, so under
    `KIWI_ULTRAWORK_CONSOLE=1` that guard only breaks command-bar submits.
    """
    return text.replace(
        """        if (buffer.text.trim()) {
          if (pasteWorkaround && recentPasteTime !== null) {
            return true;
          }""",
        """        if (buffer.text.trim()) {
          if (pasteWorkaround && recentPasteTime !== null && process.env["KIWI_ULTRAWORK_CONSOLE"] !== "1") {
            return true;
          }""",
        1,
    )


_KIWI_PATH_RECOVERY_HELPER = r'''async function kiwiSuggestNearbyPath(requestedPath) {
  try {
    const fsp = (await import("node:fs")).promises;
    const pathMod = await import("node:path");
    const normalizeName = (value) => String(value || "").normalize("NFC").replace(/\s+/g, "").toLowerCase();
    const raw = String(requestedPath || "").trim();
    if (!raw) return null;
    const parsedRoot = pathMod.parse(raw).root;
    if (!parsedRoot) return null;
    const segments = raw.slice(parsedRoot.length).split(/[\\/]+/).filter(Boolean);
    if (segments.length === 0 || segments.length > 24) return null;
    let resolved = parsedRoot;
    let corrected = false;
    for (const segment of segments) {
      const direct = pathMod.join(resolved, segment);
      let directExists = false;
      try {
        await fsp.stat(direct);
        directExists = true;
      } catch {}
      if (directExists) {
        resolved = direct;
        continue;
      }
      let entries;
      try {
        entries = await fsp.readdir(resolved);
      } catch {
        return null;
      }
      const wanted = normalizeName(segment);
      if (!wanted) return null;
      const matches = entries.filter((entry) => normalizeName(entry) === wanted);
      if (matches.length !== 1) return null;
      resolved = pathMod.join(resolved, matches[0]);
      corrected = true;
    }
    if (!corrected) return null;
    await fsp.stat(resolved);
    return resolved;
  } catch {
    return null;
  }
}
__name(kiwiSuggestNearbyPath, "kiwiSuggestNearbyPath");'''

_KIWI_READ_NOT_FOUND_OLD = """      if (isNodeError(error) && error.code === "ENOENT") {
        return {
          llmContent: "Could not read file because no file was found at the specified path.",
          returnDisplay: "File not found.",
          error: `File not found: ${filePath}`,
          errorType: "file_not_found" /* FILE_NOT_FOUND */
        };
      }"""

_KIWI_READ_NOT_FOUND_PREV = """      if (isNodeError(error) && error.code === "ENOENT") {
        const kiwiSuggestedPath = await kiwiSuggestNearbyPath(filePath);
        const kiwiPathHint = kiwiSuggestedPath
          ? ` KIWI path recovery: a nearly identical path exists at "${kiwiSuggestedPath}". The requested path looks like a re-typed file name (for example, extra spaces inserted around "-" or "_" in Korean file names). Call read_file again with file_path set to exactly "${kiwiSuggestedPath}", copied character-for-character, and reuse that exact path in later edit/write_file calls.`
          : "";
        return {
          llmContent: `Could not read file because no file was found at the specified path.${kiwiPathHint}`,
          returnDisplay: kiwiSuggestedPath ? `File not found. Did you mean: ${kiwiSuggestedPath}` : "File not found.",
          error: `File not found: ${filePath}`,
          errorType: "file_not_found" /* FILE_NOT_FOUND */
        };
      }"""

_KIWI_READ_NOT_FOUND_NEW = """      if (isNodeError(error) && error.code === "ENOENT") {
        const kiwiSuggestedPath = await kiwiSuggestNearbyPath(filePath);
        const kiwiPathHint = kiwiSuggestedPath
          ? ` KIWI path recovery: a nearly identical path exists at "${kiwiSuggestedPath}". The requested path looks like a re-typed file name (for example, extra spaces inserted around "-" or "_" in Korean file names). Call read_file again with file_path set to exactly "${kiwiSuggestedPath}", copied character-for-character, and reuse that exact path in later edit/write_file calls.`
          : " Do not retry the same path. Run list_directory on the parent directory (or glob it), then copy the exact file name character-for-character from that output.";
        return {
          llmContent: `Could not read file because no file was found at the specified path.${kiwiPathHint}`,
          returnDisplay: kiwiSuggestedPath ? `File not found. Did you mean: ${kiwiSuggestedPath}` : "File not found.",
          error: `File not found: ${filePath}`,
          errorType: "file_not_found" /* FILE_NOT_FOUND */
        };
      }"""

_KIWI_EDIT_NOT_FOUND_OLD = """    } else if (!fileExists2) {
      error = {
        display: `File not found. Cannot apply edit. Use an empty old_string to create a new file.`,
        raw: `File not found: ${params.file_path}`,
        type: "file_not_found" /* FILE_NOT_FOUND */
      };
    }"""

_KIWI_EDIT_NOT_FOUND_NEW = """    } else if (!fileExists2) {
      const kiwiSuggestedPath = await kiwiSuggestNearbyPath(params.file_path);
      error = {
        display: kiwiSuggestedPath
          ? `File not found. Did you mean: ${kiwiSuggestedPath}`
          : `File not found. Cannot apply edit. Use an empty old_string to create a new file.`,
        raw: kiwiSuggestedPath
          ? `File not found: ${params.file_path}. KIWI path recovery: a nearly identical path exists at "${kiwiSuggestedPath}". The requested path looks like a re-typed file name (for example, extra spaces inserted around "-" or "_" in Korean file names). Call read_file with exactly "${kiwiSuggestedPath}" first, then retry this edit with that exact file_path.`
          : `File not found: ${params.file_path}`,
        type: "file_not_found" /* FILE_NOT_FOUND */
      };
    }"""


def _patch_file_path_recovery_hints(text: str) -> str:
    """Suggest the real on-disk path when read_file/edit miss a re-typed file name.

    Qwen3.5 sometimes re-types Korean file names with extra spaces around
    hyphens/underscores (or decomposed Hangul), so the literal path no longer
    exists. Instead of a bare file_not_found, resolve each missing path segment
    against the parent directory with whitespace/NFC-insensitive matching and
    return a single-candidate `Did you mean` hint the model can copy verbatim.
    """
    needs_read = _KIWI_READ_NOT_FOUND_OLD in text
    needs_edit = _KIWI_EDIT_NOT_FOUND_OLD in text
    needs_read_upgrade = _KIWI_READ_NOT_FOUND_PREV in text
    if not needs_read and not needs_edit and not needs_read_upgrade:
        return text
    if "kiwiSuggestNearbyPath" not in text:
        if needs_read:
            text = text.replace(
                "async function processSingleFileContent(filePath, config, offset, limit, pages) {",
                _KIWI_PATH_RECOVERY_HELPER + "\nasync function processSingleFileContent(filePath, config, offset, limit, pages) {",
                1,
            )
        else:
            text = text.replace(
                "var EditToolInvocation = class {",
                _KIWI_PATH_RECOVERY_HELPER + "\nvar EditToolInvocation = class {",
                1,
            )
    if "kiwiSuggestNearbyPath" not in text:
        return text
    text = text.replace(_KIWI_READ_NOT_FOUND_OLD, _KIWI_READ_NOT_FOUND_NEW, 1)
    text = text.replace(_KIWI_READ_NOT_FOUND_PREV, _KIWI_READ_NOT_FOUND_NEW, 1)
    text = text.replace(_KIWI_EDIT_NOT_FOUND_OLD, _KIWI_EDIT_NOT_FOUND_NEW, 1)
    return text


def _patch_edit_tool_failure_guidance(text: str) -> str:
    text = _patch_edit_tool_description(text)
    text = _patch_edit_tool_span_repair(text)
    text = _patch_file_path_recovery_hints(text)
    if "KIWI edit recovery protocol" in text:
        if "@file references or prompt-attached file content do not satisfy the edit read gate." not in text:
            text = text.replace(
                "KIWI edit recovery protocol:",
                "@file references or prompt-attached file content do not satisfy the edit read gate. KIWI edit recovery protocol:",
                1,
            )
        return text
    old = (
        "raw: `Failed to edit, 0 occurrences found for old_string in ${params.file_path}. "
        "No edits made. The exact text in old_string was not found. Ensure you're not escaping content incorrectly "
        "and check whitespace, indentation, and context. Use ${ReadFileTool.Name} tool to verify.`,"
    )
    new = (
        "raw: `Failed to edit, 0 occurrences found for old_string in ${params.file_path}. "
        "No edits made. The exact text in old_string was not found. Ensure you're not escaping content incorrectly "
        "and check whitespace, indentation, and context. Use ${ReadFileTool.Name} tool to verify. "
        "@file references or prompt-attached file content do not satisfy the edit read gate. "
        "KIWI edit recovery protocol: safe N-line span repair was attempted first; do not retry the same or a larger old_string; immediately read the target range, "
        "copy the smallest exact current N-line span from that latest read output, "
        "and stop after two failures on the same file instead of using PowerShell regex/Set-Content or full-file rewrites.`,"
    )
    return text.replace(old, new)


def _patch_write_runtime_config_custom_agents(text: str) -> str:
    text = text.replace(
        """    tools: {
      approvalMode: "default",
      sandbox: false
    },""",
        """    tools: {
      approvalMode: "yolo",
      sandbox: false
    },""",
    )
    if "compactMode: true" not in text or "useTerminalBuffer:" not in text:
        text = text.replace(
            """    telemetry: {
      enabled: false
    },
    tools: {""",
            """    telemetry: {
      enabled: false
    },
    ui: {
      compactMode: true,
      useTerminalBuffer: false
    },
    tools: {""",
            1,
        )
    text = text.replace("useTerminalBuffer: true", "useTerminalBuffer: false")
    marker = "copyBundledKiwiAgents"
    if marker in text:
        return text
    helper_anchor = "function removeFileIfExists(filePath) {\n"
    helper = r'''
function copyBundledKiwiAgents(extensionDir) {
  const sourceDir = path.join(root, "extensions", "ultrawork", "agents");
  const targetDir = path.join(extensionDir, "agents");
  if (!fs.existsSync(sourceDir)) return;
  fs.mkdirSync(targetDir, { recursive: true });
  for (const name of fs.readdirSync(sourceDir)) {
    if (!name.endsWith(".md") || name.toLowerCase() === "readme.md") continue;
    const source = path.join(sourceDir, name);
    const target = path.join(targetDir, name);
    if (path.resolve(source) === path.resolve(target)) continue;
    fs.copyFileSync(source, target);
  }
}

'''
    if helper_anchor in text:
        text = text.replace(helper_anchor, helper + helper_anchor, 1)
    call_anchor = "  console.log(`[OK] Qwen Code runtime config generated`);"
    if call_anchor in text:
        text = text.replace(call_anchor, "  copyBundledKiwiAgents(extensionDir);\n\n" + call_anchor, 1)
    return text


def _remove_generated_legacy_agents(path: Path) -> None:
    for agents_dir in _runtime_agent_dirs(path):
        for name in [
            "-".join(["coder", "next"]) + ".md",
        ]:
            try:
                (agents_dir / name).unlink(missing_ok=True)
            except OSError:
                continue


def _install_kiwi_ultrawork_agents(path: Path) -> None:
    sources: dict[str, Path] = {}
    for seed_dir in [
        path / "portable-user" / ".qwen" / "extensions" / "ultrawork" / "agents",
        path / "extensions" / "ultrawork" / "agents",
    ]:
        if not seed_dir.exists():
            continue
        for item in seed_dir.glob("*.md"):
            if item.name != "README.md":
                sources.setdefault(item.name, item)
    if AGENT_PROMPTS_DIR.exists():
        for item in AGENT_PROMPTS_DIR.glob("*.md"):
            if item.name != "README.md":
                sources[item.name] = item
    if not sources:
        return
    for agents_dir in _runtime_agent_dirs(path):
        try:
            agents_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        for source in sources.values():
            try:
                target = agents_dir / source.name
                content = source.read_text(encoding="utf-8", errors="replace")
                if target.exists() and target.read_text(encoding="utf-8", errors="replace") == content:
                    continue
                target.write_text(content, encoding="utf-8")
            except OSError:
                continue


def _install_kiwi_fast_system_prompts(path: Path) -> None:
    if not FAST_SYSTEM_PROMPTS_DIR.exists():
        return
    prompts = [item for item in FAST_SYSTEM_PROMPTS_DIR.glob("*.md")]
    if not prompts:
        return
    for extension_dir in _runtime_fast_system_prompt_dirs(path):
        try:
            extension_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        for source in prompts:
            try:
                target = extension_dir / source.name
                content = source.read_text(encoding="utf-8", errors="replace")
                if target.exists() and target.read_text(encoding="utf-8", errors="replace") == content:
                    continue
                target.write_text(content, encoding="utf-8")
            except OSError:
                continue


def _install_kiwi_ultrawork_policy(path: Path) -> None:
    if not RUNTIME_POLICY_SOURCE.exists():
        return
    try:
        policy = RUNTIME_POLICY_SOURCE.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return
    if not policy:
        return
    block = f"{POLICY_BLOCK_START}\n{policy}\n{POLICY_BLOCK_END}"
    manifest = {
        "name": "ultrawork",
        "version": "1.0.0",
        "description": "Prompt-triggered KIWI team orchestration mode for Qwen Code.",
        "agents": "agents",
        "hooks": "hooks/hooks.json",
    }
    for extension_dir in _runtime_extension_dirs(path):
        try:
            extension_dir.mkdir(parents=True, exist_ok=True)
            (extension_dir / "qwen-extension.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (extension_dir / "KIWI_POLICY.md").write_text(policy + "\n", encoding="utf-8")
            qwen_path = extension_dir / "QWEN.md"
            current = qwen_path.read_text(encoding="utf-8", errors="replace") if qwen_path.exists() else "# Ultrawork\n"
            qwen_path.write_text(_upsert_policy_block(current, block), encoding="utf-8")
        except OSError:
            continue


def _install_kiwi_superpowers_extension(path: Path) -> None:
    if not SUPERPOWERS_SKILLS_DIR.exists():
        return
    skill_dirs = [item for item in SUPERPOWERS_SKILLS_DIR.iterdir() if (item / "SKILL.md").exists()]
    if not skill_dirs:
        return
    policy = ""
    if SUPERPOWERS_POLICY_SOURCE.exists():
        try:
            policy = SUPERPOWERS_POLICY_SOURCE.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            policy = ""
    manifest = {
        "name": "superpowers",
        "version": "1.0.0",
        "description": "KIWI superpowers work mode skills for Qwen Code.",
        "skills": "skills",
        "policy": "SUPERPOWERS_POLICY.md",
    }
    for extension_dir in _runtime_superpowers_extension_dirs(path):
        try:
            extension_dir.mkdir(parents=True, exist_ok=True)
            (extension_dir / "qwen-extension.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            if policy:
                (extension_dir / "SUPERPOWERS_POLICY.md").write_text(policy + "\n", encoding="utf-8")
                (extension_dir / "QWEN.md").write_text(policy + "\n", encoding="utf-8")
            skills_dir = extension_dir / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            for source in skill_dirs:
                target = skills_dir / source.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
        except OSError:
            continue
    for skills_dir in _runtime_qwen_skill_dirs(path):
        try:
            skills_dir.mkdir(parents=True, exist_ok=True)
            for source in skill_dirs:
                target = skills_dir / source.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
        except OSError:
            continue


def _upsert_policy_block(text: str, block: str) -> str:
    pattern = re.compile(
        rf"{re.escape(POLICY_BLOCK_START)}.*?{re.escape(POLICY_BLOCK_END)}",
        flags=re.DOTALL,
    )
    if pattern.search(text):
        return pattern.sub(block, text).rstrip() + "\n"
    return text.rstrip() + "\n\n" + block + "\n"


def _runtime_extension_dirs(path: Path) -> list[Path]:
    return [
        path / "portable-user" / ".qwen" / "extensions" / "ultrawork",
        path / "extensions" / "ultrawork",
    ]


def _runtime_agent_dirs(path: Path) -> list[Path]:
    return [
        *(extension_dir / "agents" for extension_dir in _runtime_extension_dirs(path)),
        path / "portable-user" / ".qwen" / "agents",
        path / "templates" / "project" / ".qwen" / "agents",
    ]


def _runtime_superpowers_extension_dirs(path: Path) -> list[Path]:
    return [
        path / "portable-user" / ".qwen" / "extensions" / "superpowers",
        path / "extensions" / "superpowers",
    ]


def _runtime_qwen_skill_dirs(path: Path) -> list[Path]:
    return [
        path / "portable-user" / ".qwen" / "skills",
        path / "templates" / "project" / ".qwen" / "skills",
    ]


def _runtime_fast_system_prompt_dirs(path: Path) -> list[Path]:
    return [
        path / "portable-user" / ".qwen" / "extensions" / "fast-system-prompts",
        path / "extensions" / "fast-system-prompts",
    ]


def _runtime_sort_key(path: Path) -> tuple[int, tuple[int, ...], float, str]:
    name = path.name.lower()
    version_match = re.search(r"(\d+(?:\.\d+)+)", name)
    version = tuple(int(part) for part in version_match.group(1).split(".")) if version_match else (0,)
    win11_score = 1 if "win11" in name else 0
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0
    return (win11_score, version, mtime, name)


def _command_to_exec(command: str) -> list[str]:
    path = Path(command)
    if path.is_dir() and (path / "run-qwen.cmd").exists():
        path = path / "run-qwen.cmd"
        command = str(path)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", command]
    return [command]
