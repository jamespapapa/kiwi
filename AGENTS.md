# AGENTS.md

이 파일은 KIWI 저장소를 이어받는 에이전트용 운영 지침이다. 스코프는 `kiwi/` 저장소 전체다.

## 프로젝트 목적

KIWI는 삼성생명 폐쇄망 Windows 11 개발 PC에서 쓰는 웹 기반 `qwencode` 콘솔 래퍼다. 표준 설치 구조는 `D:\aiops\qwencode`에 독립 `qwencode` 런타임을 두고, `D:\aiops\kiwi`에 KIWI 웹/백엔드 번들을 두는 방식이다.

KIWI의 역할은 얇은 웹 보조층이다.

- 프로젝트 폴더 선택과 초기화
- 프로젝트별 런타임/JDK/Node/Maven/Tomcat/Yarn/Playwright 상태 확인과 실행 액션 제공
- 장기 실행 `qwen.cmd` PTY 콘솔 표시
- work mode, 티셔츠 사이즈, Prompt Builder, Agent Timeline, Agent Chat 표시
- Project Info Layer와 `D:\aiops\docs\<project-key>` 중앙 지식 문서 연결

실제 장기 실행 코딩 루프는 프로젝트 루트의 `qwen.cmd`가 실행하는 Qwen Code/qwencode 안에서 진행된다.

## 저장소 구조

- `app/`: Next.js 15/React 19 웹 UI
- `app/page.tsx`: xterm.js 기반 메인 `qwen.cmd` PTY 터미널, work mode UI, Prompt Builder, Agent Timeline/Chat
- `app/globals.css`: KIWI 레이아웃과 xterm 스타일
- `backend/app/`: FastAPI 로컬 런타임
- `backend/app/main.py`: HTTP API, 프로젝트 초기화, Prompt Builder, Ultrawork Console, runtime action endpoint
- `backend/app/ultrawork_console.py`: 장기 실행 `qwen.cmd` 콘솔 세션, stdout/stderr 로그, `team-events.jsonl`/chat JSONL tail, SSE
- `backend/app/qwencode_runtime.py`: `D:\aiops\qwencode` 탐지, `qwen-init.cmd`, runtime patch, agent/skill/policy 설치
- `backend/app/work_modes.py`: `fast`, `ultrawork`, `superpowers` mode/prefix/size 규칙
- `backend/app/ultrawork_policy.py`: 프로젝트 profile 감지, 구현 agent 선택, 티셔츠 사이즈별 agent 계약, tool reminder
- `backend/app/prompt_builder.py`: Qwen3.5/LangGraph 기반 실행 전 Prompt Builder
- `backend/app/project_runtime.py`: 프로젝트별 Java/Node/Maven/Tomcat/Yarn/Playwright 체크와 실행 액션
- `backend/app/project_info.py`: 중앙 Project Info Layer 생성/로드/상태 검증
- `docs/ultrawork-agents/`: Qwen runtime에 설치되는 특화 subagent prompt 원본
- `docs/superpowers-skills/`: Qwen 0.17 `skill` tool로 호출되는 superpowers skill 원본
- `docs/fast-system-prompts/`: FAST/lightwork profile별 시스템 프롬프트와 평가 산출물
- `docs/project-knowledge-packs/`: `D:\aiops\docs\<project-key>\knowledge`에 배치할 중앙 지식 문서 seed
- `scripts/build-offline-bundle.py`: 폐쇄망 반입용 `qwencode` ZIP과 KIWI ZIP 생성

## Git/원격 배포

로컬 git 루트는 상위 `cpd-proxy`이고 KIWI 앱은 `kiwi/` prefix 아래에 있다. GitHub 원격 `jamespapapa/kiwi`에는 `kiwi/` 내용이 저장소 루트로 올라가야 한다.

- 상위 `deliverables/`, `ref/`, `aiops/` 등은 입력/참조용이다. KIWI 변경과 섞어 커밋하지 않는다.
- 원격 push는 상위 루트를 그대로 push하지 말고 subtree split 결과를 원격 `main`에 force push한다.

권장 절차:

```bash
git add kiwi
git commit -m "<message>"
split_sha=$(git subtree split --prefix=kiwi HEAD)
push_sha=$(git commit-tree "$split_sha^{tree}" -m "<message>")
git push origin "$push_sha:main" --force
```

## 고정 모델/endpoint

모델 라우팅은 폐쇄망 기준으로 코드와 번들에 고정되어 있다. UI에서 base URL, model, API key를 다시 받는 구조로 되돌리지 말 것.

