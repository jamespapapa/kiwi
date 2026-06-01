---
kiwi_doc: true
doc_type: playbook
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "safe backend change playbooks"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:29"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:60"
  - "dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:64"
keywords:
  - playbook
  - controller
  - service
  - EAI
  - Redis
---

# Change Playbooks

## Playbook: Add Or Change A Controller Route

1. Combine class-level and method-level `@RequestMapping` before documenting the public path.
2. Identify request binding, headers/session dependencies, and response wrapper.
3. Trace service calls and side effects.
4. Search route literals in front-end and gateway docs if available.
5. Add or update an API document under `docs/knowledge/apis/`.

## Playbook: Change EAI Mapping

1. Find all service methods using the EAI service id or VO.
2. Document request field source and response field consumers.
3. Check exception handling and error code behavior.
4. Search for related Redis/session writes.
5. Verify with the smallest module test/build command available.

## Playbook: Change Shared Core Or Interceptor Code

1. Search all module callers/imports before editing.
2. Identify channel-specific behavior: Monimo, app, PC, mobile, gateway.
3. Mark privacy-sensitive data and avoid logging raw identity/token/session values.
4. Record before/after behavior in `09-security-auth-privacy.md`.
5. Run at least compile/test for affected modules and one direct consumer module.

## Playbook: Document A Domain Module

1. Read module `pom.xml`.
2. Count controllers, services, repositories/mappers, resources, EAI files.
3. Build route table.
4. Build service-to-integration table.
5. Build high-risk field/state table.
6. Add module doc under `docs/knowledge/modules/<module>.md`.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Backend has many modules, so shared-code changes need consumer search. | `pom.xml:29`, `pom.xml:50` | high |
| Controller routes are public contracts. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:60`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:75` | high |
| EAI execute calls are core integration contracts. | `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:64`, `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:144` | high |
