from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.project_info import (  # noqa: E402
    PROJECT_INFO_ARTIFACT_NAMES,
    PROJECT_INFO_JSON,
    _collect_project_files,
    analyze_project_info,
    load_project_info_bundle,
    project_info_artifact_dir,
    validate_project_info_bundle,
)


DCP_FRONT = Path("/Users/jules/Desktop/work/untitle/dcp/dcp-front-develop")
DCP_SERVICES = Path("/Users/jules/Desktop/work/untitle/dcp/dcp-services-mevelop")

FRONT_REQUIRED_KINDS = {
    "screen-role",
    "route-view-flow",
    "common-component",
    "datastore-flow",
    "backend-call-pattern",
    "verification-command",
}

SERVICES_REQUIRED_KINDS = {
    "maven-module",
    "package-role",
    "controller-service-flow",
    "repository-pattern",
    "config-profile",
    "batch-scheduler",
    "eai-interface",
    "dto-flow",
    "verification-command",
}

FORBIDDEN_GENERIC_SUMMARIES = (
    "Potential runtime",
    "Candidate user or backend flow marker",
    "No explicit verification command was detected",
    "No API/EAI marker was detected",
    "Project area identified by directory structure",
)


def main() -> None:
    front = assert_project(DCP_FRONT, "dcp-front", FRONT_REQUIRED_KINDS, min_evidence=20)
    services = assert_project(DCP_SERVICES, "dcp-services", SERVICES_REQUIRED_KINDS, min_evidence=20)
    print(
        json.dumps(
            {
                "project_info_quality": "passed",
                "dcp-front": front,
                "dcp-services": services,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def assert_project(root: Path, expected_profile: str, required_kinds: set[str], min_evidence: int) -> dict[str, Any]:
    assert root.exists(), f"target root does not exist: {root}"
    artifact_dir = project_info_artifact_dir(root)
    bundle_path = artifact_dir / PROJECT_INFO_JSON
    if not bundle_path.exists():
        analyze_project_info(root, write=True)
    assert bundle_path.exists(), f"missing Project Info JSON: {bundle_path}"
    bundle = load_project_info_bundle(root)
    assert bundle, f"unable to load Project Info bundle: {bundle_path}"

    errors = validate_project_info_bundle(root, bundle)
    assert not errors, f"{root.name} bundle validation failed: {errors[:10]}"
    assert bundle.get("profile", {}).get("key") == expected_profile, bundle.get("profile")
    assert set(PROJECT_INFO_ARTIFACT_NAMES).issubset(set(bundle.get("artifacts", {})))
    assert bundle.get("analysis_log", {}).get("searches"), f"{root.name} missing search log"

    markdown_files = [artifact_dir / f"{name}.md" for name in PROJECT_INFO_ARTIFACT_NAMES]
    for path in markdown_files:
        assert path.exists(), f"missing markdown artifact: {path}"
        assert path.read_text(encoding="utf-8", errors="ignore").strip(), f"empty markdown artifact: {path}"

    kinds = collect_kinds(bundle)
    missing_kinds = sorted(required_kinds - kinds)
    assert not missing_kinds, f"{root.name} missing required item kinds: {missing_kinds}; present={sorted(kinds)}"

    evidence = collect_evidence(bundle)
    unique_anchors = {
        (str(item.get("path")), int(item["line"]) if item.get("line") is not None else None, str(item.get("symbol") or item.get("name") or ""))
        for item in evidence
    }
    assert len(unique_anchors) >= min_evidence, f"{root.name} has only {len(unique_anchors)} evidence anchors"
    assert_evidence_paths_exist(root, evidence)
    assert_no_empty_sections(bundle)
    assert_no_generic_required_claims(bundle, required_kinds)

    if expected_profile == "dcp-front":
        assert_front_content(bundle)
    else:
        assert_services_content(root, bundle)

    return {
        "profile": expected_profile,
        "evidence_anchors": len(unique_anchors),
        "item_kinds": sorted(kinds),
        "artifact_dir": str(artifact_dir),
        "markdown_files": [str(path.relative_to(artifact_dir)) for path in markdown_files],
    }


def collect_kinds(bundle: dict[str, Any]) -> set[str]:
    return {
        str(item.get("kind"))
        for artifact in bundle.get("artifacts", {}).values()
        for item in artifact.get("items", [])
        if item.get("kind")
    }


def collect_evidence(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        evidence
        for artifact in bundle.get("artifacts", {}).values()
        for item in artifact.get("items", [])
        for evidence in item.get("evidence", [])
    ]


def assert_evidence_paths_exist(root: Path, evidence_items: list[dict[str, Any]]) -> None:
    for evidence in evidence_items:
        rel = str(evidence.get("path") or "")
        assert rel and not Path(rel).is_absolute(), f"invalid evidence path: {evidence}"
        path = root / rel
        assert path.exists(), f"evidence path missing: {root.name}:{rel}"
        if evidence.get("line") is not None:
            line = int(evidence["line"])
            assert line >= 1, f"invalid evidence line: {evidence}"
            line_count = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
            assert line <= line_count, f"evidence line out of range: {evidence}"


def assert_no_empty_sections(bundle: dict[str, Any]) -> None:
    for artifact_name, artifact in bundle.get("artifacts", {}).items():
        assert str(artifact.get("summary") or "").strip(), f"{artifact_name} empty summary"
        items = artifact.get("items", [])
        assert items, f"{artifact_name} empty items"
        for item in items:
            assert str(item.get("title") or "").strip(), f"{artifact_name} item missing title"
            assert str(item.get("summary") or "").strip(), f"{artifact_name} item missing summary"
            assert item.get("evidence"), f"{artifact_name}.{item.get('id')} missing evidence"


def assert_no_generic_required_claims(bundle: dict[str, Any], required_kinds: set[str]) -> None:
    for artifact in bundle.get("artifacts", {}).values():
        for item in artifact.get("items", []):
            if item.get("kind") not in required_kinds:
                continue
            summary = str(item.get("summary") or "")
            for forbidden in FORBIDDEN_GENERIC_SUMMARIES:
                assert forbidden not in summary, f"generic required claim remained: {item.get('id')} -> {summary}"


def assert_front_content(bundle: dict[str, Any]) -> None:
    text = json.dumps(bundle, ensure_ascii=False)
    for required in [
        "src/router",
        "src/views",
        "src/components",
        "DataStore",
        "axios",
        "tools/playwright",
    ]:
        assert required in text, f"dcp-front missing content marker: {required}"


def assert_services_content(root: Path, bundle: dict[str, Any]) -> None:
    text = json.dumps(bundle, ensure_ascii=False)
    for required in [
        "pom.xml",
        "controller",
        "service",
        "repository",
        "resources-env",
        "scheduler",
        "EAI",
        "response",
    ]:
        assert required in text, f"dcp-services missing content marker: {required}"
    eai_items = [
        item
        for artifact in bundle.get("artifacts", {}).values()
        for item in artifact.get("items", [])
        if item.get("kind") == "eai-interface"
    ]
    assert eai_items, "dcp-services missing eai-interface items"
    assert_services_file_collection(root, bundle)
    assert_services_eai_xml_index(root, eai_items)
    for item in eai_items:
        summary = str(item.get("summary") or "")
        assert "unknown with searched evidence" in summary or item.get("interface_id"), item


def assert_services_file_collection(root: Path, bundle: dict[str, Any]) -> None:
    actual_eai_xml = collect_services_eai_xml(root)
    assert actual_eai_xml, "dcp-services has no resources/eai XML files to validate"

    collected = set(_collect_project_files(root))
    missing_collected = sorted(set(actual_eai_xml) - collected)
    assert not missing_collected, (
        f"dcp-services collection missed {len(missing_collected)} resources/eai XML files; "
        f"sample={missing_collected[:5]}"
    )
    assert len(collected) > 8000, f"dcp-services collection still appears capped at {len(collected)} files"

    manifest = bundle.get("source_manifest", {})
    missing_manifest_eai = sorted(set(actual_eai_xml) - set(manifest))
    assert not missing_manifest_eai, (
        f"dcp-services source_manifest missed {len(missing_manifest_eai)} EAI XML files; "
        f"sample={missing_manifest_eai[:5]}"
    )
    for required in [
        "dcp-insurance/src/main/resources-env/WEB-INF/local/web.xml",
        "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/PanutClmApplicationController.java",
        "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/service/PanutClmApplicationService.java",
        "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/response/PanutClmApplicationInqrRes.java",
    ]:
        assert required in collected, f"dcp-services collection missed required stale-relevant file: {required}"
        assert required in manifest, f"dcp-services source_manifest missed required stale-relevant file: {required}"


def assert_services_eai_xml_index(root: Path, eai_items: list[dict[str, Any]]) -> None:
    actual_eai_xml = collect_services_eai_xml(root)
    service_xml = [rel for rel in actual_eai_xml if rel.endswith("_service.xml")]
    xml_items = [
        item
        for item in eai_items
        if any("resources/eai/" in str(evidence.get("path")) and str(evidence.get("path")).endswith(".xml") for evidence in item.get("evidence", []))
    ]
    known_items = [item for item in xml_items if str(item.get("interface_id") or "").strip()]
    indexed_xml_paths = {
        str(evidence.get("path"))
        for item in xml_items
        for evidence in item.get("evidence", [])
        if "resources/eai/" in str(evidence.get("path")) and str(evidence.get("path")).endswith(".xml")
    }
    missing_indexed = sorted(set(service_xml) - indexed_xml_paths)
    assert not missing_indexed, (
        f"dcp-services EAI XML index missed {len(missing_indexed)} *_service.xml files; "
        f"sample={missing_indexed[:5]}"
    )
    assert len(known_items) >= 50, f"dcp-services known EAI interface_id count is {len(known_items)}"
    for item in known_items:
        interface_id = str(item.get("interface_id") or "")
        xml_evidence = [
            evidence
            for evidence in item.get("evidence", [])
            if "resources/eai/" in str(evidence.get("path")) and str(evidence.get("path")).endswith(".xml")
        ]
        assert xml_evidence, f"EAI item missing XML evidence: {item}"
        for evidence in xml_evidence:
            assert interface_id in str(evidence.get("symbol") or evidence.get("name") or ""), evidence
            assert str(evidence.get("reason") or "").strip(), evidence


def collect_services_eai_xml(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.glob("**/resources/eai/**/*.xml") if path.is_file())


if __name__ == "__main__":
    main()
