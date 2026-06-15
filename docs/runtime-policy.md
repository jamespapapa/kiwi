# Runtime Policy

## 파일 경계

선택된 프로젝트 루트가 작업 경계다. 백엔드는 `Path.resolve()`와 `commonpath` 기반 검사를 사용해 루트 밖 경로 접근을 차단한다.

## 명령 실행

코드 수정 목적의 터미널 에이전트는 프로젝트 루트의 `qwen.cmd`만 실행한다. 프로젝트 초기화 시 Windows에서는 현재 우선 Qwen runtime의 `qwen-init.cmd <project-path>`를 실행해 `qwen.cmd`와 `.qwen` 파일들을 만든다. 프로젝트 로컬 `qwen.cmd`가 없거나, 없는 `run-qwen.cmd` 경로를 가리키면 콘솔 시작을 중단하고 프로젝트 초기화를 먼저 요구한다.

```powershell
qwen.cmd
```

우선 runtime은 Windows에서 `D:\aiops\qwencode`가 있으면 그 경로다. 이 경로가 있으면 `KIWI_QWENCODE_RUNTIME_DIR`보다도 먼저 선택한다. 해당 경로가 없을 때만 명시 env runtime과 KIWI 번들 내부 `vendor/qwen-runtime`이 fallback으로 사용된다. 이미 생성된 프로젝트 `qwen.cmd`가 다른 runtime 또는 존재하지 않는 runtime을 가리키면 KIWI는 runtime mismatch로 표시하고, 프로젝트 초기화를 다시 실행할 때 기존 하네스를 `.qwen\init-backups\...`로 백업한 뒤 현재 우선 runtime으로 재생성한다. mismatch 상태에서 Ultrawork Console을 바로 시작하지 않는다.

레거시 비대화형 coder run 경로만 `--model qwen3-coder-next --prompt <prompt> --approval-mode yolo` 형식으로 호출한다.

KIWI는 호출 환경에 `QWEN35_BASE_URL`, `CODER_BASE_URL`, `QWEN35_MODEL`, `CODER_MODEL`, `QWEN35_MAX_TOKENS`, `CODER_MAX_TOKENS`, `QWEN35_CONTEXT_WINDOW`, `CODER_CONTEXT_WINDOW`를 고정값으로 주입한다. Context window는 `262144`이고, API에 요청하는 출력 max tokens는 Qwen3.5 `16384`, Coder `16384`다. 출력 max tokens를 context window와 같은 `262144`로 보내면 입력 토큰이 조금만 있어도 context 초과가 난다. Ultrawork Console에서는 `QWEN_ULTRAWORK_AGENT_VISIBILITY=0`을 주입해 Qwen TUI의 agent tool 직접 메시지 출력은 끄고, Agent Chat/Timeline JSONL 스트림으로 가시성을 제공한다.

## Work Mode

KIWI 콘솔 세션은 시작 시 하나의 work mode를 선택한다. 첫 submitted prompt activation 이후 같은 세션에서 mode를 바꿀 수 없다. 프론트엔드는 선택 모드를 세션 시작 요청에 넣고, 첫 command-bar/Prompt Builder 전송에만 prefix를 자동 주입한다. 백엔드는 같은 세션에서 다른 mode prefix가 들어오면 `409`로 차단한다. Qwen runtime hook도 active state에 mode를 저장하고 이후 trigger가 들어와도 기존 mode를 보존한다.

- `fast`: prefix `lightwork` 또는 alias `fast`, `lw`. FAST/lightwork는 티셔츠 사이징 없이 Kiwi가 직접 작은 작업을 수행한다. runtime policy hook은 이 모드에서 `agent` tool 호출을 막고 직접 focused tool 사용을 허용한다. 이 denial은 정상 FAST lock으로 해석하고 mode conflict로 보지 않는다.
- `ultrawork`: prefix `ultrawork_<size>` 또는 alias `ulw_<size>`. plain `ultrawork`/`ulw`는 기본 `medium`으로 처리한다. 사용자 선택 티셔츠 사이즈에 따라 Qwen subagent 팀을 조율한다.
- `superpowers`: prefix `superpowers_<size>` 또는 alias `spw_<size>`. plain `superpowers`/`spw`는 기본 `medium`으로 처리한다. Qwen extension skill을 먼저 호출해 impact map과 실행 계약을 강화한 뒤 필요할 때 ultrawork agent 루프로 확장한다.

