---
kiwi_doc: true
doc_type: data
project: "dcp-front-develop"
profile: "dcp-front"
scope: "front-end data object and payload modeling conventions"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/store/modules/com/DataStore.js:7"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:762"
keywords:
  - data model
  - inputObj
  - payload
  - route params
---

# Data Model

## Front-End Data Model Types

This front-end project does not expose a single database-style schema. For documentation, model data as contracts between screens and boundaries:

| Model Type | Example | Documentation Focus |
| --- | --- | --- |
| Component local object | `inputObj` in insurance screens. | Field source, validation, UI binding, save/load mapping. |
| Vuex module state | `state.data` in `DataStore`. | Key names, producer/consumer, mutation/getter behavior. |
| Route payload | route `name`, params/query. | Branching values and next-screen dependencies. |
| API payload | `spotLoad`/`spotSave` request/response objects. | Backend contract and interceptor effects. |

## Sample Claim Payload Fields

| Field | Observed Role | Required Trace |
| --- | --- | --- |
| `inqrScCd` | Flow branch/inquiry code. | Route param, screen branch, save payload. |
| `uploadKey` | Upload/file linkage candidate. | Producer, save payload, backend consumer. |
| `acdtSn` | Accident sequence candidate. | Backend source and downstream consumer. |
| `acpnSno` | Acceptance/receipt sequence candidate. | Backend source and downstream consumer. |
| `ccevent` | Event/code candidate in save payload. | Producer and valid values. |
| `planId` | Plan identifier candidate. | Producer and save/next flow consumer. |

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| `DataStore` uses object state and keyed writes. | `src/store/modules/com/DataStore.js:7`, `src/store/modules/com/DataStore.js:31` | high |
| Insurance input screens define local `inputObj` fields. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020550M.vue:292` | medium |
| Later claim save payload includes identifiers and branch fields. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:750`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:762` | medium |
