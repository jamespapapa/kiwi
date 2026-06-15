---
kiwi_doc: true
doc_type: testing
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "Maven testing and quality verification sample"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:22"
  - "pom.xml:24"
keywords:
  - Maven
  - test
  - JUnit
  - compile
---

# Testing And Quality

## Available Verification Levels

| Level | Command | Use When |
| --- | --- | --- |
| Root compile | `mvn clean compile` | Broad syntax/dependency check. |
| Root test | `mvn test` | Full test run when environment supports it. |
| Module compile/test | `mvn -pl <module> -am test` | Focused domain/shared module change. |
| Static search review | `rg` controller/service/EAI/session patterns | Before editing shared or high-risk code. |

## Important Caveat

The sampled root POM contains test-skip related properties. A reported green build must state whether tests actually executed or were skipped.

## Quality Documentation Rules

- Record command, module/profile, result, and blocker.
- For controller changes, verify route extraction and service delegation.
- For EAI changes, verify service id and VO mapping.
- For Redis/session changes, verify reader/writer paths and privacy-sensitive fields.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| JUnit version is declared in root properties. | `pom.xml:22` | high |
| Test skip-related properties exist. | `pom.xml:24`, `pom.xml:26` | high |
