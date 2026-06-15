---
kiwi_doc: true
doc_type: boundary
project: "dcp-front-develop"
profile: "dcp-front"
scope: "browser, router, state, API, and backend boundary map"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/main.js:168"
  - "src/router/index.js:56"
  - "src/plugins/com/Axios.js:85"
  - "vue.config.js:75"
keywords:
  - boundary
  - browser
  - gateway
  - router
  - state
---

# System Boundaries

## Boundary Map

| Boundary | Front-End Side | Outside/Shared Side | Why It Matters |
| --- | --- | --- | --- |
| Browser app bootstrap | `src/main.js` installs router, store, Axios, plugins, and global components. | Browser runtime and imported plugin packages. | Startup changes can affect every route. |
| Route channel boundary | `src/router/index.js` chooses PC or MO route sets. | URL/domain/device state. | A route fix can silently affect only one channel. |
| State boundary | Vuex modules and `DataStore` carry cross-screen data. | Route params, local storage, backend resume APIs. | State bugs often appear several screens later. |
| API boundary | `src/plugins/com/Axios.js` mutates body/headers and handles responses. | Gateway/backend via `/gw` and CMS proxy. | Screen payload is not always wire payload. |
| Dev proxy boundary | `vue.config.js` maps local paths to `testServer`. | Internal Samsung Life backend hosts. | Local and deployed behavior may differ. |

## Boundary Rules For Documentation

- Do not document a screen as isolated. Always link route, state, API, and child component boundaries.
- Do not treat `/gw` as the final backend route. It is a front-side gateway/proxy path.
- When a flow uses `DataStore`, document producer and consumer screens, not just the mutation site.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Bootstrap installs Axios and shared plugins before mounting Vue. | `src/main.js:160`, `src/main.js:168`, `src/main.js:200` | high |
| Router has separate PC/MO route setup helpers. | `src/router/index.js:56`, `src/router/index.js:66` | high |
| Axios handles `/gw` request headers centrally. | `src/plugins/com/Axios.js:85`, `src/plugins/com/Axios.js:113` | high |
| Dev server proxies `/gw` to a target server. | `vue.config.js:75`, `vue.config.js:81` | high |
