from __future__ import annotations

import json
import zipfile
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = ROOT / "docs" / "project-knowledge-packs" / "v1"
AIOPS_DOCS_ZIP = ROOT / "docs" / "project-knowledge-packs.zip"

DOC_FILES = [
    "00-index.md",
    "01-repository-map.md",
    "02-build-and-runtime.md",
    "03-system-boundaries.md",
    "04-domain-glossary.md",
    "05-api-and-contracts.md",
    "06-data-model.md",
    "06-frontend-css-and-dom.md",
    "07-state-and-data-propagation.md",
    "08-integrations.md",
    "09-security-auth-privacy.md",
    "10-testing-and-quality.md",
    "11-operations-and-deployment.md",
    "12-change-playbooks.md",
    "99-gaps-and-questions.md",
    "_worklog.md",
]


PACKS: dict[str, dict[str, object]] = {
    "drt-front": {
        "label": "DRT Front",
        "source": "../ref/drt-front-main",
        "agent": "drt-front-developer",
        "summary": "DRT customer-facing Vue 3/Vite/TypeScript front-end. Source is usually under `dev/`, with public assets one level above.",
        "stack": "Vue 3, Vite, TypeScript, Vue Router 4, Pinia, Axios, Sass, SSR entry/server assets, shared public resources.",
        "evidence": [
            "ref/drt-front-main/dev/package.json:2 name=dcp-front-frame",
            "ref/drt-front-main/dev/package.json:6 scripts serve/build/ssr",
            "ref/drt-front-main/dev/package.json:25 dependencies vue/vue-router/pinia/axios",
            "ref/drt-front-main/dev/vite.config.ts:4 proxy to api.t.drt.samsunglife.kr",
            "ref/drt-front-main/dev/src/router/index.ts:1 createRouter",
            "ref/drt-front-main/dev/src/module/DrtHttpClient.ts:1 axios wrapper",
            "ref/drt-front-main/dev/src/store/ApplicationMaster.ts:2 Pinia store",
        ],
        "areas": [
            "`dev/src/router/**`: customer route families for main, product, application, coverage analysis, event, community, mypage, support, and digital agent.",
            "`dev/src/view/**/*.vue`: screen components reached by route modules.",
            "`dev/src/components/**/*.vue`: shared layouts, modals, UI controls, and domain components.",
            "`dev/src/store/*.ts`: Pinia stores for application, product, calculator, session, cart, recent calculation, and maintenance state.",
            "`dev/src/module/service/**/*.ts`: typed service/API functions used by views, modals, stores, and guards.",
            "`dev/src/module/DrtHttpClient.ts`: Axios wrapper, loading, session timeout, system block, Adobe response, alert/error handling.",
            "`public/resource/**`: fonts, styles, images, lottie, video, and browser/static assets.",
        ],
        "flows": [
            "Route -> view -> modal/component -> Pinia store -> service -> DrtHttpClient -> DRT API.",
            "Application subscription flows span application route modules, application stores, product plan services, and many modal components.",
            "Coverage analysis flows span `coverageAnalysis` routes, result components, stores, and service methods.",
            "System block/session behavior is global through `DrtHttpClient`, `SessionTimeout`, and `SystemMaintenance`.",
        ],
        "api": [
            "`vite.config.ts` proxies `/api` and `/auth` to the internal DRT API host in localhost mode.",
            "`DrtHttpClient` normalizes `DrtHttpResponse<T>` with `code`, `message`, `data`, auth flags, Adobe fields, and loading behavior.",
            "Service files under `src/module/service/**` should be paired with route/view/store consumers before payload edits.",
        ],
        "verification": [
            "`cd dev && yarn install --offline` installs dependencies from the offline cache/lockfile when needed.",
            "`cd dev && yarn start` is the default local frontend run command.",
            "`cd dev && yarn run build:local` is the preferred local build verification when a full production build is too broad.",
            "Use DOM/text/CSS assertions plus screenshot path for human visual confirmation.",
        ],
        "playbooks": [
            "For a route change, read route file, target view, guards, affected store, and service call before editing.",
            "For a payload field, trace view/model/store/service/DrtHttpClient and downstream API contract.",
            "For CSS/layout, inspect scoped/global style location, containing block, public assets, and existing class naming.",
        ],
    },
    "drt-api": {
        "label": "DRT API",
        "source": "../ref/drt-api-main",
        "agent": "drt-backend-developer",
        "summary": "DRT customer API backend. Spring Boot jar using drt-core, web/JDBC, Redis/session, Kafka, DynamoDB, MyBatis, auth/crypto plugins, and Oracle-oriented mapper XML.",
        "stack": "Maven, Spring Boot, Java, Spring MVC, JDBC, Redis/session, Kafka, DynamoDB, MyBatis, validation, retry, Lombok, Oracle JDBC.",
        "evidence": [
            "ref/drt-api-main/pom.xml:14 artifactId=drt-api",
            "ref/drt-api-main/pom.xml:24 drt-core dependency",
            "ref/drt-api-main/pom.xml:33 spring-boot-starter-web",
            "ref/drt-api-main/pom.xml:47 spring-boot-starter-data-redis",
            "ref/drt-api-main/pom.xml:60 spring-kafka",
            "ref/drt-api-main/pom.xml:67 mybatis-spring-boot-starter",
            "ref/drt-api-main/src/main/java/com/samsunglife/drt/api/Application.java:17 SpringBootApplication",
            "ref/drt-api-main/src/main/resources/mapper/pd/drt/PdDirectMapper.xml:1 mapper XML",
        ],
        "areas": [
            "`src/main/java/com/samsunglife/drt/api/cm`: common/auth/banner/menu/log/block/HTTP/TCP/masking utilities.",
            "`pd`, `of`, `cv`, `an`, `et`, `mp`, `cu`, `qg`, `da`: domain controller/service/biz/mapper/model packages.",
            "`src/main/resources/mapper/**`: MyBatis SQL mapped to Java mapper interfaces.",
            "`src/main/resources/application-*.properties` and `*/env.properties`: runtime profile configuration.",
            "`src/main/resources/template/**`: mail/document templates.",
            "`src/main/resources/*/plugin/**`: ksign/transkey and other closed-network plugin resources.",
        ],
        "flows": [
            "Controller mapping -> request/model -> service/biz -> mapper interface -> MyBatis XML -> response wrapper.",
            "Subscription/offering APIs under `of/drt` coordinate direct subscription steps, plan input, underwriting, postback, and session state.",
            "Product APIs under `pd/**` coordinate product lists, plans, calculation, treaty, shopping cart, and display content.",
            "Digital Agent APIs include normal JSON endpoints and text-event-stream endpoints.",
        ],
        "api": [
            "Spring annotations define the public API surface: `@RestController`, `@RequestMapping`, `@PostMapping`, `@GetMapping`.",
            "Mapper XML statement ids and Java mapper signatures must match before any SQL edit.",
            "Redis/Kafka/Dynamo/external client code must be reviewed for retry, timeout, masking, and profile config.",
        ],
        "verification": [
            "`mvn package` as broad backend verification.",
            "`mvn -DskipTests package` when external resources prevent tests from running locally.",
            "For SQL-only changes, pair static mapper namespace/id checks with targeted service/controller compile if full Maven is blocked.",
        ],
        "playbooks": [
            "For endpoint change, trace controller method, model, service, mapper interface, XML, profile config, and frontend caller.",
            "For SQL change, verify Java mapper method, parameter names, result DTO, XML namespace, and dynamic conditions.",
            "For auth/OCR/crypto/plugin work, stop unless the exact resource/profile ownership is clear.",
        ],
    },
    "drt-cms": {
        "label": "DRT CMS",
        "source": "../ref/drt-cms-main",
        "agent": "drt-cms-front-developer or drt-cms-backend-developer by target path",
        "summary": "Integrated DRT admin CMS repository. Root Maven parent contains `backend` and `frontend`; backend is Spring Boot 3/Java 17 admin API and frontend is Quasar/Vue 3 admin UI.",
        "stack": "Maven parent, Java 17, Spring Boot 3, MyBatis/Dynamic SQL, Redis/session, WebFlux/WebSocket, Quasar, Vue 3, TypeScript, Pinia, Axios, ag-grid, Cypress.",
        "evidence": [
            "ref/drt-cms-main/pom.xml:16 artifactId=drt-cms-parent",
            "ref/drt-cms-main/pom.xml:39 java.version=17",
            "ref/drt-cms-main/pom.xml:52 modules backend/frontend",
            "ref/drt-cms-main/backend/pom.xml:10 artifactId=drt-cms-backend",
            "ref/drt-cms-main/frontend/package.json:2 name=edirect",
            "ref/drt-cms-main/frontend/package.json:8 quasar scripts",
            "ref/drt-cms-main/frontend/src/router/routes.ts:17 asyncRouterMap",
            "ref/drt-cms-main/backend/src/main/resources/mybatis/sql/cms/ManagerRepository.xml:1 mapper XML",
        ],
        "areas": [
            "`frontend/src/router/routes*.ts`: admin route families for operation, report, event, content, board, marketing-tool, consult, system, embd, batch, digital-agent.",
            "`frontend/src/views/**`: list/detail/modal/admin screens.",
            "`frontend/src/services/**` and `model/**`: API service classes and field/model metadata.",
            "`frontend/src/components/plugins/grid/**`: ag-grid/pagination/excel shared admin table behavior.",
            "`backend/src/main/java/com/samsunglife/drt/cms/rest/**`: REST resources under `/api/**`.",
            "`backend/src/main/java/com/samsunglife/drt/cms/modules/**`: service/repository/domain/support packages.",
            "`backend/src/main/resources/mybatis/sql/**`: MyBatis XML by domain.",
            "`erd/**` and `genie-sql/**`: admin database/domain reference inputs.",
        ],
        "flows": [
            "Frontend route -> view/list/detail/modal -> service/model -> backend `/api/**` resource -> service -> repository/domain/MyBatis.",
            "Admin grid flows share ag-grid, pagination, excel download/upload, and service query contracts.",
            "Backend resource flows often return list/count/empty/detail/save/delete/excel/download-task variants.",
            "Security/session/CTI/OAM behavior sits outside ordinary CRUD and must be scoped explicitly.",
        ],
        "api": [
            "`frontend/src/boot/axios.ts` owns Axios base API behavior and auth/session error handling.",
            "Backend `*Resource` classes under `/api` define admin endpoints and often pair with generated domain/service/repository files.",
            "MyBatis XML under `backend/src/main/resources/mybatis/sql/**` is the persistence contract; generated domain/support classes should not be edited casually.",
        ],
        "verification": [
            "`mvn package` from repo root for integrated backend/frontend build when feasible.",
            "`cd frontend && yarn install --offline` installs frontend dependencies from the offline cache/lockfile when needed.",
            "`cd frontend && yarn run dev` is the default admin UI run command.",
            "`cd frontend && yarn run lint` or `yarn run build` for admin UI work.",
            "For backend-only edits, use backend module Maven compile/package plus static MyBatis namespace/id checks if external profile blocks runtime tests.",
        ],
        "playbooks": [
            "For frontend UI, trace route, view, service, model fields, grid/excel/pagination, and backend endpoint.",
            "For backend API, trace Resource, Service, Repository/domain/support, MyBatis XML, frontend service caller, and permission/security effects.",
            "For CMS generated domain/DSL, stop unless regeneration ownership is explicit.",
        ],
    },
    "dcp-front": {
        "label": "DCP Front",
        "source": "docs/reference-samples/good-knowledge-base/dcp-front",
        "agent": "dcp-front-developer",
        "summary": "DCP Vue 2 front-end knowledge seed for route/view/Vuex DataStore/API/CSS/browser verification work.",
        "stack": "Vue 2.7, Vue CLI, Vue Router 3, Vuex 3, Options API, Axios, mobile/PC screen trees, Playwright verification assets when present.",
        "evidence": [
            "docs/reference-samples/good-knowledge-base/dcp-front/docs/knowledge/01-repository-map.md",
            "docs/samsunglife-dcp-overview.md:8 dcp-front overview",
        ],
        "areas": [
            "`src/router/**`: route definitions.",
            "`src/views/**`: screen components.",
            "`src/store/modules/com/DataStore.js`: shared state carrier.",
            "`src/plugins/com/Common.js`: common flow utility and claim continuation logic.",
            "`src/components/**`: common UI and modal components.",
        ],
        "flows": [
            "route -> view -> DataStore/store -> API/client -> downstream consumer.",
            "Insurance claim and state propagation flows require positional array and save/load payload checks.",
        ],
        "api": ["Axios/Vue.$http call sites must be traced from current files before edits."],
        "verification": ["Use the narrowest lint/build/Playwright/DOM fallback documented in the target repo."],
        "playbooks": ["Copy this pack, then replace every sample claim with current target repo path:line evidence before implementation."],
    },
    "dcp-services": {
        "label": "DCP Services",
        "source": "docs/reference-samples/good-knowledge-base/dcp-services",
        "agent": "dcp-backend-developer",
        "summary": "DCP Java/Spring/Maven backend knowledge seed for controller/service/Redis/EAI/MyBatis/verification work.",
        "stack": "Maven multi-module, Java 8, Spring MVC, MyBatis, Oracle, Redis, EAI XML/service calls, batch/async modules.",
        "evidence": [
            "docs/reference-samples/good-knowledge-base/dcp-services/docs/knowledge/01-repository-map.md",
            "docs/samsunglife-dcp-overview.md:9 dcp-services overview",
        ],
        "areas": [
            "`pom.xml` and module poms: module boundaries.",
            "`*/src/main/java/**/controller`: HTTP boundaries.",
            "`*/src/main/java/**/service`: business logic.",
            "`*/src/main/resources/**`: Spring, MyBatis, resources-env, EAI XML.",
            "`resources/eai/**/*.xml`: EAI interface metadata.",
        ],
        "flows": [
            "controller -> service -> repository/mapper -> XML/EAI/Redis -> response DTO.",
            "Batch/async flows require scheduler/executor/resource-env checks.",
        ],
        "api": ["EAI interface id, service id, DTO fields, MyBatis statement id, and Redis key must be verified from current files."],
        "verification": ["Use module-specific Maven compile/package and static EAI/MyBatis path checks when full build is blocked."],
        "playbooks": ["Copy this pack, then replace every sample claim with current target repo path:line evidence before implementation."],
    },
}


