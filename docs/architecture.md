# KIWI Architecture

## 목표

KIWI는 폐쇄망 Windows 11 개발자가 웹 UI에서 `qwencode` Ultrawork 멀티에이전트 세션을 관찰하고 제어하도록 만든 로컬 콘솔 런타임이다.

## 컴포넌트

- Next.js UI
  - 프로젝트 경로 선택과 초기화
  - 장기 실행 `qwencode` 콘솔 시작/중지
  - Kiwi 메인 세션 프롬프트 입력
  - Prompt Builder 우측 패널에서 실행 전 요구사항 인터뷰, LangGraph activity, 최종 ultrawork 프롬프트 표시
  - `xterm.js` 기반 `qwencode` 터미널 출력 스트리밍
  - `team-events.jsonl` 기반 Agent Timeline 표시

- FastAPI Runtime
  - SQLite 설정/세션/메시지 저장
  - OS 폴더 피커 호출
  - 프로젝트 분석과 `KIWI.md`/`docs` 생성
  - OpenAI-compatible `/v1/chat/completions` 호출
  - `pywinpty` 기반 `qwencode` 대화형 프로세스 실행
  - 터미널 출력과 서브에이전트 이벤트 SSE 스트리밍

- LangGraph
  - 현재 메인 사용자 실행 루프는 아니다.
  - 실행 전 Prompt Builder에서 Qwen3.5가 의도 분석, 로컬 검색 계획, 인터뷰 질문, 표준 ultrawork 프롬프트 생성을 수행하는 보조 워크플로로 사용한다.

- Documentation Harness
  - 대형 프로젝트를 수정하기 전에 `docs/knowledge/` 지식 베이스를 만들기 위한 표준 절차와 산출물 계약이다.
  - 공통 하네스는 `docs/project-documentation-harness.md`, 산출물 스펙은 `docs/documentation-output-spec.md`, 실행 프롬프트는 `docs/prompts/project-documentation-ultrawork.md`에 둔다.
  - 프로젝트별 특성은 `docs/documentation-profiles/*.md` 단일 파일로 분리한다. `dcp-front`, `dcp-services`는 초기 목표 프로필이고, 새 프로젝트는 프로필 파일만 교체해 같은 절차를 사용한다.

## 왜 Python 백엔드인가

브라우저 기반 Next 앱은 로컬 절대 경로, OS 폴더 피커, CLI 실행에 제약이 크다. Windows 로컬 앱에 가까운 경험을 제공하려면 로컬 프로세스가 필요하다. Python은 사내 폐쇄망에서도 배포가 쉽고 `git`, `mvn`, `qwencode` 같은 CLI 제어에 적합하다.

## 데이터 흐름

1. 사용자가 프로젝트 폴더를 선택한다.
2. FastAPI가 프로젝트를 분석하고 `KIWI.md` 및 `docs/`를 생성한다.
3. 사용자가 Ultrawork Console을 시작한다.
4. FastAPI가 프로젝트 루트의 `qwen.cmd`를 PTY로 실행한다.
5. 복잡한 작업은 오른쪽 Prompt Builder가 Qwen3.5/LangGraph로 먼저 구체화한다.
6. Prompt Builder는 `KIWI.md`, 삼성생명 DCP 큰그림 문서, 선택된 프로젝트 루트 내부 검색 결과를 합쳐 최종 ultrawork 프롬프트를 만든다.
7. 사용자가 생성된 프롬프트를 실행 중인 `qwencode` stdin으로 전달한다.
8. `qwencode` stdout/stderr는 콘솔 패널에 SSE로 스트리밍된다.
9. `portable-runtime/team-events.jsonl` 신규 이벤트는 Agent Timeline에 SSE로 스트리밍된다.
10. 프로젝트별 `portable-runtime/projects/<project>/chats/<session>.jsonl` 신규 record는 Agent Chat에 SSE로 스트리밍된다.
11. Qwen3.5/Coder 역할 분담과 멀티에이전트 orchestration은 `qwencode` Ultrawork extension 내부의 Kiwi/agent tool 흐름이 담당한다.

## 문서화 데이터 흐름

1. 사용자가 target 프로젝트와 프로젝트 프로필을 선택한다.
2. Kiwi/Qwen은 공통 하네스, 산출물 스펙, 프로젝트 프로필을 읽는다.
3. `qwencode ultrawork`가 target 프로젝트 루트 안에서 read-only 탐색을 수행한다.
4. 문서화 산출물은 target 프로젝트의 `docs/knowledge/` 아래에 생성된다.
5. target 프로젝트의 `KIWI.md`에는 상세 내용을 복사하지 않고 knowledge base 인덱스와 핵심 사용법만 요약한다.
6. 이후 Prompt Builder와 벡터DB ingest는 `docs/knowledge/`의 front matter, keyword, evidence, cross-link를 사용해 관련 문서를 검색한다.

## 가시성 경계

현재 `qwencode` 서브에이전트는 별도 터미널 프로세스가 아니라 내부 `agent` tool 호출이다. 따라서 서브에이전트별 raw stdout을 각각 별도 터미널에 붙일 수는 없다. KIWI는 다음 두 스트림을 합쳐 웹에 보여준다. 메인 터미널 출력은 ANSI escape sequence를 직접 해석하는 `xterm.js`로 렌더링해야 하며, `<pre>`에 raw 출력 문자열을 넣으면 색상/커서 제어 문자가 깨져 보인다.

- 메인 `qwencode` PTY 출력
- Ultrawork hook이 기록하는 `team-events.jsonl`
- Qwen session recorder가 기록하는 프로젝트별 `chats/<session>.jsonl`

서브에이전트의 모든 read-only tool 호출까지 보려면 Qwen runtime hook matcher를 확장해야 한다. 이 모드는 Windows에서 hook 프로세스 수가 늘어 성능 비용이 있으므로 별도 full visibility 옵션으로 다루는 것이 맞다.
