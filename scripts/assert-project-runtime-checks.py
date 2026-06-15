from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
sys.path.insert(0, str(ROOT))

import backend.app.project_runtime as project_runtime_module  # noqa: E402
from backend.app.project_runtime import collect_project_runtime  # noqa: E402


DCP_ROOT = Path("/Users/jules/Desktop/work/untitle/dcp")
REF_ROOT = PARENT / "ref"


def main() -> None:
    assert_dcp_services_runtime()
    assert_dcp_front_runtime()
    assert_dcp_front_node10_runtime()
    assert_dcp_front_nested_node10_runtime()
    assert_dcp_front_node10_folder_does_not_fallback_to_path()
    assert_dcp_front_runtime_mismatch_uses_preferred_node10()
    assert_managed_backend_runtimes()
    assert_drt_runtime_refs()
    assert_api_and_frontend_wiring()
    print("project runtime checks assertions passed")


def assert_dcp_services_runtime() -> None:
    root = DCP_ROOT / "dcp-services-mevelop"
    if not root.exists():
        root = make_dcp_services_fixture()
    runtime = collect_project_runtime(root, {"status": "exists"})
    assert runtime["project_key"] == "dcp-services", runtime["project_key"]
    backend = runtime["components"]["backend"]
    assert backend["java_required"] == "8"
    assert backend["dcp_core"]["ok"] is True, backend["dcp_core"]
    assert "dcp-core" in backend["modules"], backend["modules"][:5]
    commands = {action["id"]: action["command"] for action in runtime["actions"]}
    assert commands["maven-clean"] == "mvn clean"
    assert commands["maven-compile"] == "mvn compile"
    assert commands["maven-test"] == "mvn test"
    assert_runtime_items(runtime, {"Java", "Maven", "Tomcat"})
    assert any(req["id"] == "dcp-core-reactor" and req["status"] == "ok" for req in runtime["requirements"])


def assert_dcp_front_runtime() -> None:
    root = DCP_ROOT / "dcp-front-develop"
    if not root.exists():
        root = make_front_fixture("dcp-front-develop", package_manager="npm", scripts={"serve": "vue-cli-service serve"})
    runtime = collect_project_runtime(root, {"status": "exists"})
    assert runtime["project_key"] == "dcp-front"
    frontend = runtime["components"]["frontend"]
    assert frontend["package_manager"] == "npm"
    assert frontend["node_required"] == "10"
    actions = {action["id"]: action for action in runtime["actions"]}
    assert actions["frontend-run"]["command"].endswith("npm run serve")
    assert "playwright-test" in actions
    assert_runtime_items(runtime, {"Node", "Npm"})


def assert_dcp_front_node10_runtime() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-qwencode-node10-") as raw_tmp:
        base = Path(raw_tmp)
        qwen_runtime = base / "qwencode"
        write_executable(qwen_runtime / "runtimes" / "node10" / "node", "#!/bin/sh\necho v10.24.1\n")
        write_executable(
            qwen_runtime / "runtimes" / "node10" / "npm",
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 6.14.18; else echo npm \"$@\"; fi\n",
        )
        root = make_front_fixture("dcp-front-develop", package_manager="npm", scripts={"serve": "vue-cli-service serve"})
        original = project_runtime_module.find_latest_qwencode_runtime
        project_runtime_module.find_latest_qwencode_runtime = lambda: qwen_runtime
        try:
            runtime = collect_project_runtime(root, {"status": "exists"})
        finally:
            project_runtime_module.find_latest_qwencode_runtime = original
        frontend = runtime["components"]["frontend"]
        assert frontend["node_runtime_folder"] == "runtimes/node10"
        assert frontend["managed_node_runtime"] is True
        assert frontend["node_executable"].endswith("/runtimes/node10/node")
        assert any(req["id"] == "node-version" and req["status"] == "ok" for req in runtime["requirements"])
        actions = {action["id"]: action for action in runtime["actions"]}
        command = actions["frontend-run"]["command"].replace("\\", "/")
        assert "/runtimes/node10/npm run serve" in command, command
        assert actions["frontend-run"]["status"] == "ready"


