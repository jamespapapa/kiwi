# KIWI

KIWI는 Windows 11 로컬 개발 환경에서 `qwencode` Ultrawork 세션을 웹으로 관찰하고 제어하는 통제형 바이브코딩 콘솔입니다. Qwen3.5-397B는 `qwencode` 내부의 Kiwi 메인 오케스트레이터, 설계/기획/리뷰 컨설턴트, `coder-35` 구현 담당자로 동작하고, Qwen3-Coder-Next는 `explorer-next` read-only 탐색 역할을 맡습니다.

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

산출물은 `build/offline/kiwi-offline-win11-py313.zip`이며, Python cp313 wheelhouse, npm 오프라인 캐시, 상위 `deliverables`의 최신 Qwen Code 런타임이 포함됩니다. 상세 절차는 `docs/offline-bundle.md`를 참고합니다.

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
- 승인 없이 실행: KIWI ultrawork 콘솔은 기본적으로 새 `qwencode` 콘솔을 `--approval-mode yolo`로 시작합니다.
- Node heap: 콘솔 실행 시 `NODE_OPTIONS=--max-old-space-size=8192`를 주입합니다.

## 작업 흐름

1. 프로젝트 폴더를 선택하거나 경로를 직접 입력합니다.
2. 초기화를 실행하면 `KIWI.md`와 `docs/` 문서가 생성 또는 갱신됩니다.
3. Ultrawork Console을 시작합니다.
4. 웹 터미널에서 Kiwi에게 요구사항을 직접 프롬프트합니다.
5. 복잡한 작업은 오른쪽 Prompt Builder에 먼저 입력해 Qwen3.5/LangGraph가 인터뷰 질문, 로컬 파일 검색, 표준 ultrawork 프롬프트 생성을 수행하게 합니다.
6. 생성된 프롬프트는 첫 줄에 `ultrawork`를 포함하며, 실행 중인 콘솔에 직접 전송할 수 있습니다.
7. `qwencode` 터미널 출력은 중앙 패널에 실시간 표시됩니다.
8. 서브에이전트 시작/종료, agent tool, 파일 수정, shell command, permission 이벤트는 오른쪽 Agent Timeline에 표시됩니다.
9. 사용자/Kiwi/subagent 응답과 tool call 요약은 오른쪽 Agent Chat에 표시됩니다.
10. Kiwi는 실질 작업 전에 계획을 세우고, subagent 결과나 주요 결정 뒤에 계획 상태를 갱신해야 합니다.
11. ultrawork 콘솔 시작 시 항상 `--approval-mode yolo`가 적용됩니다.

## 프로젝트 지식 베이스 문서화

큰 프로젝트를 바로 수정하기 전에 Qwen3.5-397B-A17B가 폐쇄망 안에서 스스로 레포를 분석해 `docs/knowledge/` 지식 베이스를 만들도록 하는 별도 하네스가 있습니다.

- 공통 절차: `docs/project-documentation-harness.md`
- 산출물 스펙: `docs/documentation-output-spec.md`
- 실행 프롬프트: `docs/prompts/project-documentation-ultrawork.md`
- DCP 프론트 프로필: `docs/documentation-profiles/dcp-front.md`
- DCP 서비스 프로필: `docs/documentation-profiles/dcp-services.md`
- 새 프로젝트 프로필 템플릿: `docs/documentation-profiles/generic-template.md`

이 문서화 하네스는 현재 프로젝트 파일을 근거로 문서를 만들게 하며, 프로필은 시작 힌트로만 사용합니다. 결과 문서는 이후 Prompt Builder와 벡터DB 검색에서 작업 프롬프트의 근거로 사용할 수 있습니다.

## qwencode 런타임 연동

Windows에서 `D:\aiops\qwencode\run-qwen.cmd`가 있으면 KIWI는 이 기존 runtime을 우선 사용한다. 해당 경로가 없을 때만 KIWI 번들 내부 `vendor/qwen-runtime`을 fallback으로 사용한다.

프로젝트 초기화는 Windows에서 현재 우선 runtime의 `qwen-init.cmd <project-path>`를 실행한다. 이 단계에서 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `.qwen/settings.json`, `QWEN.md`가 생성된다.

Ultrawork Console은 이후 프로젝트 루트의 `qwen.cmd`를 PTY로 실행한다. `qwen.cmd`가 없거나 현재 우선 runtime과 다른 runtime을 가리키면 콘솔 시작을 중단하고 프로젝트 초기화를 먼저 요구한다.

## 보안 경계

- 프로젝트 루트 밖 경로 접근은 백엔드에서 차단합니다.
- 파일 수정 목적의 외부 에이전트 실행은 `qwencode` 경로로 제한합니다.
- `dangerous` 모드는 UI에서 명시적으로 켜야 합니다.
- 콘솔 로그는 `data/ultrawork/`에 저장됩니다.
- 비대화형 coder run 로그는 레거시 호환용으로 `data/runs/`에 저장됩니다.
- 세션과 설정은 SQLite에 저장됩니다.

## LangGraph의 현재 위치

초기 버전의 `/api/chat` 경로는 LangGraph로 Qwen3.5를 직접 호출해 요구사항을 구체화하고 비대화형 `qwencode --prompt` 실행을 만들었습니다. Ultrawork Console에서는 메인 오케스트레이션이 `qwencode` 내부 Kiwi/agent tool 흐름으로 이동했기 때문에 LangGraph는 메인 실행 루프가 아니라 실행 전 보조 워크플로에 둡니다.

현재 LangGraph의 핵심 용도는 오른쪽 Prompt Builder입니다. 사용자의 작업 의도를 Qwen3.5가 분석하고, 필요한 경우 질문을 만들며, 선택된 프로젝트 루트 안에서 파일 검색을 수행하고, `docs/samsunglife-dcp-overview.md`의 삼성생명 DCP 큰그림을 합쳐 `qwencode`에 넘길 표준 ultrawork 프롬프트를 생성합니다. 사용자와 상호작용하는 주 실행 화면은 여전히 Ultrawork Console입니다.
