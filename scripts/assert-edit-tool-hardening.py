#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "docs" / "ultrawork-agents"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_agent_protocols() -> None:
    required = [
        "Exact Edit Protocol",
        "latest `read_file` output",
        "After any successful `edit`",
        "For any N-line deletion or replacement",
        "smallest exact current span",
        "boundary/context",
        "edit_no_occurrence_found",
        "do not retry the same",
        "Stop after two failed `edit`",
        "PowerShell regex",
        "Set-Content",
        "@file",
        "prompt-attached file content",
        "edit tool read gate",
    ]
    for path in sorted(AGENT_DIR.glob("*developer.md")):
        text = read(path)
        for phrase in required:
            assert phrase in text, f"{path.name} missing edit protocol phrase: {phrase}"


def assert_runtime_and_policy_protocols() -> None:
    paths = [
        ROOT / "docs" / "qwen-edit-tool-hardening.md",
        ROOT / "docs" / "ultrawork-runtime-policy.md",
        ROOT / "docs" / "superpowers-runtime-policy.md",
        ROOT / "docs" / "ultrawork-prompt-template.md",
        ROOT / "docs" / "superpowers-skills" / "kiwi-superpowers" / "SKILL.md",
        ROOT / "docs" / "superpowers-skills" / "subagent-driven-development" / "SKILL.md",
        ROOT / "backend" / "app" / "ultrawork_policy.py",
        ROOT / "backend" / "app" / "qwencode_runtime.py",
        ROOT / "scripts" / "build-offline-bundle.py",
    ]
    required = [
        "Exact Edit Protocol",
        "edit_no_occurrence_found",
        "latest read_file",
        "N-line",
        "smallest exact current span",
        "boundary/context",
        "PowerShell regex",
        "Set-Content",
        "@file",
        "prompt-attached file content",
        "edit tool read gate",
    ]
    for path in paths:
        text = read(path)
        for phrase in required:
            assert phrase in text, f"{path.relative_to(ROOT)} missing {phrase}"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_runtime_patch_functions() -> None:
    sample = (
        "raw: `Failed to edit, 0 occurrences found for old_string in ${params.file_path}. "
        "No edits made. The exact text in old_string was not found. Ensure you're not escaping content incorrectly "
        "and check whitespace, indentation, and context. Use ${ReadFileTool.Name} tool to verify.`,"
    )
    runtime = _load_module(ROOT / "backend" / "app" / "qwencode_runtime.py", "kiwi_qwencode_runtime")
    bundle = _load_module(ROOT / "scripts" / "build-offline-bundle.py", "kiwi_build_bundle")
    backend_patched = runtime._patch_edit_tool_failure_guidance(sample)
    bundle_patched = bundle.patch_edit_tool_failure_guidance(sample)
    assert backend_patched == bundle_patched, "backend/offline edit guidance patch drift"
    for phrase in [
        "KIWI edit recovery protocol",
        "safe N-line span repair was attempted first",
        "do not retry the same or a larger old_string",
        "copy the smallest exact current N-line span",
        "PowerShell regex/Set-Content",
        "@file references or prompt-attached file content do not satisfy the edit read gate",
    ]:
        assert phrase in backend_patched, f"edit failure guidance missing {phrase}"
    assert runtime._patch_edit_tool_failure_guidance(backend_patched) == backend_patched
    assert bundle.patch_edit_tool_failure_guidance(bundle_patched) == bundle_patched


