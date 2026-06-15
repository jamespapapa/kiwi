from __future__ import annotations

import json
import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
EXPECTED_MODEL = "Qwen3.5-397B"
EXPECTED_QWEN_CODE_VERSION = "0.17.1"
EXPECTED_RUNTIME_NAME = "qwen-code-offline-win11-v0.17.1"
EXPECTED_STANDALONE_RUNTIME_DIR = r"D:\aiops\qwencode"
BUNDLE = ROOT / "build" / "offline" / "kiwi-offline-win11-py313.zip"
QWENCODE_BUNDLE = ROOT / "build" / "offline" / "qwencode-win11-v0.17.1.zip"
ZIP_ROOT = "kiwi"
QWENCODE_ZIP_ROOT = "qwencode"
CORE_AGENT_NAMES = [
    "architect-35",
    "coder-35",
    "debugger-35",
    "explorer-35",
    "planner-35",
    "reviewer-35",
    "tester-35",
]


def load_bundle_module():
    path = ROOT / "scripts" / "build-offline-bundle.py"
    spec = importlib.util.spec_from_file_location("build_offline_bundle_assert_qwen_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_zip_text(zf: zipfile.ZipFile, relative: str, root: str = ZIP_ROOT) -> str:
    return zf.read(f"{root}/{relative}").decode("utf-8", errors="replace")


def read_zip_json(zf: zipfile.ZipFile, relative: str, root: str = ZIP_ROOT) -> dict:
    return json.loads(read_zip_text(zf, relative, root=root))


def source_skill_names() -> list[str]:
    skills_dir = ROOT / "docs" / "superpowers-skills"
    return sorted(path.name for path in skills_dir.iterdir() if (path / "SKILL.md").exists())


def source_agent_names() -> list[str]:
    agents_dir = ROOT / "docs" / "ultrawork-agents"
    custom = [path.stem for path in agents_dir.glob("*.md") if path.name != "README.md"]
    return sorted(set(CORE_AGENT_NAMES + custom))


def assert_native_agent_frontmatter(text: str, label: str) -> None:
    assert text.startswith("---\n"), f"{label} missing YAML frontmatter"
    assert "\n---\n" in text[4:], f"{label} malformed YAML frontmatter"
    frontmatter = text.split("\n---\n", 1)[0]
    for required in [
        "name:",
        "description:",
        "model: openai:Qwen3.5-397B",
        "approvalMode: yolo",
        "tools:",
        "  - read_file",
        "  - grep_search",
        "  - glob",
        "  - list_directory",
    ]:
        assert required in frontmatter, f"{label} missing native Qwen agent frontmatter term: {required}"
    if any(agent in label for agent in ["coder-35", "-developer"]):
        for required in ["  - edit", "  - write_file", "  - run_shell_command"]:
            assert required in frontmatter, f"{label} implementation agent missing mutating tool: {required}"
    if "tester-35" in label:
        assert "  - run_shell_command" in frontmatter, f"{label} tester missing verification shell tool"
    assert "tools: read," not in frontmatter, f"{label} uses invalid string tools frontmatter"


def assert_team_log_contract(text: str, label: str) -> None:
    for required in [
        "FAST/lightwork has no size report",
        "`todo_write` tool",
        "do not claim a mode conflict",
        "`todo_write` tool is mandatory",
        "selectedTaskSizeFromPrompt(prompt)",
        "teamModeContext(trigger, prompt = \"\", input = {})",
        "function projectDocsKey(input)",
        "projectKnowledgeIndex(input)",
        "projectDocsRuntimeLine(input)",
        "superpowersSkillRuntimeLine(input)",
        "D:/aiops/docs/${projectDocsKey(input)}",
        "Never try project-relative docs/<project-key>/... or docs/kiwi/project-info/... paths",
        "invoke local superpowers with the built-in skill tool",
        'skill="kiwi-superpowers"',
        'skill="using-superpowers"',
    ]:
        assert required in text, f"{label} team-log contract missing: {required}"
    for forbidden in ["tool_search", "select:", "native skill lookup", "Qwen native skills", "native local Qwen skills"]:
        assert forbidden not in text, f"{label} should not expose local-skill lookup decoy token: {forbidden}"
    for stale in [
        "create a concise visible plan in Korean",
        "Kiwi가 티셔츠 사이징을 먼저 보고하고",
        "teamModeContext(trigger, prompt = \"\")",
        "inspect D:/aiops/docs/<project-key>/project-info and invoke",
        "D:/aiops/docs/<project-key>/knowledge first",
        "load or account for local Qwen skills",
        "load local superpowers skills through Qwen native skills",
    ]:
        assert stale not in text, f"{label} team-log contract still contains stale text: {stale}"


def assert_runtime_source() -> None:
    runtime = PARENT / "deliverables" / EXPECTED_RUNTIME_NAME
    assert runtime.exists(), f"missing runtime source: {runtime}"
    bundle = load_bundle_module()
    bundle.normalize_qwencode_runtime_layout(runtime)
    package = json.loads((runtime / "app" / "package.json").read_text(encoding="utf-8"))
    assert package["version"] == EXPECTED_QWEN_CODE_VERSION, package["version"]
    assert (runtime / "run-qwen.cmd").exists(), "runtime source missing run-qwen.cmd"
    assert (runtime / "qwen-init.cmd").exists(), "runtime source missing qwen-init.cmd"
    assert (runtime / "runtimes" / "node" / "node.exe").exists(), "runtime source missing bundled runtimes/node"
    assert (runtime / "runtimes" / "node" / "yarn.cmd").exists(), "runtime source missing bundled Yarn classic wrapper"
    assert (runtime / "runtimes" / "node" / "node_modules" / "yarn" / "bin" / "yarn.js").exists(), "runtime source missing Yarn classic package"
    yarn_cmd = (runtime / "runtimes" / "node" / "yarn.cmd").read_text(encoding="utf-8", errors="replace")
    assert "node_modules\\yarn\\bin\\yarn.js" in yarn_cmd, "runtime source yarn.cmd must bypass Corepack registry lookup"
    assert not (runtime / "node").exists(), "runtime source must not keep duplicate root node runtime"
    assert EXPECTED_MODEL in (runtime / "config" / "env.cmd").read_text(encoding="utf-8")
    run_qwen = (runtime / "run-qwen.cmd").read_text(encoding="utf-8", errors="replace")
    assert "KIWI forced no sandbox for Windows closed-network runtime" in run_qwen
    assert 'set "QWEN_SANDBOX=0"' in run_qwen
    assert "KIWI syncs bundled project skills and agents into existing qwen projects" in run_qwen
    assert "templates\\project\\.qwen\\skills" in run_qwen
    assert "templates\\project\\.qwen\\agents" in run_qwen
    assert "robocopy" in run_qwen
    assert "KIWI forced yolo approval for Windows closed-network runtime" not in run_qwen
    assert "--approval-mode yolo" not in run_qwen
    cli = (runtime / "app" / "cli.js").read_text(encoding="utf-8", errors="replace")
    assert "if (Array.isArray(value)) value = value[value.length - 1];" in cli
    assert 'if (typeof value !== "string") value = String(value ?? "");' in cli
    writer = (runtime / "scripts" / "write-runtime-config.js").read_text(encoding="utf-8")
    assert "modalities: { image: true }" in writer, "runtime writer missing image modality"
    assert "splitToolMedia: true" in writer, "runtime writer missing splitToolMedia"
    assert "compactMode: true" in writer, "runtime writer missing compactMode"
    assert "useTerminalBuffer: false" in writer, "runtime writer must disable virtual terminal buffer"
    init_script = (runtime / "scripts" / "qwen-init.ps1").read_text(encoding="utf-8", errors="replace")
    assert '".qwen\\skills"' in init_script and '".qwen\\agents"' in init_script
    assert 'Copy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"' in init_script
    assert 'Copy-TemplateDirectory ".qwen\\agents" ".qwen\\agents"' in init_script
    source_team_log = (runtime / "scripts" / "team-log-lib.js").read_text(encoding="utf-8", errors="replace")
    patched_team_log = bundle.patch_ultrawork_activation_message(bundle.patch_work_mode_state_script(source_team_log))
    assert_team_log_contract(patched_team_log, "runtime source patch result")
    for relative in [
        "portable-user/.qwen/settings.json",
        "templates/project/.qwen/settings.json",
    ]:
        settings = json.loads((runtime / relative).read_text(encoding="utf-8"))
        assert settings["tools"]["approvalMode"] == "yolo", f"runtime source {relative} approvalMode drift"
        assert "sandbox" not in settings["tools"], f"runtime source {relative} must not put boolean sandbox under tools"
        assert settings["ui"]["compactMode"] is True, f"runtime source {relative} compactMode drift"
        assert settings["ui"]["useTerminalBuffer"] is False, f"runtime source {relative} terminal buffer drift"
    modality_files = [
        path
        for path in (runtime / "app").rglob("*.js")
        if "qwen3\\.5-397b" in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert modality_files, "runtime source missing Qwen3.5-397B modality fallback patch"
    for skill in source_skill_names():
        skill_path = runtime / "portable-user" / ".qwen" / "extensions" / "superpowers" / "skills" / skill / "SKILL.md"
        assert skill_path.exists(), f"runtime source missing superpowers skill: {skill}"
        text = skill_path.read_text(encoding="utf-8", errors="replace")
        assert "## Qwen tool mapping" in text, f"runtime skill missing tool mapping: {skill}"
        assert "D:/aiops/docs/<project-key>/project-info" in text, f"runtime skill missing Project Info contract: {skill}"
        assert "D:/aiops/docs/<project-key>/knowledge" in text, f"runtime skill missing central knowledge contract: {skill}"
    for agent in source_agent_names():
        for relative in [
            f"portable-user/.qwen/extensions/ultrawork/agents/{agent}.md",
            f"extensions/ultrawork/agents/{agent}.md",
            f"portable-user/.qwen/agents/{agent}.md",
            f"templates/project/.qwen/agents/{agent}.md",
        ]:
            assert (runtime / relative).exists(), f"runtime source missing Qwen agent path: {relative}"
            assert_native_agent_frontmatter(
                (runtime / relative).read_text(encoding="utf-8", errors="replace"),
                f"runtime source {relative}",
            )
    for manifest in [
        "portable-user/.qwen/extensions/ultrawork/qwen-extension.json",
        "extensions/ultrawork/qwen-extension.json",
    ]:
        data = json.loads((runtime / manifest).read_text(encoding="utf-8"))
        assert data["agents"] == "agents", f"runtime ultrawork manifest missing agents: {manifest}"


def assert_kiwi_initialize_refreshes_project_skills() -> None:
    main_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8", errors="replace")
    for required in [
        "_project_superpowers_skills_stale",
        "_project_qwen_assets_stale",
        'root / ".qwen" / "agents"',
        'required = ["kiwi-superpowers", "using-superpowers"]',
        'root / ".qwen" / "skills"',
        'runtime / "templates" / "project" / ".qwen" / "skills"',
        'runtime / "templates" / "project" / ".qwen" / "agents"',
        "existing and not runtime_mismatch and not qwen_assets_stale",
        '"qwen_assets_refreshed"',
        '"project_skills_status"',
        '"project_agents_status"',
    ]:
        assert required in main_source, f"KIWI initialize does not refresh project superpowers skills: {required}"


def assert_bundle_zip() -> None:
    assert BUNDLE.exists(), f"missing offline bundle: {BUNDLE}"
    expected_skills = source_skill_names()
    assert expected_skills, "missing local superpowers skills"

    with zipfile.ZipFile(BUNDLE) as zf:
        names = set(zf.namelist())
        manifest = read_zip_json(zf, "bundle-manifest.json")
        assert manifest["name"] == ZIP_ROOT, manifest.get("name")
        assert manifest["zipName"] == BUNDLE.name, manifest.get("zipName")
        assert manifest["pairedQwencodeZip"] == QWENCODE_BUNDLE.name, manifest.get("pairedQwencodeZip")
        assert manifest["qwenRuntime"] == EXPECTED_RUNTIME_NAME, manifest["qwenRuntime"]
        assert manifest["qwenCodeVersion"] == EXPECTED_QWEN_CODE_VERSION, manifest.get("qwenCodeVersion")
        assert manifest["orchestratorModel"] == EXPECTED_MODEL, manifest["orchestratorModel"]
        assert manifest["orchestratorModalities"] == {"image": True}, manifest.get("orchestratorModalities")
        assert manifest["orchestratorSplitToolMedia"] is True, manifest.get("orchestratorSplitToolMedia")
        assert manifest["standaloneQwencodeRuntimeDir"] == EXPECTED_STANDALONE_RUNTIME_DIR
        assert manifest["runtimeBundled"] is False, manifest.get("runtimeBundled")
        assert manifest["externalQwencodeRuntimeRequired"] is True, manifest.get("externalQwencodeRuntimeRequired")
        assert manifest["runtimePriority"] == [EXPECTED_STANDALONE_RUNTIME_DIR, "KIWI_QWENCODE_RUNTIME_DIR"]
        assert manifest["superpowersSkills"] == expected_skills, "manifest skill list drift"

        forbidden_prefix = f"{ZIP_ROOT}/vendor/qwen-runtime/"
        bundled_runtime_files = [name for name in names if name.startswith(forbidden_prefix)]
        assert not bundled_runtime_files, f"KIWI zip must not contain duplicated qwen runtime: {bundled_runtime_files[:3]}"

        check_runtime = read_zip_text(zf, "check-qwencode-runtime.cmd")
        for term in [
            EXPECTED_STANDALONE_RUNTIME_DIR,
            "SetEnvironmentVariable('KIWI_QWENCODE_RUNTIME_DIR'",
            "SetEnvironmentVariable('Path'",
            "qwen-init.cmd",
            "run-qwen.cmd",
            "runtimes\\node\\npm.cmd",
            "runtimes\\node\\yarn.cmd",
        ]:
            assert term in check_runtime, f"external runtime checker missing: {term}"

        install = read_zip_text(zf, "install-offline.cmd")
        for term in [
            "check-qwencode-runtime.cmd",
            "%RUNTIME%\\runtimes\\node\\npm.cmd",
            "KIWI offline install complete",
        ]:
            assert term in install, f"install script missing external runtime use: {term}"


def assert_qwencode_zip() -> None:
    assert QWENCODE_BUNDLE.exists(), f"missing qwencode bundle: {QWENCODE_BUNDLE}"
    expected_skills = source_skill_names()

    with zipfile.ZipFile(QWENCODE_BUNDLE) as zf:
        names = set(zf.namelist())
        package = read_zip_json(zf, "app/package.json", root=QWENCODE_ZIP_ROOT)
        assert package["version"] == EXPECTED_QWEN_CODE_VERSION, package["version"]
        for relative in [
            "run-qwen.cmd",
            "qwen-init.cmd",
            "qwen.cmd",
            "qwencode.cmd",
            "install-path.cmd",
            "README_QWENCODE.md",
            "runtimes/node/node.exe",
            "runtimes/node/npm.cmd",
            "runtimes/node/yarn.cmd",
            "runtimes/node/node_modules/yarn/bin/yarn.js",
        ]:
            assert f"{QWENCODE_ZIP_ROOT}/{relative}" in names, f"qwencode zip missing: {relative}"
        yarn_cmd = read_zip_text(zf, "runtimes/node/yarn.cmd", root=QWENCODE_ZIP_ROOT)
        assert "node_modules\\yarn\\bin\\yarn.js" in yarn_cmd, "qwencode zip yarn.cmd must use bundled Yarn classic"
        assert not any(name.startswith(f"{QWENCODE_ZIP_ROOT}/node/") for name in names), "qwencode zip must not include duplicate root node runtime"

        assert not any(
            name.startswith(f"{QWENCODE_ZIP_ROOT}/portable-runtime/") for name in names
        ), "qwencode zip should not include stale portable-runtime logs"

        install_path = read_zip_text(zf, "install-path.cmd", root=QWENCODE_ZIP_ROOT)
        for term in [
            "SetEnvironmentVariable('KIWI_QWENCODE_RUNTIME_DIR'",
            "SetEnvironmentVariable('Path'",
            "qwen-init.cmd",
            "run-qwen.cmd",
            "runtimes\\node\\npm.cmd",
            "runtimes\\node\\yarn.cmd",
        ]:
            assert term in install_path, f"install-path missing: {term}"

        env_cmd = read_zip_text(zf, "config/env.cmd", root=QWENCODE_ZIP_ROOT)
        template_env = read_zip_text(zf, "templates/project/.qwen/env.cmd", root=QWENCODE_ZIP_ROOT)
        assert f'QWEN35_MODEL={EXPECTED_MODEL}' in env_cmd, "global env model drift"
        assert f'QWEN35_MODEL={EXPECTED_MODEL}' in template_env, "project template env model drift"
        for label, text in {"global env": env_cmd, "template env": template_env}.items():
            assert 'QWEN_SANDBOX=0' in text, f"{label} must disable Qwen sandbox for Windows closed-network runtime"

        run_qwen = read_zip_text(zf, "run-qwen.cmd", root=QWENCODE_ZIP_ROOT)
        assert "KIWI forced no sandbox for Windows closed-network runtime" in run_qwen
        assert 'set "QWEN_SANDBOX=0"' in run_qwen
        assert "KIWI syncs bundled project skills and agents into existing qwen projects" in run_qwen
        assert "templates\\project\\.qwen\\skills" in run_qwen
        assert "templates\\project\\.qwen\\agents" in run_qwen
        assert "robocopy" in run_qwen
        assert "KIWI forced yolo approval for Windows closed-network runtime" not in run_qwen
        assert "--approval-mode yolo" not in run_qwen
        init_script = read_zip_text(zf, "scripts/qwen-init.ps1", root=QWENCODE_ZIP_ROOT)
        assert '".qwen\\skills"' in init_script and '".qwen\\agents"' in init_script
        assert 'Copy-TemplateDirectory ".qwen\\skills" ".qwen\\skills"' in init_script
        assert 'Copy-TemplateDirectory ".qwen\\agents" ".qwen\\agents"' in init_script
        cli = read_zip_text(zf, "app/cli.js", root=QWENCODE_ZIP_ROOT)
        assert "if (Array.isArray(value)) value = value[value.length - 1];" in cli
        assert 'if (typeof value !== "string") value = String(value ?? "");' in cli

        settings = read_zip_json(zf, "portable-user/.qwen/settings.json", root=QWENCODE_ZIP_ROOT)
        assert settings["model"]["name"] == EXPECTED_MODEL, settings["model"]
        assert settings["tools"]["approvalMode"] == "yolo", settings["tools"]
        assert "sandbox" not in settings["tools"], settings["tools"]
        assert settings["ui"]["compactMode"] is True, settings["ui"]
        assert settings["ui"]["useTerminalBuffer"] is False, settings["ui"]
        template_settings = read_zip_json(zf, "templates/project/.qwen/settings.json", root=QWENCODE_ZIP_ROOT)
        assert template_settings["tools"]["approvalMode"] == "yolo", template_settings["tools"]
        assert "sandbox" not in template_settings["tools"], template_settings["tools"]
        assert template_settings["ui"]["compactMode"] is True, template_settings["ui"]
        assert template_settings["ui"]["useTerminalBuffer"] is False, template_settings["ui"]
        providers = settings["modelProviders"]["openai"]
        main_provider = next(provider for provider in providers if provider["id"] == EXPECTED_MODEL)
        generation = main_provider["generationConfig"]
        assert generation["modalities"]["image"] is True, generation
        assert generation["splitToolMedia"] is True, generation

        writer = read_zip_text(zf, "scripts/write-runtime-config.js", root=QWENCODE_ZIP_ROOT)
        assert "modalities: { image: true }" in writer, "qwencode writer missing image modality"
        assert "splitToolMedia: true" in writer, "qwencode writer missing splitToolMedia"
        assert "compactMode: true" in writer, "qwencode writer missing compactMode"
        assert "useTerminalBuffer: false" in writer, "qwencode writer must disable virtual terminal buffer"
        assert_team_log_contract(
            read_zip_text(zf, "scripts/team-log-lib.js", root=QWENCODE_ZIP_ROOT),
            "qwencode zip",
        )

        modality_patch_files = [
            name
            for name in names
            if name.startswith(f"{QWENCODE_ZIP_ROOT}/app/")
            and name.endswith(".js")
            and "qwen3\\.5-397b" in zf.read(name).decode("utf-8", errors="replace")
        ]
        assert modality_patch_files, "qwencode zip missing Qwen3.5-397B modality fallback patch"

        for skill in expected_skills:
            skill_paths = [
                (
                    f"{QWENCODE_ZIP_ROOT}/portable-user/.qwen/extensions/"
                    f"superpowers/skills/{skill}/SKILL.md"
                ),
                f"{QWENCODE_ZIP_ROOT}/portable-user/.qwen/skills/{skill}/SKILL.md",
                f"{QWENCODE_ZIP_ROOT}/templates/project/.qwen/skills/{skill}/SKILL.md",
            ]
            for skill_path in skill_paths:
                assert skill_path in names, f"qwencode zip missing superpowers skill: {skill_path}"
                text = zf.read(skill_path).decode("utf-8", errors="replace")
                assert "## Qwen tool mapping" in text, f"skill missing tool mapping: {skill}"
                assert "D:/aiops/docs/<project-key>/project-info" in text, f"skill missing Project Info contract: {skill}"
                assert "D:/aiops/docs/<project-key>/knowledge" in text, f"skill missing central knowledge contract: {skill}"
        for agent in source_agent_names():
            for agent_path in [
                f"{QWENCODE_ZIP_ROOT}/portable-user/.qwen/extensions/ultrawork/agents/{agent}.md",
                f"{QWENCODE_ZIP_ROOT}/extensions/ultrawork/agents/{agent}.md",
                f"{QWENCODE_ZIP_ROOT}/portable-user/.qwen/agents/{agent}.md",
                f"{QWENCODE_ZIP_ROOT}/templates/project/.qwen/agents/{agent}.md",
            ]:
                assert agent_path in names, f"qwencode zip missing Qwen agent path: {agent_path}"
                assert_native_agent_frontmatter(
                    zf.read(agent_path).decode("utf-8", errors="replace"),
                    f"qwencode zip {agent_path}",
                )


def main() -> None:
    assert_runtime_source()
    assert_kiwi_initialize_refreshes_project_skills()
    assert_qwencode_zip()
    assert_bundle_zip()
    print("PASS: qwencode standalone bundle and KIWI no-duplicate bundle are valid")


if __name__ == "__main__":
    main()
