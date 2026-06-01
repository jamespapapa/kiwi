# Project Documentation Harness

이 문서는 폐쇄망 안에서 Qwen3.5-397B-A17B가 단독으로, 또는 `qwencode ultrawork` 멀티에이전트로 대형 프로젝트를 면밀히 분석하고 장기 활용 가능한 문서를 작성하기 위한 표준 하네스다.

목표는 빠른 요약이 아니다. 목표는 이후 KIWI Prompt Builder, Ultrawork 실행 프롬프트, 벡터DB 검색, 실제 코드 변경 작업에서 반복적으로 재사용할 수 있는 “근거 있는 프로젝트 지식 베이스”를 만드는 것이다.

## 핵심 원칙

- 현재 레포가 진실이다. 프로젝트 프로필, 과거 메모, README, 기존 문서는 모두 시작 힌트일 뿐이다.
- 모든 중요한 설명에는 파일 경로, 검색어, symbol, command, `path:line` 형태의 근거를 붙인다.
- 문서를 한 번에 쓰려고 하지 않는다. 먼저 지도, 다음 흐름, 다음 계약, 다음 위험 순서로 넓히고 마지막에 검증한다.
- 코드 수정은 하지 않는다. 문서화 실행 중에는 `docs/`, `KIWI.md`, 필요하면 `.kiwi/` 아래 문서화 작업 파일만 쓴다.
- 불확실한 내용은 확정 문장으로 쓰지 않는다. `확인됨`, `추정`, `미확인`, `깨진 근거`를 분리한다.
- 반복 탐색을 통제한다. 같은 파일을 이유 없이 계속 읽지 말고, 파일별 읽은 목적과 요약을 `docs/knowledge/_worklog.md`에 남긴다.
- 약한 모델 기준으로 작업한다. 추상적인 “전체 파악” 지시 대신 작고 검증 가능한 질문 목록으로 나눈다.

## 하네스 입력물

폐쇄망 실행 전에 KIWI는 다음 세 종류의 입력물을 제공한다.

- 공통 하네스: 이 문서와 `docs/documentation-output-spec.md`
- 프로젝트 프로필: `docs/documentation-profiles/*.md` 중 하나
- 실행 프롬프트: `docs/prompts/project-documentation-ultrawork.md`

프로젝트 프로필은 교체 가능해야 한다. `dcp-front`, `dcp-services`는 초기 목표용 프로필이고, 제3/제4 프로젝트는 `generic-template.md`를 복사해 새 프로필 하나만 만들면 같은 하네스를 재사용한다.

## 권장 실행 방식

Qwen3.5-397B-A17B 단독으로도 실행할 수 있지만, 결과 품질은 `ultrawork` 멀티에이전트 방식이 유리하다.

권장 역할 분담:

- Kiwi Orchestrator: 전체 계획, 우선순위, 산출물 계약, 진행률, 중단 판단을 관리한다.
- planner-35: 문서 목차, 분석 질문, 누락 영역, phase별 체크리스트를 설계한다.
- architect-35: 시스템 경계, 모듈 관계, runtime 흐름, cross-repo 계약을 정리한다.
- explorer-next: read-only 탐색을 담당한다. `rg`, `rg --files`, `find`, `sed`, `nl`, build descriptor 확인을 수행하며 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- coder-35: 문서 파일 작성/수정과 필요한 코드 근거 정리를 담당한다. Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않는다.
- reviewer-35: 근거 누락, 과잉 추정, 벡터DB 부적합 문장, 문서 간 모순을 검토한다.
- frontend/CSS 분석이 있으면 architect-35와 reviewer-35가 DOM 계층, style root, layout constraint, animation side effect 근거를 별도 검토한다.

멀티에이전트가 불안정하면 단독 모드로 전환하되 같은 phase와 산출물 계약을 유지한다.

## 전체 진행 순서

### Phase 0. 준비와 경계 확정

해야 할 일:

- `pwd`, `git status --short`, `rg --files`로 현재 루트와 작업 상태를 확인한다.
- 프로젝트 프로필을 읽고 “프로필 힌트”와 “반드시 현재 레포에서 검증할 항목”을 분리한다.
- 문서 작성 대상 디렉터리를 만든다.
- `docs/knowledge/_worklog.md`를 만들고 phase, 질문, 읽은 파일, 결론, 다음 작업을 기록한다.

금지:

- target repo 밖을 임의로 읽지 않는다.
- 사용자가 명시하지 않은 외부 인터넷 검색을 하지 않는다.
- `git reset`, `git checkout`, 대량 포맷팅, 빌드 산출물 삭제를 하지 않는다.

Phase 0 산출물:

- `docs/knowledge/_worklog.md`
- `docs/knowledge/00-index.md` 초안
- `docs/knowledge/99-gaps-and-questions.md` 초안

### Phase 1. 물리 구조 인벤토리

해야 할 일:

- top-level directory, build descriptor, lockfile, config, script, source root, resource root, test root를 분류한다.
- frontend 프로젝트는 router/view/component/store root와 함께 style root, asset root, shared layout wrapper, design token/theme 파일을 별도 분류한다.
- `node_modules`, `target`, `dist`, `.git`, generated output은 제외한다.
- 문서와 코드가 충돌하면 코드와 실행 설정을 우선한다.
- root별 책임을 한 문장으로 쓴 뒤, 근거 파일을 붙인다.

권장 검색:

```bash
rg --files -g '!node_modules' -g '!target' -g '!dist' -g '!build' -g '!*min.js'
rg -n "scripts|dependencies|devDependencies|modules|artifactId|groupId|plugins|mainClass|spring|router|routes|store|controller|service" .
rg -n "style|scss|sass|less|css|theme|layout|wrapper|transition|animation|position|z-index|overflow|transform" .
```

Phase 1 산출물:

- `docs/knowledge/01-repository-map.md`
- `docs/knowledge/02-build-and-runtime.md`
- `docs/knowledge/modules/<module-or-area>.md` 초안

### Phase 2. 실행/빌드/검증 체계

해야 할 일:

- 실제 개발자가 쓰는 명령과 CI가 쓰는 명령을 분리한다.
- build, typecheck, lint, unit test, integration test, local dev, packaging, deploy 관련 명령을 찾는다.
- 실행에 필요한 Java/Node/Python 버전, env var, profile, proxy, certificate, internal registry 의존성을 기록한다.
- 실행하지 못한 명령은 이유를 남긴다.

문서화 포인트:

- “명령어”만 쓰지 말고, 언제 쓰는지, 실패하면 어느 파일을 볼지까지 적는다.
- local command와 server/container command를 혼동하지 않는다.
- 폐쇄망 전용 endpoint, dummy key, certificate 우회 같은 설정은 보안 주석을 붙인다.

Phase 2 산출물:

- `docs/knowledge/02-build-and-runtime.md`
- `docs/knowledge/10-testing-and-quality.md`
- `docs/knowledge/11-operations-and-deployment.md`

### Phase 3. 시스템 경계와 모듈 책임

해야 할 일:

- 사용자가 보는 기능 경계, 내부 모듈 경계, 외부 시스템 경계를 구분한다.
- 각 모듈에 대해 책임, entrypoint, 주요 public contract, 의존 모듈, 데이터 저장소, 위험 변경점을 기록한다.
- 모듈 간 호출이 명시적인 import/call인지, route/API/config 기반인지 구분한다.

권장 산출물 형식:

```markdown
## <module>

- 책임:
- 주요 entrypoint:
- 입력:
- 출력:
- 내부 의존:
- 외부 의존:
- 저장/상태:
- 검증 방법:
- 변경 위험:
- 근거:
```

Phase 3 산출물:

- `docs/knowledge/03-system-boundaries.md`
- `docs/knowledge/modules/*.md`

### Phase 4. 도메인 용어와 업무 흐름

해야 할 일:

- 코드에서 자주 반복되는 업무 명사, 코드값, enum, branch driver, 화면ID, API family를 수집한다.
- 한 용어가 여러 의미로 쓰이면 문맥별로 분리한다.
- legacy 코드값은 임의로 영어 문장으로 번역하지 말고 원문, 값, 사용 위치, 추정 의미를 함께 적는다.
- 화면/업무 flow는 “사용자 행동 -> 화면/route -> local state -> API -> backend service -> persistence/external -> 응답 처리” 순서로 쓴다.
- frontend flow는 “route -> parent layout/wrapper -> screen template -> child component/modal -> DOM/class/style binding -> local/store/API state” 순서도 함께 쓴다.

근거 규칙:

- flow 문서에는 반드시 entry route 또는 controller 근거가 있어야 한다.
- 값 전파 문서에는 producer, carrier, consumer 근거가 있어야 한다.
- code value 문서에는 선언부 또는 비교/분기 사용처가 있어야 한다.