def assert_edit_tool_description_and_span_repair() -> None:
    source = ROOT.parent / "deliverables" / "_extract-qwen-0.17.1" / "qwen-code" / "lib" / "chunks" / "edit-JWXCQ4KK.js"
    if not source.exists():
        source = ROOT.parent / "deliverables" / "qwen-code-offline-win11-v0.17.1" / "app" / "chunks" / "edit-JWXCQ4KK.js"
    assert source.exists(), "missing Qwen edit chunk fixture"
    runtime = _load_module(ROOT / "backend" / "app" / "qwencode_runtime.py", "kiwi_qwencode_runtime_span")
    bundle = _load_module(ROOT / "scripts" / "build-offline-bundle.py", "kiwi_build_bundle_span")
    original = read(source)
    backend_patched = runtime._patch_edit_tool_failure_guidance(original)
    bundle_patched = bundle.patch_edit_tool_failure_guidance(original)
    assert backend_patched == bundle_patched, "backend/offline edit span repair patch drift"
    assert "kiwiDeriveSafeEditSpan" in backend_patched, "missing safe N-line edit span repair helper"
    assert "Use the smallest exact current span that occurs once" in backend_patched
    assert "For N-line deletion or replacement" in backend_patched
    assert "Prompt-attached file content, including @file references, does not satisfy this tool's read gate" in backend_patched
    assert "@file references or prompt-attached file content do not satisfy the edit read gate" in backend_patched
    assert "include at least 3 lines of context BEFORE and AFTER" not in backend_patched

    start = backend_patched.index("var UNICODE_EQUIVALENT_MAP = {")
    end_marker = '__name(countOccurrences, "countOccurrences");'
    end = backend_patched.index(end_marker) + len(end_marker)
    helper_source = backend_patched[start:end]
    js = f"""
function __name(fn, name) {{ return fn; }}
{helper_source}
function assertEq(actual, expected, label) {{
  if (actual !== expected) {{
    throw new Error(`${{label}} expected=${{JSON.stringify(expected)}} actual=${{JSON.stringify(actual)}}`);
  }}
}}
function assertNull(actual, label) {{
  if (actual !== null) {{
    throw new Error(`${{label}} expected null actual=${{JSON.stringify(actual)}}`);
  }}
}}
const cobrowseLine = '  <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>\\n';
const file1 = [
  'root',
  '  <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>AI 상담하기</span></button>',
  '  <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>',
  '</div>',
  'end'
].join('\\n') + '\\n';
const staleOld1 = [
  '  <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>AI 상담하기</span></button>  ',
  '  <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>',
  '</div>'
].join('\\n') + '\\n';
const staleNew1 = [
  '  <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>AI 상담하기</span></button>  ',
  '</div>'
].join('\\n') + '\\n';
    const repaired1 = kiwiDeriveSafeEditSpan(file1, staleOld1, staleNew1);
    assertEq(repaired1.oldString, cobrowseLine, 'single-line deletion core');
    assertEq(repaired1.newString, '', 'single-line deletion replacement');

const fileMainLocalView = [
  '                        <div class="btn-group">',
  '                            <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>디지털 agent화면 </span></button>',
  '                            <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>',
  '                        </div>'
].join('\\n');
const staleMainLocalViewOld = [
  '                        <div class="btn-group">',
  '                            <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>디지털 agent 화면 </span></button>',
  '                            <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>',
  '                        </div>'
].join('\\n');
const staleMainLocalViewNew = [
  '                        <div class="btn-group">',
  '                            <button type="button" class="btn btn-pry" @click="clickAgentChat"><span>디지털 agent 화면 </span></button>',
  '                        </div>'
].join('\\n');
const repairedMainLocalView = kiwiDeriveSafeEditSpan(fileMainLocalView, staleMainLocalViewOld, staleMainLocalViewNew);
assertEq(
  repairedMainLocalView.oldString,
  '                            <button type="button" class="btn btn-pry" @click="clickCobrowse"><span>Cobrowse PoC </span></button>\\n',
  'MainLocalView stale neighbor context repair'
);
assertEq(repairedMainLocalView.newString, '', 'MainLocalView stale neighbor context replacement');

const file2 = 'actual before\\nold-a\\nold-b\\nactual after\\n';
const staleOld2 = 'stale before\\nold-a\\nold-b\\nstale after\\n';
const staleNew2 = 'stale before\\nstale after\\n';
const repaired2 = kiwiDeriveSafeEditSpan(file2, staleOld2, staleNew2);
assertEq(repaired2.oldString, 'old-a\\nold-b\\n', 'N-line deletion core');
assertEq(repaired2.newString, '', 'N-line deletion replacement');

const staleNew3 = 'stale before\\nnew-a\\nnew-b\\nstale after\\n';
const repaired3 = kiwiDeriveSafeEditSpan(file2, staleOld2, staleNew3);
assertEq(repaired3.oldString, 'old-a\\nold-b\\n', 'N-line replacement core');
assertEq(repaired3.newString, 'new-a\\nnew-b\\n', 'N-line replacement new core');

const ambiguous = 'old-a\\nold-b\\n---\\nold-a\\nold-b\\n';
assertNull(kiwiDeriveSafeEditSpan(ambiguous, staleOld2, staleNew2), 'ambiguous repeated core');

// aaa.zip real-log class: model inserts single spaces inside Korean context lines
// (file: `2개 이상인`, model old/new: `2 개 이상인`), with real changes on both sides.
const koFile = [
  '      <div class="component-wrap">',
  '        <span>병명이 2개 이상인 통원(외래진료비) 청구시 병명을 모두 기재해 주세요!</span>',
  '        <button type="button">기존 버튼</button>',
  '      </div>'
].join('\\n') + '\\n';
const koOld = [
  '      <div class="component-wrap">',
  '        <span>병명이 2 개 이상인 통원 (외래진료비) 청구시 병명을 모두 기재해 주세요!</span>',
  '        <button type="button">기존 버튼</button>',
  '      </div>'
].join('\\n') + '\\n';
const koNew = [
  '      <div class="component-wrap claim">',
  '        <span>병명이 2 개 이상인 통원 (외래진료비) 청구시 병명을 모두 기재해 주세요!</span>',
  '        <button type="button">새 청구 버튼</button>',
  '      </div>'
].join('\\n') + '\\n';
assertNull(kiwiDeriveSafeEditSpan(koFile, koOld, koNew), 'spacing typos must fall through derive to ws repair');
const koRepair = kiwiWhitespaceTolerantRepair(koFile, koOld, koNew);
assertEq(koRepair.oldString, koFile, 'ws repair must return the exact file span');
assertEq(
  koRepair.newString.includes('2개 이상인 통원(외래진료비)'),
  true,
  'preserved context line must come from the file, not the typoed model copy'
);
assertEq(koRepair.newString.includes('2 개'), false, 'spacing typo must not be written to the file');
assertEq(koRepair.newString.includes('component-wrap claim'), true, 'intended class change must survive');
assertEq(koRepair.newString.includes('새 청구 버튼'), true, 'intended button change must survive');

const koAmbiguousFile = koFile + '---\\n' + koFile;
assertNull(kiwiWhitespaceTolerantRepair(koAmbiguousFile, koOld, koNew), 'ws repair must refuse ambiguous windows');
assertNull(kiwiWhitespaceTolerantRepair(koFile, '<div>\\n', '<section>\\n'), 'ws repair must refuse weak signals');
assertNull(kiwiWhitespaceTolerantRepair(koFile, koFile, koNew), 'exact old_string never enters ws repair');
console.log('safe edit span repair fixtures passed');
"""
    subprocess.run(["node", "--input-type=module"], input=js, text=True, check=True)

    # v1 -> v2 migration: a runtime that already carries the v1 span repair must gain the ws repair
    v1_like = backend_patched.replace(runtime.KIWI_EDIT_WS_REPAIR_HELPER, "", 1).replace(
        runtime.KIWI_EDIT_SPAN_INSERT_V2, runtime.KIWI_EDIT_SPAN_INSERT_V1, 1
    )
    assert "kiwiWhitespaceTolerantRepair" not in v1_like, "v1 fabrication failed"
    remigrated = runtime._patch_edit_tool_failure_guidance(v1_like)
    assert remigrated == backend_patched, "v1->v2 span repair migration drift"
    assert bundle.patch_edit_tool_failure_guidance(v1_like) == backend_patched, "bundler v1->v2 migration drift"


