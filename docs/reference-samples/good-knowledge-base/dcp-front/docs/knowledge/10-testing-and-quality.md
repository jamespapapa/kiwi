---
kiwi_doc: true
doc_type: testing
project: "dcp-front-develop"
profile: "dcp-front"
scope: "test, lint, and quality command sample"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "package.json:17"
  - "package.json:18"
  - "package.json:19"
  - "package.json:20"
keywords:
  - lint
  - unit test
  - e2e
  - jsdoc
---

# Testing And Quality

## Available Commands

| Command | Purpose | Evidence |
| --- | --- | --- |
| `npm run lint` | Lint source files. | `package.json:17` |
| `npm run test:unit` | Run unit tests. | `package.json:18` |
| `npm run test:e2e` | Run e2e tests. | `package.json:19` |
| `npm run jsdoc` | Generate or validate JSDoc output. | `package.json:20` |

## Quality Documentation Rules

- Record command, environment, timestamp, and result.
- If tests cannot run in closed network, record the blocker and nearest safe alternative.
- For route/flow changes, document manual regression paths even when automated tests are absent.
- For shared modal or DataStore changes, test at least one consumer per distinct branch.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| The project defines lint, unit, e2e, and jsdoc scripts. | `package.json:17`, `package.json:18`, `package.json:19`, `package.json:20` | high |
