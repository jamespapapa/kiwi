# Project Profile Template

이 파일은 제3, 제4 프로젝트용 단일 프로필을 만들 때 복사해서 사용한다. 프로필은 현재 레포를 대신 분석하는 문서가 아니라, Qwen3.5-397B-A17B가 폐쇄망 안에서 어떤 가설과 탐색 순서로 문서화를 시작해야 하는지 알려주는 힌트다.

프로필 파일 하나만 교체하면 `docs/project-documentation-harness.md`, `docs/documentation-output-spec.md`, `docs/prompts/project-documentation-ultrawork.md`는 그대로 재사용할 수 있어야 한다.

## 프로젝트 정체성 힌트

- 프로젝트 이름:
- 제품/업무 영역:
- 예상 기술 스택:
- 예상 실행 환경:
- 예상 source root:
- 예상 build/test 도구:
- 예상 주요 모듈:
- 예상 외부 연계:
- 가장 위험한 변경 영역:

## 반드시 현재 레포에서 검증할 것

- 실제 기술 스택과 버전:
- 실제 source/resource/test root:
- 실제 build/test command:
- 실제 module 목록:
- 실제 entrypoint:
- 실제 API/integration 방식:
- 실제 state/persistence 방식:
- 실제 security/auth/session 방식:
- 실제 기존 문서 위치:

## 우선 읽을 후보

먼저 `rg --files`로 존재 여부를 확인한 뒤 읽는다.

- `README.md`
- `QWEN.md`
- `KIWI.md`
- package/build descriptor:
- runtime config:
- source root:
- resource/config root:
- test root:
- docs root:

## 필수 검색어

구조:

```bash
rg --files -g '!node_modules' -g '!target' -g '!dist' -g '!build'
rg -n "<project-specific-structure-keywords>" .
```

entrypoint:

```bash
rg -n "<route|controller|command|handler|main|bootstrap keywords>" .
```

state/data:

```bash
rg -n "<state|cache|session|db|mapper|repository|payload keywords>" .
```

integration:

```bash
rg -n "<api|client|external|queue|event|eai|redis|kafka|http keywords>" .
```

## 문서화해야 할 구조 패턴

### Pattern 1

- 목적:
- 찾는 방법:
- 근거 파일:
- 산출 문서:
- 주의:

### Pattern 2

- 목적:
- 찾는 방법:
- 근거 파일:
- 산출 문서:
- 주의:

### Pattern 3

- 목적:
- 찾는 방법:
- 근거 파일:
- 산출 문서:
- 주의:

## 산출물 우선순위

1. `00-index.md`:
2. `01-repository-map.md`:
3. `02-build-and-runtime.md`:
4. `03-system-boundaries.md`:
5. `04-domain-glossary.md`:
6. `05-api-and-contracts.md`:
7. `06-data-model.md`:
8. `07-state-and-data-propagation.md`:
9. `08-integrations.md`:
10. `09-security-auth-privacy.md`:
11. `10-testing-and-quality.md`:
12. `11-operations-and-deployment.md`:
13. `12-change-playbooks.md`:

## 품질 체크리스트

- 프로젝트의 큰 구조를 10분 안에 설명할 수 있는가?
- build/run/test 방법이 근거와 함께 정리되었는가?
- 주요 entrypoint가 문서화되었는가?
- 주요 data flow가 producer/consumer 기준으로 정리되었는가?
- 외부 연계가 contract 중심으로 정리되었는가?
- 보안/세션/권한이 근거 기반으로 정리되었는가?
- 위험 변경 지점과 중단 조건이 명확한가?
- 벡터DB 검색용 keyword와 source path가 충분한가?

## 중단 조건

- build descriptor를 찾지 못했다.
- source root를 찾지 못했다.
- entrypoint를 찾지 못했다.
- 외부 연계 또는 persistence가 추정만 가능하다.
- 기존 문서와 코드가 충돌하지만 어느 쪽이 최신인지 판단할 수 없다.