Phase 4 산출물:

- `docs/knowledge/04-domain-glossary.md`
- `docs/knowledge/flows/<flow-name>.md`
- `docs/knowledge/07-state-and-data-propagation.md`

### Phase 4F. 프론트 CSS와 DOM 구조

frontend 프로젝트 또는 UI 변경 가능성이 있는 프로젝트에서는 Phase 4와 병행해 반드시 수행한다.

해야 할 일:

- style root를 분리한다. 전역 CSS/SCSS, scoped component style, channel-specific style, theme/design token, static asset 위치를 구분한다.
- 화면 family별 parent layout/wrapper와 주요 container class를 찾는다.
- 버튼, tab, panel, modal, toolbar, drawer 같은 반복 control의 공통 class와 selector 우선순위를 정리한다.
- `position`, `z-index`, `overflow`, `transform`, `transition`, `animation`, `::before`, `::after`, `box-shadow`, `filter` 사용처를 찾아 layout/visual side effect를 기록한다.
- DOM 직접 조작 패턴을 찾는다. `$refs`, directives, `querySelector`, `getElementById`, class toggle, inline style binding, lifecycle hook 기반 DOM 변경을 분리한다.
- 작은 control 시각 효과 playbook을 작성한다. 효과는 대상 bounds 안에서 clipping되어야 하며, 큰 absolute overlay나 부모 영역을 덮는 animation을 금지한다.
- responsive/zoom/window resize에서 text overflow, horizontal scroll, layout shift가 생길 수 있는 고정 너비와 min-width를 기록한다.

권장 검색:

```bash
rg -n "class=|:class|v-bind:class|ref=|\\$refs|querySelector|getElementById|addEventListener|style=|:style" src
rg -n "position:|z-index|overflow|transform|transition|animation|::before|::after|box-shadow|filter" src
rg -n "button|btn|control|toolbar|tab|panel|drawer|inspector|modal|dialog" src
```

Phase 4F 산출물:

- `docs/knowledge/06-frontend-css-and-dom.md`
- `docs/knowledge/playbooks/frontend-css-safe-change.md`
- 관련 flow 문서의 “CSS/DOM 영향” 섹션

### Phase 5. API, 이벤트, 외부 연계 계약

해야 할 일:

- frontend 프로젝트는 API client, proxy path, request builder, response mapping, error handling을 찾는다.
- backend 프로젝트는 controller route, request/response DTO, service method, mapper, EAI/external client, Redis/session usage를 찾는다.
- 같은 API가 front/backend 양쪽에 있으면 contract 문서에 양쪽 근거를 붙인다.
- request/response field는 이름, 타입 추정, 필수 여부, default, source, consumer를 기록한다.

API 문서 최소 항목:

- endpoint 또는 service id
- 호출 주체
- 처리 주체
- request fields
- response fields
- validation/default/error
- state/session/Redis 영향
- downstream external/EAI/SQL
- 테스트/샘플/fixture 위치
- 근거

Phase 5 산출물:

- `docs/knowledge/05-api-and-contracts.md`
- `docs/knowledge/apis/*.md`
- `docs/knowledge/08-integrations.md`

### Phase 6. 상태, 저장, 캐시, 세션

해야 할 일:

- frontend state, route params, persistent storage, save/load API, backend session, Redis, DB table, file upload/download를 분리한다.
- 값이 화면 사이를 넘어가면 반드시 propagation map을 만든다.
- 캐시/세션/임시저장 값은 만료, key, invalidation, reload behavior를 찾는다.

값 전파 표준 형식:

```markdown
## <field-or-state>

- 목적:
- 허용 값:
- 기본값:
- producer:
- local carrier:
- cross-screen carrier:
- load binding:
- save binding:
- backend carrier:
- persistence/cache:
- consumers:
- skipped branch behavior:
- 근거:
```

Phase 6 산출물:

- `docs/knowledge/07-state-and-data-propagation.md`
- `docs/knowledge/data/*.md`

### Phase 7. 보안, 인증, 권한, 개인정보

해야 할 일:

- 로그인/session/access token/cookie/header/interceptor 흐름을 찾는다.
- 권한 분기, 본인/대리인/미성년/계약자/피보험자 같은 role 분기를 찾는다.
- PII, 금융거래, 파일첨부, 암호화, masking, audit log 위치를 기록한다.
- 보안 판단은 추정하지 말고 코드 근거와 미확인 항목을 분리한다.

Phase 7 산출물:

