---
kiwi_doc: true
doc_type: repository-map
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "Maven modules and source/resource layout"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:29"
  - "dcp-insurance/pom.xml:11"
  - "dcp-core/pom.xml:11"
  - "dcp-gateway/pom.xml:11"
keywords:
  - Maven modules
  - dcp-core
  - dcp-gateway
  - dcp-insurance
---

# Repository Map

## Top-Level Layout

| Path | Type | Responsibility | Primary Consumers | Evidence |
| --- | --- | --- | --- | --- |
| `pom.xml` | Maven root | Aggregates modules, defines Java/Spring versions, profiles, repositories. | Maven build, all modules. | `pom.xml:5`, `pom.xml:15`, `pom.xml:29` |
| `dcp-core` | shared module | Common helpers, auth/session, interceptors, Redis support, shared VO usage. | Gateway and domain modules. | `dcp-core/pom.xml:11`, `dcp-core/pom.xml:19` |
| `dcp-gateway` | gateway module | Gateway-facing controllers and vendor/security integrations. | Web/API gateway flows. | `dcp-gateway/pom.xml:11`, `dcp-gateway/pom.xml:16` |
| `dcp-insurance` | domain module | Insurance controllers/services, claim flows, PDF/image dependencies. | Insurance front-end/API clients. | `dcp-insurance/pom.xml:11`, `dcp-insurance/pom.xml:28` |
| `dcp-fund` | domain module | Fund domain services and EAI integration examples. | Fund API/controllers. | `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:31` |

## Module List Pattern

The sampled root POM includes modules such as:

`dcp-core`, `dcp-gateway`, `dcp-example`, `dcp-async`, `dcp-batch`, `dcp-cms`, `dcp-display`, `dcp-member`, `dcp-insurance`, `dcp-loan`, `dcp-product`, `dcp-fund`, `dcp-trust`, `dcp-retire`, `dcp-pension`, `dcp-upload`, `dcp-cs`, `dcp-chatbot`, `dcp-monimo`, `dcp-group`.

A full documentation run should convert this list into a module table with:

- artifactId,
- packaging,
- source roots,
- resource roots,
- dependencies on `dcp-core` or `dcp-eai-vo`,
- controller/service/mapper counts,
- high-risk integrations.

## Resource Roots

Observed module resource patterns include:

- `src/main/resources`,
- `src/main/resources-env`,
- `src/main/resources/META-INF/eai`,
- `src/main/resources/spring`,
- `src/main/resources/sqlconf`,
- `src/main/resources/rulesets`.

Do not assume every module has every root. Record presence per module.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Root POM lists many modules. | `pom.xml:29`, `pom.xml:50` | high |
| `dcp-insurance` is a module artifact and depends on `dcp-core` and `dcp-eai-vo`. | `dcp-insurance/pom.xml:11`, `dcp-insurance/pom.xml:16`, `dcp-insurance/pom.xml:23` | high |
| `dcp-core` is a shared module with dependency on `dcp-eai-vo`. | `dcp-core/pom.xml:11`, `dcp-core/pom.xml:19` | high |
| `dcp-gateway` depends on shared core and EAI VO artifacts. | `dcp-gateway/pom.xml:11`, `dcp-gateway/pom.xml:16`, `dcp-gateway/pom.xml:23` | high |
