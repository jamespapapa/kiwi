---
kiwi_doc: true
doc_type: flow
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "insurance claim Redis state sample"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:59"
  - "dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:136"
keywords:
  - insurance claim
  - Redis
  - AccBenefitClaimInqrRes
  - DiffBenefitClaimService
---

# Flow: Insurance Claim Redis State

## Purpose

This sample shows how to document backend state that persists across claim steps. It should be paired with front-end field propagation docs when changing an insurance internet claim flow.

## Observed State Objects

| Object/Key | Responsibility | Evidence |
| --- | --- | --- |
| `Namespace.NS_INSURANCE + ".claim.baseInfo"` | Claim base information Redis key candidate. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:59` |
| child base key | Child insurance claim base information key candidate. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:61` |
| `AccBenefitClaimInqrRes` | Redis-backed claim inquiry response object with step objects. | `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:136` |

## Step Mapping

`AccBenefitClaimInqrRes` contains step-shaped properties such as:

- `accBenefitClaimStp0Res`,
- `accBenefitClaimStp1Res`,
- `accBenefitClaimStp2Res`,
- `accBenefitClaimStp3Res`.

The `resolve` method initializes and maps step objects and claim fields. Field-level docs should link frontend fields such as `clamCause` and `clamReason*` to backend fields only after confirming exact names in both repositories.

## Write/Read Pattern

`DiffBenefitClaimService` includes methods that set/read Redis claim information. A full doc must record:

- controller and service entrypoint,
- when Redis is read,
- when Redis is written,
- which keys are touched,
- whether write replaces or merges data,
- downstream API or EAI call that consumes the Redis-backed object.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Insurance claim service defines Redis key constants for claim base info. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:59`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:61` | high |
| Claim service sets step values and writes Redis info. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:311`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:327`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/internet/service/DiffBenefitClaimService.java:736` | medium |
| Redis response object defines step properties and maps claim fields in `resolve`. | `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:136`, `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:148`, `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:665`, `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:678` | medium |