- `docs/knowledge/09-security-auth-privacy.md`

### Phase 8. 변경 플레이북 작성

해야 할 일:

- 나중에 사용자가 요구사항을 넣었을 때 어떤 순서로 조사해야 하는지 playbook을 만든다.
- 화면 추가, 필드 추가, API field 변경, backend EAI 변경, Redis/session 변경, 공통 컴포넌트 변경 같은 반복 작업별 절차를 쓴다.
- 각 playbook에는 필수 검색어, 필수 파일, 중단 조건, 검증 명령을 포함한다.

Phase 8 산출물:

- `docs/knowledge/12-change-playbooks.md`

### Phase 9. 리뷰와 gap closure

해야 할 일:

- reviewer-35가 문서 전체를 훑어 unsupported claim, duplicated section, stale hint, missing evidence를 찾는다.
- 문서별 front matter, index link, cross-link, evidence 표기를 확인한다.
- “완벽하지 않은 영역”을 숨기지 말고 `99-gaps-and-questions.md`에 남긴다.
- 마지막에 `KIWI.md`에 문서 인덱스와 사용 방법을 요약한다.

Phase 9 산출물:

- `docs/knowledge/99-gaps-and-questions.md`
- 갱신된 `docs/knowledge/00-index.md`
- 갱신된 `KIWI.md`

## 반복 탐색 방지 규칙

Qwen 모델이 같은 파일을 반복해서 읽는 현상을 막기 위해 다음 규칙을 강제한다.

- 모든 file read, search query, command는 `_worklog.md`에 남긴다.
- 같은 파일을 세 번째 읽기 전에 “왜 다시 읽는지”를 한 문장으로 쓴다.
- 같은 검색어를 세 번째 실행하지 않는다. 검색어를 바꿔야 한다.
- 파일을 읽은 뒤 바로 요약하지 못하면 다음 파일로 넘어가지 않는다.
- 긴 파일은 먼저 symbol 또는 keyword 위치를 찾고, 필요한 line 주변만 읽는다.
- `rg --files`로 후보를 좁힌 다음 파일을 읽는다.
- 읽기 루프가 10분 이상 새 문서를 만들지 못하면 중단하고 `99-gaps-and-questions.md`에 막힌 이유를 쓴다.

## 문서 품질 기준

문서 완료 기준:

- 새 개발자가 30분 안에 프로젝트의 큰 구조, 실행 방법, 주요 모듈, 위험 영역을 설명할 수 있어야 한다.
- 요구사항을 받았을 때 Prompt Builder가 어떤 문서를 검색해야 하는지 알 수 있어야 한다.
- Qwen이 작업 중 “관련 문서”를 벡터DB에서 찾았을 때, 그 문서 안에 다음 행동이 있어야 한다.
- 중요한 업무 flow는 entrypoint부터 persistence/external까지 연결되어 있어야 한다.
- 불확실한 부분은 명확히 gap으로 남아 있어야 한다.

거절 기준:

- “대체로”, “아마”, “보통”만 있고 근거가 없는 문서.
- README 내용을 재서술했지만 코드 근거가 없는 문서.
- 파일 목록만 있고 역할/호출/위험 설명이 없는 문서.
- API field나 state carrier를 설명하면서 producer/consumer가 없는 문서.
- DCP 프로필 힌트를 현재 레포 검증 없이 사실처럼 쓴 문서.

## KIWI와 벡터DB 연계 기준

나중에 KIWI가 이 문서를 벡터DB화할 때 검색 품질을 높이기 위해 다음을 지킨다.

- 한 문서는 하나의 주제를 다룬다.
- 문서 앞부분에 `summary`, `keywords`, `source_paths`, `last_verified`를 둔다.
- 긴 flow 문서는 section마다 독립적으로 검색될 수 있게 heading을 구체적으로 쓴다.
- 코드 경로와 업무 용어를 모두 넣는다. 예: `spotSave`, `DataStore`, `보험금 청구`, `020530L`.
- 같은 정보를 여러 문서에 복사하지 말고 index와 cross-link를 사용한다.
- 결론보다 근거를 먼저 회수할 수 있게 `Evidence` 섹션을 유지한다.

## 최종 완료 보고 형식

문서화 작업이 끝나면 Qwen은 다음 형식으로 보고한다.

```markdown
## 완료 요약

- 프로젝트:
- 사용 프로필:
- 생성/수정한 문서 수:
- 핵심 구조 요약:
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