- Orchestrator/Explorer API: `https://api.t.drt.samsunglife.kr/llmproxy/v1`
- Orchestrator/Explorer model: `Qwen3.5-397B`
- Coder API: `https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1`
- Coder model: `qwen3-coder-next`
- Dummy key: OpenAI-compatible client 형식용이며 실제 인증 key로 취급하지 않는다.
- Context window: `262144`
- Output max tokens: Qwen3.5 `16384`, Coder `16384`
- Qwen3.5 vision: runtime/provider `generationConfig.modalities.image=true`와 `splitToolMedia=true`를 반입 runtime에 반영한다.

이 값은 `backend/app/config.py`, `backend/app/models.py`, `scripts/build-offline-bundle.py`, runtime env/settings patch, README/docs가 서로 맞아야 한다.

## qwencode 런타임 규칙

표준 runtime 위치는 Windows에서 `D:\aiops\qwencode`다. `find_latest_qwencode_runtime()`은 Windows에서 이 경로를 최우선으로 사용하고, 없을 때만 `KIWI_QWENCODE_RUNTIME_DIR`, 개발용 `vendor/qwen-runtime`, 상위 `deliverables`를 fallback으로 본다.

KIWI 번들은 Qwen runtime을 중복 포함하지 않는다. 별도 `qwencode-win11-v0.17.1.zip`을 `D:\aiops`에 풀어 `D:\aiops\qwencode`를 만든다. `install-path.cmd`는 `KIWI_QWENCODE_RUNTIME_DIR`와 사용자 `PATH`를 등록한다.

관리형 개발 런타임은 모두 `D:\aiops\qwencode\runtimes` 아래에 둔다.

- `runtimes\node`: Qwen/DRT/Playwright용 Node 22, npm, Yarn classic
- `runtimes\node10`: dcp-front용 Node 10
- `runtimes\java`: Java 17 JDK
- `runtimes\java8`: Java 8 JDK
- `runtimes\maven3.6.3`: Maven 3.6.3
- `runtimes\tomcat9`: dcp-services용 Tomcat 9.0.115

프로젝트 초기화는 Windows에서 현재 우선 runtime의 `qwen-init.cmd <project-path>`를 실행해 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `.qwen/settings.json`, `.qwen/skills`, `.qwen/agents`, `QWEN.md`를 만든다. 이후 Ultrawork Console은 프로젝트 루트의 `qwen.cmd`만 PTY로 실행한다.

프로젝트 `qwen.cmd`가 없거나, 존재하지 않는 `run-qwen.cmd`를 가리키거나, 현재 우선 runtime과 다른 runtime을 가리키면 콘솔 시작을 중단하고 프로젝트 초기화를 다시 요구한다.

## Work Mode 규칙

세션에는 최초 activation 후 하나의 work mode만 존재한다. 다른 mode prefix를 같은 세션에 다시 넣으면 frontend/backend/runtime policy가 차단하거나 기존 mode를 유지해야 한다.

- `fast`: prefix `lightwork`, alias `fast`, `lw`
- `ultrawork`: prefix `ultrawork_<size>`, alias `ulw_<size>`
- `superpowers`: prefix `superpowers_<size>`, alias `spw_<size>`

`<size>`는 `xsmall`, `small`, `medium`, `large`, `xlarge` 중 하나다. plain `ultrawork`, `ulw`, `superpowers`, `spw`는 기본 `medium`이다.

FAST/lightwork에는 티셔츠 사이즈가 없다. 규모 산정, 규모 보고, subagent 위임이 없어야 하며 Kiwi가 직접 계획, 최소 수정, focused verification을 수행한다.

ultrawork/superpowers에서 티셔츠 사이즈는 사용자 선택값이 source of truth다. KIWI나 Prompt Builder가 자동 산정해 덮어쓰지 않는다. Prompt Builder 요청에 non-FAST size가 없으면 기본 `medium`으로 처리한다.

모든 실질 작업 전 계획은 `todo_write` tool을 사용해야 한다. 일반 텍스트 계획만 쓰거나 `mcp_todowrite` 같은 alias를 먼저 시도하게 만들지 말 것.

## superpowers 규칙

superpowers는 `tool_search`로 스킬을 찾는 구조가 아니다. Qwen 0.17의 내장 `skill` tool을 사용한다.

첫 superpowers tool action은 다음 순서가 되어야 한다.

1. built-in `skill` tool with `skill="kiwi-superpowers"`
2. built-in `skill` tool with `skill="using-superpowers"`
3. 필요 시 task-specific superpowers skill

