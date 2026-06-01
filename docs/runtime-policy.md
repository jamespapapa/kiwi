# Runtime Policy

## 파일 경계

선택된 프로젝트 루트가 작업 경계다. 백엔드는 `Path.resolve()`와 `commonpath` 기반 검사를 사용해 루트 밖 경로 접근을 차단한다.

## 명령 실행

코드 수정 목적의 터미널 에이전트는 프로젝트 루트의 `qwen.cmd`만 실행한다. 프로젝트 초기화 시 Windows에서는 현재 우선 Qwen runtime의 `qwen-init.cmd <project-path>`를 실행해 `qwen.cmd`와 `.qwen` 파일들을 만든다. 프로젝트 로컬 `qwen.cmd`가 없으면 콘솔 시작을 중단하고 프로젝트 초기화를 먼저 요구한다.

```powershell
qwen.cmd
```

우선 runtime은 Windows에서 `D:\aiops\qwencode`가 있으면 그 경로다. 해당 경로가 없을 때만 KIWI 번들 내부 `vendor/qwen-runtime`이 fallback으로 사용된다. 이미 생성된 프로젝트 `qwen.cmd`가 다른 runtime을 가리키면 KIWI는 runtime mismatch로 표시하고, 프로젝트 초기화를 다시 실행할 때 기존 하네스를 `.qwen\init-backups\...`로 백업한 뒤 현재 우선 runtime으로 재생성한다. mismatch 상태에서 Ultrawork Console을 바로 시작하지 않는다.

레거시 비대화형 coder run 경로만 `--model qwen3-coder-next --prompt <prompt> --approval-mode yolo` 형식으로 호출한다.

KIWI는 호출 환경에 `QWEN35_BASE_URL`, `CODER_BASE_URL`, `QWEN35_MODEL`, `CODER_MODEL`, `QWEN35_MAX_TOKENS`, `CODER_MAX_TOKENS`, `QWEN35_CONTEXT_WINDOW`, `CODER_CONTEXT_WINDOW`를 고정값으로 주입한다. Context window는 `262144`이고, API에 요청하는 출력 max tokens는 Qwen3.5 `16384`, Coder `16384`다. 출력 max tokens를 context window와 같은 `262144`로 보내면 입력 토큰이 조금만 있어도 context 초과가 난다. Ultrawork Console에서는 `QWEN_ULTRAWORK_AGENT_VISIBILITY=0`을 주입해 Qwen TUI의 agent tool 직접 메시지 출력은 끄고, Agent Chat/Timeline JSONL 스트림으로 가시성을 제공한다.

Kiwi 메인 오케스트레이터는 실질 작업 전에 한국어로 계획을 세운다. 계획에는 순서, 현재 진행 중인 항목, 완료/검증 조건이 들어가야 하며, subagent 결과나 주요 결정 뒤에는 완료 항목과 다음 항목을 갱신해야 한다. 요구사항, 수용조건, 실행 순서가 모호하면 `planner-35`를 사용한다. 파일 위치가 불명확한 경우 `explorer-next` read-only 탐색은 최대 5개까지 병렬 호출할 수 있다. 사용자 판단이 필요한 경우에는 일반 텍스트 질문 대신 실제 tool 이름인 `ask_user_question`을 호출한다. UI 표시명은 AskUserQuestion이다.

Ultrawork 팀의 모델 라우팅은 다음과 같다.

- `coder-35`: `Qwen3.5-397B`를 사용하며 구현, 코드 수정, 파일 작성, 테스트 추가, 좁은 repair slice를 담당한다.
- `explorer-next`: `qwen3-coder-next`를 사용하지만 read-only 탐색 전용이다. 독립 질문은 최대 5개까지 병렬 호출할 수 있다.
- `planner-35`, `architect-35`, `reviewer-35`, `debugger-35`, `tester-35`: 모두 `Qwen3.5-397B`를 사용하며 직접 파일을 수정하지 않는다. `tester-35`는 non-mutating 검증 명령만 수행한다.
- Kiwi는 직접 Write/Edit/파일 변경 shell을 실행하지 않고 모든 구현을 `coder-35`에 위임한다.
- 기존 코드 수정 후 테스트 통과, 빌드 실패, 오류 수정 같은 repair 미션은 구현 agent 전에 `debugger-35`가 실패 표면, root cause, 최소 repair slice를 먼저 정리한다.
- 하나의 구현 agent 호출은 하나의 repair slice만 맡긴다. 한 번의 coherent change와 한 번의 focused verification 후 Kiwi로 복귀해야 하며, 검증 실패 시 같은 agent가 계속 alternate fix를 시도하지 않는다.
- `coder-35` 위임은 Objective, Scope, Files/ownership, Exact steps, Non-goals, Verification, Expected response, failure 시 stop-and-return-to-Kiwi 규칙을 프롬프트에 명시해야 한다.
- `coder-35`가 2번 실패하면 3번째 시도 전 `ask_user_question` tool로 사용자에게 확인한다.
- 모든 구현 결과는 완료 보고나 다음 구현 루프 전에 반드시 `reviewer-35` 검토를 거친다.
- `reviewer-35` 또는 `tester-35`가 문제를 찾았거나 edit/test/tool 실패가 발생하면, 다음 수정 지시 전에 `debugger-35`가 원인과 교정 전략을 정리한다.

검토 단계에서는 `git -C <project-root> diff -- .`를 실행해 변경 내용을 수집한다. 이 명령도 프로젝트 루트 기준으로만 실행된다.

## Dangerous Mode

- 기본 정책: 새 콘솔을 항상 `--approval-mode yolo` 인자와 함께 시작한다.
- 기존 SQLite 설정에 `dangerous_mode=false`가 남아 있어도 KIWI 런타임은 YOLO를 effective value로 사용한다.

이 모드는 UI 상단에 현재 상태가 표시되지만, 폐쇄망 ultrawork 실행 정책은 YOLO 고정이다.

## 로그

Ultrawork Console 세션은 고유 session id를 가지며 터미널 로그를 `data/ultrawork/<session-id>.terminal.log`에 저장한다. UI는 같은 로그를 SSE로 tail하듯 표시한다.

서브에이전트 이벤트는 프로젝트 `qwen.cmd`가 실제로 가리키는 Qwen runtime의 `portable-runtime/team-events.jsonl`을 tail 한다. 이 파일은 `SubagentStart`, `SubagentStop`, `agent` tool 완료, 파일 수정, shell command, permission 이벤트를 제공한다. 서브에이전트는 별도 콘솔 프로세스가 아니므로 raw stdout을 개별 pane에 직접 연결하지 않는다. 성능 때문에 read-only 도구 호출 전체를 hook으로 남기지는 않고, Agent Chat의 대화 record와 Agent Timeline 이벤트를 함께 본다.

Qwen의 프로젝트별 `portable-runtime/projects/<project>/chats/<session>.jsonl`도 세션 시작 후 생성된 최신 파일을 자동 감지해 tail 한다. KIWI는 이 JSONL에서 사용자 메시지, Kiwi 메시지, `agent` 요청/응답, subagent completion, tool call 요약만 추출해 오른쪽 Agent Chat에 표시한다. 이 스트림은 terminal TUI가 subagent 진행 중 빈 화면을 재렌더링하더라도 실제 agent가 무엇을 요청하고 응답했는지 확인하기 위한 보조 가시성 레이어다.

레거시 비대화형 coder run은 여전히 `data/runs/<run-id>.log`를 사용한다.
