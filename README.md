# KIWI

KIWI는 Windows 11 로컬 개발 환경에서 `qwencode` Ultrawork 세션을 웹으로 관찰하고 제어하는 통제형 바이브코딩 콘솔입니다. Qwen3.5-397B는 `qwencode` 내부의 Kiwi 메인 오케스트레이터, 설계/기획/리뷰 컨설턴트, `coder-35`/DCP 특화 구현 담당자, `explorer-35` read-only 탐색 역할을 맡습니다.

## 구조

- `app/`: Next.js 웹 인터페이스
- `backend/app/`: FastAPI 로컬 런타임
- `backend/app/ultrawork_console.py`: 장기 실행 `qwencode` 콘솔 세션, 터미널 출력, 서브에이전트 이벤트 스트리밍
- `backend/app/prompt_builder.py`: LangGraph 기반 실행 전 프롬프트 빌더
- `data/`: SQLite DB와 실행 로그 저장 위치
- `scripts/`: Windows PowerShell 실행 스크립트

## 런타임 판단

Next 단독으로는 브라우저 보안 제약 때문에 절대 경로 기반 OS 폴더 선택, 로컬 파일 쓰기, `git`/`mvn`/`qwencode` 실행을 안정적으로 처리하기 어렵습니다. 그래서 Python FastAPI를 로컬 런타임으로 두고, 웹은 이 런타임을 호출합니다.

Windows 11에서 Python은 `pywinpty`와 `subprocess`로 `git`, `mvn`, `qwencode` 같은 CLI를 실행할 수 있습니다. KIWI는 대화형 `qwencode` 콘솔은 PTY로 실행하고, 웹에서는 `xterm.js`로 ANSI 터미널 출력을 렌더링합니다. 또한 프로젝트 `qwen.cmd`가 실제로 호출하는 Qwen runtime의 `portable-runtime/team-events.jsonl`과 프로젝트별 `chats/<session>.jsonl`을 tail 해서 서브에이전트 이벤트와 대화 내용을 웹에 스트리밍합니다. 조건은 다음과 같습니다.

- 실행 파일이 `PATH`에 있거나 설정의 `qwencode command`에 절대 경로가 들어가야 합니다.
- KIWI 백엔드 프로세스가 해당 프로젝트 폴더에 대한 읽기/쓰기 권한을 가져야 합니다.
- 명령은 선택된 프로젝트 루트를 working directory로 실행됩니다.
- KIWI는 프로젝트 루트 밖 파일 접근을 차단합니다.

## 설치

```powershell
.\scripts\dev.ps1 -Install
```

폐쇄망에서는 `backend\requirements.txt`와 `package.json` 의존성을 사내 패키지 저장소나 오프라인 번들에서 설치해야 합니다.

## 폐쇄망 반입 번들

인터넷 가능한 준비 환경에서 다음 명령으로 Windows 11/Python 3.13용 번들을 만듭니다.

```bash
.venv/bin/python scripts/build-offline-bundle.py
```

산출물은 `build/offline/qwencode-win11-v0.17.1.zip`과 `build/offline/kiwi-offline-win11-py313.zip`입니다. qwencode ZIP은 `D:\aiops\qwencode`용 Qwen Code 0.17.1 runtime이고, KIWI ZIP은 `D:\aiops\kiwi`용 웹 wrapper와 Python cp313 wheelhouse, npm 오프라인 캐시를 포함합니다. 상세 절차는 `docs/offline-bundle.md`를 참고합니다.

## 실행

```powershell
.\scripts\dev.ps1
```

- 웹: `http://localhost:3000`
- 백엔드: `http://localhost:8787`

## 설정

모델 라우팅은 삼성생명 폐쇄망 기준으로 고정되어 있습니다. 웹에서는 실행 승인 정책만 바꿉니다.

- Orchestrator API: `https://api.t.drt.samsunglife.kr/llmproxy/v1`
- Orchestrator model: `Qwen3.5-397B`
- Coder API: `https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1`
- Coder model: `qwen3-coder-next`
- API key: 사용하지 않습니다.
- qwencode: 프로젝트 초기화가 만든 프로젝트 루트의 `qwen.cmd`만 실행합니다.
- 승인 정책: KIWI/qwencode 폐쇄망 런타임은 기본 `approvalMode=yolo`, `QWEN_SANDBOX=0`으로 실행합니다.
- Node heap: 콘솔 실행 시 `NODE_OPTIONS=--max-old-space-size=8192`를 주입합니다.

## 작업 흐름

