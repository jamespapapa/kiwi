---
kiwi_doc: true
doc_type: repository-map
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "sample knowledge-base index"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:5"
  - "pom.xml:29"
  - "dcp-insurance/pom.xml:11"
  - "dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:67"
keywords:
  - Maven
  - Spring
  - EAI
  - Redis
  - controller
---

# dcp-services Knowledge Base Sample

## Executive Summary

`dcp-services-mevelop` is a Java 8 / Spring 5 Maven multi-module DCP backend. The root project aggregates shared modules, gateway modules, and domain modules such as insurance, loan, fund, member, CMS, and upload.

The highest-risk maintenance areas are:

- module boundary and dependency direction,
- controller route to service method contracts,
- EAI service-id request/response mapping,
- Redis/session side effects,
- authentication/JWT/filter/interceptor behavior,
- financial/insurance domain request field drift between front-end and backend.

## How To Use This Knowledge Base

| Need | Read |
| --- | --- |
| Understand modules | [01-repository-map.md](01-repository-map.md) |
| Build and profile behavior | [02-build-and-runtime.md](02-build-and-runtime.md) |
| Understand system boundaries | [03-system-boundaries.md](03-system-boundaries.md) |
| Decode backend/domain terms | [04-domain-glossary.md](04-domain-glossary.md) |
| Trace controller/API shape | [05-api-and-contracts.md](05-api-and-contracts.md) |
| Understand DTO/VO/data objects | [06-data-model.md](06-data-model.md) |
| Trace backend state side effects | [07-state-and-data-propagation.md](07-state-and-data-propagation.md) |
| Trace EAI/Redis integrations | [08-integrations.md](08-integrations.md) |
| Inspect security/session risks | [09-security-auth-privacy.md](09-security-auth-privacy.md) |
| Check test commands and quality gates | [10-testing-and-quality.md](10-testing-and-quality.md) |
| Check profile/deployment operations | [11-operations-and-deployment.md](11-operations-and-deployment.md) |
| Inspect insurance claim Redis sample | [flows/insurance-claim-redis.md](flows/insurance-claim-redis.md) |
| Plan a safe change | [12-change-playbooks.md](12-change-playbooks.md) |
| Check unresolved assumptions | [99-gaps-and-questions.md](99-gaps-and-questions.md) |

## Most Important Entry Points

| Entry Point | Why It Matters |
| --- | --- |
| `pom.xml` | Root Maven modules, Java/Spring versions, profiles, repositories. |
| `*/pom.xml` | Module dependencies and domain/shared coupling. |
| `dcp-core` | Shared auth, interceptor, Redis/session, helper, VO, and common behavior. |
| `dcp-gateway` | Gateway/security/vendor integration surface. |
| `dcp-insurance` | Insurance domain controllers/services and claim flows. |
| `src/main/resources-env` | Profile-specific config/resource pattern in modules. |
| `src/main/resources/META-INF/eai` | EAI metadata/config location candidate. |

## High Risk Areas

- `dcp-core` is a shared dependency for many modules. Changes require consumer search.
- EAI service id strings and VO mapping are business contracts; do not infer them from method names only.
- Redis/session writes can affect later requests outside the immediate controller.
- Controller class-level mappings can include multiple prefixes, such as `/` and `/monimo`.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Root project is a Maven POM aggregator under group `com.samsunglife`. | `pom.xml:5`, `pom.xml:8`, `pom.xml:9` | high |
| Root POM declares many DCP modules. | `pom.xml:29`, `pom.xml:50` | high |
| Java and Spring versions are defined in root properties. | `pom.xml:15`, `pom.xml:17`, `pom.xml:18` | high |
| Domain modules depend on shared `dcp-core` and EAI VO artifacts. | `dcp-insurance/pom.xml:16`, `dcp-insurance/pom.xml:23` | high |