def assert_dcp_front_nested_node10_runtime() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-qwencode-node10-nested-") as raw_tmp:
        base = Path(raw_tmp)
        qwen_runtime = base / "qwencode"
        node10 = qwen_runtime / "runtimes" / "node10" / "node-v10.24.1-win-x64"
        write_executable(node10 / "node.exe", "#!/bin/sh\necho v10.24.1\n")
        write_executable(
            node10 / "npm.cmd",
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 6.14.18; else echo npm \"$@\"; fi\n",
        )
        root = make_front_fixture("dcp-front-develop", package_manager="npm", scripts={"serve": "vue-cli-service serve"})
        original_runtime = project_runtime_module.find_latest_qwencode_runtime
        project_runtime_module.find_latest_qwencode_runtime = lambda: qwen_runtime
        try:
            runtime = collect_project_runtime(root, {"status": "exists"})
        finally:
            project_runtime_module.find_latest_qwencode_runtime = original_runtime
        frontend = runtime["components"]["frontend"]
        assert frontend["node_runtime_present"] is True
        assert frontend["managed_node_runtime"] is True
        assert frontend["node_executable"].replace("\\", "/").endswith("/runtimes/node10/node-v10.24.1-win-x64/node.exe")
        assert frontend["managed_npm_executable"].replace("\\", "/").endswith("/runtimes/node10/node-v10.24.1-win-x64/npm.cmd")


def assert_dcp_front_node10_folder_does_not_fallback_to_path() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-qwencode-node10-empty-") as raw_tmp:
        base = Path(raw_tmp)
        qwen_runtime = base / "qwencode"
        (qwen_runtime / "runtimes" / "node10").mkdir(parents=True)
        root = make_front_fixture("dcp-front-develop", package_manager="npm", scripts={"serve": "vue-cli-service serve"})
        original_runtime = project_runtime_module.find_latest_qwencode_runtime
        project_runtime_module.find_latest_qwencode_runtime = lambda: qwen_runtime
        try:
            runtime = collect_project_runtime(root, {"status": "exists"})
        finally:
            project_runtime_module.find_latest_qwencode_runtime = original_runtime
        frontend = runtime["components"]["frontend"]
        assert frontend["node_runtime_present"] is True
        assert frontend["node_executable"] is None
        assert frontend["npm_executable"] is None
        node_item = next(item for item in runtime["items"] if item["name"] == "Node")
        npm_item = next(item for item in runtime["items"] if item["name"] == "Npm")
        assert node_item["status"] == "missing", node_item
        assert npm_item["status"] == "missing", npm_item


def assert_dcp_front_runtime_mismatch_uses_preferred_node10() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-qwencode-node10-mismatch-") as raw_tmp:
        base = Path(raw_tmp)
        preferred_runtime = base / "qwencode"
        stale_runtime = base / "old-qwencode"
        make_qwen_runtime(preferred_runtime)
        make_qwen_runtime(stale_runtime)
        write_executable(preferred_runtime / "runtimes" / "node10" / "node", "#!/bin/sh\necho v10.24.1\n")
        write_executable(
            preferred_runtime / "runtimes" / "node10" / "npm",
            "#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 6.14.18; else echo npm \"$@\"; fi\n",
        )
        root = make_front_fixture("dcp-front-develop", package_manager="npm", scripts={"serve": "vue-cli-service serve"})
        write(root / "qwen.cmd", f'@echo off\ncall "{stale_runtime / "run-qwen.cmd"}" %*\n')
        original_runtime = project_runtime_module.find_latest_qwencode_runtime
        project_runtime_module.find_latest_qwencode_runtime = lambda: preferred_runtime
        try:
            runtime = collect_project_runtime(root, {"status": "exists"})
        finally:
            project_runtime_module.find_latest_qwencode_runtime = original_runtime
        qwen = runtime["qwen"]
        frontend = runtime["components"]["frontend"]
        assert qwen["runtime_mismatch"] is True, qwen
        assert Path(qwen["runtime_dir"]).resolve() == preferred_runtime.resolve(), qwen
        assert Path(qwen["project_runtime_dir"]).resolve() == stale_runtime.resolve(), qwen
        assert qwen["runtime_source"] == "preferred", qwen
        assert frontend["managed_node_runtime"] is True, frontend
        assert frontend["node_executable"].endswith("/runtimes/node10/node"), frontend
        assert any(req["id"] == "node-version" and req["status"] == "ok" for req in runtime["requirements"])


