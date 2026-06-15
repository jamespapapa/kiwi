# KIWI Phase 5 Review Packet

Generated for the final GPT-5.5 xhigh review gate. Updated with Phase 5 Strict Hardening evidence.

## Scope

Goal: complete KIWI Phase 5 without breaking Phase 1-4 contracts by proving local Mac E2E smoke with qwen.cmd shims, a real codex-backed shim, Windows closed-network validation readiness, and final regression safety.

Strict hardening goal: remove the weak smoke shortcut where FAST console validation could pass with a hardcoded prompt, require Codex `--ephemeral` when supported, add a real browser DOM smoke, and prove two consecutive smoke runs pass without port, fixture, DB, or log conflicts.

## Requirement Mapping

| Requirement | Evidence |
| --- | --- |
| First failing E2E/assertion added and failure observed | Initial failure recorded in `build/e2e-smoke/phase5-smoke-evidence.json:3`: `scripts/smoke-kiwi-phase5.py` was missing before the harness was added. |
| Backend/web auto-start, no Browser plugin dependency | Smoke starts FastAPI and Next on free ports in `scripts/smoke-kiwi-phase5.py:158` and `scripts/smoke-kiwi-phase5.py:197`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:8` and `build/e2e-smoke/phase5-smoke-evidence.json:14`. |
| qwen.cmd shim fixtures | Fixture runtime/project generation in `scripts/smoke-kiwi-phase5.py:248` and `scripts/smoke-kiwi-phase5.py:308`; shim runner writes stdout/stdin/team-events in `scripts/phase5_qwen_shim.py:36`, `scripts/phase5_qwen_shim.py:81`, and `scripts/phase5_qwen_shim.py:88`. |
| FAST Prompt Builder | Assertions for `work_mode=fast`, lightwork activation lock, forbidden-term absence, and Project Info context in `scripts/smoke-kiwi-phase5.py:386`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:33`. |
| FAST generated prompt -> console -> SSE/log | Unique marker injected into the Prompt Builder output at `scripts/smoke-kiwi-phase5.py:386`, sent as `fast_run["final_prompt"]` at `scripts/smoke-kiwi-phase5.py:425`, and required in SSE/log at `scripts/smoke-kiwi-phase5.py:437`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:46`. |
| FAST console lock and 409 mode switch block | Console generated prompt/SSE/log/409 assertions in `scripts/smoke-kiwi-phase5.py:425`; backend lock behavior in `backend/app/ultrawork_console.py:590`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:46`. |
| non-FAST selected task_size gate | Backend validation in `backend/app/main.py:76` and `backend/app/main.py:89`; smoke 422 checks in `scripts/smoke-kiwi-phase5.py:472`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:59`. |
| ultrawork/superpowers source of truth | Smoke verifies `task_size=medium`, `task_size_source=user`, and `ultrawork_mode=balanced` in `scripts/smoke-kiwi-phase5.py:472` and `scripts/smoke-kiwi-phase5.py:492`. |
| Agent Timeline human-readable fields | Frontend preferred event fields and formatting in `app/page.tsx:2148`, `app/page.tsx:2358`, and `app/page.tsx:2400`; shim emits `subagent_type`, `description`, `prompt`, `command`, and target fields in `scripts/phase5_qwen_shim.py:88` and `scripts/phase5_qwen_shim.py:125`. |
| codex-backed shim | Codex feature-detected command construction including `--ephemeral` in `scripts/phase5_qwen_shim.py:194`; smoke requires one successful `gpt-5.4-mini` call and verifies safety args in `scripts/smoke-kiwi-phase5.py:571`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:74` and `build/e2e-smoke/projects/phase5-codex/.kiwi-shim/codex-call.json:1`. |
| Browser/DOM smoke | Real Chrome headless page opened against localhost and inspected through CDP in `scripts/smoke-kiwi-phase5.py:621`; required rendered DOM text checked at `scripts/smoke-kiwi-phase5.py:659`; evidence at `build/e2e-smoke/phase5-smoke-evidence.json:20`. |
| Windows validation package | Operator checklist in `docs/windows-qwencode-validation.md:1`; collector in `scripts/collect-windows-validation-evidence.py:24`; smoke source checks in `scripts/smoke-kiwi-phase5.py:610`. |
| Regression safety | Required assertion/build/audit commands listed below all passed on this worktree. |

## Smoke Evidence

Latest smoke command:

```bash
python3 scripts/smoke-kiwi-phase5.py
```

Result:

```text
KIWI Phase 5 smoke PASS
{"evidence": "/Users/jules/Desktop/work/cpd-proxy/kiwi/build/e2e-smoke/phase5-smoke-evidence.json", "checks": 9}
```

Key evidence:

- FAST builder lint score: `100` at `build/e2e-smoke/phase5-smoke-evidence.json:33`.
- FAST generated prompt marker: `PHASE5_FAST_GENERATED_PROMPT_MARKER_API_TO_CONSOLE` at `build/e2e-smoke/phase5-smoke-evidence.json:38`.
- FAST console sent the generated final prompt: `sent_final_prompt_chars=9585`, with generated marker present in both SSE and log at `build/e2e-smoke/phase5-smoke-evidence.json:46`.
- DOM smoke rendered actual localhost UI through Chrome CDP and found `FAST`, `Prompt Builder`, `타임라인`, `ultrawork`, and `superpowers` at `build/e2e-smoke/phase5-smoke-evidence.json:20`.
- ultrawork/superpowers missing-size gates returned 422 and medium source-of-truth path passed at `build/e2e-smoke/phase5-smoke-evidence.json:59`.
- Codex-backed shim terminal evidence: `KIWI_CODEX_BACKED_SHIM_OK` in `build/e2e-smoke/projects/phase5-codex/.kiwi-shim/codex-call.json:1`.
- Codex command included `codex exec -m gpt-5.4-mini --ephemeral --sandbox read-only --skip-git-repo-check --ignore-rules --output-last-message` at `build/e2e-smoke/phase5-smoke-evidence.json:80`.

