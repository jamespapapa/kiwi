---
kiwi_doc: true
doc_type: api
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "controller route and backend API contract patterns"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:60"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/loan/controller/ContractController.java:78"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/actualcost/controller/SlicInsramBilCndtController.java:40"
keywords:
  - controller
  - RequestMapping
  - API
  - contract
---

# API And Contracts

## Controller Documentation Pattern

Each controller/API document should include:

| Section | Required Content |
| --- | --- |
| Route | Class-level mapping + method-level mapping + HTTP method. |
| Request | Binding style, request object, headers/session dependencies. |
| Service Call | Service method, dependencies, transaction note if any. |
| Response | Wrapper/DTO fields consumed by clients. |
| External Calls | EAI service id, mapper, Redis/session, file/PDF, vendor API. |
| Errors | Exception class, error code, fallback branch. |
| Evidence | Route annotation, service invocation, request/response mapping lines. |

## Sampled Route Families

| Controller | Sample Routes | Notes |
| --- | --- | --- |
| `DividendamtController` | `/dividendamt/total/inqury`, `/dividendamt/inqury`, `/dividendamt/detail`, `/dividendamt/proc` | Class-level mapping includes root/Monimo-style prefix. |
| `PartialWithdrawalApplicationController` | `/partial/withdrawal/application/inqury`, `/detail`, `/info`, `/proc` | Loan/withdrawal domain candidate. |
| `ContractController` | `/contract/inqr`, `/contract/allInqr`, `/contract/status/inqr`, `/contract/common/inqury` | Contract inquiry domain candidate. |
| `SlicInsramBilCndtController` | `/claim/searchSlicInsramBilCndt` | Uses versioned Monimo API path with landscape prefix option. |

## Route Extraction Rules

- Always combine class and method annotations.
- Record whether route supports multiple base prefixes.
- Preserve literal misspellings in paths such as `inqury` if they appear in code. They are contracts, not typos to silently correct.
- Link request/response object docs if present.
- If the controller delegates immediately to a service, document that service in the same API entry or a linked module document.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| `DividendamtController` exposes dividend inquiry/proc routes. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:46`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:60`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/give/controller/DividendamtController.java:114` | high |
| `ContractController` exposes contract inquiry routes. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/loan/controller/ContractController.java:60`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/loan/controller/ContractController.java:78`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/loan/controller/ContractController.java:145` | high |
| `SlicInsramBilCndtController` has a versioned Monimo/landscape mapping. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/actualcost/controller/SlicInsramBilCndtController.java:40`, `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/actualcost/controller/SlicInsramBilCndtController.java:62` | high |
