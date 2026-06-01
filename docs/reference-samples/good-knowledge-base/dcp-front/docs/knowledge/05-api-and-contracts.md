---
kiwi_doc: true
doc_type: api
project: "dcp-front-develop"
profile: "dcp-front"
scope: "front-end API client, proxy, and payload contract patterns"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/plugins/com/Axios.js:13"
  - "src/plugins/com/Axios.js:47"
  - "src/plugins/com/Axios.js:85"
  - "vue.config.js:75"
keywords:
  - Axios
  - gateway
  - dcpChnlTyp
  - /gw
  - interceptor
---

# API And Contracts

## API Client Responsibility

`src/plugins/com/Axios.js` is the central HTTP behavior layer. It controls default content type, request transformation, gateway headers, app/channel detection, response session updates, and common error branches.

A screen-level API documentation entry must therefore include both:

1. the component method that builds the request payload,
2. the Axios plugin behavior that mutates or wraps the request.

## Request Transformation Pattern

Observed behavior:

- POST content type defaults to `application/x-www-form-urlencoded`.
- `transformRequest` chooses between `Vue.vestAjax(...)` and `qs.stringify(...)`.
- The branch depends on `headers.dcpChnlTyp`.

This means the raw object assembled by a screen is not necessarily the wire payload.

## Gateway Header Pattern

For URLs starting with `/gw`, the request interceptor adds channel/session/app headers:

| Field/Behavior | Source Pattern |
| --- | --- |
| `dcpChnlTyp` | Set to APP, PC, or MOBILE from app/device conditions. |
| UUID | Read from localStorage when available. |
| Monimo app headers | Added when Monimo app auth data exists. |

## Proxy Behavior

The dev server proxies:

- `/gw` to `testServer`,
- `/cms/contents` to `testServer` after path rewrite.

When debugging an API issue, first decide whether the failing path is browser-side, dev-proxy-side, gateway-side, or backend-service-side.

## Documentation Pattern For Each API

Use this table in flow/API docs:

| Item | What To Record |
| --- | --- |
| Call site | Component, method, line. |
| Endpoint/path | Literal URL or wrapper method target. |
| Request object | Field names, required/optional, source of each field. |
| Response object | Fields consumed by UI, default/error handling. |
| Interceptor effects | Header/body/session mutations from Axios plugin. |
| Backend hint | Gateway path or service/controller candidate if known. |
| Verification | Exact lines for call site and interceptor behavior. |

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Axios defaults POST content type to form URL encoding. | `src/plugins/com/Axios.js:13` | high |
| Request transformation has a `dcpChnlTyp` branch. | `src/plugins/com/Axios.js:23`, `src/plugins/com/Axios.js:36`, `src/plugins/com/Axios.js:40` | high |
| `/gw` requests receive channel/session/app headers in the request interceptor. | `src/plugins/com/Axios.js:85`, `src/plugins/com/Axios.js:89`, `src/plugins/com/Axios.js:97`, `src/plugins/com/Axios.js:101` | high |
| Dev proxy sends `/gw` and CMS content requests to `testServer`. | `vue.config.js:75`, `vue.config.js:82` | high |
| Response interceptor updates session and handles common error codes. | `src/plugins/com/Axios.js:126`, `src/plugins/com/Axios.js:150`, `src/plugins/com/Axios.js:172`, `src/plugins/com/Axios.js:192` | high |