`kiwi-superpowers`나 `using-superpowers`라는 이름의 tool을 직접 호출하지 않는다. `tool_search select:kiwi-superpowers`에서 나오지 않는 것은 정상이다. `tool_search`는 ToolRegistry/MCP/deferred tool 검색용이고, `.qwen/skills`는 SkillManager/SkillTool 영역이다.

`skill` tool이 unavailable/unknown skill을 반환할 때만 fallback으로 프로젝트 `.qwen/skills/<skill>/SKILL.md`, `D:\aiops\qwencode\portable-user\.qwen\skills\<skill>\SKILL.md`, `SUPERPOWERS_POLICY.md`를 읽는다.

## 특화 agent

프로젝트 profile에 따라 구현 agent를 고른다.

- `dcp-front`, `dcp-front-develop`: `dcp-front-developer`
- `dcp-services`, `dcp-services-mevelop`, 하위 `dcp-*` Maven 모듈: `dcp-backend-developer`
- `drt-front`, `drt-front-main`: `drt-front-developer`
- `drt-api`, `drt-api-main`: `drt-backend-developer`
- `drt-cms`, `drt-cms-main`: target path/요구사항에 따라 `drt-cms-front-developer` 또는 `drt-cms-backend-developer`
- 그 외: `coder-35`

특화 agent 원본은 `docs/ultrawork-agents/*.md`이고, runtime patch 시 `portable-user/.qwen/agents`, `templates/project/.qwen/agents`, `extensions/ultrawork/agents`에 설치된다.

team mode에서 Kiwi는 구현 mutation을 selected implementation agent에 위임하는 것이 원칙이다. 다만 Qwen hook payload가 subagent identity를 누락하거나 drift할 수 있어 현재 runtime hook은 identity mismatch만으로 hard-deny하지 않는 advisory 정책이다. planner/architect/reviewer/debugger/explorer/tester는 직접 파일 수정하지 않는다는 프롬프트 계약을 유지한다.

## Project Docs와 Project Info

중앙 문서 루트는 `D:\aiops\docs\<project-key>`다. 프로젝트 내부 `docs/<project-key>`나 `docs/kiwi/project-info` 경로로 되돌리지 말 것.

- 지식 seed: `D:\aiops\docs\<project-key>\knowledge\00-index.md` 및 관련 문서
- 선택적 Project Info: `D:\aiops\docs\<project-key>\project-info\*.md`, `project-info.json`

runtime activation은 중앙 knowledge index를 먼저 읽게 하고, Project Info는 해당 중앙 디렉터리가 있을 때만 optional summary로 사용하게 한다. Prompt Builder는 Project Info Layer 상태/요약을 프롬프트에 축약 주입한다. `project-info.json` 전체나 대형 EAI markdown 전체를 프롬프트에 붙이지 않는다.

seed pack은 `docs/project-knowledge-packs.zip`과 `docs/project-knowledge-packs/v1/`에 있다. Windows에서는 ZIP의 프로젝트 키 디렉터리를 `D:\aiops\docs` 밑에 풀어 `D:\aiops\docs\dcp-services\knowledge\00-index.md` 같은 형태로 배치한다.

## 프로젝트 런타임 체크/실행

`backend/app/project_runtime.py`는 선택 프로젝트에 필요한 항목만 표시한다.

- `dcp-services`: Java 8, Maven 3.6.3, Tomcat 9.0.115, dcp-core reactor, Tomcat deploy/run
- `dcp-front`: Node 10, npm
- `drt-front`: Node 20+, Yarn classic, cwd `dev`, `yarn install --offline`, `yarn start`
- `drt-api`: Java 17, Maven, Spring Boot run
- `drt-cms`: backend는 Java 17/Maven, frontend는 Node 20+/Yarn, frontend cwd `frontend`

런타임 실행 액션은 새 OS 터미널을 열어 실행한다. Yarn 상태 체크는 네트워크를 막기 위해 `yarn --version`을 실행하지 않고 lockfile/offline mirror/런타임 metadata를 본다. `yarn install --offline`은 상태 체크가 아니라 사용자가 누르는 실행 액션이다.

Playwright는 프로젝트 Node가 아니라 `D:\aiops\qwencode\runtimes\node`의 Node 22/npx를 사용한다.

## UI 규칙

