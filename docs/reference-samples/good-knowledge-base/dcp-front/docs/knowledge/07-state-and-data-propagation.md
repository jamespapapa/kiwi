---
kiwi_doc: true
doc_type: state
project: "dcp-front-develop"
profile: "dcp-front"
scope: "Vuex/DataStore and route-driven value propagation"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/store/index.js:16"
  - "src/store/modules/com/DataStore.js:6"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:399"
keywords:
  - Vuex
  - DataStore
  - DATA_UPDATE
  - getDataJson
  - route params
  - spotSave
---

# State And Data Propagation

## State Layers

| Layer | Responsibility | Risk |
| --- | --- | --- |
| Local component `data()` | Immediate screen fields, form objects, modal state. | medium |
| Vuex module state | Shared app state and UI/domain modules. | medium-high |
| `DataStore` module | Cross-screen arbitrary object carrier keyed by detail name. | high |
| Route params/query | Navigation-time payload between screens. | high |
| `spotLoad`/`spotSave` | Backend persistence/resume boundary. | high |

## DataStore Contract

The `data` Vuex module is registered in `src/store/index.js` and implemented by `src/store/modules/com/DataStore.js`.

Observed contract:

- `state.data` is an object map.
- getter `getDataJson` returns data by key/detail.
- mutation `DATA_UPDATE` writes a selected target object under a detail key.

When documenting a value, record both the logical field and every carrier key. Do not document only the screen label.

## Example: Insurance Claim Cause Fields

In the sampled mobile insurance internet claim screens, `clamCause` and `clamReason*` fields appear as local input fields and are saved through `spotSave`.

| Field | Local Carrier | Persistence/Navigation Pattern |
| --- | --- | --- |
| `inqrScCd` | screen state / route param | Controls branch such as child claim vs other claim flow. |
| `clamCause` | `inputObj.clamCause` | Loaded from prior response and included in save payload. |
| `clamReason1..8` | `inputObj.clamReason*` | Grouped checkbox/watch behavior maps UI selections to individual fields. |
| `whoGbn` | DataStore value in sampled screen | Loaded before branching the flow. |

## Field Trace Template

Use this structure for a real target field:

```text
Field:
User-visible label:
Producer:
Local component key:
Vuex/DataStore key:
Route param/query key:
spotLoad response key:
spotSave request key:
Downstream consumers:
Default/null behavior:
Validation:
Evidence:
```

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Vuex registers a `data` module. | `src/store/index.js:16`, `src/store/index.js:27` | high |
| `DataStore` is namespaced and stores data under keyed details. | `src/store/modules/com/DataStore.js:6`, `src/store/modules/com/DataStore.js:7`, `src/store/modules/com/DataStore.js:31` | high |
| `getDataJson` is the read contract for stored data. | `src/store/modules/com/DataStore.js:10`, `src/store/modules/com/DataStore.js:23` | high |
| Insurance claim screen uses local `inputObj` fields for claim cause/reason. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:224` | medium |
| The same screen uses `spotLoad` and `spotSave` boundaries. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:243`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:399`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:414` | medium |
