from __future__ import annotations

import json
import os
import sys
import types
import tempfile
from pathlib import Path


class _StubHTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


if "fastapi" not in sys.modules:
    fastapi_stub = types.ModuleType("fastapi")
    fastapi_stub.HTTPException = _StubHTTPException
    sys.modules["fastapi"] = fastapi_stub

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.project_info import (  # noqa: E402
    PROJECT_INFO_ARTIFACT_NAMES,
    PROJECT_INFO_SCHEMA_VERSION,
    analyze_project_info,
    assert_project_info_loadable_for_work_modes,
    collect_project_info_stale_inputs,
    detect_project_info_profile,
    load_project_info_context,
    project_info_artifact_dir,
    validate_project_info_bundle,
)


REQUIRED_ARTIFACTS = {
    "project-summary",
    "architecture-map",
    "module-responsibility-map",
    "entrypoints",
    "key-flows",
    "api/eai-interface-index",
    "verification-guide",
}


def main() -> None:
    assert set(PROJECT_INFO_ARTIFACT_NAMES) >= REQUIRED_ARTIFACTS
    assert_backend_integration_points()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["KIWI_AIOPS_DOCS_DIR"] = str(Path(tmp) / "aiops-docs")
        root = Path(tmp) / "sample-project"
        make_sample_project(root)

        bundle = analyze_project_info(root, write=True)
        assert bundle["schema_version"] == PROJECT_INFO_SCHEMA_VERSION
        assert bundle["profile"]["key"] == "dcp-front"
        assert bundle["artifact_dir"] == project_info_artifact_dir(root).as_posix()
        assert REQUIRED_ARTIFACTS.issubset(set(bundle["artifacts"]))

        errors = validate_project_info_bundle(root, bundle)
        assert not errors, "valid bundle should not have validation errors: " + json.dumps(errors, ensure_ascii=False)

        assert_profile_detector(root)
        assert_artifact_files(root)
        assert_invalid_bundle_failures(root, bundle)
        assert_loadable_for_all_work_modes(root)
        assert_stale_detection(root, bundle)

    print("project info layer assertions passed")


def assert_backend_integration_points() -> None:
    main_py = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    prompt_builder_py = (ROOT / "backend" / "app" / "prompt_builder.py").read_text(encoding="utf-8")
    assert "summary[\"project_info\"] = _project_info_initialize_status(root)" in main_py
    assert "init_fast_path" in main_py
    assert "bundle = analyze_project_info(root, write=True)" in main_py
    assert "/api/projects/{project_id}/project-info" in main_py
    assert "load_project_info_context" in prompt_builder_py
    assert "project_info_context" in prompt_builder_py


def make_sample_project(root: Path) -> None:
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim").mkdir(parents=True)
    (root / "src" / "router").mkdir(parents=True)
    (root / "src" / "store" / "modules" / "com").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "components").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "sample-dcp-front",
                "scripts": {"build": "vue-cli-service build", "test": "vue-cli-service test:unit"},
                "dependencies": {"vue": "2.7.16", "vuex": "3.6.2", "axios": "1.7.0"},
                "devDependencies": {"@vue/cli-service": "3.12.1"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "src" / "router" / "index.js").write_text(
        "\n".join(
            [
                "import Vue from 'vue'",
                "import Router from 'vue-router'",
                "import ClaimIntro from '@/views/mo/mysamsunglife/claim/ClaimIntro.vue'",
                "Vue.use(Router)",
                "export default new Router({",
                "  routes: [{ path: '/claim/intro', name: 'ClaimIntro', component: ClaimIntro }]",
                "})",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src" / "views" / "mo" / "mysamsunglife" / "claim" / "ClaimIntro.vue").write_text(
        "\n".join(
            [
                "<template><section class=\"claim-intro\">보험금 청구</section></template>",
                "<script>",
                "import claimApi from '@/api/claim'",
                "export default {",
                "  name: 'ClaimIntro',",
                "  methods: { submitClaim() { return claimApi.saveClaim({ claimType: 'internet' }) } }",
                "}",
                "</script>",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src" / "api" / "claim.js").write_text(
        "\n".join(
            [
                "import axios from 'axios'",
                "export function saveClaim(payload) {",
                "  return axios.post('/api/claim/save', payload)",
                "}",
                "export default { saveClaim }",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src" / "store" / "modules" / "com" / "DataStore.js").write_text(
        "\n".join(
            [
                "export default {",
                "  namespaced: true,",
                "  state: { claimDraft: null },",
                "  mutations: { setClaimDraft(state, value) { state.claimDraft = value } }",
                "}",
            ]
        ),
        encoding="utf-8",
    )


def assert_profile_detector(root: Path) -> None:
    profile = detect_project_info_profile(root)
    assert profile["key"] == "dcp-front"
    assert profile["implementation_agent"] == "dcp-front-developer"

    with tempfile.TemporaryDirectory() as tmp:
        service_root = Path(tmp) / "dcp-services-mevelop"
        (service_root / "dcp-core" / "src" / "main" / "java").mkdir(parents=True)
        (service_root / "pom.xml").write_text(
            "<project><modules><module>dcp-core</module><module>dcp-gateway</module><module>dcp-insurance</module></modules></project>",
            encoding="utf-8",
        )
        backend_profile = detect_project_info_profile(service_root)
        assert backend_profile["key"] == "dcp-services"
        assert backend_profile["implementation_agent"] == "dcp-backend-developer"


def assert_artifact_files(root: Path) -> None:
    artifact_dir = project_info_artifact_dir(root)
    assert (artifact_dir / "project-info.json").exists()
    for artifact_name in REQUIRED_ARTIFACTS:
        assert (artifact_dir / f"{artifact_name}.md").exists(), f"missing markdown artifact: {artifact_name}"


def assert_invalid_bundle_failures(root: Path, bundle: dict[str, object]) -> None:
    missing_evidence_bundle = json.loads(json.dumps(bundle))
    missing_evidence_bundle["artifacts"]["project-summary"]["items"][0]["evidence"] = []
    errors = validate_project_info_bundle(root, missing_evidence_bundle)
    assert any("missing evidence" in error for error in errors), errors

    missing_path_bundle = json.loads(json.dumps(bundle))
    evidence = missing_path_bundle["artifacts"]["project-summary"]["items"][0]["evidence"][0]
    evidence["path"] = "src/does-not-exist.js"
    errors = validate_project_info_bundle(root, missing_path_bundle)
    assert any("missing evidence path" in error for error in errors), errors


def assert_loadable_for_all_work_modes(root: Path) -> None:
    assert_project_info_loadable_for_work_modes(root)
    for mode in ["fast", "ultrawork", "superpowers"]:
        context = load_project_info_context(root, mode, max_chars=20_000)
        assert "Project Info Layer" in context
        assert "project-summary" in context
        assert "Evidence" in context


def assert_stale_detection(root: Path, bundle: dict[str, object]) -> None:
    stale = collect_project_info_stale_inputs(root, bundle)
    assert not stale["is_stale"], stale

    source = root / "src" / "api" / "claim.js"
    source.write_text(source.read_text(encoding="utf-8") + "\nexport const changedForAssertion = true\n", encoding="utf-8")
    stale = collect_project_info_stale_inputs(root, bundle)
    assert stale["is_stale"], stale
    assert any(item["path"] == "src/api/claim.js" for item in stale["changed"]), stale


if __name__ == "__main__":
    main()