- 메인 터미널은 `@xterm/xterm`과 `@xterm/addon-fit`을 유지한다. ANSI 출력을 `<pre>`로 되돌리지 말 것.
- xterm 스크롤은 내부 `.xterm-viewport`만 사용한다. `.terminal` 외부 overflow를 `auto`로 만들어 이중 스크롤을 만들지 말 것.
- 중앙 터미널 아래 명령 입력창은 유지한다. 사용자는 xterm 직접 입력과 command bar 입력, Prompt Builder 전송을 모두 사용할 수 있어야 한다.
- 알림은 fixed popup layer로 유지한다. 상단 전체 레이아웃을 미는 bar로 되돌리지 말 것.
- 좌측 런타임 설정/프로젝트/모드/티셔츠 UI를 상단 전체 폭 패널로 되돌리지 말 것.
- 오른쪽 Prompt Builder/Agent Chat 패널은 열고 닫을 수 있어야 하며, 닫으면 터미널 영역이 확장되어야 한다.

## 보안과 작업 경계

- 선택된 프로젝트 루트가 작업 경계다.
- 백엔드는 프로젝트 루트 밖 경로 접근을 차단한다.
- 폐쇄망 KIWI/qwencode runtime은 기본 `dangerous_mode=true`, `--approval-mode yolo`, `QWEN_SANDBOX=0`로 실행한다.
- `tools.sandbox` boolean을 settings에 다시 쓰지 말 것. Qwen 0.17 parser와 충돌할 수 있다.
- 외부 네트워크 의존을 추가하지 말 것. 반입 번들은 폐쇄망에서 설치/실행 가능해야 한다.
- 기존 사용자 변경, 대상 프로젝트 변경, 상위 참조 소스를 임의로 되돌리지 말 것.

## 로그와 가시성

- 콘솔 로그: `data/ultrawork/<session-id>.terminal.log`
- Prompt Builder 로그: `data/prompt-builder/<run-id>.jsonl`
- 레거시 coder run 로그: `data/runs/<run-id>.log`
- Qwen team events: 실제 runtime의 `portable-runtime/team-events.jsonl`
- Qwen chat records: runtime의 `portable-runtime/projects/<project>/chats/<session>.jsonl`

Qwen subagent는 별도 콘솔 프로세스가 아니라 내부 `agent` tool 호출이다. subagent별 raw stdout을 별도 터미널에 붙일 수 있다고 가정하지 말 것. KIWI는 메인 PTY 출력, Agent Timeline, Agent Chat을 합쳐 보여준다.

## 오프라인 번들

생성 명령:

```bash
python3 scripts/build-offline-bundle.py
```

산출물:

- `build/offline/qwencode-win11-v0.17.1.zip`
- `build/offline/qwencode-win11-v0.17.1.zip.sha256`
- `build/offline/kiwi-offline-win11-py313.zip`
- `build/offline/kiwi-offline-win11-py313.zip.sha256`

번들러는 상위 `deliverables/qwen-code-offline-*` runtime을 patch한 뒤 `qwencode` ZIP으로 만들고, KIWI ZIP에는 Python cp313 wheelhouse, npm offline cache, wrapper scripts, source를 포함한다. KIWI ZIP 안에 Qwen runtime을 중복 포함하지 않는다.

번들 후 확인:

```bash
unzip -p build/offline/kiwi-offline-win11-py313.zip kiwi/bundle-manifest.json
unzip -p build/offline/qwencode-win11-v0.17.1.zip qwencode/README-KIWI.md
npm cache verify --cache build/offline/kiwi/vendor/npm-cache
```

## 검증 명령

문서만 수정하면 build는 필수는 아니지만, 코드/번들러/runtime policy를 건드렸다면 아래를 확인한다.

```bash
python3 -m compileall backend scripts/build-offline-bundle.py scripts/*.py
npm run typecheck
npm run build
npm audit --audit-level=moderate
git diff --check
```

관련 영역별 assertion:

```bash
python3 scripts/assert-work-mode-foundation.py
python3 scripts/assert-superpowers-porting.py
python3 scripts/assert-superpowers-full-port.py
python3 scripts/assert-qwen-runtime-upgrade.py
python3 scripts/assert-project-runtime-checks.py
python3 scripts/assert-drt-profiles-and-knowledge-packs.py
python3 scripts/assert-edit-tool-hardening.py
python3 scripts/smoke-kiwi-phase5.py
```

## 변경 원칙

- 현재 코드가 진실이다. 문서와 코드가 충돌하면 먼저 코드에서 확인한다.
- 폐쇄망 반입 가능성을 깨는 의존성을 추가하지 않는다.
- Python 의존성 추가 시 Windows cp313 wheelhouse 가능성을 확인한다.
- npm 의존성 추가 시 `package-lock.json`과 npm offline cache 번들링을 확인한다.
- 모델/endpoint/런타임 경로를 사용자 확인 없이 바꾸지 않는다.
- 진단 가능성을 낮추지 않는다. 오류는 UI 또는 백엔드 로그에서 endpoint/model/status/body 일부가 보이게 유지한다.
