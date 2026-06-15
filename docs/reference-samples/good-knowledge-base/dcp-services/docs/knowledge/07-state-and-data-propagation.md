---
kiwi_doc: true
doc_type: state
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "backend state, Redis/session, and cross-call propagation"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:88"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:736"
keywords:
  - state
  - Redis
  - session
  - propagation
---

# State And Data Propagation

## State Layers

| Layer | Responsibility | Risk |
| --- | --- | --- |
| HTTP request/session | Header, cookie, servlet session, request attributes. | high |
| Redis session support | Cross-request identity/session fields. | high |
| Domain Redis keys | Claim state and step data. | high |
| EAI response state | External results mapped into internal response objects. | medium-high |
| Controller response | Final API response consumed by front-end/gateway. | medium |

## Trace Template

Use this for any stateful backend field:

```text
Field/key:
HTTP source:
Session source:
Redis key:
Writer:
Reader:
EAI/source system:
Response consumer:
Delete/expiry behavior:
Privacy sensitivity:
Evidence:
```

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Shared interceptor reads Redis session id and Redis fields. | `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:88`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:98`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:103` | high |
| Shared interceptor can delete session-related items. | `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:154`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:158` | medium |
| Insurance claim service writes claim state into Redis. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:736`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:737` | high |