def main() -> None:
    PACK_ROOT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "v1",
        "generated_by": "scripts/generate-project-knowledge-packs.py",
        "profiles": sorted(PACKS),
        "document_files": DOC_FILES,
        "zip_layout": "extract project-knowledge-packs.zip directly under D:/aiops/docs",
    }
    (PACK_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PACK_ROOT / "README.md").write_text(_root_readme(), encoding="utf-8")
    for profile, facts in PACKS.items():
        write_pack(profile, facts)
    write_aiops_docs_zip()


def write_pack(profile: str, facts: dict[str, object]) -> None:
    base = PACK_ROOT / profile
    knowledge = base / "docs" / "knowledge"
    (knowledge / "apis").mkdir(parents=True, exist_ok=True)
    (knowledge / "data").mkdir(parents=True, exist_ok=True)
    (knowledge / "flows").mkdir(parents=True, exist_ok=True)
    (knowledge / "modules").mkdir(parents=True, exist_ok=True)
    (knowledge / "decisions").mkdir(parents=True, exist_ok=True)
    (base / "README.md").write_text(_pack_readme(profile, facts), encoding="utf-8")
    for name in DOC_FILES:
        (knowledge / name).write_text(render_doc(profile, facts, name), encoding="utf-8")
    (knowledge / "flows" / f"{profile}-primary-flow.md").write_text(render_flow_doc(profile, facts), encoding="utf-8")
    (knowledge / "modules" / f"{profile}-module-map.md").write_text(render_module_doc(profile, facts), encoding="utf-8")
    (knowledge / "apis" / f"{profile}-api-index.md").write_text(render_api_doc(profile, facts), encoding="utf-8")
    (knowledge / "data" / f"{profile}-data-index.md").write_text(render_data_doc(profile, facts), encoding="utf-8")
    (knowledge / "decisions" / "000-knowledge-pack-seed.md").write_text(render_decision_doc(profile, facts), encoding="utf-8")


