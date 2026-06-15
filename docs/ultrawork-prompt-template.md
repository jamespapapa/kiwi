# Ultrawork Prompt Builder Guide

이 문서는 KIWI Prompt Builder의 LangGraph 에이전트가 최종 `qwencode` work mode 프롬프트를 만들 때 참고하는 작성 가이드와 표준 템플릿이다.

목표는 Qwen3.5-397B Kiwi 오케스트레이터, 프로젝트 특화 developer agent, explorer-35 탐색 담당자가 폐쇄망 안에서 끝까지 실행할 수 있는, 구체적이고 검증 가능한 작업 지시문을 만드는 것이다.

## 기본 판단

- 최종 프롬프트는 멋진 요약이 아니라 실행 계약이다.
- 약한 모델도 따를 수 있도록 추상어를 줄이고, 읽을 파일, 검색어, 중단 조건, 검증 명령을 명시한다.
- 장기 기억은 시작 힌트로만 사용하고, 실제 판단은 현재 target repo 파일 근거를 우선한다.
- 구현이 허용된 요청과 단순 조사/리뷰 요청을 분리한다.
- 모호하면 바로 구현 프롬프트를 만들지 말고 `interview_user` tool을 호출한다.
- 먼저 선택된 KIWI work mode(`FAST/lightwork`, `ultrawork`, `superpowers`)를 확인한다. 티셔츠 사이즈(`xsmall`, `small`, `medium`, `large`, `xlarge`)는 ultrawork/superpowers에서만 사용자 선택값을 source of truth로 사용하며, Prompt Builder가 자동 산정해 덮어쓰지 않는다. plain prefix 또는 누락값은 `medium`이다.
- DCP Front에서는 `dcp-front-developer`, dcp-services 또는 그 하위 모듈에서는 `dcp-backend-developer`, DRT Front에서는 `drt-front-developer`, DRT API에서는 `drt-backend-developer`, DRT CMS에서는 target path에 따라 `drt-cms-front-developer` 또는 `drt-cms-backend-developer`, 그 외 프로젝트에서는 `coder-35`를 구현 agent로 사용한다.

## 인터뷰 tool contract

Prompt Builder가 사용자 확인이 필요하다고 판단하면 `needs_input`을 반환하고 다음 구조를 포함한다.

```json
{
  "status": "needs_input",
  "assistant_message": "짧은 설명",
  "interview_tool": {
    "name": "interview_user",
    "reason": "왜 확인이 필요한지",
    "questions": [
      {
        "id": "scope",
        "header": "범위",
        "question": "이번 작업 범위를 어디까지로 볼까요?",
        "options": [
          {
            "label": "프론트만",
            "description": "화면, route, store, API 호출부까지만 포함합니다."
          },
          {
            "label": "백엔드 포함",
            "description": "controller/service/EAI/mapper 영향까지 같이 추적합니다."
          }
        ],
        "allow_other": true
      }
    ]
  }
}
```

질문 규칙:

- 질문은 최대 3개다.
- 각 질문의 보기는 2~4개다.
- 보기는 서로 배타적이어야 한다.
- 추천 보기는 첫 번째에 둔다.
- 사용자가 모를 수 있는 내부 용어만 묻지 말고, 업무 의미나 원하는 결과 기준으로 묻는다.
- 보기로 충분하지 않으면 `allow_other=true`를 둔다.

## 최종 프롬프트 필수 섹션

최종 프롬프트는 다음 섹션을 포함한다.

1. KIWI work mode lock
2. 제목
3. 실행 모드
4. 작업 목표
5. 사용자가 확인한 답변
6. 티셔츠 사이징(ultrawork/superpowers 전용, FAST에는 포함 금지)
7. 필수 읽기 파일
8. 필수 검색 명령
9. 구현 규칙
10. 영향도 지도 작성 규칙
11. subagent 운영 계약
12. qwencode 기본 tool 사용법 초간단 참조
13. 검증 계획
14. 완료 보고 형식
15. 중단 조건
16. 진행 방식

## 표준 템플릿

````text
# <작업 제목>

`<IMPLEMENT APPROVED | ANALYSIS ONLY | REVIEW ONLY>`

## KIWI work mode lock

- Session work mode: `<fast | ultrawork | superpowers>`
- Activation prefix: `<lightwork | ultrawork_<size> | superpowers_<size>>`
- This mode is locked for the current console session after first activation.

## 작업 목표

- 사용자의 원 요청:
- 레포 용어로 다시 쓴 목표:
- 이번 세션의 완료 조건:
- 명시적 비목표:

## 사용자 확인 답변

- <질문>: <선택/직접입력 답변>
- 불확실하거나 미확인인 답변:

## 티셔츠 사이징

