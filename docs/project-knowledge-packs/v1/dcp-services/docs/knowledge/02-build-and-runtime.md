---
kiwi_knowledge_pack_version: "v1"
profile: "dcp-services"
title: "02-build-and-runtime"
source_reference: "docs/reference-samples/good-knowledge-base/dcp-services"
copy_mode: "seed; verify and replace evidence in the target project"
---

# Build And Runtime

## Runtime Summary

DCP Java/Spring/Maven backend knowledge seed for controller/service/Redis/EAI/MyBatis/verification work.

## Verification/Build Commands

- Use module-specific Maven compile/package and static EAI/MyBatis path checks when full build is blocked.

## Evidence

- docs/reference-samples/good-knowledge-base/dcp-services/docs/knowledge/01-repository-map.md
- docs/samsunglife-dcp-overview.md:9 dcp-services overview

## Worker Startup Checklist

- Resolve the active project key as `dcp-services` before using this pack.
- Read `D:/aiops/docs/dcp-services/project-info/project-summary.md` and `D:/aiops/docs/dcp-services/project-info/architecture-map.md` before broad analysis.
- Read `D:/aiops/docs/dcp-services/knowledge/00-index.md` and this document only when the task touches the matching area.
- Treat every statement here as seed knowledge. Confirm the relevant claim against the current project files before changing code.
- If this document conflicts with current code, current code wins and the conflict must be reported.

## Current-file Verification

- Search the current project for the named route, screen, controller, service, store, mapper, resource, or config before relying on this guide.
- Open the nearest owner file and at least one caller/consumer before changing a shared contract.
- Record path:line evidence from the current project in the final report or worklog.
- Do not paste a full large generated index into a prompt; read targeted sections and cite specific files.
- If a required file is missing, mark this pack stale for that area and continue from current-file discovery.

## Profile-specific Focus

- Maven module boundary and controller/service package ownership.
- MyBatis mapper XML, DTO/request/response, Redis/cache, and EAI interface id propagation.
- resources-env/profile configuration and async/batch scheduler effects.
- Module-specific Maven/static EAI verification when full runtime tests are blocked.

## Evidence Refresh Targets

- docs/reference-samples/good-knowledge-base/dcp-services/docs/knowledge/01-repository-map.md
- docs/samsunglife-dcp-overview.md:9 dcp-services overview

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
- Unknowns are written to `D:/aiops/docs/dcp-services/knowledge/99-gaps-and-questions.md` when they affect future work.
