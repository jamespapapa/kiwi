---
kiwi_doc: true
doc_type: security
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "JWT, session, and privacy-sensitive backend surfaces"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:88"
  - "dcp-core/src/main/java/com/samsunglife/dcp/core/auth/jwt/PartnAuthService.java:102"
  - "dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/monimo/controller/MonimoSSOController.java:133"
keywords:
  - JWT
  - Redis session
  - interceptor
  - security
  - privacy
---

# Security, Auth, And Privacy

## Session/Redis Behavior

The sampled interceptor reads a Redis session id header, falls back through session attributes, reads Redis fields, and can delete or inspect session-related values. This makes shared interceptor changes high risk.

Document any code path that:

- reads headers/cookies/session attributes,
- reads or writes Redis session fields,
- deletes session data,
- maps identity fields into logs or downstream parameters.

## JWT/Claim Behavior

Sampled classes parse and build JWT claims in core/gateway code. A good security document must record:

- claim names,
- source of signing key/material,
- token lifetime if visible,
- consumer endpoints,
- privacy-sensitive fields,
- error behavior on invalid/missing token.

## Review Rules

- Never log full personal identifiers, JWTs, or raw Redis payloads in examples.
- Treat helper classes as shared contracts; search all callers before editing.
- Record whether auth logic differs by Monimo/app/PC/mobile channel.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Interceptor reads Redis session id/header and Redis fields. | `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:88`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:98`, `dcp-core/src/main/java/com/samsunglife/dcp/interceptor/ApiCmmuLoggingInterceptor.java:103` | high |
| Shared auth service parses JWT claims. | `dcp-core/src/main/java/com/samsunglife/dcp/core/auth/jwt/PartnAuthService.java:102`, `dcp-core/src/main/java/com/samsunglife/dcp/core/auth/jwt/PartnAuthService.java:110` | high |
| Monimo SSO controller extracts claims and builds/parses JWTs. | `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/monimo/controller/MonimoSSOController.java:133`, `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/monimo/controller/MonimoSSOController.java:308`, `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/monimo/controller/MonimoSSOController.java:370` | high |
