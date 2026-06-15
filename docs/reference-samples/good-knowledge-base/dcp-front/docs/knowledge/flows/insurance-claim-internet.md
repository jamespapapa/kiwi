---
kiwi_doc: true
doc_type: flow
project: "dcp-front-develop"
profile: "dcp-front"
scope: "mobile insurance internet claim flow sample"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/router/mo/mysamsunglife/insurance/internet/route.js:18"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:125"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:168"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:750"
keywords:
  - MYINT
  - insurance claim
  - mobile
  - spotLoad
  - spotSave
  - inqrScCd
---

# Flow: Mobile Insurance Internet Claim

## Purpose

This sample flow documents the expected style for a route-driven screen family. It does not claim to cover every insurance claim screen. A full target run must enumerate all route entries and screen transitions.

## Route Family

The mobile insurance internet route file defines named screens such as:

| Route Name | Role In Flow | Evidence |
| --- | --- | --- |
| `MDP-MYINT020110M` | Entry/intro screen candidate. | `src/router/mo/mysamsunglife/insurance/internet/route.js:18` |
| `MDP-MYINT020130M` | Follow-up claim flow candidate. | `src/router/mo/mysamsunglife/insurance/internet/route.js:26` |

## Representative Screen Responsibilities

| Screen | Observed Responsibility | Important Couplings |
| --- | --- | --- |
| `MDP-MYINT020110M.vue` | Entry screen with many modal imports and navigation branches. | Shared modals, login/app branch, route pushes to later screens. |
| `MDP-MYINT020530M.vue` | Branch screen using `inqrScCd`, `clamCause`, and `DataStore` values. | DataStore, route push to `MDP-MYINT020220M`. |
| `MDP-MYINT020541M.vue` | Claim cause/reason input and save/load flow. | `spotLoad`, `spotSave`, grouped checkbox watcher, next route selection. |
| `MDP-MYINT020550M.vue` | Additional claim detail save/load screen with progress by `inqrScCdParam`. | `spotLoad`, `spotSave`, `busnScCd`. |
| `MDP-MYINT020720M.vue` | Later claim/agent save flow. | `agentBenefit/claim/spotSave`, branch back or next. |

## Transition And Branch Notes

- `MDP-MYINT020110M.vue` imports many modal components. Any modal contract change must search all consumers by imported component name.
- `MDP-MYINT020541M.vue` uses `inqrScCd === '5'` to influence title/branch behavior in the sampled lines.
- `MDP-MYINT020541M.vue` maps loaded API data into `inputObj` and later uses `spotSave`, so field changes require load/save symmetry checks.
- `MDP-MYINT020720M.vue` uses `busnScCd === 'AG'` and save request parameters such as `inqrScCd`, `uploadKey`, `acdtSn`, `acpnSno`, `ccevent`, and `planId`.

## Safe Documentation Checklist

Before editing this family, produce or refresh:

- complete route table for the route file,
- screen-to-screen transition table,
- modal import and consumer table,
- field propagation table for `inqrScCd`, `clamCause`, `clamReason*`, `whoGbn`, `busnScCd`,
- `spotLoad`/`spotSave` payload table for changed screens.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| The route file declares `MDP-MYINT020110M` and `MDP-MYINT020130M`. | `src/router/mo/mysamsunglife/insurance/internet/route.js:18`, `src/router/mo/mysamsunglife/insurance/internet/route.js:26` | high |
| `MDP-MYINT020110M.vue` imports many modal components. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:125`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:134` | high |
| Entry screen navigates to later MYINT screens. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:553`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:555`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:748` | medium |
| Claim input screen uses `spotLoad`/`spotSave` and claim cause/reason fields. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:214`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:243`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020541M.vue:399` | high |
| Later claim screen saves through an agent benefit claim endpoint. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:750`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020720M.vue:762` | medium |
