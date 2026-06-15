---
kiwi_doc: true
doc_type: glossary
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "backend module and integration terms"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:29"
  - "dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:52"
  - "dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/actualcost/controller/SlicInsramBilCndtController.java:40"
keywords:
  - glossary
  - EAI
  - Redis
  - Monimo
  - module
---

# Domain Glossary

| Term | Meaning In This Project | Documentation Rule |
| --- | --- | --- |
| `dcp-core` | Shared module for common backend behavior. | Treat changes as cross-module risk. |
| `dcp-gateway` | Gateway/vendor/auth-facing module. | Check security and external integration docs. |
| `dcp-insurance` | Insurance domain module. | Link controller, service, EAI, Redis claim docs. |
| EAI | External/backend integration mechanism using service ids and VO payloads. | Always document service id, request, response, and exception behavior. |
| Redis/session | Cross-request state and session carrier. | Document key, value object, reader/writer, deletion behavior. |
| Monimo | Channel/prefix visible in gateway/controller paths. | Keep route prefix and auth differences explicit. |
| `landscape` | Environment path variable candidate in versioned route mappings. | Preserve exact route pattern. |
| `inqury` | Literal spelling in sampled routes. | Do not silently correct if present in public path. |

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Root project includes shared, gateway, and domain modules. | `pom.xml:29`, `pom.xml:50` | high |
| Literal EAI service IDs appear in gateway service code. | `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:52`, `dcp-gateway/src/main/java/com/samsunglife/dcp/gateway/biz/directmail/service/DirectMailService.java:78` | high |
| Versioned Monimo/landscape route pattern appears in an insurance controller. | `dcp-insurance/src/main/java/com/samsunglife/dcp/insurance/actualcost/controller/SlicInsramBilCndtController.java:40` | high |