def assert_managed_backend_runtimes() -> None:
    with tempfile.TemporaryDirectory(prefix="kiwi-qwencode-runtimes-") as raw_tmp:
        base = Path(raw_tmp)
        qwen_runtime = base / "qwencode"
        write_executable(qwen_runtime / "runtimes" / "java8" / "bin" / "java", "#!/bin/sh\necho 'openjdk version \"1.8.0_372\"'\n")
        write_executable(qwen_runtime / "runtimes" / "java" / "bin" / "java", "#!/bin/sh\necho 'openjdk version \"17.0.10\"'\n")
        write_executable(
            qwen_runtime / "runtimes" / "maven3.6.3" / "bin" / "mvn",
            "#!/bin/sh\nif [ \"$1\" = \"-version\" ]; then echo 'Apache Maven 3.6.3'; else echo mvn \"$@\"; fi\n",
        )
        write_executable(
            qwen_runtime / "runtimes" / "tomcat9" / "bin" / "catalina",
            "#!/bin/sh\nif [ \"$1\" = \"version\" ]; then echo 'Server version: Apache Tomcat/9.0.115'; else echo catalina \"$@\"; fi\n",
        )
        original = project_runtime_module.find_latest_qwencode_runtime
        project_runtime_module.find_latest_qwencode_runtime = lambda: qwen_runtime
        try:
            dcp = collect_project_runtime(make_dcp_services_fixture(), {"status": "exists"})
            drt = collect_project_runtime(make_drt_api_fixture(), {"status": "exists"})
        finally:
            project_runtime_module.find_latest_qwencode_runtime = original

    dcp_backend = dcp["components"]["backend"]
    assert dcp_backend["java_runtime_folder"] == "runtimes/java8"
    assert dcp_backend["maven_runtime_folder"] == "runtimes/maven3.6.3"
    assert dcp_backend["tomcat_runtime_folder"] == "runtimes/tomcat9"
    assert dcp_backend["tomcat_deploy_module"] == "dcp-gateway"
    assert dcp_backend["tomcat_deploy_context"] == "dcp-gateway"
    assert dcp_backend["managed_java_runtime"] is True
    assert dcp_backend["managed_maven_runtime"] is True
    assert dcp_backend["managed_tomcat_runtime"] is True
    assert any(item["name"] == "Java" and item["major"] == 8 for item in dcp["items"])
    assert any(item["name"] == "Tomcat" and item["major"] == 9 for item in dcp["items"])
    assert any(req["id"] == "tomcat9-runtime" and req["status"] == "ok" for req in dcp["requirements"])
    dcp_clean = {action["id"]: action for action in dcp["actions"]}["maven-clean"]
    command = dcp_clean["command"].replace("\\", "/")
    assert "/runtimes/java8" in command and "/runtimes/maven3.6.3" in command, command
    assert dcp_clean["status"] == "ready"
    dcp_run = {action["id"]: action for action in dcp["actions"]}["backend-run"]
    run_command = dcp_run["command"].replace("\\", "/")
    assert "-pl dcp-gateway -am clean install" in run_command, run_command
    assert "-Ddeploy-path=" in run_command and "/runtimes/tomcat9/webapps/dcp-gateway" in run_command, run_command
    assert "/runtimes/tomcat9/bin/catalina run" in run_command, run_command
    assert dcp_run["status"] == "ready"

    drt_backend = drt["components"]["backend"]
    assert drt_backend["java_runtime_folder"] == "runtimes/java"
    assert drt_backend["managed_java_runtime"] is True
    assert any(item["name"] == "Java" and item["major"] == 17 for item in drt["items"])
    drt_run = {action["id"]: action for action in drt["actions"]}["backend-run"]
    assert "/runtimes/java" in drt_run["command"].replace("\\", "/"), drt_run["command"]
    assert drt_run["status"] == "ready"


