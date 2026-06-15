#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.project_info import project_info_artifact_dir  # noqa: E402

DEFAULT_RUNTIME = Path(r"D:\aiops\qwencode")
DEFAULT_OUTPUT = ROOT / "build" / "windows-validation-evidence"
SCRIPT_NAME = "collect-windows-validation-evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect KIWI Windows qwencode validation evidence")
    parser.add_argument("--project-root", default=os.getenv("KIWI_VALIDATION_PROJECT", ""))
    parser.add_argument("--runtime-dir", default=os.getenv("KIWI_QWENCODE_RUNTIME_DIR", str(DEFAULT_RUNTIME)))
    parser.add_argument("--bundle", default=str(ROOT / "build" / "offline" / "kiwi-offline-win11-py313.zip"))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--strict", action="store_true", help="Fail if required Windows evidence is missing")
    parser.add_argument("--self-check", action="store_true", help="Validate collector/doc wiring without Windows-only paths")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = output_dir / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir.mkdir(parents=True, exist_ok=True)

    runtime_dir = Path(args.runtime_dir).expanduser()
    project_root = Path(args.project_root).expanduser() if args.project_root else None
    bundle = Path(args.bundle).expanduser()
    strict = args.strict or (os.name == "nt" and not args.self_check)

    report: dict[str, Any] = {
        "schema": "kiwi.phase5.windows-validation.v1",
        "collector": SCRIPT_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python": sys.version,
            "cwd": str(Path.cwd()),
        },
        "inputs": {
            "project_root": str(project_root) if project_root else "",
            "runtime_dir": str(runtime_dir),
            "bundle": str(bundle),
            "output_dir": str(evidence_dir),
        },
        "checks": [],
        "commands": [],
        "artifacts": [],
        "failures": [],
    }

    check_path(report, "runtime D:\\aiops\\qwencode", runtime_dir, required=True)
    check_path(report, "runtime run-qwen.cmd", runtime_dir / "run-qwen.cmd", required=True)
    check_path(report, "runtime qwen-init.cmd", runtime_dir / "qwen-init.cmd", required=True)
    check_path(report, "team-events.jsonl", runtime_dir / "portable-runtime" / "team-events.jsonl", required=False)
    check_path(report, "offline bundle zip", bundle, required=True)

    if project_root is not None:
        check_path(report, "project root", project_root, required=True)
        check_path(report, "project qwen.cmd", project_root / "qwen.cmd", required=True)
        project_info_dir = project_info_artifact_dir(project_root)
        check_path(report, "Project Info JSON", project_info_dir / "project-info.json", required=True)
        check_path(report, "Project Info summary", project_info_dir / "project-summary.md", required=True)
        collect_file(report, project_root / "qwen.cmd", evidence_dir / "project-qwen.cmd.txt")
        collect_tree(report, project_info_dir, evidence_dir / "project-info-tree.txt")
    else:
        report["failures"].append("project_root not provided; pass --project-root <initialized KIWI target>")

    collect_file(report, runtime_dir / "portable-runtime" / "team-events.jsonl", evidence_dir / "team-events.tail.jsonl", tail_bytes=256_000)
    collect_file(report, runtime_dir / "config" / "env.cmd", evidence_dir / "runtime-env.cmd.txt")
    collect_file(report, runtime_dir / "templates" / "project" / ".qwen" / "env.cmd", evidence_dir / "project-template-env.cmd.txt")
    collect_file(report, ROOT / "docs" / "windows-qwencode-validation.md", evidence_dir / "windows-qwencode-validation.md")

    run_command(report, ["py", "-3.13", "--version"], cwd=ROOT)
    run_command(report, ["node", "--version"], cwd=ROOT)
    run_command(report, ["npm", "--version"], cwd=ROOT)
    if bundle.exists():
        report["bundle_sha256"] = sha256(bundle)
        run_command(report, ["python", "-m", "zipfile", "--test", str(bundle)], cwd=ROOT)
        inspect_bundle(report, bundle)

    report_path = evidence_dir / "windows-validation-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archive_path = shutil.make_archive(str(evidence_dir), "zip", root_dir=str(evidence_dir))
    print(f"evidence_report={report_path}")
    print(f"evidence_archive={archive_path}")

    if strict and report["failures"]:
        print("validation evidence has failures:", file=sys.stderr)
        for failure in report["failures"]:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


def check_path(report: dict[str, Any], name: str, path: Path, required: bool) -> None:
    exists = path.exists()
    item = {
        "name": name,
        "path": str(path),
        "exists": exists,
        "required": required,
        "kind": "directory" if exists and path.is_dir() else "file" if exists else "missing",
    }
    report["checks"].append(item)
    if required and not exists:
        report["failures"].append(f"missing required path: {name} ({path})")


def collect_file(report: dict[str, Any], source: Path, dest: Path, tail_bytes: int | None = None) -> None:
    if not source.exists() or not source.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if tail_bytes is None:
        shutil.copy2(source, dest)
    else:
        data = source.read_bytes()
        dest.write_bytes(data[-tail_bytes:])
    report["artifacts"].append({"source": str(source), "dest": str(dest), "bytes": dest.stat().st_size})


def collect_tree(report: dict[str, Any], source: Path, dest: Path) -> None:
    if not source.exists() or not source.is_dir():
        return
    lines = []
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source).as_posix()
        lines.append(rel + ("/" if path.is_dir() else ""))
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report["artifacts"].append({"source": str(source), "dest": str(dest), "bytes": dest.stat().st_size})


def run_command(report: dict[str, Any], command: list[str], cwd: Path) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        report["commands"].append(
            {
                "command": command,
                "cwd": str(cwd),
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    except Exception as exc:
        report["commands"].append({"command": command, "cwd": str(cwd), "error": str(exc)})


def inspect_bundle(report: dict[str, Any], bundle: Path) -> None:
    required_entries = [
        "kiwi-offline-win11-py313/vendor/qwen-runtime/config/env.cmd",
        "kiwi-offline-win11-py313/vendor/qwen-runtime/templates/project/.qwen/env.cmd",
        "kiwi-offline-win11-py313/bundle-manifest.json",
        "kiwi-offline-win11-py313/install-offline.cmd",
        "kiwi-offline-win11-py313/start-kiwi.cmd",
        "kiwi-offline-win11-py313/verify-offline.cmd",
    ]
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
    missing = [name for name in required_entries if name not in names]
    report["checks"].append({"name": "offline bundle required entries", "missing": missing, "required": True})
    if missing:
        report["failures"].append("offline bundle missing entries: " + ", ".join(missing))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