def write_aiops_docs_zip() -> None:
    if AIOPS_DOCS_ZIP.exists():
        AIOPS_DOCS_ZIP.unlink()
    with zipfile.ZipFile(AIOPS_DOCS_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for profile in sorted(PACKS):
            source = PACK_ROOT / profile / "docs" / "knowledge"
            for path in sorted(source.rglob("*")):
                if not path.is_file() or path.name == ".DS_Store":
                    continue
                relative = path.relative_to(source)
                archive.write(path, Path(profile) / "knowledge" / relative)


def frontmatter(profile: str, facts: dict[str, object], title: str) -> str:
    return dedent(
        f"""\
        ---
        kiwi_knowledge_pack_version: "v1"
        profile: "{profile}"
        title: "{title}"
        source_reference: "{facts['source']}"
        copy_mode: "seed; verify and replace evidence in the target project"
        ---

        """
    )


def render_doc(profile: str, facts: dict[str, object], name: str) -> str:
    title = name.removesuffix(".md")
    evidence = bullet(facts["evidence"])
    areas = bullet(facts["areas"])
    flows = bullet(facts["flows"])
    api = bullet(facts["api"])
    verification = bullet(facts["verification"])
    playbooks = bullet(facts["playbooks"])
    common = {
        "00-index.md": f"# {facts['label']} Knowledge Pack Index\n\n{facts['summary']}\n\n## Required Reading Order\n\n{bullet(DOC_FILES)}\n\n## Evidence Seeds\n\n{evidence}\n",
        "01-repository-map.md": f"# Repository Map\n\n## Stack\n\n{facts['stack']}\n\n## Areas\n\n{areas}\n\n## Evidence\n\n{evidence}\n",
        "02-build-and-runtime.md": f"# Build And Runtime\n\n## Runtime Summary\n\n{facts['summary']}\n\n## Verification/Build Commands\n\n{verification}\n\n## Evidence\n\n{evidence}\n",
        "03-system-boundaries.md": f"# System Boundaries\n\n## Primary Boundaries\n\n{areas}\n\n## Cross-Boundary Flows\n\n{flows}\n",
        "04-domain-glossary.md": f"# Domain Glossary\n\n## Terms\n\n{glossary(profile)}\n",
        "05-api-and-contracts.md": f"# API And Contracts\n\n## Contract Seeds\n\n{api}\n\n## Flow Cross-Checks\n\n{flows}\n",
        "06-data-model.md": f"# Data Model\n\n## Data/State Seeds\n\n{data_model(profile, facts)}\n\n## Evidence\n\n{evidence}\n",
        "06-frontend-css-and-dom.md": f"# Frontend CSS And DOM\n\n## Frontend Notes\n\n{frontend_css(profile)}\n",
        "07-state-and-data-propagation.md": f"# State And Data Propagation\n\n## Propagation Flows\n\n{flows}\n\n## Required Checks\n\n{state_checks(profile)}\n",
        "08-integrations.md": f"# Integrations\n\n## Integration Seeds\n\n{integrations(profile)}\n",
        "09-security-auth-privacy.md": f"# Security Auth Privacy\n\n## Guardrails\n\n{security(profile)}\n",
        "10-testing-and-quality.md": f"# Testing And Quality\n\n## Commands/Fallbacks\n\n{verification}\n\n## Quality Gate\n\n- Read current files before edits.\n- Keep diffs minimal.\n- Record command output or exact fallback.\n",
        "11-operations-and-deployment.md": f"# Operations And Deployment\n\n## Operational Inputs\n\n{operations(profile)}\n",
        "12-change-playbooks.md": f"# Change Playbooks\n\n## Playbooks\n\n{playbooks}\n",
        "99-gaps-and-questions.md": "# Gaps And Questions\n\n- Replace seed evidence with target repo path:line evidence after copying.\n- Mark unknown ownership before edits.\n- Ask user before deployment, secret, auth/session, generated-code, or DB-contract changes.\n",
        "_worklog.md": f"# Worklog\n\n- v1 seed generated from `{facts['source']}` for `{profile}`.\n- Next maintainer must refresh evidence after copying into a target project.\n",
    }
    return frontmatter(profile, facts, title) + common[name].rstrip() + "\n\n" + quality_appendix(profile, facts, name) + "\n"


def render_flow_doc(profile: str, facts: dict[str, object]) -> str:
    return (
        frontmatter(profile, facts, f"{profile} primary flow")
        + f"# Primary Flow\n\n{bullet(facts['flows'])}\n\n## Required Evidence\n\n{bullet(facts['evidence'])}\n\n"
        + quality_appendix(profile, facts, f"{profile}-primary-flow.md")
        + "\n"
    )


def render_module_doc(profile: str, facts: dict[str, object]) -> str:
    return (
        frontmatter(profile, facts, f"{profile} module map")
        + f"# Module Map\n\n{bullet(facts['areas'])}\n\n"
        + quality_appendix(profile, facts, f"{profile}-module-map.md")
        + "\n"
    )


def render_api_doc(profile: str, facts: dict[str, object]) -> str:
    return (
        frontmatter(profile, facts, f"{profile} api index")
        + f"# API Index\n\n{bullet(facts['api'])}\n\n"
        + quality_appendix(profile, facts, f"{profile}-api-index.md")
        + "\n"
    )


def render_data_doc(profile: str, facts: dict[str, object]) -> str:
    return (
        frontmatter(profile, facts, f"{profile} data index")
        + f"# Data Index\n\n{data_model(profile, facts)}\n\n"
        + quality_appendix(profile, facts, f"{profile}-data-index.md")
        + "\n"
    )


def render_decision_doc(profile: str, facts: dict[str, object]) -> str:
    return (
        frontmatter(profile, facts, "knowledge pack seed decision")
        + f"# Decision: v1 Knowledge Pack Seed\n\nUse this pack as a starting context for `{profile}`. Do not treat seed evidence as target-project truth after installation; verify every claim against current files.\n\n"
        + quality_appendix(profile, facts, "000-knowledge-pack-seed.md")
        + "\n"
    )


def quality_appendix(profile: str, facts: dict[str, object], doc_name: str) -> str:
    central_root = f"D:/aiops/docs/{profile}"
    focus = profile_focus(profile)
    return "\n".join(
        [
            "## Worker Startup Checklist",
            "",
            f"- Resolve the active project key as `{profile}` before using this pack.",
            f"- Read `{central_root}/project-info/project-summary.md` and `{central_root}/project-info/architecture-map.md` before broad analysis.",
            f"- Read `{central_root}/knowledge/00-index.md` and this document only when the task touches the matching area.",
            "- Treat every statement here as seed knowledge. Confirm the relevant claim against the current project files before changing code.",
            "- If this document conflicts with current code, current code wins and the conflict must be reported.",
            "",
            "## Current-file Verification",
            "",
            "- Search the current project for the named route, screen, controller, service, store, mapper, resource, or config before relying on this guide.",
            "- Open the nearest owner file and at least one caller/consumer before changing a shared contract.",
            "- Record path:line evidence from the current project in the final report or worklog.",
            "- Do not paste a full large generated index into a prompt; read targeted sections and cite specific files.",
            "- If a required file is missing, mark this pack stale for that area and continue from current-file discovery.",
            "",
            "## Profile-specific Focus",
            "",
            bullet(focus),
            "",
            "## Evidence Refresh Targets",
            "",
            bullet(facts["evidence"]),
            "",
            "## Change Risk Flags",
            "",
            "- Shared state, route registration, request/response DTO, SQL mapper, EAI/external interface, auth/session, generated code, deployment profile, and public asset changes are higher risk.",
            "- For higher-risk changes, expand the current-file trace to entrypoint, producer, carrier, persistence/cache/session, downstream consumer, and verification surface.",
            "- For frontend layout/CSS work, include wrapper, scoped/global style location, selector specificity, overflow/positioning, and DOM mutation checks.",
            "- For backend persistence/API work, include controller/resource, service, model/DTO, mapper/repository, XML/query, profile config, and caller checks.",
            "",
            "## Done Criteria For This Document",
            "",
            "- The task has a bounded owner area tied to this document.",
            "- Current files have been read and cited.",
            "- The planned change avoids unrelated refactors and generated-output churn.",
            "- Focused verification or a concrete fallback check is selected before edits finish.",
            f"- Unknowns are written to `{central_root}/knowledge/99-gaps-and-questions.md` when they affect future work.",
        ]
    )


def profile_focus(profile: str) -> list[str]:
    return {
        "drt-front": [
            "Route module and target Vue screen/component ownership.",
            "Pinia store and service call propagation.",
            "DrtHttpClient behavior, loading, session timeout, system block, and Adobe response side effects.",
            "Vite proxy/public asset/build mode implications.",
        ],
        "drt-api": [
            "Spring controller/resource mapping and request/response model.",
            "Service/biz package ownership and MyBatis mapper interface/XML pairing.",
            "Redis, Kafka, DynamoDB, OCR/NICE/Toss/Ksign/Transkey integration boundary.",
            "Profile properties, masking, templates, and plugin resource packaging.",
        ],
        "drt-cms": [
            "Frontend route/view/service/model/grid path versus backend resource/service/repository path.",
            "Admin grid, pagination, excel upload/download, modal, and permission behavior.",
            "Generated domain/support classes and MyBatis XML regeneration sensitivity.",
            "Security/session/CTI/OAM/static resource impact.",
        ],
        "dcp-front": [
            "Vue route/view/component ownership and mobile/PC channel path.",
            "Vuex DataStore, spotLoad/spotSave, route params, and downstream consumer propagation.",
            "Shared modal/component blast radius and legacy Options API conventions.",
            "Playwright/DOM/text/CSS fallback verification assets.",
        ],
        "dcp-services": [
            "Maven module boundary and controller/service package ownership.",
            "MyBatis mapper XML, DTO/request/response, Redis/cache, and EAI interface id propagation.",
            "resources-env/profile configuration and async/batch scheduler effects.",
            "Module-specific Maven/static EAI verification when full runtime tests are blocked.",
        ],
    }[profile]


def bullet(items: object) -> str:
    if not isinstance(items, list):
        return f"- {items}"
    return "\n".join(f"- {item}" for item in items)


def glossary(profile: str) -> str:
    terms = {
        "drt-front": ["DRT: direct customer insurance channel.", "DrtHttpClient: shared Axios wrapper.", "Pinia store: client state carrier.", "System block: global maintenance/block response handling."],
        "drt-api": ["Controller: Spring HTTP boundary.", "Mapper XML: MyBatis SQL contract.", "Redis/session: state/cache boundary.", "External client: NICE/Toss/Ksign/OCR/Dynamo/Kafka integration surface."],
        "drt-cms": ["CMS: DRT admin application.", "Resource: backend REST controller.", "Quasar view: admin screen.", "ag-grid: shared admin table/grid behavior.", "Generated domain/DSL: regeneration-sensitive backend model."],
        "dcp-front": ["DataStore: Vuex shared state carrier.", "spotLoad/spotSave: long-flow persistence API.", "route/view flow: screen navigation contract."],
        "dcp-services": ["EAI: external interface metadata/call.", "resources-env: profile-specific runtime config.", "Mapper: MyBatis persistence contract."],
    }
    return bullet(terms[profile])


def data_model(profile: str, facts: dict[str, object]) -> str:
    if profile == "drt-front":
        return bullet(["Pinia stores under `src/store/*.ts` are client state carriers.", "`DrtHttpResponse<T>` defines common response fields.", "Payload changes must trace view -> store/service -> backend contract."])
    if profile == "drt-api":
        return bullet(["Java model/DTO classes and MyBatis XML define request/response/persistence shapes.", "Mapper parameter names, XML ids, and response wrappers must be checked together."])
    if profile == "drt-cms":
        return bullet(["Frontend service model files define admin field metadata.", "Backend generated domain/support classes and MyBatis XML define persistence shape.", "`erd/**` and `genie-sql/**` are seed references, not automatic migration authority."])
    return bullet(facts["areas"])


def frontend_css(profile: str) -> str:
    if profile in {"drt-front", "drt-cms", "dcp-front"}:
        return bullet(["Identify scoped vs global style location before edits.", "Trace containing block, selector specificity, and shared component usage.", "Use DOM/text/CSS checks and screenshot path for human visual confirmation."])
    return "- Not a frontend-first profile. If UI artifacts are generated, verify the consumer frontend separately."


def state_checks(profile: str) -> str:
    if profile == "drt-front":
        return bullet(["route -> view -> store -> service -> DrtHttpClient", "Session/system block/Adobe response side effects"])
    if profile == "drt-cms":
        return bullet(["route -> view -> service/model -> backend resource", "grid/pagination/excel state", "auth/permission/session effects"])
    return bullet(["controller/resource -> service -> mapper/repository -> DTO/response", "cache/session/EAI/external side effects"])


def integrations(profile: str) -> str:
    if profile == "drt-front":
        return bullet(["DRT API proxy via Vite.", "Adobe response data.", "Session timeout/system maintenance handling.", "SSE agent client where used."])
    if profile == "drt-api":
        return bullet(["Redis/session/cache.", "Kafka.", "DynamoDB logging.", "NICE/Toss/Ksign/OCR/Transkey plugin resources.", "Mail/document templates."])
    if profile == "drt-cms":
        return bullet(["Frontend Axios/admin API.", "Backend Redis/session/security/WebSocket/WebFlux.", "CTI static resources.", "Firo/file/excel/batch utilities.", "EAI modules under embd/pd where present."])
    if profile == "dcp-services":
        return bullet(["EAI XML/service calls.", "Redis.", "Oracle/MyBatis.", "Batch/async scheduler."])
    return bullet(["Backend API calls.", "Browser verification assets.", "Shared state persistence."])


def security(profile: str) -> str:
    if profile in {"drt-api", "drt-cms", "dcp-services"}:
        return bullet(["Do not change auth/session/security filters without explicit scope.", "Treat plugin resources, certificates, secret/profile files, masking, and personal data as high risk.", "Verify logging/masking behavior before adding fields."])
    return bullet(["Do not expose personal data in UI/logs.", "Trace auth/session redirects and system-block handling before frontend changes.", "Do not modify global interceptors without explicit scope."])


def operations(profile: str) -> str:
    if profile == "drt-front":
        return bullet(["Dockerfile_dev/stage/release/dr and SSR server exist near the Vite app.", "Do not change build mode/proxy/publicDir without explicit scope."])
    if profile == "drt-api":
        return bullet(["Dockerfile_dev/stage/release/dr and profile properties/env resources exist.", "Closed-network plugin resources must stay packaged."])
    if profile == "drt-cms":
        return bullet(["Root Maven parent builds backend/frontend modules.", "Frontend Quasar build scripts include dev/stage/release/dr.", "Backend profile config and CTI/static/plugin resources are operational inputs."])
    return bullet(["Use repository-local build/profile docs.", "Do not change deployment files without explicit user confirmation."])


def _root_readme() -> str:
    return dedent(
        """\
        # KIWI Project Knowledge Packs v1

        These packs are seed documents installed under `D:/aiops/docs/<project-key>/knowledge/` before running lightwork, ultrawork, or superpowers.

        Rules:

        - Treat every file as a starting context, not target-project truth.
        - After copying, replace seed evidence with current target repo `path:line` evidence.
        - Keep `kiwi_knowledge_pack_version: "v1"` front matter so KIWI can identify the pack version.
        """
    )


def _pack_readme(profile: str, facts: dict[str, object]) -> str:
    return dedent(
        f"""\
        # {facts['label']} Knowledge Pack v1

        Source reference: `{facts['source']}`
        Implementation agent: `{facts['agent']}`

        Install this pack as `D:/aiops/docs/{profile}/knowledge/`, then refresh evidence from current files before making implementation decisions.
        """
    )


if __name__ == "__main__":
    main()
