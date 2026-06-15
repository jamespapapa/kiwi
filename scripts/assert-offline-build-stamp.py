from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE_SCRIPT = ROOT / "scripts" / "build-offline-bundle.py"
BUILD_ROOT = ROOT / "build" / "offline" / "kiwi"
UI_BUILD_MARKER = 'data-kiwi-ui-build="xterm-fit-v4-port-guard"'


def require_contains(text: str, needle: str, label: str) -> None:
    assert needle in text, f"missing {label}: {needle}"


def assert_bundle_script_has_stamp_logic() -> None:
    text = BUNDLE_SCRIPT.read_text(encoding="utf-8")
    page_text = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    css_text = (ROOT / "app" / "globals.css").read_text(encoding="utf-8")
    require_contains(page_text, UI_BUILD_MARKER, "HTML UI build marker")
    require_contains(page_text, "command-bar-hint", "stable command bar hint")
    require_contains(page_text, "disabled={!consoleRunning}", "stable command bar disabled textarea")
    require_contains(css_text, "grid-template-columns: 22px 1fr auto 56px;", "stable command bar grid")
    forbidden_page_terms = [
        "terminalPendingSubmitRef",
        "handlePreActivationTerminalData",
        "sendPreActivationTerminalPrompt",
        "xtermRef.current?.write(data)",
    ]
    for term in forbidden_page_terms:
        assert term not in page_text, f"frontend must not locally echo pre-activation xterm input: {term}"
    for needle, label in [
        ("FRONTEND_BUILD_STAMP_INPUTS", "frontend stamp input list"),
        ("def write_frontend_build_stamp", "stamp writer"),
        ("kiwi-source-stamp.txt", "stamp filename"),
        ('target_root / "stop-kiwi.cmd"', "Windows stop script"),
        ("Get-NetTCPConnection", "Windows port listener detection"),
        ("Stop-Process -Id $processId -Force", "Windows stale process cleanup"),
        ('call "%ROOT%\\stop-kiwi.cmd"', "startup stop script call"),
        ('fc /b "%ROOT%\\kiwi-source-stamp.txt" "%ROOT%\\.next\\kiwi-source-stamp.txt"', "Windows stamp comparison"),
        ('rmdir /s /q "%ROOT%\\.next"', "stale .next deletion"),
        ("Next production build is missing or stale", "stale build message"),
    ]:
        require_contains(text, needle, label)


def assert_generated_bundle_has_stamp_logic() -> None:
    if not BUILD_ROOT.exists():
        return
    stamp = BUILD_ROOT / "kiwi-source-stamp.txt"
    assert stamp.exists(), f"missing generated stamp file: {stamp}"
    assert len(stamp.read_text(encoding="utf-8").strip()) == 64, "generated stamp must be sha256 hex"
    generated_page = BUILD_ROOT / "app" / "page.tsx"
    assert generated_page.exists(), f"missing generated app page: {generated_page}"
    require_contains(generated_page.read_text(encoding="utf-8"), UI_BUILD_MARKER, "generated HTML UI build marker")
    stop_script = BUILD_ROOT / "stop-kiwi.cmd"
    assert stop_script.exists(), f"missing generated stop script: {stop_script}"
    stop_text = stop_script.read_text(encoding="utf-8")
    for needle, label in [
        ("KIWI_STOP_PORTS=3000,8787", "default KIWI ports"),
        ("Get-NetTCPConnection", "port listener detection"),
        ("Stop-Process -Id $processId -Force", "stale process cleanup"),
    ]:
        require_contains(stop_text, needle, label)
    for script_name in ["start-kiwi.cmd", "run-web.cmd"]:
        script = BUILD_ROOT / script_name
        assert script.exists(), f"missing generated script: {script}"
        text = script.read_text(encoding="utf-8")
        for needle, label in [
            ('call "%ROOT%\\stop-kiwi.cmd"', f"{script_name} stop script call"),
            ("NEEDS_BUILD", f"{script_name} stale flag"),
            ("kiwi-source-stamp.txt", f"{script_name} stamp file"),
            ("fc /b", f"{script_name} stamp comparison"),
            ('rmdir /s /q "%ROOT%\\.next"', f"{script_name} stale .next deletion"),
            ("npm.cmd\" run build", f"{script_name} rebuild command"),
        ]:
            require_contains(text, needle, label)
    backend_script = BUILD_ROOT / "run-backend.cmd"
    assert backend_script.exists(), f"missing generated script: {backend_script}"
    require_contains(
        backend_script.read_text(encoding="utf-8"),
        'call "%ROOT%\\stop-kiwi.cmd"',
        "run-backend.cmd stop script call",
    )


def main() -> None:
    assert_bundle_script_has_stamp_logic()
    assert_generated_bundle_has_stamp_logic()


if __name__ == "__main__":
    main()
