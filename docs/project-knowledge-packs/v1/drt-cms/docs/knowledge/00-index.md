---
kiwi_knowledge_pack_version: "v1"
profile: "drt-cms"
title: "00-index"
source_reference: "../ref/drt-cms-main"
copy_mode: "seed; verify and replace evidence in the target project"
---

# DRT CMS Knowledge Pack Index

Integrated DRT admin CMS repository. Root Maven parent contains `backend` and `frontend`; backend is Spring Boot 3/Java 17 admin API and frontend is Quasar/Vue 3 admin UI.

## Required Reading Order

- 00-index.md
- 01-repository-map.md
- 02-build-and-runtime.md
- 03-system-boundaries.md
- 04-domain-glossary.md
- 05-api-and-contracts.md
- 06-data-model.md
- 06-frontend-css-and-dom.md
- 07-state-and-data-propagation.md
- 08-integrations.md
- 09-security-auth-privacy.md
- 10-testing-and-quality.md
- 11-operations-and-deployment.md
- 12-change-playbooks.md
- 99-gaps-and-questions.md
- _worklog.md

## Evidence Seeds

- ref/drt-cms-main/pom.xml:16 artifactId=drt-cms-parent
- ref/drt-cms-main/pom.xml:39 java.version=17
- ref/drt-cms-main/pom.xml:52 modules backend/frontend
- ref/drt-cms-main/backend/pom.xml:10 artifactId=drt-cms-backend
- ref/drt-cms-main/frontend/package.json:2 name=edirect
- ref/drt-cms-main/frontend/package.json:8 quasar scripts
- ref/drt-cms-main/frontend/src/router/routes.ts:17 asyncRouterMap
- ref/drt-cms-main/backend/src/main/resources/mybatis/sql/cms/ManagerRepository.xml:1 mapper XML

## Worker Startup Checklist

- Resolve the active project key as `drt-cms` before using this pack.
- Read `D:/aiops/docs/drt-cms/project-info/project-summary.md` and `D:/aiops/docs/drt-cms/project-info/architecture-map.md` before broad analysis.
- Read `D:/aiops/docs/drt-cms/knowledge/00-index.md` and this document only when the task touches the matching area.
- Treat every statement here as seed knowledge. Confirm the relevant claim against the current project files before changing code.
- If this document conflicts with current code, current code wins and the conflict must be reported.

## Current-file Verification

- Search the current project for the named route, screen, controller, service, store, mapper, resource, or config before relying on this guide.
- Open the nearest owner file and at least one caller/consumer before changing a shared contract.
- Record path:line evidence from the current project in the final report or worklog.
- Do not paste a full large generated index into a prompt; read targeted sections and cite specific files.
- If a required file is missing, mark this pack stale for that area and continue from current-file discovery.

## Profile-specific Focus

- Frontend route/view/service/model/grid path versus backend resource/service/repository path.
- Admin grid, pagination, excel upload/download, modal, and permission behavior.
- Generated domain/support classes and MyBatis XML regeneration sensitivity.
- Security/session/CTI/OAM/static resource impact.

## Evidence Refresh Targets

- ref/drt-cms-main/pom.xml:16 artifactId=drt-cms-parent
- ref/drt-cms-main/pom.xml:39 java.version=17
- ref/drt-cms-main/pom.xml:52 modules backend/frontend
- ref/drt-cms-main/backend/pom.xml:10 artifactId=drt-cms-backend
- ref/drt-cms-main/frontend/package.json:2 name=edirect
- ref/drt-cms-main/frontend/package.json:8 quasar scripts
- ref/drt-cms-main/frontend/src/router/routes.ts:17 asyncRouterMap
- ref/drt-cms-main/backend/src/main/resources/mybatis/sql/cms/ManagerRepository.xml:1 mapper XML

## Change Risk Flags

- Shared state, route registration, request/response DTO, SQL mapper, EAI/external interface, auth/session, generated code, deployment profile, and public asset changes are higher risk.
- For higher-risk changes, expand the current-file trace to entrypoint, producer, carrier, persistence/cache/session, downstream consumer, and verification surface.
- For frontend layout/CSS work, include wrapper, scoped/global style location, selector specificity, overflow/positioning, and DOM mutation checks.
- For backend persistence/API work, include controller/resource, service, model/DTO, mapper/repository, XML/query, profile config, and caller checks.

## Done Criteria For This Document

- The task has a bounded owner area tied to this document.
- Current files have been read and cited.
- The planned change avoids unrelated refactors and generated-output churn.
- Focused verification or a concrete fallback check is selected before edits finish.
- Unknowns are written to `D:/aiops/docs/drt-cms/knowledge/99-gaps-and-questions.md` when they affect future work.
