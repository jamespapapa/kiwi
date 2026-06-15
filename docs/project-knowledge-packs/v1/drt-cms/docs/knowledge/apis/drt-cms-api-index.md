---
kiwi_knowledge_pack_version: "v1"
profile: "drt-cms"
title: "drt-cms api index"
source_reference: "../ref/drt-cms-main"
copy_mode: "seed; verify and replace evidence in the target project"
---

# API Index

- `frontend/src/boot/axios.ts` owns Axios base API behavior and auth/session error handling.
- Backend `*Resource` classes under `/api` define admin endpoints and often pair with generated domain/service/repository files.
- MyBatis XML under `backend/src/main/resources/mybatis/sql/**` is the persistence contract; generated domain/support classes should not be edited casually.

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
