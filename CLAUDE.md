# Kiwi — OpenCode Plugin for Qwen Tool Call Stabilization

## Project Overview

Kiwi는 폐쇄망 환경에서 Qwen(qwen3-235b-a22b) 모델의 OpenCode 사용을 안정화하는 플러그인이다.

**핵심 문제 3가지:**
1. Tool Call 실패 — Qwen이 도구를 텍스트로 출력하거나 인자 포맷을 깨뜨림
2. Context Window 소진 — tool output이 컨텍스트를 잡아먹어 잦은 Compaction 발생
3. Compaction 후 도구 사용법 유실 — 요약 후 정확도 급락

## Architecture

```
kiwi/
├── src/
│   ├── index.ts                         ← 플러그인 엔트리 (모든 훅 등록)
│   ├── hooks/
│   │   ├── tool-output-guard.ts         ← tool output 크기 제한 + 잘라내기
│   │   └── post-compaction-reinject.ts  ← Compaction 후 도구 사용법 재주입
│   └── prompt/
│       └── tool-guide.ts               ← Qwen 전용 도구 사용 가이드
├── package.json
├── tsconfig.json
├── .ref/                                ← 레퍼런스 리포 (gitignored)
│   ├── opencode/                        ← OpenCode 소스코드
│   └── oh-my-opencode/                  ← OMO 소스코드
└── dist/                                ← 빌드 출력 (gitignored)
```

## Tech Stack

- **Language**: TypeScript (ESM)
- **Build**: `bun build` → `dist/index.js` 단일 파일 ESM 번들
- **SDK**: `@opencode-ai/plugin` (external, OpenCode 런타임 제공)
- **Schema**: Zod (via `tool.schema`)

## Build & Deploy

```bash
# 인터넷 PC에서 빌드
bun install
bun build src/index.ts --outdir dist --target node --format esm \
  --external @opencode-ai/plugin --external @opencode-ai/sdk

# 폐쇄망에서 배포
cp dist/index.js <project>/.opencode/plugins/kiwi-agent.js
# opencode 재시작 → 플러그인 로딩 확인
```

## OpenCode Plugin API (핵심 훅)

플러그인은 async 함수로, `PluginInput`을 받아 `Hooks` 객체를 반환한다.

### 사용하는 훅

| 훅 | 용도 | 위치 |
|----|------|------|
| `experimental.chat.system.transform` | 시스템 프롬프트에 도구 가이드 주입 | `prompt/tool-guide.ts` |
| `tool.execute.after` | tool output 크기 제한 | `hooks/tool-output-guard.ts` |
| `experimental.session.compacting` | Compaction 후 도구 가이드 재주입 | `hooks/post-compaction-reinject.ts` |

### 훅 시그니처 요약

```typescript
// 시스템 프롬프트 수정
"experimental.chat.system.transform": async (
  input: { sessionID?: string; model: Model },
  output: { system: string[] }  // 배열에 push로 추가
) => Promise<void>

// 도구 실행 후 output 수정
"tool.execute.after": async (
  input: { tool: string; sessionID: string; callID: string },
  output: { title: string; output: string; metadata: any }
) => Promise<void>

// Compaction 시 컨텍스트 보존
"experimental.session.compacting": async (
  input: { sessionID: string },
  output: { context: string[]; prompt?: string }
) => Promise<void>
```

## Reference Projects

### OpenCode (`.ref/opencode/`)
- 플러그인 SDK: `packages/plugin/src/index.ts`
- 도구 정의: `packages/opencode/src/tool/`
- Compaction: `packages/opencode/src/session/compaction.ts`
- 플러그인 로딩: `packages/opencode/src/plugin/index.ts`

### Oh My OpenCode (`.ref/oh-my-opencode/`)
- 시시포스 에이전트: `src/agents/sisyphus.ts` (530줄, 도구 규칙 섹션 참조)
- 동적 프롬프트: `src/agents/dynamic-agent-prompt-builder.ts`
- tool output 절삭: `src/hooks/tool-output-truncator.ts` (50K 토큰 캡)
- 동적 절삭: `src/shared/dynamic-truncator.ts` (context-aware)
- Compaction 주입: `src/hooks/compaction-context-injector/`
- 선제 Compaction: `src/hooks/preemptive-compaction.ts` (78% 임계값)
- 에러 복구: `src/hooks/anthropic-context-window-limit-recovery/`

## Conventions

- **빌드 도구**: bun (npm/yarn 사용 금지)
- **모듈 포맷**: ESM only
- **외부 의존성**: `@opencode-ai/plugin`, `@opencode-ai/sdk`는 반드시 external
- **에러 처리**: 훅 에러가 도구 실행을 차단하지 않도록 graceful degradation
- **토큰 효율**: 가이드 텍스트는 자세하되 간결하게, 반복 금지
- **방어적 코딩**: output.system, output.context에 Array.isArray 가드 필수
- **Phase 2 참고**: 모델 게이팅(Qwen만 주입) 및 tool.execute.before 가드레일 추가 예정

## Phase 1 Tasks (Issue #1)

1. **프로젝트 스캐폴딩** — TypeScript + bun build → dist/index.js
2. **Qwen 전용 도구 사용 가이드** — system prompt 주입 (핵심)
3. **Tool Output 크기 제한** — tool.execute.after로 output 절삭
4. **Compaction 후 재주입** — 도구 가이드 재주입 (핵심)
