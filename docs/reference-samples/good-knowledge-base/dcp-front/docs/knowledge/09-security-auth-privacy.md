---
kiwi_doc: true
doc_type: security
project: "dcp-front-develop"
profile: "dcp-front"
scope: "front-end auth, session, local storage, and privacy-sensitive behavior"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/plugins/com/Axios.js:97"
  - "src/plugins/com/Axios.js:150"
  - "src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:435"
keywords:
  - security
  - auth
  - session
  - localStorage
  - privacy
---

# Security, Auth, And Privacy

## Sensitive Front-End Surfaces

| Surface | Risk | Documentation Rule |
| --- | --- | --- |
| localStorage UUID/app data | Can identify device/session context. | Do not log raw values in docs or screenshots. |
| Monimo/app auth headers | Auth state can change request behavior. | Record source and branch condition. |
| Session update in response interceptor | Central side effect after API responses. | Link response handling when documenting API failures. |
| Login route branches | Flow can redirect outside current screen. | Document redirect target and trigger condition. |

## Review Rules

- Do not paste full tokens, identifiers, or personal data into knowledge docs.
- If an API depends on app/PC/mobile channel, record channel-specific behavior.
- When changing login/session behavior, search Axios plugin, route guards, app bridge helpers, and affected screens.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Axios request interceptor reads UUID from localStorage. | `src/plugins/com/Axios.js:97`, `src/plugins/com/Axios.js:99` | high |
| Response interceptor updates session-related state. | `src/plugins/com/Axios.js:126`, `src/plugins/com/Axios.js:150` | medium |
| Insurance entry screen has app login route branches. | `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:435`, `src/views/mo/mysamsunglife/insurance/internet/MDP-MYINT020110M.vue:438` | medium |