Kiwi 메인 오케스트레이터는 ultrawork/superpowers 작업에서 실질 작업 전에 `todo_write` tool로 계획 상태를 만들고, 사용자 선택 티셔츠 사이즈(`xsmall`, `small`, `medium`, `large`, `xlarge`)와 한국어 계획을 보고한다. Kiwi는 사이즈를 산정하지 않으며, prefix 또는 KIWI UI 사용자 선택값을 source of truth로 따른다. plain `ultrawork`/`ulw`와 `superpowers`/`spw`는 기본 `medium`이다. `xsmall`은 Kiwi 단독, `small`은 light, `medium`은 balanced, `large/xlarge`는 full ultrawork로 진행한다. 계획에는 순서, 현재 진행 중인 항목, 완료/검증 조건이 들어가야 하며, subagent 결과나 주요 결정 뒤에는 todo 상태를 갱신해야 한다. 요구사항, 수용조건, 실행 순서가 모호하면 `planner-35`를 사용한다. 파일 위치가 불명확한 경우 `explorer-35` read-only 탐색은 최대 5개까지 병렬 호출할 수 있다. 사용자 판단이 필요한 경우에는 일반 텍스트 질문 대신 먼저 `ask_user_question` 사용법/schema를 로드한 뒤 실제 `ask_user_question` tool을 호출한다.

`superpowers`는 실제 Qwen extension skill 구조를 사용한다. KIWI는 runtime policy 적용 시 다음 위치에 `superpowers` extension을 설치한다.

- `portable-user/.qwen/extensions/superpowers/qwen-extension.json`
- `portable-user/.qwen/extensions/superpowers/skills/kiwi-superpowers/SKILL.md`
- `portable-user/.qwen/skills/kiwi-superpowers/SKILL.md`
- `templates/project/.qwen/skills/kiwi-superpowers/SKILL.md`
- fallback 호환용 `extensions/superpowers/skills/kiwi-superpowers/SKILL.md`

Qwen SkillTool은 `.qwen/skills/<name>/SKILL.md`와 active extension skill을 모두 읽을 수 있으므로, `superpowers` 모드는 텍스트 프롬프트만이 아니라 실제 `skill` tool로 호출 가능한 런타임 기반을 가진다.

## Project Knowledge Packs

중앙 문서 루트 `D:/aiops/docs/<project-key>/knowledge/00-index.md`와 관련 pack 문서가 있으면, FAST/lightwork, ultrawork, superpowers 모두 이 knowledge index를 시작 지식으로 읽는다. 선택적 Project Info Layer 요약은 `D:/aiops/docs/<project-key>/project-info/`가 실제로 존재할 때만 읽는다. `D:/aiops/docs/<project-key>/knowledge`는 seed 지식이며, 실제 변경 판단은 현재 프로젝트 파일 read/search 근거와 Project Info evidence가 있으면 그 evidence를 우선한다. 긴 pack 전문, `project-info.json` 전체, 대형 EAI markdown 전체를 프롬프트에 붙이지 않고 관련 문서와 필요한 evidence path만 선택적으로 읽고 보고한다.

Ultrawork 팀의 모델 라우팅은 다음과 같다.

