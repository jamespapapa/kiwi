---
kiwi_doc: true
doc_type: ops
project: "dcp-front-develop"
profile: "dcp-front"
scope: "front-end build modes, output directories, and local proxy operations"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "vue.config.js:24"
  - "vue.config.js:47"
  - "vue.config.js:75"
  - "vue.config.js:90"
keywords:
  - operations
  - deployment
  - outputDir
  - proxy
  - HTTPS
---

# Operations And Deployment

## Build Output Behavior

`vue.config.js` computes output directories by mode. A release/deployment document should record the exact output directory per mode and how artifacts are moved into the hosting environment.

## Local Runtime Behavior

| Setting | Sampled Behavior |
| --- | --- |
| Dev server protocol | HTTPS enabled. |
| Host | `0.0.0.0`. |
| Port | `443`. |
| `/gw` proxy | Targeted to `testServer`. |
| `/cms/contents` proxy | Targeted to `testServer` with path rewrite. |
| Sass globals | Include paths and global SCSS data injected by config. |

## Operational Risks

- Port 443 may require elevated privileges or conflict with local services.
- TLS/proxy behavior can differ in closed network environments.
- Build mode and proxy target can change backend behavior without code changes.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Output directory changes by `NODE_ENV`. | `vue.config.js:24`, `vue.config.js:35` | high |
| Sass include paths and global data are injected. | `vue.config.js:47`, `vue.config.js:61` | high |
| Dev server uses HTTPS, host `0.0.0.0`, port `443`. | `vue.config.js:90`, `vue.config.js:92` | high |
| `/gw` and CMS paths are proxied locally. | `vue.config.js:75`, `vue.config.js:82` | high |
