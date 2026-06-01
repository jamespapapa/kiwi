# AGENTS.md

이 파일은 KIWI 저장소를 이어받는 에이전트용 운영 지침이다. 현재 스코프는 저장소 전체다.

## 프로젝트 목적

KIWI는 삼성생명 폐쇄망 Windows 11 로컬 개발 환경에서 사용할 웹 기반 Ultrawork Console이다. 사용자는 Next.js 웹 UI에서 프로젝트 폴더를 선택하고, KIWI가 프로젝트 구조를 분석해 `KIWI.md`와 `docs/`를 초기화한다. 이후 웹에서 장기 실행 `qwencode` 세션을 시작하고, `qwencode` 내부 Kiwi(Qwen3.5) 메인 오케스트레이터에게 직접 프롬프트한다.

핵심 목표는 터미널 기반 vibe coding을 웹 UI에서 더 통제 가능하게 만드는 것이다. KIWI는 메인 `qwencode` 터미널 출력과 Ultrawork `team-events.jsonl`을 함께 스트리밍해서 서브에이전트 작업 흐름을 Agent Timeline으로 보여준다.

## 현재 아키텍처

- `app/`: Next.js 웹 UI
- `app/page.tsx`: `@xterm/xterm`으로 메인 `qwencode` PTY 출력을 렌더링한다. ANSI escape sequence를 `<pre>`에 직접 렌더링하는 구조로 되돌리지 말 것.
- 중앙 터미널 아래 별도 프롬프트 입력창과 숏컷 버튼은 제거했다. 사용자는 xterm에 직접 입력하거나 우측 Prompt Builder의 생성 프롬프트를 콘솔로 전송한다.
- 알림은 상단 레이아웃을 밀어내는 바가 아니라 fixed layer popup으로 표시한다.
- 고정 런타임 설정은 좌측 패널 안에 있다. 상단 전체 폭 설정 패널로 되돌리지 말 것.
- 우측 Prompt Builder/Agent Timeline 패널은 열고 닫을 수 있어야 한다. 닫으면 중앙 터미널이 확장되고, 열면 터미널 폭이 줄어든다.
- xterm 스크롤은 내부 viewport만 사용한다. `.terminal` 외부 overflow를 다시 auto로 만들어 이중 스크롤바가 겹치게 하지 말 것.
- `backend/app/`: FastAPI 로컬 런타임
- `backend/app/ultrawork_console.py`: 장기 실행 `qwencode` 콘솔 세션, stdout/stderr 로그 저장, `team-events.jsonl` tail, SSE 스트리밍
- `backend/app/prompt_builder.py`: Qwen3.5/LangGraph 기반 실행 전 프롬프트 빌더, 로컬 검색, 인터뷰 질문, 최종 ultrawork 지시문 생성
- `backend/app/agent_runtime.py`: 레거시 PM, Architect, Planner, Answer 노드 기반 LangGraph 흐름
- `backend/app/coder_runner.py`: 레거시 비대화형 `qwencode --prompt` 실행, stdout/stderr 로그 저장, SSE 스트리밍, 완료 후 리뷰
- `backend/app/project_analyzer.py`: 프로젝트 구조 분석, `KIWI.md`, `docs/architecture.md`, `docs/decisions/*` 생성
- `backend/app/qwencode_runtime.py`: 프로젝트 `qwen.cmd` 확인, `qwen-init.cmd`용 런타임 탐지, 레거시 runner 명령 해석
- `backend/app/qwen_client.py`: OpenAI-compatible `/v1/chat/completions` 호출
- `data/`: SQLite DB, `data/ultrawork/<session-id>.terminal.log` 콘솔 로그, `data/prompt-builder/<run-id>.jsonl` 프롬프트 빌더 로그, 레거시 `data/runs/<run-id>.log`
- `scripts/build-offline-bundle.py`: 폐쇄망 반입용 Windows 11/Python 3.13 오프라인 ZIP 생성

## Git/원격 배포

현재 로컬 git 루트는 상위 `cpd-proxy`이지만 실제 KIWI 앱은 `kiwi/` prefix 아래에 있다. GitHub 원격 `jamespapapa/kiwi`에는 `kiwi/` 내용이 저장소 루트로 올라가야 한다.

