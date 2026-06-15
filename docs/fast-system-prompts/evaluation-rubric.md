# FAST System Prompt Evaluation Rubric

## Objective Rubric

Score each FAST profile prompt from 0 to 5 on these criteria:

- Profile fit: dcp-front covers route/view/component/Vuex DataStore/Axios/CSS/Playwright; dcp-services covers controller/service/repository/MyBatis/EAI/resources-env/profile/verification; generic covers entrypoint/module/config/data/tests/scripts.
- Project docs discipline: requires reading `D:/aiops/docs/<project-key>/knowledge/00-index.md` first when present, then optional Project Info Layer summaries only if that central directory exists, and verifying claims against current files.
- Direct-work quality: asks Kiwi to restate, plan, inspect, make a minimal diff, run focused verification, and report evidence.
- Scope control: includes stop/question conditions for ambiguity, shared ownership, and unverifiable behavior.
- Leakage control: avoids FAST-forbidden sizing, delegation, and mode-switch language in profile prompt bodies.
- Runtime split: keeps a concise runtime injection summary separate from the human-review final prompt.

Passing threshold: every criterion must score 4 or higher, and leakage control must score 5.

## Benchmark Tasks

- dcp-front simple text: "보험금 청구 인트로 화면의 안내 문구 한 줄을 바꾸고 확인해줘."
- dcp-front CSS containment: "버튼 hover 효과가 주변 레이아웃을 밀지 않게 고쳐줘."
- dcp-front state trace: "청구 구분 선택값이 DataStore와 API payload에 반영되는지 확인하고 누락만 고쳐줘."
- dcp-services mapper fix: "특정 조회 조건이 누락되는 MyBatis 동적 SQL 분기를 좁게 수정해줘."
- dcp-services EAI evidence: "EAI 호출 파라미터 한 필드의 전달 경로를 확인하고 필요한 최소 수정만 해줘."
- generic config check: "README의 실행 명령이 현재 package scripts와 맞는지 확인하고 고쳐줘."

## Weakness

- FAST can under-plan if the prompt does not force current-file verification after reading Project Info summaries.
- FAST can become vague if profile-specific surface terms are missing.
- FAST can accidentally inherit team-mode language from older prompt builder templates.
- FAST can over-edit when stop/question conditions are too weak.

## Accepted Improvements

- Added a profile-specific Project Info read and current-file verification requirement.
- Added explicit minimal diff and focused verification rules to every profile.
- Added dcp-front route/view/component/Vuex DataStore/Axios/CSS/Playwright checklist.
- Added dcp-services controller/service/repository/MyBatis/EAI/resources-env/profile/verification checklist.
- Added leakage assertions and runtime/offline bundle reference checks.