1. 프로젝트 폴더를 선택하거나 경로를 직접 입력합니다.
2. 초기화를 실행하면 `KIWI.md`와 `docs/` 문서가 생성 또는 갱신됩니다.
3. 좌측 work mode에서 `FAST`, `ultrawork`, `superpowers` 중 하나를 고르고 콘솔을 시작합니다.
4. 웹 터미널에서 Kiwi에게 요구사항을 직접 프롬프트합니다.
5. 복잡한 작업은 오른쪽 Prompt Builder에 먼저 입력해 Qwen3.5/LangGraph가 인터뷰 질문, KK docs MCP/로컬 검색, 선택 work mode별 표준 프롬프트 생성을 수행하게 합니다.
6. 생성된 프롬프트는 실행 중인 세션의 work mode prefix(`lightwork`, `ultrawork`, `superpowers`)로 최초 1회 감싸져 콘솔에 전송됩니다.
7. `qwencode` 터미널 출력은 중앙 패널에 실시간 표시됩니다.
8. 서브에이전트 시작/종료, agent tool, 파일 수정, shell command, permission 이벤트는 오른쪽 Agent Timeline에 표시됩니다.
9. 사용자/Kiwi/subagent 응답과 tool call 요약은 오른쪽 Agent Chat에 표시됩니다.
10. FAST/lightwork는 티셔츠 사이징 없이 Kiwi가 직접 처리합니다. ultrawork/superpowers는 사용자 선택 또는 plain prefix 기본값 `medium`을 source of truth로 사용하며, 실질 작업 전에 `todo_write` 기반 계획과 선택 사이즈를 보고합니다.
11. 콘솔 시작 시 `--approval-mode yolo`가 적용되고, 프로젝트 `.qwen/settings.json`도 `tools.approvalMode=yolo`로 보정됩니다. Sandbox 비활성화는 `QWEN_SANDBOX=0`으로만 처리합니다.

Prompt Builder는 선택된 프로젝트가 `dcp-front`이면 `dcp-front-developer`, `dcp-services` 또는 그 하위 Maven 모듈이면 `dcp-backend-developer`를 구현 agent로 지정합니다. 그 외 프로젝트는 기본 `coder-35`를 사용합니다.

## KIWI Work Modes

- `FAST/lightwork`: prefix `lightwork`. 작은 작업을 Kiwi가 직접 처리하며 티셔츠 사이징과 subagent 호출이 없습니다.
- `ultrawork`: prefix `ultrawork` 또는 `ultrawork_<size>`. plain prefix는 `medium`이며, 사용자 선택 티셔츠 사이즈에 따라 Qwen subagent 팀을 규모별로 조율합니다.
- `superpowers`: prefix `superpowers` 또는 `superpowers_<size>`. plain prefix는 `medium`이며, Qwen extension skill `kiwi-superpowers`를 먼저 호출할 수 있는 skill-first 모드입니다.

한 콘솔 세션에서 최초 work mode activation 이후 mode는 바꿀 수 없습니다. 다른 mode가 필요하면 콘솔을 종료하고 새 세션을 시작합니다.

`superpowers`의 `kiwi-superpowers`, `using-superpowers`는 Qwen 0.17 built-in `skill` tool의 `skill` 파라미터 값입니다. `tool_search`는 ToolRegistry/MCP 검색용이므로 `tool_search select:kiwi-superpowers`에서 나오지 않는 것이 정상입니다.

## 프로젝트 지식 베이스 문서화

큰 프로젝트를 바로 수정하기 전에 Qwen3.5-397B가 폐쇄망 안에서 스스로 레포를 분석해 `D:/aiops/docs/<project-key>/knowledge/` 지식 베이스를 만들도록 하는 별도 하네스가 있습니다.

- 공통 절차: `docs/project-documentation-harness.md`
- 산출물 스펙: `docs/documentation-output-spec.md`
- 실행 프롬프트: `docs/prompts/project-documentation-ultrawork.md`
- DCP 프론트 프로필: `docs/documentation-profiles/dcp-front.md`
- DCP 서비스 프로필: `docs/documentation-profiles/dcp-services.md`
- 새 프로젝트 프로필 템플릿: `docs/documentation-profiles/generic-template.md`

보강된 seed 문서 묶음은 `docs/project-knowledge-packs.zip`입니다. ZIP 내부 최상위가 `dcp-front/`, `dcp-services/`, `drt-front/`, `drt-api/`, `drt-cms/`라서 Windows에서는 `D:\aiops\docs`에 그대로 풀면 됩니다. 예: `D:\aiops\docs\drt-front\knowledge\00-index.md`.

이 문서화 하네스는 현재 프로젝트 파일을 근거로 문서를 만들게 하며, 프로필은 시작 힌트로만 사용합니다. 결과 문서는 이후 Prompt Builder와 벡터DB 검색에서 작업 프롬프트의 근거로 사용할 수 있습니다.

중앙 지식 문서는 프로젝트 루트 안 `docs/<project-key>`가 아니라 `D:\aiops\docs\<project-key>` 아래에 둡니다. Optional Project Info Layer도 같은 중앙 루트의 `project-info` 디렉터리를 사용합니다.

## qwencode 런타임 연동

Windows 폐쇄망 설치의 표준 runtime 위치는 `D:\aiops\qwencode`다. Qwen Code/qwencode runtime은 `qwencode-win11-v0.17.1.zip`으로 별도 제공하며, `D:\aiops`에 풀면 바로 `D:\aiops\qwencode`가 된다. `D:\aiops\qwencode\install-path.cmd`는 사용자 환경변수 `KIWI_QWENCODE_RUNTIME_DIR`와 `PATH`에 이 경로를 등록한다. 새 터미널을 열면 KIWI 웹을 통하지 않고도 어느 프로젝트 경로에서든 `qwen-init.cmd`, `qwen.cmd`, `qwencode.cmd`를 바로 호출할 수 있다.

