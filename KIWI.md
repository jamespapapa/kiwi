# KIWI.md - KIWI 프로젝트 지도

이 파일은 KIWI 자체 개발을 위한 장기 기억입니다. 사용자가 선택한 외부 프로젝트에도 같은 형식의 `KIWI.md`가 생성됩니다.

<!-- KIWI:MAP:START -->
## 프로젝트 지도

- 프로젝트명: `kiwi`
- 목적: `qwencode` Ultrawork 멀티에이전트 세션을 웹에서 관찰하고 제어하는 Windows 11 로컬 콘솔
- UI: Next.js App Router + `xterm.js`
- 런타임: Python FastAPI + `pywinpty`/SSE 콘솔 스트리밍
- 저장소: SQLite (`data/kiwi.sqlite3`)
- 실행 로그: `data/ultrawork/`, 레거시 coder run은 `data/runs/`
- 현재 UI 원칙: 좌측 프로젝트/런타임, 중앙 xterm 단독 터미널, 우측 슬라이드 Prompt Builder/Agent Timeline

### 핵심 파일

- `app/page.tsx`: 메인 웹 인터페이스
- `app/globals.css`: UI 스타일
- `backend/app/main.py`: FastAPI API 엔트리포인트
- `backend/app/ultrawork_console.py`: 장기 실행 `qwencode` 콘솔 세션, 터미널 출력, Agent Timeline 이벤트 스트리밍
- `backend/app/agent_runtime.py`: 레거시 LangGraph 기반 PM/아키텍트/기획자 역할 분기
- `backend/app/prompt_builder.py`: Qwen3.5 LangGraph 기반 ultrawork 프롬프트 빌더, 로컬 검색, 인터뷰 질문, 최종 지시문 생성
- `backend/app/ultrawork_policy.py`: 티셔츠 사이징, 프로젝트 프로필 감지, 규모별 subagent 계약, tool 치트시트 생성
- `backend/app/coder_runner.py`: 레거시 비대화형 `qwencode --prompt` 실행, 로그 스트리밍, 완료 후 리뷰
- `backend/app/qwencode_runtime.py`: 프로젝트 `qwen.cmd` 확인, `qwen-init.cmd`용 Qwen Code 런타임 탐지
- `backend/app/project_analyzer.py`: 프로젝트 초기 분석, `KIWI.md`, `docs/` 생성
- `backend/app/security.py`: 프로젝트 루트 밖 접근 차단

### 문서 인덱스

- `README.md`: 설치, 실행, 운영 흐름
- `docs/architecture.md`: 전체 아키텍처
- `docs/runtime-policy.md`: CLI 실행 및 보안 정책
- `docs/ultrawork-agents/`: Qwen runtime에 설치되는 ultrawork subagent 시스템 프롬프트 원본
- `docs/ultrawork-runtime-policy.md`: Qwen runtime ultrawork extension `QWEN.md`에 주입되는 정책 supplement
- `docs/offline-bundle.md`: Windows 11 폐쇄망 반입 번들 생성/설치 절차
- `docs/samsunglife-dcp-overview.md`: 삼성생명 DCP 홈페이지 프론트/백엔드 큰그림과 ultrawork 프롬프트 산출물 규칙

### 실행 명령

- `.\scripts\dev.ps1 -Install`: Windows 의존성 설치
- `.\scripts\dev.ps1`: 백엔드와 웹 동시 실행
- `npm run typecheck`: Next 타입 검증
- `python -m compileall backend`: Python 문법 검증

### 운영 원칙

- 브라우저가 직접 로컬 파일을 수정하지 않는다.
- Python 런타임만 프로젝트 루트 경계 안에서 파일/CLI 작업을 수행한다.
- 주 사용자 루프는 LangGraph 채팅이 아니라 `qwencode` Ultrawork Console이다.
- LangGraph는 `qwencode` 실행 전 표준 프롬프트를 만드는 우측 Prompt Builder 워크플로에 사용한다.
- Prompt Builder는 먼저 티셔츠 사이즈를 산정하고, xsmall은 Kiwi 단독, small/medium/large/xlarge는 규모별 ultrawork 모드로 분기하는 프롬프트를 만든다.
- dcp-front 작업은 `dcp-front-developer`, dcp-services 및 하위 모듈 작업은 `dcp-backend-developer`, 그 외 구현은 `coder-35`를 사용한다.
- ultrawork 콘솔은 항상 `--approval-mode yolo` 인자와 함께 시작한다. 기존 SQLite 설정에 `dangerous_mode=false`가 남아 있어도 effective runtime 값은 true다.
- 실행 흐름은 어제 성공한 `resolve_project_qwen_command() -> _command_to_exec(str(project_command))` 방식을 유지한다.
- UI/터미널 개선 중 PowerShell 래핑이나 PATH 압축 같은 실행 방식 변경을 섞지 않는다.
- xterm fit 결과는 콘솔 시작 요청 전에 `cols<=500`, `rows<=160`으로 제한한다.
- 중앙 터미널 아래 별도 입력창과 숏컷 버튼을 두지 않는다. xterm stdin과 Prompt Builder의 콘솔 전송을 사용한다.
- 상단 알림바로 레이아웃 높이를 빼앗지 않고 fixed layer popup으로 표시한다.
- 우측 패널은 열고 닫을 수 있어야 하며, 닫힌 상태에서는 터미널이 확장된다.
- xterm 외부 컨테이너는 overflow hidden으로 유지해 이중 스크롤바가 겹치지 않게 한다.
- 서브에이전트 가시성은 `xterm.js`로 렌더링한 메인 PTY 출력과 `portable-runtime/team-events.jsonl` 스트림을 합쳐 제공한다.
<!-- KIWI:MAP:END -->
