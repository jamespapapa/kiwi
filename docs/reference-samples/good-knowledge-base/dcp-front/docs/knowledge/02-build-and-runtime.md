---
kiwi_doc: true
doc_type: runtime
project: "dcp-front-develop"
profile: "dcp-front"
scope: "build, local runtime, proxy, and verification commands"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "package.json:6"
  - "package.json:11"
  - "vue.config.js:12"
  - "vue.config.js:75"
keywords:
  - npm
  - Vue CLI
  - build mode
  - proxy
  - local
---

# Build And Runtime

## Required Runtime Versions

The sampled `package.json` shows a Vue CLI 3 / Vue 2 stack. The exact Node/npm version is not stated in the sampled files and must be confirmed from team runtime notes or lockfile behavior before changing build tooling.

| Runtime | Evidence |
| --- | --- |
| Vue 2 | `package.json:57` |
| Vue Router 3 | `package.json:67` |
| Vuex 3 | `package.json:73` |
| Vue CLI service 3 | `package.json:76` |

## Local Development Commands

```bash
npm run serve
npm run serve:dev
npm run serve:stage
npm run serve:qa
npm run serve:release
```

These commands select Vue CLI modes. The mode changes environment resolution and can affect backend routing through config and environment files.

## Build Commands

```bash
npm run build
npm run build:local
npm run build:dev
npm run build:stage
npm run build:qa
npm run build:release
```

`vue.config.js` computes `outputDir` from `process.env.NODE_ENV`, with separate output names for `local`, `development`, `stage`, `qa`, and default production-like builds.

## Test And Quality Commands

```bash
npm run lint
npm run test:unit
npm run test:e2e
npm run jsdoc
```

Do not assume these commands currently pass. A documentation run should execute only safe read/build commands unless the user asks for full verification.

## Profiles And Environment Behavior

| Mode/Condition | Behavior |
| --- | --- |
| default local server target | `testServer` starts as `https://twww.samsunglife.com`. |
| local build | `testServer` can switch to `https://api.q.dcp.samsunglife.kr`. |
| `/gw` requests in dev server | proxied to `testServer`, with `secure: false` and `changeOrigin: true`. |
| `/cms/contents` requests | proxied to `testServer` with path rewrite. |
| dev server | HTTPS enabled, host `0.0.0.0`, port `443`. |

## Troubleshooting Notes

- If a screen works in one mode and fails in another, compare Vue mode, `testServer`, and proxy path first.
- If CSS variables/mixins fail during build, check Sass `includePaths` and prepended global SCSS data in `vue.config.js`.
- If API behavior is surprising, inspect both the screen call site and `src/plugins/com/Axios.js`; request headers/body are mutated centrally.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Vue CLI serve/build scripts are mode-specific. | `package.json:6`, `package.json:16` | high |
| Lint, unit, e2e, and jsdoc scripts exist. | `package.json:17`, `package.json:20` | high |
| Local build can change `testServer`. | `vue.config.js:12`, `vue.config.js:14`, `vue.config.js:22` | high |
| Dev server proxies `/gw` and `/cms/contents`. | `vue.config.js:75`, `vue.config.js:82` | high |
