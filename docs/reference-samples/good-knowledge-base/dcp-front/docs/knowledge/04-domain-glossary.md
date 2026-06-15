---
kiwi_doc: true
doc_type: glossary
project: "dcp-front-develop"
profile: "dcp-front"
scope: "front-end and insurance-flow terms"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/router/index.js:63"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:190"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:750"
keywords:
  - glossary
  - MYINT
  - inqrScCd
  - clamCause
  - DataStore
---

# Domain Glossary

| Term | Meaning In This Project | Documentation Rule |
| --- | --- | --- |
| PC/MO | PC and mobile route/channel split. | Always record which channel a screen belongs to. |
| MYINT | Mobile My Samsung Life insurance internet screen family prefix. | Use route name and component file together. |
| `DataStore` | Vuex-backed cross-screen data carrier. | Trace producer, key, consumer, and fallback behavior. |
| `spotLoad` | Screen/API resume or load boundary in sampled screens. | Document endpoint/call site and response field mapping. |
| `spotSave` | Screen/API save boundary in sampled screens. | Document request payload and next route. |
| `inqrScCd` | Inquiry/branch code used by insurance claim screens. | Never rename or reinterpret without finding all branches. |
| `clamCause` | Claim cause field in insurance flow. | Trace load/save and backend Redis/API counterpart before editing. |
| `clamReason*` | Claim reason boolean/code fields. | Document grouped UI mapping and individual payload fields. |
| `busnScCd` | Business section/code branch value in sampled insurance screens. | Record branch values such as `AG` with exact evidence. |

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Router commits route type values for PC/MO route setup. | `src/router/index.js:63`, `src/router/index.js:73` | high |
| Insurance claim screens branch on `inqrScCd`. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:190`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020550M.vue:8` | medium |
| `clamCause` and `clamReason*` appear in claim input objects. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020550M.vue:292` | medium |
| `busnScCd === 'AG'` appears in later claim flow logic. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:448`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:570` | medium |