def assert_drt_runtime_refs() -> None:
    cases = [
        (REF_ROOT / "drt-front-main", "drt-front", "frontend", "yarn", ">=20", None, "yarn start"),
        (REF_ROOT / "drt-api-main", "drt-api", "backend", None, "17", "mvn spring-boot:run", None),
        (REF_ROOT / "drt-cms-main", "drt-cms", "fullstack", "yarn", "17", "mvn spring-boot:run", "yarn run dev"),
    ]
    for root, key, kind, package_manager, required, backend_run, frontend_run in cases:
        if not root.exists():
            continue
        runtime = collect_project_runtime(root, {"status": "exists"})
        assert runtime["project_key"] == key, f"{root} -> {runtime['project_key']}"
        actions = {action["id"]: action for action in runtime["actions"]}
        if kind in {"backend", "fullstack"}:
            backend = runtime["components"]["backend"]
            assert backend["java_required"] == required, backend
            assert actions["backend-run"]["command"].endswith(backend_run), actions["backend-run"]["command"]
            assert "Tomcat" not in {item["name"] for item in runtime["items"]}, runtime["items"]
        if kind in {"frontend", "fullstack"}:
            frontend = runtime["components"]["frontend"]
            assert frontend["package_manager"] == package_manager
            assert frontend["node_required"] == ">=20"
            run_command = actions["frontend-run"]["command"].replace("\\", "/")
            install_command = actions["frontend-install"]["command"].replace("\\", "/")
            assert run_command.endswith(frontend_run), actions["frontend-run"]["command"]
            assert install_command.endswith("yarn install --offline"), actions["frontend-install"]["command"]
            if frontend.get("managed_yarn_executable"):
                assert "/runtimes/node/yarn" in install_command, install_command
            if key == "drt-front":
                assert Path(actions["frontend-install"]["cwd"]).name == "dev", actions["frontend-install"]
                assert Path(frontend["cwd"]).name == "dev", frontend
            if key == "drt-cms":
                assert Path(actions["frontend-install"]["cwd"]).name == "frontend", actions["frontend-install"]
                assert Path(frontend["cwd"]).name == "frontend", frontend
            yarn_item = next(item for item in runtime["items"] if item["name"] == "Yarn")
            assert yarn_item["status"] == "ok", yarn_item
            assert yarn_item["command"] == "offline metadata check; yarn --version intentionally skipped", yarn_item
            assert "registry.npmjs.org" not in str(yarn_item.get("detail", "")), yarn_item
            assert str(yarn_item.get("offline_mirror") or "").endswith("npm_packages"), yarn_item
            assert_runtime_items(
                runtime,
                {"Java", "Maven", "Node", "Yarn"} if kind == "fullstack" else {"Node", "Yarn"},
            )
    cms = REF_ROOT / "drt-cms-main"
    if cms.exists():
        frontend_only = collect_project_runtime(cms / "frontend", {"status": "exists"})
        assert frontend_only["components"]["backend"] is None
        assert frontend_only["components"]["frontend"]["package_manager"] == "yarn"
        assert_runtime_items(frontend_only, {"Node", "Yarn"})
        assert {action["id"] for action in frontend_only["actions"]} >= {"frontend-install", "frontend-run"}
        backend_only = collect_project_runtime(cms / "backend", {"status": "exists"})
        assert backend_only["components"]["backend"]["java_required"] == "17"
        assert backend_only["components"]["frontend"] is None
        assert_runtime_items(backend_only, {"Java", "Maven"})