def _runtime_fixture(relative: str) -> Path:
    source = ROOT.parent / "deliverables" / "_extract-qwen-0.17.1" / "qwen-code" / "lib" / relative
    if not source.exists():
        source = ROOT.parent / "deliverables" / "qwen-code-offline-win11-v0.17.1" / "app" / relative
    assert source.exists(), f"missing Qwen runtime fixture: {relative}"
    return source


def assert_console_paste_guard() -> None:
    runtime = _load_module(ROOT / "backend" / "app" / "qwencode_runtime.py", "kiwi_qwencode_runtime_paste")
    bundle = _load_module(ROOT / "scripts" / "build-offline-bundle.py", "kiwi_build_bundle_paste")
    cli = read(_runtime_fixture("cli.js"))
    backend_patched = runtime._patch_console_paste_guard(cli)
    bundle_patched = bundle.patch_console_paste_guard(cli)
    assert backend_patched == bundle_patched, "backend/offline paste guard patch drift"
    assert backend_patched != cli, "paste guard anchor missing in cli.js fixture"
    bypass_marker = 'process.env["KIWI_ULTRAWORK_CONSOLE"] !== "1"'
    assert bypass_marker in backend_patched, "patched cli.js missing bypass marker"
    assert runtime._patch_console_paste_guard(backend_patched) == backend_patched, "paste guard patch not idempotent"
    console_text = read(ROOT / "backend" / "app" / "ultrawork_console.py")
    assert f"QWEN_PASTE_GUARD_BYPASS_MARKER = '{bypass_marker}'" in console_text, "console bypass marker constant drifted from runtime patch"
    assert "PASTE_SUBMIT_BYPASS_SECONDS" in console_text, "console missing bypassed submit delay"
    assert "_runtime_paste_guard_bypassed" in console_text, "console missing runtime bypass detection"


