# Offline Bundle

## 생성

인터넷이 가능한 반출 준비 환경에서 실행한다.

```bash
.venv/bin/python scripts/build-offline-bundle.py
```

생성 산출물:

- `build/offline/kiwi-offline-win11-py313.zip`
- `build/offline/kiwi-offline-win11-py313.zip.sha256`

## 포함 정책

- Python: Windows x64 Python 3.13(cp313) wheelhouse
- Node/npm: 상위 `deliverables`의 최신 `qwen-code-offline-*` 런타임에 포함된 Node 사용
- Qwen Code: 상위 `deliverables` 최신 폴더를 `vendor/qwen-runtime`으로 복사
- Python PTY: Windows cp313 `pywinpty` wheel을 별도 포함하고 설치
- Qwen runtime config: 삼성생명 폐쇄망 Orchestrator/Explorer endpoint와 모델명을 고정해 복사
- Next 의존성: `package-lock.json`의 모든 resolved tarball을 npm cache 형식으로 저장

## 폐쇄망 설치

압축 해제 후 Windows 11에서 실행한다.

```cmd
install-offline.cmd
start-kiwi.cmd
```

`install-offline.cmd`는 Python 가상환경 생성, wheelhouse 기반 pip 설치, npm 오프라인 설치, Next production build를 수행한다.

## qwencode 통합

번들 안의 `vendor/qwen-runtime`은 fallback runtime이다. Windows에서 `D:\aiops\qwencode\run-qwen.cmd`가 있으면 KIWI는 이 기존 runtime을 우선 사용하고, `KIWI_QWENCODE_RUNTIME_DIR`도 `D:\aiops\qwencode`로 설정한다. `D:\aiops\qwencode`가 없을 때만 번들 내부 `vendor/qwen-runtime`을 사용한다.

프로젝트 초기화 시 Windows에서는 현재 우선 runtime의 `qwen-init.cmd <project-path>`를 실행한다. 이 단계에서 프로젝트 루트에 `qwen.cmd`, `qwen-init.cmd`, `.qwen/env.cmd`, `QWEN.md`가 생성되고, 이후 KIWI의 코딩 실행은 프로젝트 루트의 `qwen.cmd`를 사용한다. `qwen.cmd`가 없으면 콘솔 시작은 실패한다.

이미 생성된 프로젝트 `qwen.cmd`가 현재 우선 runtime과 다른 경로를 가리키면 KIWI는 runtime mismatch로 표시한다. 프로젝트 초기화를 다시 실행하면 기존 하네스를 `.qwen\init-backups\...`로 백업하고 현재 우선 runtime 기준으로 재생성한다. mismatch 상태에서 Ultrawork Console은 조용히 예전 runtime으로 시작하지 않는다.

고정 라우팅:

- Orchestrator: `https://api.t.drt.samsunglife.kr/llmproxy/v1`, `Qwen3.5-397B`
- Explorer-next: `https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1`, `qwen3-coder-next`
- Context window: `262144`
- Output max tokens: Qwen3.5 `16384`, Explorer `16384`
- Node heap: `NODE_OPTIONS=--max-old-space-size=8192`
- Terminal agent visibility: `QWEN_ULTRAWORK_AGENT_VISIBILITY=0`
