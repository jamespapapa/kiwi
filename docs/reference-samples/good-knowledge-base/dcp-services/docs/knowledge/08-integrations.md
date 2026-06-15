---
kiwi_doc: true
doc_type: integration
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "EAI, Redis, and external integration patterns"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:49"
  - "dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:52"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:736"
keywords:
  - EAI
  - service id
  - EaiParams
  - Redis
  - integration
---

# Integrations

## EAI Integration Pattern

Sampled services follow this shape:

1. inject or use `EaiExecuteService`,
2. prepare a service id,
3. build `EaiParams`,
4. execute the EAI call,
5. map response or throw an `EaiProcessException` branch.

For each EAI interaction, create a table:

| Field | Meaning |
| --- | --- |
| Service id | Literal id or generation method. |
| Caller | Controller/service method. |
| Request object | VO or map fields and source. |
| Response object | VO fields and consumers. |
| Error behavior | Exception, return code, retry/fallback. |
| Side effects | Redis/session/log/file writes. |

## Sample EAI IDs

| Location | EAI ID Pattern | Notes |
| --- | --- | --- |
| `FundAdditionalBuyingInquryService` | service id generated through helper methods | Multiple EAI calls in one service. |
| `FundResaleService` | service id generated through helper methods | Similar EAI params/execute pattern. |
| `DirectMailService` | literal ids `COCM0197`, `CHIC0185`, `INVV0001` | Gateway direct-mail related service sample. |

## Redis/Session Integration Pattern

Redis is used both in common interceptor/session behavior and insurance claim domain state. Document:

- key namespace,
- value object,
- writer method,
- reader method,
- consumer flow,
- expiration/deletion if visible,
- privacy sensitivity.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Fund service builds EAI service id, `EaiParams`, and executes through EAI service. | `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:49`, `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:62`, `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:64` | high |
| Direct mail service uses literal EAI IDs. | `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:52`, `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:78`, `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:101` | high |
| Insurance claim service writes claim data into Redis. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:59`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:736`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:737` | high |
