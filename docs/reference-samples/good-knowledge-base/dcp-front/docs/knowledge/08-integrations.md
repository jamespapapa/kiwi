---
kiwi_doc: true
doc_type: integration
project: "dcp-front-develop"
profile: "dcp-front"
scope: "browser integrations, gateway proxy, app/web bridge"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "src/main.js:168"
  - "src/plugins/com/Axios.js:36"
  - "src/plugins/com/Axios.js:101"
  - "vue.config.js:82"
keywords:
  - integration
  - Axios
  - vestWeb
  - Monimo
  - CMS
---

# Integrations

## Integration Map

| Integration | Front-End Location | What To Document |
| --- | --- | --- |
| Axios/gateway | `src/plugins/com/Axios.js` | Request transform, headers, response/session behavior. |
| Vest/app bridge | Axios transform branch and plugin install options. | When `Vue.vestAjax` is used and what payload shape it expects. |
| Monimo app auth | Axios request header branch. | Header names, token source, channel conditions. |
| CMS contents | `vue.config.js` proxy path. | Local proxy rewrite and target host. |
| Internal backend gateway | `/gw` proxy and runtime path. | Front path vs backend service route distinction. |

## Documentation Rules

- Record integration behavior at the plugin/config layer, not only screen code.
- If an integration reads localStorage or app auth data, mark privacy/security sensitivity.
- If a path is proxy-rewritten locally, document both browser path and target path.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Axios is installed as a Vue plugin with vestWeb options. | `src/main.js:168` | high |
| Axios transform can use `Vue.vestAjax`. | `src/plugins/com/Axios.js:36`, `src/plugins/com/Axios.js:38` | high |
| Monimo app auth headers are added in the request interceptor. | `src/plugins/com/Axios.js:101`, `src/plugins/com/Axios.js:110` | medium |
| CMS contents are proxied and rewritten locally. | `vue.config.js:82`, `vue.config.js:88` | high |
