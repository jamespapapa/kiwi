---
kiwi_doc: true
doc_type: playbook
project: "dcp-front-develop"
profile: "dcp-front"
scope: "safe change playbooks for front-end maintenance"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/router/index.js:56"
  - "src/store/modules/com/DataStore.js:31"
  - "src/plugins/com/Axios.js:85"
keywords:
  - playbook
  - safe change
  - Vue
  - DataStore
  - modal
---

# Change Playbooks

## Playbook: Add Or Rename A Screen Field

1. Locate the route-mounted screen and any child modals/components.
2. Search the field name and related business terms across `src/views`, `src/components`, `src/store`, and plugins.
3. Trace field carriers in this order: local `data()` -> computed/watch -> validation -> DataStore/Vuex -> route params -> `spotLoad` -> `spotSave` -> downstream screen.
4. Update docs for the field before editing code if the flow is ambiguous.
5. Verify the branch for each `inqrScCd`, `busnScCd`, or channel-specific value involved.

## Playbook: Change A Shared Modal

1. Search by import name, file name, emitted event name, and prop name.
2. Build a consumer table: caller screen, props passed, events handled, expected return payload.
3. If the modal returns arrays or positional values, document index meaning before changing anything.
4. Prefer additive payload fields over changing existing order/meaning.
5. Test at least one consumer per distinct branch.

## Playbook: Add Or Change An API Call

1. Document screen call site and payload source fields.
2. Check `src/plugins/com/Axios.js` for request mutation, gateway headers, and response handling.
3. Check `vue.config.js` proxy behavior for local mode.
4. If backend contract is known, link controller/service docs; otherwise record as a gap.
5. Verify error path and loading/session behavior.

## Playbook: Route Or Navigation Change

1. Read `src/router/index.js` to confirm PC/MO route set behavior.
2. Read the specific route file for `path`, `name`, `meta`, and component mapping.
3. Search for `$router.push`, `$router.replace`, and route name literals.
4. Confirm route params/query fields and default behavior on back/reload.
5. Update flow docs and any prompt-builder context before code work.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Route selection has separate PC/MO helper paths. | `src/router/index.js:56`, `src/router/index.js:66` | high |
| DataStore writes arbitrary keyed data and is high risk for field changes. | `src/store/modules/com/DataStore.js:25`, `src/store/modules/com/DataStore.js:31` | high |
| Axios can mutate gateway requests centrally. | `src/plugins/com/Axios.js:85`, `src/plugins/com/Axios.js:113` | high |
