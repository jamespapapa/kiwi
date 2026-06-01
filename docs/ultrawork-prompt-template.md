# Ultrawork Prompt Builder Guide

이 문서는 KIWI Prompt Builder의 LangGraph 에이전트가 최종 `qwencode ultrawork` 프롬프트를 만들 때 참고하는 작성 가이드와 표준 템플릿이다.

목표는 Qwen3.5-397B-A17B Kiwi 오케스트레이터, coder-35 구현 담당자, explorer-next 탐색 담당자가 폐쇄망 안에서 끝까지 실행할 수 있는, 구체적이고 검증 가능한 작업 지시문을 만드는 것이다.

## 기본 판단

- 최종 프롬프트는 멋진 요약이 아니라 실행 계약이다.
- 약한 모델도 따를 수 있도록 추상어를 줄이고, 읽을 파일, 검색어, 중단 조건, 검증 명령을 명시한다.
- 기존 프로젝트 지식 베이스가 있으면 반드시 우선 참고하도록 지시한다.
- DCP 큰그림 문서는 오래된 힌트일 수 있으므로 현재 target repo 파일 근거를 우선한다.
- 구현이 허용된 요청과 단순 조사/리뷰 요청을 분리한다.
- 모호하면 바로 구현 프롬프트를 만들지 말고 `interview_user` tool을 호출한다.

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

1. `ultrawork` mode switch
2. 제목
3. 실행 모드
4. 작업 목표
5. 사용자가 확인한 답변
6. DCP 큰그림
7. 프로젝트 지식 베이스 참고 지시
8. 현재 로컬 근거
9. 필수 읽기 파일
10. 필수 검색 명령
11. 구현 규칙
12. 영향도 지도 작성 규칙
13. subagent 운영 계약
14. 검증 계획
15. 완료 보고 형식
16. 중단 조건
17. 진행 방식

## 표준 템플릿

````text
ultrawork

# <작업 제목>

`<IMPLEMENT APPROVED | ANALYSIS ONLY | REVIEW ONLY>`

## 작업 목표

- 사용자의 원 요청:
- 레포 용어로 다시 쓴 목표:
- 이번 세션의 완료 조건:
- 명시적 비목표:

## 사용자 확인 답변

- <질문>: <선택/직접입력 답변>
- 불확실하거나 미확인인 답변:

## DCP 큰그림

- 프론트, 백엔드, 공통 런타임에서 현재 작업과 관련된 큰그림을 요약한다.
- 이 큰그림은 시작 힌트이며, 실제 판단은 현재 프로젝트 파일 검색 결과를 우선한다.

## 프로젝트 지식 베이스 우선 참고

먼저 현재 프로젝트 루트에서 아래 문서를 확인한다. 없으면 없는 사실을 보고하고 코드 검색으로 대체한다.

- `QWEN.md`
- `KIWI.md`
- `docs/knowledge/00-index.md`
- `docs/knowledge/01-repository-map.md`
- `docs/knowledge/02-build-and-runtime.md`
- `docs/knowledge/03-system-boundaries.md`
- `docs/knowledge/04-domain-glossary.md`
- `docs/knowledge/05-api-and-contracts.md`
- `docs/knowledge/06-frontend-css-and-dom.md`
- `docs/knowledge/07-state-and-data-propagation.md`
- `docs/knowledge/12-change-playbooks.md`

## 현재 로컬 프로젝트에서 확인한 근거

- 검색 `<query>`: <match summary>
- 파일 `<path>`: <왜 중요한지>
- 아직 근거가 부족한 항목:

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
- 프론트/UI 작업이면 CSS와 DOM 구조를 별도 영향 범위로 취급한다. template/script/style, scoped/global style 위치, parent layout wrapper, DOM 조작 코드를 함께 읽은 뒤 편집한다.
- `position`, `z-index`, `overflow`, `transform`, `top/left/right/bottom`, `transition`, `animation`, `::before`, `::after` 변경은 기존 containing block과 주변 layout 영향도를 먼저 확인한다.
- 버튼/작은 control의 glow, shine, bling 효과는 버튼 bounds 안에 갇히게 구현한다. 화면이나 부모 영역을 덮는 큰 absolute overlay는 금지한다.

## 프론트 CSS/DOM 가드레일

프론트 작업일 때만 이 섹션을 구체화한다.

- 현재 화면의 DOM 계층:
- parent/wrapper layout:
- scoped style 위치:
- global/shared style 위치:
- button/control 공통 class:
- direct DOM/ref/directive/class toggle:
- 변경할 CSS selector:
- 변경하지 않을 layout 속성:
- animation/effect bounds:
- resize/zoom/horizontal scroll 확인:
- 시각 검증: 현재 폐쇄망 Qwen3.5는 vision이 꺼져 있으므로 Playwright screenshot 파일 경로, DOM/CSS 수치, 사람이 확인해야 할 항목을 남긴다.

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
- explorer-next는 coder endpoint를 쓰는 read-only 탐색 역할이며 파일 위치와 호출 관계가 불명확할 때만 짧게 사용한다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- planner-35는 요구사항/수용조건/순서가 모호할 때 사용한다.
- architect-35는 cross-module, 데이터, 보안, high-blast-radius 작업에서 사용한다.
- coder-35는 Qwen3.5-397B 구현 담당자다. Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않고 모든 구현을 coder-35에 위임한다.
- tester-35는 Qwen3.5 검증 역할이며 검증 명령 실행과 결과 해석이 필요할 때 사용한다.
- reviewer-35는 모든 구현 결과 뒤 최종 diff와 누락 위험을 반드시 검토한다.
- debugger-35는 reviewer/tester 지적, failed edit, failed test, 반복 tool 실패 뒤 수정 루프를 시작하기 전에 원인과 교정 전략을 정리한다.
- 애매하거나 사용자 판단이 필요한 경우에는 일반 텍스트 질문이 아니라 실제 tool 이름인 `ask_user_question`을 호출한다. UI 표시명은 AskUserQuestion이다.

### 구현 agent 작업 계약

coder-35를 호출할 때는 다음 항목을 반드시 포함한다.

- Objective:
- Scope:
- Files/ownership:
- Required reading:
- Exact implementation steps:
- Non-goals:
- Verification command:
- Exploration budget:
- Expected response:

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
- 프로젝트 지식 베이스와 현재 코드가 충돌하면 현재 코드를 우선하고 충돌 사실을 보고한다.

## 진행 방식

1. 요구사항을 현재 코드 용어로 다시 확인한다.
2. 필수 문서와 파일을 읽는다.
3. 필수 검색을 수행한다.
4. 영향도 지도를 작성한다.
5. 구현 모드라면 coder-35에 좁은 repair slice로 위임한다.
6. 구현 결과를 reviewer-35가 검토한다.
7. 변경 후 focused verification을 실행한다.
8. 실패나 수정 루프가 필요하면 debugger-35로 원인을 정리한 뒤 적절한 구현 agent에 재위임한다.
9. 최종 diff와 위험을 reviewer-35가 다시 확인한다.
````

## DCP 특화 강조점

프론트 작업:

- route, screen, shared component/modal, Vuex/DataStore, route params, `spotLoad`, `spotSave`, downstream screen을 추적한다.
- CSS 구조, scoped/global style, parent wrapper layout, 직접 DOM 조작, animation/transition/pseudo-element 범위를 추적한다.
- 단순 버튼 스타일 변경도 기존 CSS selector와 layout/overflow 영향을 확인한 뒤 진행한다.
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
- 프로젝트 지식 베이스가 있으면 참고하도록 지시했는가?
- 완료 보고와 중단 조건이 명확한가?
