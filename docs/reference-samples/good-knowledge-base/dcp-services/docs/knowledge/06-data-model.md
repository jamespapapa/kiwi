---
kiwi_doc: true
doc_type: data
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "backend DTO, VO, EAI, and Redis data objects"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:136"
  - "dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:62"
keywords:
  - DTO
  - VO
  - EAI
  - Redis object
  - data model
---

# Data Model

## Backend Data Model Types

| Model Type | Example | Documentation Focus |
| --- | --- | --- |
| Request/response VO | EAI request/response classes and controller binding objects. | Field name, source, validation, external contract. |
| Redis object | `AccBenefitClaimInqrRes` step objects. | Key, step, field mapping, writer/reader. |
| EAI params | `EaiParams` built in service methods. | Service id, request payload, response payload. |
| Controller response | API return object/wrapper. | Client-consumed fields and error behavior. |

## Claim Redis Object Example

`AccBenefitClaimInqrRes` is a representative state object for claim step data. It defines step-shaped properties and a resolver that maps request/result fields into step objects. A full data doc should turn each step into a field table and link front-end claim fields when available.

## EAI Payload Documentation Rule

For each EAI call, document:

- service id,
- request VO or map,
- response VO,
- field mapping method,
- null/default handling,
- exception behavior,
- caller/controller.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Claim Redis response object defines step properties. | `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:136`, `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:148` | high |
| Claim Redis response resolver maps fields into step objects. | `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:665`, `dcp-core/src/main/java/com/samsunglife/dcp/core/insurance/request/redis/AccBenefitClaimInqrRes.java:794` | medium |
| EAI services build `EaiParams` before execute. | `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:62`, `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:64` | high |
