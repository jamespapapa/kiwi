---
kiwi_knowledge_pack_version: "v1"
profile: "dcp-front"
title: "06-data-model"
source_reference: "docs/reference-samples/good-knowledge-base/dcp-front"
copy_mode: "seed; verify and replace evidence in the target project"
---

# Data Model

## Data/State Seeds

- `src/router/**`: route definitions.
- `src/views/**`: screen components.
- `src/store/modules/com/DataStore.js`: shared state carrier.
- `src/plugins/com/Common.js`: common flow utility and claim continuation logic.
- `src/components/**`: common UI and modal components.

## Evidence

- docs/reference-samples/good-knowledge-base/dcp-front/docs/knowledge/01-repository-map.md
- docs/samsunglife-dcp-overview.md:8 dcp-front overview

## Worker Startup Checklist

- Resolve the active project key as `dcp-front` before using this pack.
- Read `D:/aiops/docs/dcp-front/project-info/project-summary.md` and `D:/aiops/docs/dcp-front/project-info/architecture-map.md` before broad analysis.
- Read `D:/aiops/docs/dcp-front/knowledge/00-index.md` and this document only when the task touches the matching area.
- Treat every statement here as seed knowledge. Confirm the relevant claim against the current project files before changing code.
- If this document conflicts with current code, current code wins and the conflict must be reported.

## Current-file Verification

- Search the current project for the named route, screen, controller, service, store, mapper, resource, or config before relying on this guide.
- Open the nearest owner file and at least one caller/consumer before changing a shared contract.
- Record path:line evidence from the current project in the final report or worklog.
- Do not paste a full large generated index into a prompt; read targeted sections and cite specific files.
- If a required file is missing, mark this pack stale for that area and continue from current-file discovery.

## Profile-specific Focus

- Vue route/view/component ownership and mobile/PC channel path.
- Vuex DataStore, spotLoad/spotSave, route params, and downstream consumer propagation.
- Shared modal/component blast radius and legacy Options API conventions.
- Playwright/DOM/text/CSS fallback verification assets.

## Evidence Refresh Targets

- docs/reference-samples/good-knowledge-base/dcp-front/docs/knowledge/01-repository-map.md
- docs/samsunglife-dcp-overview.md:8 dcp-front overview

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
- Unknowns are written to `D:/aiops/docs/dcp-front/knowledge/99-gaps-and-questions.md` when they affect future work.
