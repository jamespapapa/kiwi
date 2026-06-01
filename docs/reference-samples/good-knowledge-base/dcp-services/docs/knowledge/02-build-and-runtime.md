---
kiwi_doc: true
doc_type: runtime
project: "dcp-services-mevelop"
profile: "dcp-services"
scope: "Maven build, profiles, and runtime constraints"
status: reviewed
confidence: medium
last_verified: "2026-05-20"
source_paths:
  - "pom.xml:15"
  - "pom.xml:17"
  - "pom.xml:52"
  - "pom.xml:229"
keywords:
  - Maven
  - Java 8
  - Spring 5
  - profiles
  - Nexus
---

# Build And Runtime

## Required Runtime Versions

| Runtime/Dependency | Sampled Version | Evidence |
| --- | --- | --- |
| Java | 1.8 | `pom.xml:15` |
| Spring Framework | 5.1.2.RELEASE | `pom.xml:17` |
| Spring Security | 5.1.1.RELEASE | `pom.xml:18` |
| Spring Data | 2.1.2.RELEASE | `pom.xml:19` |
| Spring Data Redis | 2.1.2.RELEASE | `pom.xml:20` |
| JUnit | 4.12 | `pom.xml:22` |

## Build Commands

Use Maven from the root aggregator:

```bash
mvn clean compile
mvn test
mvn package
```

For a single module with dependencies:

```bash
mvn -pl dcp-insurance -am test
```

In a closed network, builds may require the internal Nexus repository configured in the root POM.

## Profiles

The root POM defines profile-specific module lists. The sampled profiles include local/default, dev, qa, stage, and release sections. A full target run must document which modules differ by profile and whether resource filtering changes by profile.

## Skip Flags

The root POM contains test-related skip properties. A build result must record whether tests were actually run or skipped.

## Internal Repository

The sample root POM points to an internal Nexus repository. Do not replace this with public Maven Central assumptions when documenting the closed-network project.

## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| Java 8 and Spring versions are declared in root properties. | `pom.xml:15`, `pom.xml:17`, `pom.xml:18`, `pom.xml:19`, `pom.xml:20` | high |
| Local profile is active by default in the sampled POM. | `pom.xml:52`, `pom.xml:87` | high |
| Multiple environment profiles are declared. | `pom.xml:89`, `pom.xml:122`, `pom.xml:156`, `pom.xml:190` | high |
| Internal Nexus repository is configured. | `pom.xml:229`, `pom.xml:239` | high |