def assert_file_path_recovery_hints() -> None:
    runtime = _load_module(ROOT / "backend" / "app" / "qwencode_runtime.py", "kiwi_qwencode_runtime_path")
    bundle = _load_module(ROOT / "scripts" / "build-offline-bundle.py", "kiwi_build_bundle_path")
    read_chunk = read(_runtime_fixture("chunks/chunk-C5CUHYSM.js"))
    edit_chunk = read(_runtime_fixture("chunks/edit-JWXCQ4KK.js"))
    for original in [read_chunk, edit_chunk]:
        backend_patched = runtime._patch_edit_tool_failure_guidance(original)
        bundle_patched = bundle.patch_edit_tool_failure_guidance(original)
        assert backend_patched == bundle_patched, "backend/offline path recovery patch drift"
        assert "kiwiSuggestNearbyPath" in backend_patched, "missing path recovery helper"
        assert "Did you mean" in backend_patched, "missing Did you mean hint"
        assert runtime._patch_edit_tool_failure_guidance(backend_patched) == backend_patched, "path recovery patch not idempotent"

    import tempfile

    with tempfile.TemporaryDirectory() as raw_dir:
        base = Path(raw_dir) / "프로젝트" / "문서"
        base.mkdir(parents=True)
        (base / "파일-이름-읽기.md").write_text("hello", encoding="utf-8")
        (base / "중복 파일.md").write_text("x", encoding="utf-8")
        (base / "중복파일.md").write_text("y", encoding="utf-8")
        js = f"""
function __name(fn, name) {{ return fn; }}
{runtime._KIWI_PATH_RECOVERY_HELPER}
const assertEq = (actual, expected, label) => {{
  if (actual !== expected) throw new Error(`${{label}} expected=${{JSON.stringify(expected)}} actual=${{JSON.stringify(actual)}}`);
}};
const base = {str(base)!r};
const target = base + "/파일-이름-읽기.md";
const run = async () => {{
  assertEq(await kiwiSuggestNearbyPath(base + "/파일 - 이름 - 읽기.md"), target, "spaced hyphen recovery");
  assertEq(await kiwiSuggestNearbyPath(base.replace("문서", "문 서") + "/파일-이름-읽기.md"), target, "spaced directory recovery");
  assertEq(await kiwiSuggestNearbyPath(base + "/중복  파일.md"), null, "ambiguous candidates stay null");
  assertEq(await kiwiSuggestNearbyPath(base + "/전혀없는파일.md"), null, "unrelated missing file stays null");
  assertEq(await kiwiSuggestNearbyPath(target), null, "existing path is never rewritten");
  console.log("path recovery fixtures passed");
}};
run().catch((error) => {{ console.error(error); process.exit(1); }});
"""
        subprocess.run(["node", "--input-type=module"], input=js, text=True, check=True)


def main() -> None:
    assert_agent_protocols()
    assert_runtime_and_policy_protocols()
    assert_runtime_patch_functions()
    assert_edit_tool_description_and_span_repair()
    assert_console_paste_guard()
    assert_file_path_recovery_hints()
    print("edit tool hardening assertions passed")


if __name__ == "__main__":
    main()