- 상위 `deliverables/`는 런타임/번들 생성 입력으로만 사용한다.
- 원격 `jamespapapa/kiwi`에 push할 때는 상위 루트를 그대로 push하지 말고 `git subtree split --prefix=kiwi` 결과를 원격 `main`에 force push한다.
- 이렇게 해야 원격 루트가 `app/`, `backend/`, `docs/`, `package.json` 구조를 유지한다.

## 고정 런타임 설정

모델 라우팅은 코드와 번들에 고정되어 있다. UI에서 API base, model, API key를 다시 받는 구조로 되돌리지 말 것.

- Orchestrator API: `https://api.t.drt.samsunglife.kr/llmproxy/v1`
- Orchestrator model: `Qwen3.5-397B`
- Coder API: `https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1`
- Coder model: `qwen3-coder-next`
- API key: 실제 key는 불필요하다. OpenAI-compatible 클라이언트 형식상 더미 Bearer를 사용한다.
- Main dummy key: `sk-local-qwen35`
- Coder dummy key: `sk-local-coder`
- Context window: `262144`
- Output max tokens: Qwen3.5 `16384`, Coder `16384`

이 값은 다음 위치들이 일관되게 맞아야 한다.

- `backend/app/config.py`
- `backend/app/models.py`
- `app/page.tsx`
- `scripts/build-offline-bundle.py`
- 번들 내부 `vendor/qwen-runtime/config/env.cmd`
- 번들 내부 `vendor/qwen-runtime/templates/project/.qwen/env.cmd`
- `README.md`, `docs/offline-bundle.md`, `docs/runtime-policy.md`

## qwencode 통합 규칙

프로젝트 초기화 시 Windows에서는 `qwen-init.cmd <project-path>`를 실행해 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `.qwen/settings.json`, `QWEN.md`를 만든다. 이후 Ultrawork Console은 프로젝트 루트의 `qwen.cmd`만 실행한다.

메인 사용자 루프에서는 `qwencode`를 비대화형 `--prompt`로 호출하지 않는다. `backend/app/ultrawork_console.py`가 프로젝트 루트의 `qwen.cmd`만 장기 실행 대화형 콘솔로 띄운다. 프로젝트 루트에 `qwen.cmd`가 없으면 콘솔 시작을 중단하고 프로젝트 초기화를 요구한다. Windows에서는 `pywinpty`를 사용하고, fallback으로 pipe subprocess를 사용한다.

레거시 coder run 경로만 `--model qwen3-coder-next --prompt <prompt> --approval-mode yolo` 형식으로 호출한다.

## 보안과 작업 경계

- 선택된 프로젝트 루트가 작업 경계다.
- 프로젝트 루트 밖 파일 접근은 백엔드에서 차단한다.
- `dangerous_mode=false`: 콘솔을 기본 approval 정책으로 시작한다.
- `dangerous_mode=true`: 기존 실행 흐름처럼 새 콘솔을 `--approval-mode yolo` 인자와 함께 시작한다.
- 외부 네트워크 의존을 추가하지 말 것. 반입 번들은 폐쇄망에서 설치/실행 가능해야 한다.
- 실행 로그는 `data/ultrawork/`에 저장하고, 웹 UI에서는 SSE로 tail 형태로 보여준다.
- 서브에이전트 이벤트는 Qwen runtime의 `portable-runtime/team-events.jsonl`을 tail 한다.
- Qwen 서브에이전트는 별도 콘솔 프로세스가 아니라 내부 `agent` tool 호출이다. raw stdout을 서브에이전트별 터미널에 직접 붙일 수 있다고 가정하지 말 것.
- 오른쪽 Prompt Builder는 `qwencode`에 큰 작업을 시키기 전 Qwen3.5/LangGraph로 표준 ultrawork 프롬프트를 만든다. 이 워크플로는 `qwen.cmd`를 실행하지 않고 프롬프트만 생성한다.
- 삼성생명 DCP 작업 지시를 만들 때는 `docs/samsunglife-dcp-overview.md`를 큰그림 컨텍스트로 사용하되, 실제 구현 판단은 선택된 프로젝트 루트 안의 현재 파일 검색 결과를 우선한다.
- 현재 폐쇄망 Qwen3.5 배포는 vision 기능이 꺼져 있다. Playwright screenshot을 캡처해 파일 경로를 남기는 구조는 추후 시각 검증용으로 유지할 수 있지만, 지금은 Qwen3.5가 이미지를 직접 판독한다고 가정하지 말고 DOM/CSS 수치, 텍스트, screenshot 경로, 사람 확인 항목으로 보고한다.
- 기존 사용자가 만든 프로젝트 파일이나 로컬 변경을 임의로 되돌리지 말 것.

