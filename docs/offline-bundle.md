# Offline Bundle

## 생성

인터넷이 가능한 반출 준비 환경에서 실행한다.

```bash
.venv/bin/python scripts/build-offline-bundle.py
```

생성 산출물:

- `build/offline/kiwi-offline-win11-py313.zip`
- `build/offline/kiwi-offline-win11-py313.zip.sha256`
- `build/offline/qwencode-win11-v0.17.1.zip`
- `build/offline/qwencode-win11-v0.17.1.zip.sha256`

## 포함 정책

- Python: Windows x64 Python 3.13(cp313) wheelhouse
- Node/npm: KIWI 설치/실행 시 별도 반입된 `D:\aiops\qwencode\runtimes\node\npm.cmd` 사용
- Qwen Code: `qwencode-win11-v0.17.1.zip`으로 별도 제공한다. `D:\aiops`에 풀면 `D:\aiops\qwencode`가 된다.
- 관리형 개발 런타임: `D:\aiops\qwencode\runtimes\node`, `node10`, `java`, `java8`, `maven3.6.3`, `tomcat9` 아래에 모은다. `java`는 Java 17 JDK, `java8`은 Java 8 JDK, `tomcat9`는 Tomcat 9.0.115이다.
- Python PTY: Windows cp313 `pywinpty` wheel을 별도 포함하고 설치
- Qwen runtime config: 별도 반입 runtime source에 삼성생명 폐쇄망 Orchestrator/Explorer endpoint와 모델명을 고정
- Qwen work mode: 별도 반입 runtime source에 `lightwork`, `ultrawork`, `superpowers` trigger와 mode lock runtime policy를 patch
- Qwen superpowers: 별도 반입 runtime source에 `portable-user/.qwen/skills/*/SKILL.md`, `templates/project/.qwen/skills/*/SKILL.md`, `portable-user/.qwen/extensions/superpowers/skills/*/SKILL.md`, `extensions/superpowers/skills/*/SKILL.md`를 함께 설치
- Next 의존성: `package-lock.json`의 모든 resolved tarball을 npm cache 형식으로 저장

## 폐쇄망 설치

두 압축을 모두 `D:\aiops` 아래에 해제한다.

```cmd
D:
cd \aiops\qwencode
install-path.cmd

cd \aiops\kiwi
install-offline.cmd
start-kiwi.cmd
```

`install-offline.cmd`는 Python 가상환경 생성, wheelhouse 기반 pip 설치, npm 오프라인 설치, Next production build를 수행한다.
단, npm 실행과 KIWI 콘솔 runtime은 `qwencode-win11-v0.17.1.zip`에서 반입된 `D:\aiops\qwencode`를 사용한다.
설치 스크립트는 `D:\aiops\qwencode\run-qwen.cmd`, `qwen-init.cmd`, `runtimes\node\npm.cmd`를 검증하고, 사용자 환경변수 `KIWI_QWENCODE_RUNTIME_DIR=D:\aiops\qwencode`와 사용자 `PATH`를 등록한다. 새 터미널을 열면 어느 프로젝트 경로에서든 `qwen-init.cmd`, `qwen.cmd`, `qwencode.cmd`를 바로 호출할 수 있다.
`start-kiwi.cmd`는 먼저 3000/8787 포트의 기존 KIWI 프로세스를 정리한 뒤 시작한다. 그 다음 `.next\BUILD_ID`가 없거나 `kiwi-source-stamp.txt`가 현재 소스와 맞지 않으면 기존 `.next`를 삭제하고 오프라인 캐시로 `npm run build`를 먼저 완료한 뒤 Backend/Web을 시작한다.
페이지 소스보기에서 `data-kiwi-ui-build="xterm-fit-v4-port-guard"`가 보이면 xterm 높이/port guard 패치가 포함된 UI다. chunk 파일명은 Windows 빌드마다 달라질 수 있으므로 이 marker를 기준으로 확인한다.

설치 후 KIWI를 통하지 않고 터미널에서 바로 사용할 수 있다.

```cmd
cd /d D:\path\to\project
qwen-init.cmd D:\path\to\project
qwen.cmd
```