- FAST/lightwork 프롬프트에는 이 섹션을 넣지 않는다.
- 사용자 선택: `<xsmall | small | medium | large | xlarge>`
- 최종 source of truth: 사용자 선택값을 따른다.
- 선택 근거: 사용자가 KIWI 좌측 work mode 패널에서 선택한 규모다.
- ultrawork 운영 모드:
  - xsmall: Kiwi 단독. subagent 호출 없이 짧게 처리한다.
  - small: light. explorer-35와 구현 agent 위주, planner/architect는 생략한다.
  - medium: balanced. explorer-35, 구현 agent, reviewer-35 중심으로 진행하고 위험 시 architect-35를 짧게 호출한다.
  - large: full. planner-35, architect-35, 구현 agent, reviewer-35, debugger-35/tester-35를 사용한다.
  - xlarge: full-phased. phase별 계획/구현/리뷰/검증을 분리한다.
- 프로젝트 프로필:
- 구현 담당 agent: `<dcp-front-developer | dcp-backend-developer | drt-front-developer | drt-backend-developer | drt-cms-front-developer | drt-cms-backend-developer | coder-35>`
- 시작 시 이 사이징 결과와 그에 맞는 계획을 사용자에게 먼저 보고한다.

## 필수 읽기 파일

- `<path>`: <확인해야 하는 이유>

## 필수 검색

```bash
rg -n "<keyword>" .
```

각 검색은 목적을 적고 실행한다. 같은 검색을 반복하지 말고, 결과가 부족하면 검색어를 바꾼다.

## 구현 규칙

- 관련 없는 리팩터링, 대규모 포맷팅, 파일 이동, 임의 명명 변경을 하지 않는다.
- 공유 컴포넌트, 공통 store, core module은 모든 consumer를 확인한 뒤에만 건드린다.
- 화면, API, store, core module 등 공유 지점은 현재 파일과 caller/consumer를 확인한 뒤에만 변경한다.

## 영향도 지도 작성

편집 또는 결론 전에 다음을 작성한다.

- entrypoint:
- producer:
- local state/carrier:
- cross-screen or cross-module carrier:
- API/request/response:
- backend controller/service/mapper/EAI/Redis:
- persistence/cache/session:
- downstream consumers:
- skipped branch/default behavior:
- security/privacy risk:

해당 없는 항목은 `해당 없음`이라고 쓰고 근거를 붙인다.

## subagent 운영 계약

- Kiwi는 계획, 위임, 결과 통합, 최종 판단을 맡는다.
- explorer-35는 Qwen3.5-397B를 쓰는 read-only 탐색 역할이며 파일 위치와 호출 관계가 불명확할 때만 짧게 사용한다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- planner-35는 요구사항/수용조건/순서가 모호할 때 사용한다.
- architect-35는 cross-module, 데이터, 보안, high-blast-radius 작업에서 사용한다.
- xsmall은 Kiwi 단독 처리이며 subagent를 호출하지 않는다.
- small은 planner/architect를 생략하고 구현 agent 중심으로 짧게 처리한다.
- medium은 구현 agent와 reviewer-35 중심으로 진행하고, 위험도가 커지면 architect-35를 호출한다.
- large/xlarge는 planner-35, architect-35, 구현 agent, reviewer-35, debugger-35, tester-35를 규모에 맞게 사용한다.
- 구현 agent는 Qwen3.5-397B 담당자다. DCP/DRT/CMS 특화 profile에서는 해당 전용 developer agent를 사용하고, 그 외에는 `coder-35`를 사용한다.
- tester-35는 Qwen3.5 검증 역할이며 검증 명령 실행과 결과 해석이 필요할 때 사용한다.
- reviewer-35는 모든 구현 결과 뒤 최종 diff와 누락 위험을 반드시 검토한다.
- debugger-35는 reviewer/tester 지적, failed edit, failed test, 반복 tool 실패 뒤 수정 루프를 시작하기 전에 원인과 교정 전략을 정리한다.
- 애매하거나 사용자 판단이 필요한 경우에는 일반 텍스트 질문이 아니라 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다.

### 구현 agent 작업 계약

구현 agent를 호출할 때는 다음 항목을 반드시 포함한다.

- Objective:
- Scope:
- Files/ownership:
- Required reading:
- Mandatory workflow:
  1. Scope 확인
  2. 현재 파일 read
  3. Impact map 작성
  4. 작은 수정
  5. Focused verification
  6. Evidence 보고
- Exact implementation steps:
- Non-goals:
- Verification command:
- Exploration budget:
- Required response:
  - scope confirmed 또는 stop reason
  - files read
  - files changed
  - impact map
  - verification
  - remaining risks 또는 exact question

## qwencode 기본 tool 사용법 초간단 참조

