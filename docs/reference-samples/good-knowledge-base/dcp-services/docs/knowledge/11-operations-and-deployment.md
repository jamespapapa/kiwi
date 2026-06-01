---
kiwi_doc: true
doc_type: ops
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "profiles, internal repository, resource, and deployment documentation sample"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:52"
  - "pom.xml:89"
  - "pom.xml:229"
keywords:
  - operations
  - deployment
  - Maven profile
  - Nexus
  - resources-env
---

# Operations And Deployment

## Profile Map

The root POM contains environment profiles with module lists. Document every profile as:

| Profile | Modules | Resource Differences | Build/Deploy Notes |
| --- | --- | --- | --- |
| local/default | Root POM sampled with full DCP module family. | Confirm `resources-env` and module resources per target module. | Active-by-default in sampled root POM. |
| dev | Root POM sampled with environment-specific module list. | Confirm profile-specific resources before build/deploy. | Compare module list with local/default. |
| qa | Root POM sampled with environment-specific module list. | Confirm profile-specific resources before build/deploy. | Compare module list with dev/stage. |
| stage | Root POM sampled with environment-specific module list. | Confirm profile-specific resources before build/deploy. | Treat as pre-release deployment profile. |
| release | Root POM sampled with environment-specific module list. | Confirm profile-specific resources before build/deploy. | Treat as production-like deployment profile. |

## Internal Dependency Repository

The sampled root POM references an internal Nexus repository. Closed-network builds should document:

- repository id/name/url,
- whether snapshots/releases are enabled,
- whether public Maven Central fallback is allowed,
- which profiles require internal artifacts.

## Resource Documentation Rules

- For each module, record `src/main/resources`, `src/main/resources-env`, `spring`, `sqlconf`, and `META-INF/eai` presence.
- Keep environment-specific secrets or credentials out of docs. Record keys and purpose, not values.
- Link operations docs to build/test results.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Local/default and other environment profiles are declared in the root POM. | `pom.xml:52`, `pom.xml:89`, `pom.xml:122`, `pom.xml:156`, `pom.xml:190` | high |
| Internal Nexus repository is configured. | `pom.xml:229`, `pom.xml:239` | high |