관리형 개발 런타임은 모두 `D:\aiops\qwencode\runtimes` 아래에 둔다. `runtimes\node`는 Qwen/DRT/Playwright용 Node 22, `runtimes\node10`은 dcp-front용 Node 10, `runtimes\java`는 Java 17 JDK, `runtimes\java8`은 Java 8 JDK, `runtimes\maven3.6.3`은 Maven 3.6.3, `runtimes\tomcat9`는 dcp-services용 Tomcat 9.0.115이다. KIWI 런타임 체크와 새 터미널 실행 액션은 이 경로들을 우선 사용한다.

런타임 체크 UI는 선택 프로젝트에 필요한 항목만 표시한다. dcp-services는 Java 8/Maven/Tomcat과 Tomcat deploy/run 액션을 사용하고, drt-api와 drt-cms backend는 Java 17/Maven Spring Boot 실행을 사용한다. drt-front와 drt-cms frontend는 Node 20+/Yarn만 표시하며 `yarn install --offline`은 초기화/자동 체크가 아니라 별도 실행 액션이다. Yarn 상태 체크는 Corepack의 `yarn --version`을 실행하지 않고 `.yarnrc`/`yarn.lock`/offline mirror 메타데이터만 확인한다. 실제 실행은 `D:\aiops\qwencode\runtimes\node\yarn.cmd`에 포함된 Yarn classic으로 수행한다. drt-front 액션 cwd는 `dev`, drt-cms frontend 액션 cwd는 `frontend`다. drt-front 기본 실행은 `yarn start`, drt-cms frontend 기본 실행은 `yarn run dev`다.

KIWI 웹은 얇은 래퍼다. Windows에서 `D:\aiops\qwencode\run-qwen.cmd`가 있으면 KIWI는 이 standalone runtime을 최우선으로 사용한다. KIWI 번들에는 Qwen runtime을 포함하지 않으므로 해당 경로가 없으면 설치와 실행은 명확히 실패한다.

프로젝트 초기화는 Windows에서 현재 우선 runtime의 `qwen-init.cmd <project-path>`를 실행한다. 이 단계에서 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `.qwen/settings.json`, `QWEN.md`가 생성된다.

Ultrawork Console은 이후 프로젝트 루트의 `qwen.cmd`를 PTY로 실행한다. `qwen.cmd`가 없거나, 없는 `run-qwen.cmd` 경로를 가리키거나, 현재 우선 runtime과 다른 runtime을 가리키면 콘솔 시작을 중단하고 프로젝트 초기화를 먼저 요구한다.

KIWI는 runtime에 `extensions/ultrawork` 정책과 agent prompt를 주입하고, superpowers skill library를 `portable-user/.qwen/skills/*`, `templates/project/.qwen/skills/*`, `portable-user/.qwen/extensions/superpowers/skills/*`에 함께 설치한다. Qwen 0.17 SkillTool의 기본 탐색 경로인 `.qwen/skills`까지 채우므로 standalone `qwen.cmd`에서도 `kiwi-superpowers`, `using-superpowers`가 바로 호출 가능해야 한다.

## 보안 경계

- 프로젝트 루트 밖 경로 접근은 백엔드에서 차단합니다.
- 파일 수정 목적의 외부 에이전트 실행은 `qwencode` 경로로 제한합니다.
- `dangerous` 모드는 UI에서 명시적으로 켜야 합니다.
- 콘솔 로그는 `data/ultrawork/`에 저장됩니다.
- 비대화형 coder run 로그는 레거시 호환용으로 `data/runs/`에 저장됩니다.
- 세션과 설정은 SQLite에 저장됩니다.

## LangGraph의 현재 위치

초기 버전의 `/api/chat` 경로는 LangGraph로 Qwen3.5를 직접 호출해 요구사항을 구체화하고 비대화형 `qwencode --prompt` 실행을 만들었습니다. Ultrawork Console에서는 메인 오케스트레이션이 `qwencode` 내부 Kiwi/agent tool 흐름으로 이동했기 때문에 LangGraph는 메인 실행 루프가 아니라 실행 전 보조 워크플로에 둡니다.

현재 LangGraph의 핵심 용도는 오른쪽 Prompt Builder입니다. 사용자의 작업 의도를 Qwen3.5가 분석하고, 필요한 경우 질문을 만들며, KK docs MCP와 선택된 프로젝트 루트 안의 파일 검색 계획을 합쳐 `qwencode`에 넘길 선택 work mode별 표준 프롬프트를 생성합니다. FAST/lightwork는 Kiwi 단독 실행 프롬프트로, ultrawork/superpowers는 티셔츠 사이징과 팀/skill 계약을 포함한 프롬프트로 분기합니다. 사용자와 상호작용하는 주 실행 화면은 여전히 Ultrawork Console입니다.