## 오프라인 번들

목표 환경은 Windows 11 + Python 3.13.5다. Python wheel도 번들에 포함해야 한다.

생성 명령:

```bash
.venv/bin/python scripts/build-offline-bundle.py
```

산출물:

- `build/offline/kiwi-offline-win11-py313.zip`
- `build/offline/kiwi-offline-win11-py313.zip.sha256`

현재 번들러는 다음을 수행한다.

- 소스 파일 복사
- 상위 `deliverables` 최신 Qwen Code runtime을 `vendor/qwen-runtime`으로 복사
- Qwen runtime `env.cmd`와 프로젝트 `.qwen/env.cmd` 템플릿을 삼성생명 고정 라우팅으로 덮어쓰기
- Windows x64 Python 3.13용 wheelhouse 다운로드
- Windows x64 Python 3.13용 `pywinpty` wheel 별도 다운로드 및 설치
- `package-lock.json` 기반 npm offline cache 생성
- `install-offline.cmd`, `start-kiwi.cmd`, `run-backend.cmd`, `run-web.cmd`, `verify-offline.cmd` 생성
- ZIP과 SHA256 생성

`run-web.cmd`는 `.next/BUILD_ID`가 없으면 시작 전에 오프라인 캐시로 `npm run build`를 수행한다.

## 현재까지 해결한 이슈

- `colorama; platform_system == 'Windows'` 누락으로 오프라인 pip 설치가 실패했다.
  - `backend/requirements.txt`에 `colorama>=0.4.6`을 명시 추가했다.
- `next start`가 `.next` production build 누락으로 실패했다.
  - `run-web.cmd`가 `.next/BUILD_ID` 누락 시 `npm run build`를 자동 수행하도록 했다.
- 초기 설정값이 UI/SQLite에 의존해 잘못된 endpoint/model이 남을 수 있었다.
  - 라우팅 값을 서버 기본값으로 고정하고, SQLite의 locked setting은 무시하도록 했다.
- LLM 호출 실패가 UI에 `502 Bad Gateway`만 보였다.
  - `/api/diagnostics/llm`와 UI의 `메인 테스트`, `코더 테스트` 버튼을 추가했다.
  - 실패 시 endpoint, model, status, 응답 body 일부를 표시한다.
- Python `httpx`가 내부 HTTPS 인증서와 프록시 환경변수 영향을 받을 수 있었다.
  - `verify=False`, `trust_env=False`로 맞췄다.
- coder endpoint에 `vllmm` 오타가 있었다.
  - `vllm-qwen3-coder-next-svc-route-vllm-direct...`로 수정했다.
- Orchestrator 모델명이 잘못되어 있었다.
  - `Qwen3.5-397B`로 수정했다.
- 메인 UI가 LangGraph 채팅 중심이라 내부 `qwencode` 서브에이전트 흐름을 볼 수 없었다.
  - Ultrawork Console로 전환해 `qwencode` PTY 출력과 `team-events.jsonl` Agent Timeline을 스트리밍한다.
- 여러 서브에이전트 실행 시 Node memory warning 가능성이 있었다.
  - `NODE_OPTIONS=--max-old-space-size=8192`를 `qwencode` 실행 환경과 번들 env에 주입한다.
- 실행 흐름은 어제 성공한 방식으로 유지한다.
  - 프로젝트 `qwen.cmd`를 `resolve_project_qwen_command()`가 `_command_to_exec(str(project_command))`로 해석한다.
  - UI/터미널 개선 중 PowerShell 래핑이나 PATH 압축 같은 실행 방식 변경을 섞지 않는다.
- xterm fit 결과가 240컬럼을 넘으면 `/api/ultrawork/sessions` 요청 검증에서 실패했다.
  - 터미널 시작 요청 제한을 `cols<=500`, `rows<=160`으로 확장하고 프론트에서 같은 범위로 clamp한다.
- 터미널 ANSI escape sequence가 웹 `<pre>`에서 깨져 보였다.
  - `@xterm/xterm`을 추가하고 웹 터미널 렌더러로 교체했다.