def assert_api_and_frontend_wiring() -> None:
    main_py = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    page = (ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    css = (ROOT / "app" / "globals.css").read_text(encoding="utf-8")
    assert '"/api/projects/{project_id}/runtime/check"' in main_py
    assert '"/api/projects/{project_id}/runtime/actions/{action_id}"' in main_py
    for required in ["refreshRuntimeChecks", "runRuntimeAction", "runtime-action-button", "프로젝트 요구사항", "실행 액션"]:
        assert required in page, f"frontend missing {required}"
    for required in [".runtime-action-list", ".runtime-action-button", ".mini-action-button"]:
        assert required in css, f"css missing {required}"


def assert_runtime_items(runtime: dict, expected_names: set[str]) -> None:
    actual = {item["name"] for item in runtime["items"]}
    assert actual == expected_names, f"{runtime['project_key']} items {actual} != {expected_names}"


def make_dcp_services_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="kiwi-dcp-services-"))
    write(
        tmp / "pom.xml",
        """
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.samsunglife</groupId><artifactId>dcp</artifactId><version>0.0.1-SNAPSHOT</version>
  <packaging>pom</packaging>
  <properties><jdk-version>1.8</jdk-version></properties>
  <modules><module>dcp-core</module><module>dcp-gateway</module><module>dcp-insurance</module></modules>
</project>
""",
    )
    write(tmp / "dcp-core" / "pom.xml", pom("dcp-core", dependency=False))
    write(tmp / "dcp-gateway" / "pom.xml", pom("dcp-gateway", dependency=True))
    write(tmp / "dcp-gateway" / "webapp" / "WEB-INF" / "web.xml", "<web-app/>")
    write(tmp / "dcp-insurance" / "pom.xml", pom("dcp-insurance", dependency=True))
    return tmp


def make_front_fixture(name: str, package_manager: str, scripts: dict[str, str]) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix=f"kiwi-{name}-")) / name
    script_json = ", ".join(f'"{key}": "{value}"' for key, value in scripts.items())
    write(tmp / "package.json", f'{{"name":"{name}","scripts":{{{script_json}}},"dependencies":{{"vue":"^2.7.13"}}}}')
    if package_manager == "npm":
        write(tmp / "package-lock.json", "{}")
    else:
        write(tmp / "yarn.lock", "")
    return tmp


def make_drt_api_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="kiwi-drt-api-")) / "drt-api-main"
    write(
        tmp / "pom.xml",
        """
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>kr.co.drt</groupId><artifactId>drt-api</artifactId><version>0.0.1-SNAPSHOT</version>
  <properties><java.version>17</java.version></properties>
  <build><plugins><plugin><artifactId>spring-boot-maven-plugin</artifactId></plugin></plugins></build>
</project>
""",
    )
    write(
        tmp / "src" / "main" / "java" / "kr" / "co" / "drt" / "ApiApplication.java",
        "package kr.co.drt; @SpringBootApplication public class ApiApplication { public static void main(String[] args) {} }",
    )
    return tmp


def make_qwen_runtime(path: Path) -> None:
    write(path / "run-qwen.cmd", "@echo off\n")
    write(path / "app" / "cli.js", "console.log('qwen')\n")


def pom(artifact_id: str, dependency: bool) -> str:
    dep = (
        """
  <dependencies>
    <dependency><groupId>com.samsunglife</groupId><artifactId>dcp-core</artifactId><version>${project.version}</version></dependency>
  </dependencies>
"""
        if dependency
        else ""
    )
    return f"""
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>com.samsunglife</groupId><artifactId>dcp</artifactId><version>0.0.1-SNAPSHOT</version></parent>
  <artifactId>{artifact_id}</artifactId>
{dep}
</project>
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_executable(path: Path, text: str) -> None:
    write(path, text)
    path.chmod(0o755)


if __name__ == "__main__":
    main()
