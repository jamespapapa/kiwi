# Ultrawork Prompt: Deep Project Documentation

이 프롬프트는 폐쇄망 KIWI/Qwen 환경에서 target 프로젝트를 깊게 문서화할 때 사용한다. `<...>` 값만 채워서 `qwencode` 콘솔에 전달한다.

````text
ultrawork

# Deep Project Documentation Harness

`ANALYSIS AND DOCUMENTATION ONLY`

너는 Qwen3.5-397B-A17B 기반 Kiwi Orchestrator다. 목표는 이 프로젝트를 아주 꼼꼼하게 분석하고, 이후 KIWI Prompt Builder와 ultrawork 작업, 벡터DB 검색에서 재사용 가능한 프로젝트 지식 베이스를 작성하는 것이다.

코드 수정은 금지한다. 문서 파일만 작성한다.

## 입력

- Target project: `<project-name>`
- Target root: `<project-root>`
- Project profile: `<profile-file-name>`
- Common harness: `docs/project-documentation-harness.md`
- Output spec: `docs/documentation-output-spec.md`
- Good reference sample, if available: `docs/reference-samples/good-knowledge-base/<sample-name>/docs/knowledge/`
- Documentation root in target project: `docs/knowledge/`

## 시작 전에 반드시 읽어라

1. KIWI가 제공한 공통 하네스 `docs/project-documentation-harness.md`
2. KIWI가 제공한 산출물 스펙 `docs/documentation-output-spec.md`
3. 선택된 프로젝트 프로필 `<profile-file-name>`
4. good reference sample이 제공되면 `docs/reference-samples/good-knowledge-base/<sample-name>/docs/knowledge/00-index.md`와 대표 문서 몇 개를 읽는다.
5. target 프로젝트 루트의 `QWEN.md`, `KIWI.md`, `README.md`가 존재하면 읽는다.

프로젝트 프로필은 힌트다. 현재 target repo 파일에서 검증되지 않은 내용을 사실처럼 쓰면 실패다.

good reference sample은 문서 구조, 근거 표, 상세도, cross-link 방식만 참고한다. 샘플의 사실관계, 경로, line number, 업무 설명을 target 프로젝트에 복사하면 실패다. 모든 주장은 반드시 현재 target repo에서 다시 검증한 `path:line` 근거로 교체해야 한다.

## 운영 방식

가능하면 ultrawork 멀티에이전트를 사용한다.

- planner-35: 문서 목차와 phase별 체크리스트를 만든다.
- architect-35: 시스템 경계, 모듈 관계, runtime/data/API/integration 구조를 검토한다.
- explorer-next: read-only 탐색만 수행한다. `rg`, `rg --files`, `sed`, `nl`, build descriptor 확인을 맡으며 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- coder-35: `docs/knowledge/`와 `KIWI.md` 문서 작성/수정을 담당한다. Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않는다.
- reviewer-35: 근거 누락, 과잉 추정, 문서 간 모순, 벡터DB 부적합 항목을 검토한다.
- frontend/CSS 문서화가 있으면 architect-35와 reviewer-35가 style root, DOM 조작, containing block, animation/effect bounds를 별도 검토한다.

멀티에이전트가 같은 파일 읽기를 반복하거나 진전이 없으면 단독 모드로 전환하고 `_worklog.md`에 이유를 남긴다.

## 필수 계획

먼저 전체 계획을 작성하라. 계획은 phase 단위로 작성하고, 각 phase가 끝날 때마다 진행 상태를 갱신하라.

계획에는 최소 다음 항목이 있어야 한다.

1. 작업 경계 확인
2. 물리 구조 인벤토리
3. 빌드/런타임/검증 체계
4. 시스템 경계와 모듈 책임
5. 도메인 용어와 업무 flow
6. frontend CSS/DOM 구조
7. API/이벤트/외부 연계 계약
8. 상태/저장/캐시/세션
9. 보안/인증/개인정보
10. 변경 playbook
11. 리뷰와 gap closure

## 반복 탐색 방지

반드시 `docs/knowledge/_worklog.md`를 유지하라.

- 같은 파일을 세 번째 읽기 전에 왜 다시 읽는지 적어라.
- 같은 검색어를 세 번째 실행하지 마라.
- 파일을 읽은 뒤 요약을 남기지 못하면 다음 파일로 넘어가지 마라.
- 긴 파일은 먼저 `rg -n`으로 symbol 위치를 찾고 필요한 주변 line만 읽어라.
- 10분 이상 새 문서가 늘지 않으면 막힌 이유를 `99-gaps-and-questions.md`에 쓰고 다음 phase로 넘어가라.

## 산출물 구조

target 프로젝트에 다음 구조를 만들고 채워라.

```text
docs/knowledge/
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

각 문서는 `docs/documentation-output-spec.md`의 front matter와 Evidence 형식을 따른다.

## 문서 품질 요구사항

- 모든 핵심 주장에는 `path:line` 또는 명확한 symbol 근거가 있어야 한다.
- `확인됨`, `추정`, `미확인`을 분리한다.
- API와 state 문서는 producer, carrier, consumer를 포함한다.
- flow 문서는 entrypoint에서 persistence/external 또는 final UI response까지 연결한다.
- frontend 프로젝트는 CSS 구조, DOM 조작, layout wrapper, selector convention, animation/effect bounds를 `06-frontend-css-and-dom.md`에 별도 문서화한다.
- 버튼/작은 control 효과는 기존 CSS selector와 containing block 근거가 없으면 안전하다고 쓰지 않는다.
- 위험 변경 지점과 중단 조건을 문서화한다.
- 기존 README를 요약하는 것에서 멈추지 말고 실제 코드 근거로 검증한다.
- 벡터DB 검색을 위해 keyword, source_paths, cross-link를 충분히 넣는다.

## 최우선 산출물

문서화 시간이 제한되면 아래 순서로 우선 완성한다.

1. `docs/knowledge/00-index.md`
2. `docs/knowledge/01-repository-map.md`
3. `docs/knowledge/02-build-and-runtime.md`
4. `docs/knowledge/03-system-boundaries.md`
5. `docs/knowledge/04-domain-glossary.md`
6. `docs/knowledge/05-api-and-contracts.md`
7. `docs/knowledge/06-frontend-css-and-dom.md` (frontend 또는 UI 변경 가능 프로젝트)
8. `docs/knowledge/07-state-and-data-propagation.md`
9. `docs/knowledge/12-change-playbooks.md`
10. `docs/knowledge/99-gaps-and-questions.md`

## 금지 사항

- target repo 밖 파일 읽기.
- 코드 파일 수정.
- 빌드 산출물 삭제.
- `git reset`, `git checkout`, 강제 포맷팅.
- 프로젝트 프로필 내용을 검증 없이 확정 문장으로 쓰기.
- 같은 파일/검색어를 무한 반복하기.
- 근거 없는 아키텍처 그림 또는 업무 설명 쓰기.

## 최종 보고

작업을 끝내면 다음 형식으로 보고하라.

```markdown
## 완료 요약

- 프로젝트:
- 사용 프로필:
- 생성/수정한 문서 수:
- 핵심 구조:
- 가장 중요한 flow:
- 가장 위험한 변경 지점:
- 실행/검증 명령:
- 남은 gap:

## 산출물

- `docs/knowledge/00-index.md`
- ...

## 신뢰도

- high:
- medium:
- low:
```
````