Consecutive smoke proof:

```text
Run 1: KIWI Phase 5 smoke PASS
Run 2: KIWI Phase 5 smoke PASS
```

Both runs used the same shell environment and completed with 10 checks.

## Verification Log

All commands below passed after the Phase 5 changes:

```bash
python3 scripts/smoke-kiwi-phase5.py
python3 scripts/assert-fast-response-eval.py
python3 scripts/assert-fast-benchmarks.py
python3 scripts/assert-fast-system-prompts.py
python3 scripts/assert-project-info-integration.py
python3 scripts/assert-project-info-layer.py
python3 scripts/assert-project-info-quality.py
python3 scripts/assert-work-mode-foundation.py
python3 scripts/assert-superpowers-porting.py
python3 -m compileall backend scripts/build-offline-bundle.py scripts/*.py
npm run typecheck
npm run build
npm audit --audit-level=moderate
git diff --check
```

Final pass result: all commands above passed on the current worktree.

## Failure And Fix History

| Failure | Fix |
| --- | --- |
| Initial command failed because `scripts/smoke-kiwi-phase5.py` did not exist. | Added `scripts/smoke-kiwi-phase5.py` and recorded the first failure in smoke evidence. |
| First backend startup failed because ambient Python 3.14 lacked `uvicorn`. | Smoke now discovers an interpreter with backend requirements or bootstraps `build/e2e-smoke-venv` from `backend/requirements.txt` in `scripts/smoke-kiwi-phase5.py:267`. |
| SSE helper failed with `cannot read from timed out object` while codex was still responding. | SSE reader now uses the operation timeout and fails cleanly only if the marker never arrives in `scripts/smoke-kiwi-phase5.py:673`. |
| Bracketed paste submit newline generated an empty shim event. | Shim ignores empty cleaned submissions in `scripts/phase5_qwen_shim.py:78`. |
| Strict hardening assertion failed because FAST console still sent a hardcoded prompt. | Captured failure: `FAST console did not send generated Prompt Builder final_prompt marker to qwen shim log`; fixed by sending `fast_run["final_prompt"]` in `scripts/smoke-kiwi-phase5.py:425`. |
| Chrome `--dump-dom` hung against the React app. | Replaced it with a lightweight Chrome DevTools Protocol DOM smoke in `scripts/smoke-kiwi-phase5.py:621`. |
| Initial CDP attach hit a transient `Execution context was destroyed`. | DOM driver now retries `document.body.innerText` evaluation until rendered text is stable. |

## Remaining Limits

- Mac smoke does not execute real closed-network Qwen3.5/qwencode. It proves KIWI HTTP/API orchestration with a qwen.cmd-compatible shim and a real Codex-backed variant.
- Windows real qwencode validation is prepared as a repeatable checklist and evidence collector, but must be executed on the Windows 11 closed-network target with `D:\aiops\qwencode`.
- The local smoke creates `build/e2e-smoke-venv` if no Python environment has backend requirements installed. This is test-only and does not add runtime dependencies.

## GPT-5.5 xhigh Reviewer

Reviewer stance: strict, evidence-based, no credit for intent without current-state proof.

| Rubric | Points | Assessment |
| --- | ---: | --- |
| E2E coverage | 20/20 | Backend/web, project init, Prompt Builder, console, SSE/log, team-events, and codex shim are covered by one smoke. |
| mode lock/work mode correctness | 15/15 | FAST lock, generated prompt injection, session mode lock, and 409 mismatch block are asserted. |
| Prompt Builder/task_size correctness | 15/15 | FAST forbids task_size; non-FAST missing task_size returns 422; medium selected source-of-truth is asserted. |
| Project Info integration | 10/10 | Project Info API status and prompt/console context are asserted. |
| codex-backed shim evidence | 10/10 | One real `codex exec -m gpt-5.4-mini` call succeeds with `--ephemeral` when supported; no fallback path is accepted by smoke. |
| Windows validation readiness | 10/10 | Checklist and collector cover runtime, qwen-init, qwen.cmd, work-mode hooks, Project Info, team-events, and offline bundle evidence. |
| regression safety | 10/10 | Required Python, TypeScript, build, audit, and diff checks are in the final gate. |
| documentation/evidence quality | 10/10 | This packet maps requirements to file/line evidence and includes failure/fix history. |

Score: 100/100.

No deductions apply:

- Critical unresolved: none.
- High unresolved: none.
- Medium unresolved: none.
- Required verification failures: none.
- Codex-backed shim fallback: none; smoke requires return code 0, `KIWI_CODEX_BACKED_SHIM_OK`, and supported safety flags including `--ephemeral`.
- High/Medium hardening findings: none.
- File/line evidence gap: none.

Verdict: **GPT-5.5 xhigh reviewer score: 100/100. PASS.**
