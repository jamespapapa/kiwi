---
kiwi_knowledge_pack_version: "v1"
profile: "drt-front"
title: "drt-front primary flow"
source_reference: "../ref/drt-front-main"
copy_mode: "seed; verify and replace evidence in the target project"
---

# Primary Flow

- Route -> view -> modal/component -> Pinia store -> service -> DrtHttpClient -> DRT API.
- Application subscription flows span application route modules, application stores, product plan services, and many modal components.
- Coverage analysis flows span `coverageAnalysis` routes, result components, stores, and service methods.
- System block/session behavior is global through `DrtHttpClient`, `SessionTimeout`, and `SystemMaintenance`.

## Required Evidence

- ref/drt-front-main/dev/package.json:2 name=dcp-front-frame
- ref/drt-front-main/dev/package.json:6 scripts serve/build/ssr
- ref/drt-front-main/dev/package.json:25 dependencies vue/vue-router/pinia/axios
- ref/drt-front-main/dev/vite.config.ts:4 proxy to api.t.drt.samsunglife.kr
- ref/drt-front-main/dev/src/router/index.ts:1 createRouter
- ref/drt-front-main/dev/src/module/DrtHttpClient.ts:1 axios wrapper
- ref/drt-front-main/dev/src/store/ApplicationMaster.ts:2 Pinia store

## Worker Startup Checklist

- Resolve the active project key as `drt-front` before using this pack.
- Read `D:/aiops/docs/drt-front/project-info/project-summary.md` and `D:/aiops/docs/drt-front/project-info/architecture-map.md` before broad analysis.
- Read `D:/aiops/docs/drt-front/knowledge/00-index.md` and this document only when the task touches the matching area.
- Treat every statement here as seed knowledge. Confirm the relevant claim against the current project files before changing code.
- If this document conflicts with current code, current code wins and the conflict must be reported.

## Current-file Verification

- Search the current project for the named route, screen, controller, service, store, mapper, resource, or config before relying on this guide.
- Open the nearest owner file and at least one caller/consumer before changing a shared contract.
- Record path:line evidence from the current project in the final report or worklog.
- Do not paste a full large generated index into a prompt; read targeted sections and cite specific files.
- If a required file is missing, mark this pack stale for that area and continue from current-file discovery.

## Profile-specific Focus

- Route module and target Vue screen/component ownership.
- Pinia store and service call propagation.
- DrtHttpClient behavior, loading, session timeout, system block, and Adobe response side effects.
- Vite proxy/public asset/build mode implications.

## Evidence Refresh Targets

- ref/drt-front-main/dev/package.json:2 name=dcp-front-frame
- ref/drt-front-main/dev/package.json:6 scripts serve/build/ssr
- ref/drt-front-main/dev/package.json:25 dependencies vue/vue-router/pinia/axios
- ref/drt-front-main/dev/vite.config.ts:4 proxy to api.t.drt.samsunglife.kr
- ref/drt-front-main/dev/src/router/index.ts:1 createRouter
- ref/drt-front-main/dev/src/module/DrtHttpClient.ts:1 axios wrapper
- ref/drt-front-main/dev/src/store/ApplicationMaster.ts:2 Pinia store

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
- Unknowns are written to `D:/aiops/docs/drt-front/knowledge/99-gaps-and-questions.md` when they affect future work.
