---
kiwi_doc: true
doc_type: repository-map
project: "dcp-front-develop"
profile: "dcp-front"
scope: "physical source layout and responsibilities"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "package.json:6"
  - "src/main.js:63"
  - "src/router/index.js:14"
  - "src/store/index.js:16"
keywords:
  - repository map
  - src
  - router
  - store
  - plugins
---

# Repository Map

## Top-Level Layout

| Path | Type | Responsibility | Primary Consumers | Evidence |
| --- | --- | --- | --- | --- |
| `package.json` | config | Vue CLI scripts, dependency versions, test/lint/jsdoc commands. | Developers, CI/build scripts. | `package.json:6`, `package.json:17` |
| `vue.config.js` | config | Build output directory, Sass globals, dev-server proxy, HTTPS local server. | Vue CLI service. | `vue.config.js:24`, `vue.config.js:47`, `vue.config.js:75` |
| `src/main.js` | app entry | Installs Vue plugins, router, store, Axios, global components, and mounts the app. | Browser runtime. | `src/main.js:63`, `src/main.js:72`, `src/main.js:168`, `src/main.js:200` |
| `src/router` | route root | PC/MO route aggregation and channel/domain routing. | `src/main.js`, Vue Router. | `src/router/index.js:14`, `src/router/index.js:40`, `src/router/index.js:56` |
| `src/store` | state root | Vuex module registration and shared state carriers. | Screens, plugins, route handlers. | `src/store/index.js:3`, `src/store/index.js:16` |
| `src/plugins` | integration layer | Axios, UI/plugins, external app/web integration. | `src/main.js`, components. | `src/main.js:160`, `src/main.js:168` |
| `src/views` | screen root | Route-mounted page components split by channel/domain. | Router entries. | `src/router/mo/mysamsunglife/insurance/internet/route.js:18` |

## Source Roots

The application source root is `src/`. The observed routing split is:

- common route definitions under `src/router/com`,
- mobile route definitions under `src/router/mo`,
- PC route definitions under `src/router/pc`,
- route-mounted screens under matching `src/views/...` families.

`src/router/index.js` imports all three route groups and selects the runtime route set through helper functions.

## Important Config Files

| File | Important Details |
| --- | --- |
| `package.json` | Vue CLI 3 script family uses `--mode local/dev/stage/qa/release`; dependency list includes Vue 2, Vue Router 3, Vuex 3, Axios. |
| `vue.config.js` | Local output directory changes by build mode; Sass include paths and global style data are injected; dev server uses HTTPS on port 443. |
| `src/main.js` | Do not treat plugin installation as incidental. Many global behaviors are installed here before `new Vue`. |
| `src/router/index.js` | Root redirect and route type commit differ between PC and MO. |
| `src/store/index.js` | Module keys are the public state contract used by components. |

## Module/Area Table

| Area | Responsibility | Change Risk |
| --- | --- | --- |
| Router | Determines route set, redirects, and screen component loading. | high |
| Store/DataStore | Carries values across screens and reload boundaries. | high |
| Axios plugin | Mutates request headers/body and centralizes response error behavior. | high |
| Views | Page-level user flow and API payload assembly. | medium-high |
| Components/modals | Shared UI and callback contracts. | high when shared |

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| `src/router/index.js` imports PC/MO/common route groups. | `src/router/index.js:14`, `src/router/index.js:15`, `src/router/index.js:16` | high |
| Vuex module keys include `data`, `auth`, `route`, and UI modules. | `src/store/index.js:16`, `src/store/index.js:27` | high |
| Build/dev proxy behavior lives in `vue.config.js`. | `vue.config.js:24`, `vue.config.js:75`, `vue.config.js:90` | high |