- Qwen runtime에 출력 `max_tokens=262144`가 들어가서 첫 호출부터 context window 초과가 발생했다.
  - Context window는 `262144`로 유지하고 출력 max tokens는 Qwen3.5 `16384`, Coder `16384`로 낮췄다.
- `qwencode`에 바로 긴 요구사항을 던지기 전에 약한 모델용 표준 지시문을 만들 필요가 생겼다.
  - `/api/prompt-builder/runs`와 우측 Prompt Builder UI를 추가했다.
  - LangGraph activity, 사용자 인터뷰 질문, 로컬 파일 검색 결과, 최종 ultrawork 프롬프트를 웹에서 볼 수 있다.
  - 생성된 프롬프트는 사용자가 버튼을 눌러야 중앙 입력창으로 옮기거나 실행 중인 콘솔로 전송된다.

최신으로 생성한 번들 SHA256:

```text
a4b908f45c5a18e8238c5f8a2ec785bf7006e02ae128e72b986906c56974f9e1  kiwi-offline-win11-py313.zip
```

## 진단 절차

실행 후 문제가 있으면 먼저 웹 UI의 `메인 테스트`, `코더 테스트`를 누른다.

- `메인 테스트` 실패: Qwen3.5 endpoint/model/auth/proxy/TLS 문제다.
- `코더 테스트` 실패: Coder endpoint/model/auth/proxy/TLS 문제다.
- 초기화에서 `스택 자동 감지 안 됨`: LLM 호출 문제가 아니라 분석 대상 프로젝트에서 알려진 key file을 찾지 못한 상태다.
- `qwen 하네스 실패`: `qwen-init.cmd`, Windows 실행 환경, 프로젝트 폴더 권한, `D:\aiops\qwencode` 또는 번들 runtime 경로를 확인한다.

로그 확인 위치:

- 백엔드 콘솔: FastAPI/uvicorn 로그와 Qwen 호출 실패 상세
- 웹 중앙 `qwencode Terminal`: 실행 중 stdout/stderr
- 웹 오른쪽 슬라이드 패널 `Prompt Builder`: LangGraph activity, 질문, 생성된 ultrawork 프롬프트
- 웹 오른쪽 슬라이드 패널 `Agent Timeline`: `portable-runtime/team-events.jsonl` 신규 이벤트. `PreToolUse` raw label만 보여주지 말고 subagent type, description, prompt, command, target을 사람이 읽을 수 있게 요약한다.
- `data/ultrawork/<session-id>.terminal.log`: 콘솔 로그 파일
- `data/prompt-builder/<run-id>.jsonl`: Prompt Builder 이벤트 로그 파일
- `data/runs/<run-id>.log`: 레거시 비대화형 실행 로그 파일
- SQLite: `data/kiwi.sqlite3`

## 개발 검증 명령

문서만 수정한 경우 빌드는 필수는 아니지만, 코드나 번들러를 건드렸다면 아래를 확인한다.

```bash
python3 -m compileall backend scripts/build-offline-bundle.py
npm run typecheck
npm run build
npm audit --audit-level=moderate
```

오프라인 번들을 다시 만든 뒤에는 ZIP 내부 설정도 확인한다.

```bash
unzip -p build/offline/kiwi-offline-win11-py313.zip kiwi-offline-win11-py313/vendor/qwen-runtime/config/env.cmd
unzip -p build/offline/kiwi-offline-win11-py313.zip kiwi-offline-win11-py313/bundle-manifest.json
npm cache verify --cache build/offline/kiwi-offline-win11-py313/vendor/npm-cache
```

## 변경 원칙

- 기존 구조와 문서 흐름을 우선한다.
- 폐쇄망 반입 가능성을 깨는 새 의존성을 추가하지 않는다.
- 새 Python 의존성을 추가하면 Windows cp313 wheelhouse 생성 가능성을 반드시 확인한다.
- 새 npm 의존성을 추가하면 `package-lock.json`과 npm offline cache 번들링을 반드시 확인한다.
- 모델/endpoint 변경은 사용자 확인 없이 임의로 하지 않는다.
- 진단 가능성을 낮추는 변경은 피한다. 오류는 UI 또는 백엔드 로그에서 endpoint/model/status/body 일부가 보이게 유지한다.
