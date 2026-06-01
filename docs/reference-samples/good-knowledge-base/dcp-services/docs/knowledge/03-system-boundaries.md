---
kiwi_doc: true
doc_type: boundary
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "module and external system boundaries"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:46"
  - "dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:31"
  - "dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:67"
keywords:
  - boundary
  - controller
  - service
  - EAI
  - Redis
---

# System Boundaries

## Boundary Map

| Boundary | Internal Side | External/Shared Side | Why It Matters |
| --- | --- | --- | --- |
| HTTP controller | `@RequestMapping` controllers in domain/gateway modules. | Front-end/gateway clients. | URL and request binding are public contracts. |
| Service layer | `@Service` classes in domain modules. | EAI, Redis, mapper, helper dependencies. | Business mapping and side effects usually live here. |
| EAI | EAI execute services and VO artifacts. | External backend systems. | Service ID and payload mapping are high-risk contracts. |
| Redis/session | Redis support and interceptors. | Cross-request/session state. | A write can affect later API calls. |
| Security/JWT | Gateway/core auth helpers and controllers. | SSO, cookies, headers, JWT consumers. | Incorrect claim/header handling can break login or privacy guarantees. |

## Controller Prefix Pattern

Some sampled controllers use class-level mapping with multiple prefixes, such as `"/"` and `"/monimo"`. Other gateway controllers use more explicit versioned paths. Always combine class-level and method-level mappings before documenting a route.

## Service To External Boundary

Sampled fund services use `EaiExecuteService`, build `EaiParams`, generate or reference a service id, and execute the request. A good service document must identify:

- the controller/method caller,
- service method,
- EAI service id,
- request VO/object,
- response VO/object,
- exception behavior,
- whether Redis/session/cache is touched.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Sample domain controllers use class-level request mapping. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:46`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/loan/controller/ContractController.java:60` | high |
| Sample services execute EAI requests through `EaiExecuteService`. | `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:31`, `dcp-fund/src/main/java/com/samsunglife/dcp/fund/product/service/FundAdditionalBuyingInquryService.java:64` | high |
| Redis/session behavior is present in shared interceptor code. | `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:67`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:98` | high |
