---
kiwi_doc: true
doc_type: repository-map
project: "dcp-front-develop"
profile: "dcp-front"
scope: "sample knowledge-base index"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "package.json:6"
  - "vue.config.js:12"
  - "src/router/index.js:42"
  - "src/store/index.js:16"
keywords:
  - Vue 2
  - Vue Router
  - Vuex
  - DataStore
  - spotLoad
  - spotSave
---

# dcp-front Knowledge Base Sample

## Executive Summary

`dcp-front-develop` is a Vue 2 / Vue CLI front-end for Samsung Life DCP channels. The code is organized around PC/MO routing, route-driven screens, shared plugins, Vuex modules, and a `DataStore` carrier used by long user flows.

The highest-risk maintenance areas are:

- route-to-screen flow changes, especially mobile insurance internet claim screens,
- values passed through local component state, Vuex `DataStore`, route params, and `spotLoad`/`spotSave` payloads,
- shared modal/component contracts,
- gateway request/response behavior in the Axios plugin.

## How To Use This Knowledge Base

Start with the repository/runtime documents, then jump into a flow or playbook:

| Need | Read |
| --- | --- |
| Understand folder responsibility | [01-repository-map.md](01-repository-map.md) |
| Run or build the project | [02-build-and-runtime.md](02-build-and-runtime.md) |
| Understand boundaries | [03-system-boundaries.md](03-system-boundaries.md) |
| Decode domain terms | [04-domain-glossary.md](04-domain-glossary.md) |
| Trace API/proxy behavior | [05-api-and-contracts.md](05-api-and-contracts.md) |
| Understand screen data shape | [06-data-model.md](06-data-model.md) |
| Trace state and field propagation | [07-state-and-data-propagation.md](07-state-and-data-propagation.md) |
| Inspect external integrations | [08-integrations.md](08-integrations.md) |
| Review auth/privacy-sensitive behavior | [09-security-auth-privacy.md](09-security-auth-privacy.md) |
| Check test commands and quality gates | [10-testing-and-quality.md](10-testing-and-quality.md) |
| Check deployment/runtime operations | [11-operations-and-deployment.md](11-operations-and-deployment.md) |
| Modify the mobile insurance claim flow | [flows/insurance-claim-internet.md](flows/insurance-claim-internet.md) |
| Plan a safe change | [12-change-playbooks.md](12-change-playbooks.md) |
| Check unresolved assumptions | [99-gaps-and-questions.md](99-gaps-and-questions.md) |

## Most Important Entry Points

| Entry Point | Why It Matters |
| --- | --- |
| `package.json` | Defines Vue CLI scripts and core Vue/Router/Vuex dependency versions. |
| `vue.config.js` | Defines mode-specific output directories, Sass globals, and dev proxy rules. |
| `src/main.js` | Boots Vue, installs plugins, router, store, Axios, and shared components. |
| `src/router/index.js` | Selects PC/MO route sets and handles domain/device routing. |
| `src/store/index.js` | Registers the Vuex modules, including the `data` module. |
| `src/store/modules/com/DataStore.js` | Stores cross-screen data using `DATA_UPDATE` and `getDataJson`. |
| `src/plugins/com/Axios.js` | Central request/response interceptor and `/gw` gateway header behavior. |

## Most Important Flows

| Flow | Status | Notes |
| --- | --- | --- |
| Mobile insurance internet claim | sampled | Route file and representative screens are documented in [flows/insurance-claim-internet.md](flows/insurance-claim-internet.md). |
| PC/MO route selection | sampled | Root router switches PC/MO routes based on domain/device checks. |
| DataStore propagation | sampled | `DataStore` is a high-risk carrier for cross-screen values. |

## High Risk Areas

- `DataStore` and route params can hide producers and consumers far away from the edited screen.
- Shared modals under the insurance internet flow must be searched by component name before changing props, events, or return payloads.
- Axios gateway headers depend on URL prefix and channel detection; API behavior can change even when a screen payload stays the same.
- Local/proxy environment in `vue.config.js` affects which backend receives `/gw` and CMS calls.

## Known Gaps

This sample intentionally does not document every DCP front screen. It demonstrates the expected granularity. A full target run must continue through all route groups, shared components, and important API contracts.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| The project is a Vue CLI app with Vue/Router/Vuex dependencies and scripts. | `package.json:6`, `package.json:11`, `package.json:57`, `package.json:67`, `package.json:73` | high |
| Runtime configuration includes proxy and build-mode behavior. | `vue.config.js:12`, `vue.config.js:24`, `vue.config.js:75` | high |
| The router controls PC/MO route selection. | `src/router/index.js:42`, `src/router/index.js:56`, `src/router/index.js:66` | high |
| Vuex registers a `data` module backed by `DataStore`. | `src/store/index.js:16`, `src/store/modules/com/DataStore.js:6` | high |