- `coder-35`: `Qwen3.5-397B`를 사용하며 구현, 코드 수정, 파일 작성, 테스트 추가, 좁은 repair slice를 담당한다.
- `dcp-front-developer`: `Qwen3.5-397B`를 사용하는 dcp-front 전용 구현 agent다. Vue 2 route/view/Vuex DataStore/Axios/CSS-DOM 변경에만 프로젝트 프로필 감지 시 사용한다.
- `dcp-backend-developer`: `Qwen3.5-397B`를 사용하는 dcp-services 전용 구현 agent다. Java/Spring controller/service/Redis/EAI/mapper 변경에만 dcp-services 또는 하위 모듈 감지 시 사용한다.
- `drt-front-developer`: `Qwen3.5-397B`를 사용하는 DRT 고객용 Vue 3/Vite 프론트 전용 구현 agent다. route/view/component/Pinia/DrtHttpClient/service 변경에 사용한다.
- `drt-backend-developer`: `Qwen3.5-397B`를 사용하는 DRT API Spring Boot/MyBatis 백엔드 전용 구현 agent다. controller/service/biz/mapper/XML/profile config 변경에 사용한다.
- `drt-cms-front-developer`: `Qwen3.5-397B`를 사용하는 DRT CMS Quasar 관리자 프론트 전용 구현 agent다. frontend route/view/service/model/grid/store 변경에 사용한다.
- `drt-cms-backend-developer`: `Qwen3.5-397B`를 사용하는 DRT CMS Spring/MyBatis 관리자 백엔드 전용 구현 agent다. backend REST resource/service/repository/XML/security/batch 변경에 사용한다.
- `explorer-35`: `Qwen3.5-397B`를 사용하는 read-only 탐색 전용 agent다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- `planner-35`, `architect-35`, `reviewer-35`, `debugger-35`, `tester-35`: 모두 `Qwen3.5-397B`를 사용하며 직접 파일을 수정하지 않는다. `tester-35`는 non-mutating 검증 명령만 수행한다.
- `xsmall`은 subagent 없이 Kiwi가 직접 처리한다. `small` 이상에서 Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않고 구현을 `coder-35` 또는 프로젝트 특화 developer agent에 위임하는 것이 원칙이다. Qwen hook payload가 subagent identity를 누락하거나 drift할 수 있어 runtime hook은 identity mismatch만으로 hard-deny하지 않고 advisory event를 남긴다.
- 기존 코드 수정 후 테스트 통과, 빌드 실패, 오류 수정 같은 repair 미션은 구현 agent 전에 `debugger-35`가 실패 표면, root cause, 최소 repair slice를 먼저 정리한다.
- 하나의 구현 agent 호출은 하나의 repair slice만 맡긴다. 한 번의 coherent change와 한 번의 focused verification 후 Kiwi로 복귀해야 하며, 검증 실패 시 같은 agent가 계속 alternate fix를 시도하지 않는다.
- 구현 agent 위임은 Objective, Scope, Files/ownership, Exact steps, Non-goals, Verification, Expected response, failure 시 stop-and-return-to-Kiwi 규칙을 프롬프트에 명시해야 한다.
- 구현 agent가 2번 실패하면 3번째 시도 전 `ask_user_question` tool로 사용자에게 확인한다.
- 모든 구현 결과는 완료 보고나 다음 구현 루프 전에 반드시 `reviewer-35` 검토를 거친다.
- `reviewer-35` 또는 `tester-35`가 문제를 찾았거나 edit/test/tool 실패가 발생하면, 다음 수정 지시 전에 `debugger-35`가 원인과 교정 전략을 정리한다.

검토 단계에서는 `git -C <project-root> diff -- .`를 실행해 변경 내용을 수집한다. 이 명령도 프로젝트 루트 기준으로만 실행된다.

## Dangerous Mode

- 기본 정책: 폐쇄망 KIWI/qwencode 런타임은 KIWI 콘솔 command에 `--approval-mode yolo`를 추가하고 `.qwen/settings.json`의 `tools.approvalMode`도 `yolo`로 유지한다.
- Sandbox는 Windows 폐쇄망 로컬 실행을 위해 `QWEN_SANDBOX=0`으로 유지한다. Qwen 0.17 settings parser와 충돌하므로 `tools.sandbox` boolean은 settings에 쓰지 않는다.

이 모드는 UI 상단에 현재 상태가 표시되지만, 폐쇄망 ultrawork 실행 정책은 YOLO 고정이다.

## 로그

Ultrawork Console 세션은 고유 session id를 가지며 터미널 로그를 `data/ultrawork/<session-id>.terminal.log`에 저장한다. UI는 같은 로그를 SSE로 tail하듯 표시한다.

서브에이전트 이벤트는 프로젝트 `qwen.cmd`가 실제로 가리키는 Qwen runtime의 `portable-runtime/team-events.jsonl`을 tail 한다. 이 파일은 `SubagentStart`, `SubagentStop`, `agent` tool 완료, 파일 수정, shell command, permission 이벤트를 제공한다. 서브에이전트는 별도 콘솔 프로세스가 아니므로 raw stdout을 개별 pane에 직접 연결하지 않는다. 성능 때문에 read-only 도구 호출 전체를 hook으로 남기지는 않고, Agent Chat의 대화 record와 Agent Timeline 이벤트를 함께 본다.

Qwen의 프로젝트별 `portable-runtime/projects/<project>/chats/<session>.jsonl`도 세션 시작 후 생성된 최신 파일을 자동 감지해 tail 한다. KIWI는 이 JSONL에서 사용자 메시지, Kiwi 메시지, `agent` 요청/응답, subagent completion, tool call 요약만 추출해 오른쪽 Agent Chat에 표시한다. 이 스트림은 terminal TUI가 subagent 진행 중 빈 화면을 재렌더링하더라도 실제 agent가 무엇을 요청하고 응답했는지 확인하기 위한 보조 가시성 레이어다.

레거시 비대화형 coder run은 여전히 `data/runs/<run-id>.log`를 사용한다.
