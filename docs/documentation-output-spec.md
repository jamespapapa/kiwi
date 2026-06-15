# Documentation Output Specification

이 문서는 `docs/project-documentation-harness.md`를 실행했을 때 중앙 docs root에 만들어야 하는 문서 구조와 파일 형식을 정의한다. 목적은 사람이 읽기 좋은 문서와 KIWI 벡터DB 검색에 적합한 문서를 동시에 만드는 것이다.

## 기본 디렉터리

문서화 산출물은 중앙 docs root 기준으로 다음 위치에 둔다.

```text
D:/aiops/docs/<project-key>/knowledge/
  00-index.md
  01-repository-map.md
  02-build-and-runtime.md
  03-system-boundaries.md
  04-domain-glossary.md
  05-api-and-contracts.md
  06-data-model.md
  06-frontend-css-and-dom.md
  07-state-and-data-propagation.md
  08-integrations.md
  09-security-auth-privacy.md
  10-testing-and-quality.md
  11-operations-and-deployment.md
  12-change-playbooks.md
  99-gaps-and-questions.md
  _worklog.md
  apis/
  data/
  flows/
  modules/
  decisions/
```

이 구조는 프로젝트마다 일부 빈 디렉터리가 생겨도 유지한다. 벡터DB ingest는 이 경로를 기준으로 문서 타입을 추론한다.

## 공통 front matter

모든 문서는 가능한 한 다음 front matter로 시작한다.

```yaml
---
kiwi_doc: true
doc_type: repository-map|runtime|boundary|glossary|api|data|frontend-css-dom|state|integration|security|testing|ops|playbook|gap|worklog|module|flow|decision
project: "<project-name>"
profile: "<profile-name>"
scope: "<short scope>"
status: draft|reviewed|verified|stale
confidence: high|medium|low
last_verified: "YYYY-MM-DD"
source_paths:
  - "path/to/file:line"
keywords:
  - "keyword"
---
```

규칙:

- `status=verified`는 reviewer가 근거와 링크를 확인했을 때만 쓴다.
- `confidence=high`는 현재 코드 근거가 2개 이상 있거나 entrypoint부터 consumer까지 연결된 경우에만 쓴다.
- `source_paths`는 대표 근거만 넣고, 상세 근거는 문서 하단 `Evidence`에 둔다.
- `keywords`에는 코드 symbol과 업무 용어를 모두 넣는다.

## Evidence 형식

모든 중요한 문서는 마지막에 `Evidence` 섹션을 둔다.

```markdown
## Evidence

| Claim | Evidence | Confidence |
| --- | --- | --- |
| 이 모듈은 보험금 청구 모바일 플로우를 담당한다. | `src/router/.../route.js:12`, `src/views/.../MDP-....vue:1` | high |
| 이 값은 저장 API payload에 포함된다. | `...:88`, `...:144` | medium |
```

주의:

- `Claim`은 문서 본문에 쓴 핵심 주장이어야 한다.
- `Evidence`는 `rg -n` 또는 `nl -ba`로 확인한 `path:line`을 사용한다.
- line이 계속 바뀔 수 있으면 symbol name과 주변 heading도 함께 쓴다.
- 근거가 없으면 `99-gaps-and-questions.md`로 이동한다.

## 00-index.md

목적: 문서 전체의 진입점.

필수 섹션:

- Executive Summary
- How To Use This Knowledge Base
- Project Profile Used
- Documentation Map
- Most Important Entry Points
- Most Important Flows
- High Risk Areas
- Common Change Playbooks
- Known Gaps

`00-index.md`는 긴 설명을 쓰지 않는다. 각 상세 문서로 연결하는 항목 중심으로 쓴다.

## 01-repository-map.md

목적: 물리 구조와 각 디렉터리의 책임.

필수 섹션:

- Top-Level Layout
- Source Roots
- Resource Roots
- Test Roots
- Generated/Ignored Directories
- Existing Documentation
- Important Config Files
- Module/Area Table

표준 표:

```markdown
| Path | Type | Responsibility | Primary Consumers | Evidence |
| --- | --- | --- | --- | --- |
```

## 02-build-and-runtime.md

목적: 실행, 빌드, 검증, 로컬 개발 환경.

필수 섹션:

- Required Runtime Versions
- Package Managers
- Local Development Commands
- Build Commands
- Test Commands
- Profiles and Environment Variables
- Internal Network/Certificate Notes
- Troubleshooting

명령어는 다음 형식으로 쓴다.

````markdown
### <command-name>

```bash
<command>
```

- Purpose:
- When to run:
- Expected output:
- Common failure:
- Evidence:
````

## 03-system-boundaries.md

목적: 시스템 내부/외부 경계와 모듈 관계.

필수 섹션:

- Runtime Boundary
- User-Facing Boundary
- Internal Module Boundary
- External Systems
- Cross-Repo Contracts
- Dependency Direction
- Forbidden Couplings

## 04-domain-glossary.md

목적: 업무 용어, 코드값, 화면ID, branch driver를 정리.

표준 표:

```markdown
| Term | Meaning | Values | Producers | Consumers | Risk | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
```

규칙:

- 한글 업무 용어와 코드 symbol을 함께 넣는다.
- 의미가 불명확하면 `Meaning`에 `미확인`이라고 쓴다.
- branch driver는 `Risk=high`로 시작한다.

## 05-api-and-contracts.md

목적: API, controller, service id, request/response contract.

필수 섹션:

- API Discovery Method
- Frontend API Clients
- Backend Controllers
- Request/Response DTOs
- Error Handling
- Contract Index
- Cross-Repo Mapping

개별 API는 `D:/aiops/docs/<project-key>/knowledge/apis/<api-or-service-id>.md`로 분리한다.

개별 API 파일 형식:

```markdown
# <API or Service ID>

## Summary

## Callers

## Handler

## Request

| Field | Type | Required | Default | Source | Evidence |

## Response

| Field | Type | Meaning | Consumers | Evidence |

## Validation and Error Handling

## Persistence/External Calls

## Test Evidence

## Change Risks

## Evidence
```

## 06-data-model.md

목적: DTO, VO, store object, DB table, mapper, payload model.

필수 섹션:

- Model Families
- Field Naming Conventions
- Shared DTO/VO
- Persistence Models
- Derived/Calculated Fields
- Unknown Fields

## 06-frontend-css-and-dom.md

목적: frontend 프로젝트의 CSS 구조, DOM 조작 방식, layout constraint, animation/effect 안전 범위를 정리.

필수 섹션:

- Style Roots: global/scoped/channel/theme/static asset 위치
- Layout Wrappers: parent layout, page shell, panel/drawer/modal container
- Selector Conventions: 공통 button/control/tab/panel/modal class와 우선순위
- DOM Manipulation: refs/directives/querySelector/class toggle/style binding/lifecycle hook
- Positioning And Overflow: `position`, `z-index`, `overflow`, `transform`, fixed width/min-width 위험
- Animation And Effects: `transition`, `animation`, `::before`, `::after`, glow/bling effect bounds
- Responsive Risks: resize/zoom/text overflow/horizontal scroll 위험
- Safe Change Playbook Links
- Evidence

frontend가 아닌 프로젝트에서는 이 문서를 만들되 `해당 없음`과 근거를 적거나 `99-gaps-and-questions.md`에 제외 사유를 남긴다.

## 07-state-and-data-propagation.md

목적: 값이 어디에서 만들어지고 어디까지 이동하는지 정리.

필수 섹션:

- State Stores
- Route/Navigation Carriers
- Local Component State
- Save/Load Boundaries
- Session/Redis/Cache
- Field Propagation Index

개별 값 전파는 `D:/aiops/docs/<project-key>/knowledge/data/<field>.md`로 분리한다.

## 08-integrations.md

목적: EAI, external API, Redis, file service, CMS, gateway 같은 외부 연계.

필수 섹션:

- Integration Inventory
- Service IDs
- Request Builders
- Response Mapping
- Timeout/Retry/Error Behavior
- Environment/Profile Dependency
- Operational Risks

## 09-security-auth-privacy.md

목적: 인증, 권한, 세션, 개인정보, 금융거래 관련 제약.

필수 섹션:

- Authentication Flow
- Authorization/Role Branches
- Session Handling
- Sensitive Data
- Masking/Encryption
- Audit/Logging
- Dangerous Assumptions

## 10-testing-and-quality.md

목적: 검증 수단과 테스트 전략.

필수 섹션:

- Existing Test Structure
- Unit Test Commands
- Integration Test Commands
- Manual QA Paths
- Static Checks
- Known Test Gaps
- Recommended Smoke Tests

## 11-operations-and-deployment.md

목적: 운영 환경, 배포, 설정, 로그, 장애 추적.

필수 섹션:

- Deployment Shape
- Runtime Profiles
- Config Files
- Logging
- Monitoring Hooks
- Batch/Async Jobs
- Rollback/Recovery Notes

## 12-change-playbooks.md

목적: 미래 작업 프롬프트 생성에 사용할 절차.

권장 playbook:

- Add or change UI field
- Add or change API field
- Add or change backend service logic
- Change shared component/modal
- Change route/navigation
- Change EAI/external call
- Change Redis/session behavior
- Investigate production issue
- Review risky diff

각 playbook 형식:

```markdown
## <playbook name>

- Applies when:
- Required reading:
- Required search:
- Impact map:
- Edit order:
- Verification:
- Stop conditions:
- Output contract:
```

## 99-gaps-and-questions.md

목적: 모르는 것을 숨기지 않고 유지.

표준 표:

```markdown
| Gap | Why It Matters | What Was Checked | Next Step | Owner | Severity |
| --- | --- | --- | --- | --- | --- |
```

Severity:

- `critical`: 문서 결론 또는 구현 안전성을 막는다.
- `major`: 특정 flow 작업 전 추가 확인이 필요하다.
- `minor`: 편의성/정확도 개선 항목이다.

## _worklog.md

목적: 반복 탐색과 근거 손실을 막는 작업 장부.

형식:

```markdown
## YYYY-MM-DD HH:mm - Phase N

- Question:
- Commands:
- Files read:
- Findings:
- Documents updated:
- Next:
```

규칙:

- 같은 파일을 반복해서 읽었으면 이유를 적는다.
- 같은 검색어를 반복했으면 검색어 변경 이유를 적는다.
- 새 문서 업데이트 없이 오래 탐색했다면 즉시 gap으로 전환한다.

## KIWI.md 업데이트

문서화가 끝나면 target 프로젝트의 `KIWI.md`에는 상세 내용을 복사하지 않고 다음만 요약한다.

- knowledge base 위치
- 가장 중요한 entrypoint
- 가장 중요한 change playbook
- 위험 branch driver
- 검증 명령
- 최신 문서화 일자

`KIWI.md`는 장기 기억의 인덱스이고, 상세 사실은 `D:/aiops/docs/<project-key>/knowledge/`에 둔다.