## qwencode 통합

KIWI 번들은 Qwen runtime을 중복 포함하지 않는다. 정상 폐쇄망 설치 후 표준 runtime은 `D:\aiops\qwencode`다. Windows에서 `D:\aiops\qwencode\run-qwen.cmd`가 있으면 KIWI는 이 standalone runtime을 최우선으로 사용하고, 해당 경로가 없으면 설치와 실행을 중단한다. 번들 루트와 `bin`의 `qwen.cmd`/`qwen-init.cmd` wrapper도 같은 외부 runtime을 사용한다.

`qwencode-win11-v0.17.1.zip`은 다음을 포함한 상태로 생성된다.

- Qwen Code 0.17.1
- 삼성생명 고정 endpoint/model/env
- Qwen3.5-397B vision modality patch
- FAST/lightwork, ultrawork, superpowers mode hook/policy
- FAST system prompts
- ultrawork agents
- superpowers extension skills

Superpowers skill은 Qwen 0.17의 built-in `skill` tool로 호출한다. `kiwi-superpowers`와 `using-superpowers`는 standalone tool 이름이 아니라 `skill` parameter 값이다. 따라서 `tool_search select:kiwi-superpowers` 검색 성공은 검증 기준이 아니다.

프로젝트 초기화 시 Windows에서는 현재 우선 runtime의 `qwen-init.cmd <project-path>`를 실행한다. 이 단계에서 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `.qwen/settings.json`, `.qwen/skills`, `.qwen/agents`, `QWEN.md`가 생성되고, 이후 KIWI의 코딩 실행은 프로젝트 루트의 `qwen.cmd`를 사용한다. `qwen.cmd`가 없거나 내부 `run-qwen.cmd` 경로가 사라졌으면 콘솔 시작은 실패하고 프로젝트 초기화를 다시 요구한다.

이미 생성된 프로젝트 `qwen.cmd`가 현재 우선 runtime과 다른 경로를 가리키거나 존재하지 않는 경로를 가리키면 KIWI는 runtime mismatch로 표시한다. 프로젝트 초기화를 다시 실행하면 기존 하네스를 `.qwen\init-backups\...`로 백업하고 현재 우선 runtime 기준으로 재생성한다. mismatch 상태에서 Ultrawork Console은 조용히 예전 runtime으로 시작하지 않는다.

## Work Mode Bundle Policy

- `FAST/lightwork`: prefix `lightwork`, alias `fast`, `lw`
- `ultrawork`: prefix `ultrawork_<size>`, alias `ulw_<size>`; plain `ultrawork`/`ulw` defaults to `medium`
- `superpowers`: prefix `superpowers_<size>`, alias `spw_<size>`; plain `superpowers`/`spw` defaults to `medium`

세션 최초 activation 이후 mode 변경은 frontend/backend/runtime policy에서 금지된다. Backend는 다른 mode prefix를 `409`로 차단하고, Qwen runtime state는 최초 mode를 보존한다.

`superpowers`는 다음 파일로 설치된다.

```text
D:\aiops\qwencode\portable-user\.qwen\extensions\superpowers\qwen-extension.json
D:\aiops\qwencode\portable-user\.qwen\extensions\superpowers\skills\kiwi-superpowers\SKILL.md
D:\aiops\qwencode\portable-user\.qwen\skills\kiwi-superpowers\SKILL.md
D:\aiops\qwencode\templates\project\.qwen\skills\kiwi-superpowers\SKILL.md
```

고정 라우팅:

- Orchestrator: `https://api.t.drt.samsunglife.kr/llmproxy/v1`, `Qwen3.5-397B`
- Explorer-35: `https://api.t.drt.samsunglife.kr/llmproxy/v1`, `Qwen3.5-397B`
- Context window: `262144`
- Output max tokens: Qwen3.5 `16384`, Explorer `16384`
- Node heap: `NODE_OPTIONS=--max-old-space-size=8192`
- Terminal agent visibility: `QWEN_ULTRAWORK_AGENT_VISIBILITY=0`