- agent: `description`, `prompt`, `subagent_type`를 넣어 호출한다. 구현 위임은 한 번에 한 slice만 준다.
- read/read_file: `file_path`는 프로젝트 루트 기준 절대경로다. 경로가 불확실하면 glob/grep/list_directory로 존재 확인 후 읽는다.
- edit Exact Edit Protocol: `file_path`, `old_string`, `new_string` 필수. edit 직전 target range를 read_file하고, `@file` 참조나 prompt-attached file content는 edit tool read gate를 만족하지 않으므로 현재 세션에서 실제 `read_file`을 먼저 호출한다. `old_string`은 latest read_file 출력에서 그대로 복사한다. 같은 파일에서 edit 성공 후에는 이전 snippet이 stale이므로 다시 읽는다. 삭제/교체가 1줄이든 N줄이든, 즉 any N-line deletion/replacement에서는 변경 대상만 포함한 smallest exact current span을 `old_string`으로 쓰고, 고유하지 않을 때만 최소 주변 context를 붙인다. 보존할 boundary/context 라인이 `old_string`에 포함되면 `new_string`에도 그대로 보존하고, 아니면 span에서 제외한다. `edit_no_occurrence_found`가 나면 같은/더 큰 `old_string` 재시도 금지, 다시 읽고 더 작은 exact literal로 1회만 재시도한 뒤 Kiwi/debugger로 반환한다. PowerShell regex/`Set-Content`/full-file shell rewrite로 우회하지 않는다.
- write_file: `file_path`, `content` 필수. 새 파일/전체 재작성 전용이고 기존 파일 일부 수정은 edit를 우선한다.
- run_shell_command: `command` 필수, 선택 `directory`는 이미 존재하는 절대 디렉터리다.
- ask_user_question: `questions`는 1~4개 객체 배열. 각 객체는 `question`, 12자 이하 `header`, 2~4개 `{label, description}` options가 필수다.
- `todo_write` tool: `todos` 배열. 각 item은 고유 `id`, `content`, `status(pending|in_progress|completed)` 필수다.

## 검증 계획

- 우선 실행할 명령:
- 실행할 수 없는 경우 대체 확인:
- 수동 확인이 필요한 화면/업무 경로:
- 회귀 위험:

## 완료 보고 형식

- 변경/분석 요약:
- 확인한 근거:
- 변경 파일:
- 실행한 검증:
- 남은 위험:
- 사용자에게 필요한 후속 판단:

## 중단 조건

- 업무 의미, 화면/도메인, API carrier, 저장 위치가 불명확하면 편집하지 말고 `ask_user_question` tool로 질문한다.
- 공유 component/modal/store/core module 변경이 필요한데 consumer를 확인하지 못하면 중단한다.
- 보안, 인증, 개인정보, 금융거래, 배포/인프라 파일 변경 가능성이 있으면 사용자 확인 전 편집하지 않는다.
- 장기 기억과 현재 코드가 충돌하면 현재 코드를 우선하고 충돌 사실을 보고한다.

## 진행 방식

1. 요구사항을 현재 코드 용어로 다시 확인한다.
2. 필수 파일을 읽는다.
3. 필수 검색을 수행한다.
4. 영향도 지도를 작성한다.
5. 구현 모드라면 규모와 프로젝트에 맞는 구현 agent에 좁은 repair slice로 위임한다.
6. 구현 결과를 reviewer-35가 검토한다.
7. 변경 후 focused verification을 실행한다.
8. 실패나 수정 루프가 필요하면 debugger-35로 원인을 정리한 뒤 적절한 구현 agent에 재위임한다.
9. 최종 diff와 위험을 reviewer-35가 다시 확인한다.
````

## DCP 특화 강조점

프론트 작업:

- route, screen, shared component/modal, Vuex/DataStore, route params, `spotLoad`, `spotSave`, downstream screen을 추적한다.
- `whoGbn`, `busnScCd`, `clamReason`, `clamCause`, `inqrScCd` 같은 branch driver의 의미를 임의로 바꾸지 않는다.
- 공유 모달은 모든 consumer를 먼저 찾는다.

백엔드 작업:

- controller, request/response DTO, service, mapper/SQL, EAI service id, Redis/session, transaction/error handling을 연결한다.
- EAI/Redis/session 변경은 key, TTL, producer, consumer, failure behavior를 확인한다.
- SQL mapper만 보고 결론 내리지 말고 service caller와 response mapping을 함께 본다.

## 최종 점검

프롬프트를 반환하기 전에 다음을 확인한다.

- 약한 모델이 파일을 어디서부터 읽어야 하는지 알 수 있는가?
- `rg` 검색어가 실제로 실행 가능한가?
- 구현 범위와 금지 범위가 분리되어 있는가?
- 사용자 답변이 반영되었는가?
- 완료 보고와 중단 조건이 명확한가?
