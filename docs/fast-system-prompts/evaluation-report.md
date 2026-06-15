# FAST System Prompt Evaluation Report

## GPT-5.5 xhigh evaluator evaluation packet

This file is the evaluation packet for a hypothetical GPT-5.5 xhigh evaluator. No external model call was performed. The packet gives benchmark prompts, expected behavior, failure patterns, accepted improvements, and self-review findings so a stronger evaluator can audit the FAST prompt source.

Packet index: objective rubric, benchmark tasks, benchmark prompts, expected behavior, failure patterns, weakness, accepted improvements, self-review findings.

## Objective Rubric

- Project Info Layer is mandatory starting context and must be verified against current files.
- Profile-specific prompt content must cover the expected dcp-front, dcp-services, or generic surfaces.
- Runtime injection summary and human-review final prompt must be visibly separated.
- FAST prompt bodies must avoid forbidden sizing/delegation/mode-switch language.
- Output behavior must be direct: restate, plan, inspect, minimal diff, focused verification, concise report.

## Benchmark Prompts

- dcp-front: "보험금 청구 인트로 화면의 안내 문구 한 줄을 바꾸고 확인해줘."
- dcp-front: "버튼 hover 효과가 주변 레이아웃을 밀지 않게 고쳐줘."
- dcp-front: "선택값이 Vuex DataStore와 Axios payload에 반영되는지 확인하고 누락만 고쳐줘."
- dcp-services: "특정 조회 조건이 누락되는 MyBatis 동적 SQL 분기를 좁게 수정해줘."
- dcp-services: "EAI 호출 파라미터 한 필드의 전달 경로를 확인하고 필요한 최소 수정만 해줘."
- generic: "README의 실행 명령이 현재 package scripts와 맞는지 확인하고 고쳐줘."

## Expected Behavior

- Read Project Info summaries first when present.
- Verify Project Info claims against current files before editing.
- Use targeted repository search and read only the relevant files.
- Produce a short Korean plan.
- Apply a minimal diff and avoid unrelated formatting.
- Run focused verification or report a concrete fallback check.
- Stop and ask when ownership, business meaning, data contract, CSS containment, runtime profile, or verification scope is unclear.

## Failure Patterns

- Treating Project Info as authoritative without current-file verification.
- Skipping profile-specific surfaces such as DataStore, Axios, MyBatis, EAI, or resources-env.
- Creating broad refactors for a narrow request.
- Reporting success without verification evidence.
- Continuing when the state carrier, payload shape, or runtime profile is ambiguous.
- Leaking sizing or delegation vocabulary into FAST prompt bodies.

## Weakness

- The runtime patch can only inject a compact summary because the Qwen runtime script is a JavaScript patch surface, not a Python loader.
- Project profile detection still depends on path and repository markers when Project Info has not been generated.
- Visual checks remain DOM/CSS/text and screenshot-path oriented because the deployed model is not assumed to read images.

## Accepted Improvements

- Created standalone profile prompt files with runtime summary and human-review final prompt sections.
- Added profile-aware FAST prompt loading for Prompt Builder and Console activation.
- Added Qwen runtime and offline bundle installation paths for FAST prompt source files.
- Added assertions for required files, profile keywords, leakage control, runtime references, and evaluator packet contents.
- Added self-review gates so open Critical, High, or Medium findings block completion.
- Phase 4D response-eval hardening accepted the first-response failure pattern: profile prompts now explicitly require the first visible response to start with `계획:` and name Project Info, current-file verification, minimal scope, a focused verification command or fallback check, and stop conditions.
- Phase 4D response-eval hardening accepted the user-facing wording failure pattern: profile prompts now require direct-work wording and suppress routing, scoring, and handoff mechanics in FAST responses.
- Phase 4D response-eval runner results now expose `source_counts`, `fallback_events`, and `codex_available` so codex success, codex fallback, and intentionally weak fixtures can be audited separately.
- Phase 4D response-eval output uses stable `generated_at` behavior to avoid timestamp-only dirty diffs on equivalent reruns.
- Phase 4D follow-up response-eval hardening added `KIWI_FAST_EVAL_CODEX_MODEL` so codex mode can pin a model such as `gpt-5.4-mini` while leaving the default unset for normal mock/dry-run use.
- Phase 4D follow-up codex execution now records and asserts feature-detected safety args: `--ephemeral` and `--sandbox read-only` stay in the command, while `--ask-for-approval never` is included only when `codex exec --help` advertises it.
- Phase 4D follow-up codex metadata now records unsupported safety args separately, so unsupported `--ask-for-approval` does not create fallback events or hide real task execution results.
- Phase 4D follow-up codex runs now preserve separate `response-eval-results.codex.json` and `.md` audit artifacts with source counts, fallback events, codex availability, and codex model metadata.
- Phase 4D follow-up real-codex artifact assertions now fail all-fallback codex artifacts with `real codex artifact must include at least one codex response`.
- Phase 4D follow-up local Codex CLI 0.137.0 verification with `KIWI_FAST_EVAL_CODEX_MODEL=gpt-5.4-mini` produced real codex samples rather than mock fallback.
- Phase 4E response-eval closure now requires every codex-originated FAIL to be tied to an accepted prompt improvement, accepted rubric improvement, accepted benchmark adjustment, or not-accepted reason.
- Phase 4E accepted rubric improvement: Korean equivalents for explicit change boundaries, bounded verification, static fallback checks, and concrete stop conditions are scored without requiring the literal English phrase `focused verification`.
- Phase 4F hardening accepted the latest lightwork regression: FAST planning now requires TodoWrite/todo_write, and FAST responses must not produce a size report or treat delegation denial as a mode conflict.

## Response Eval Loop Closure

- Failure pattern: weak CSS response skipped Project Info/current-file evidence, gave broad styling intent, and lacked focused verification or stop conditions.
  Accepted improvement: added first-visible-response discipline to all profile prompt files.
- Failure pattern: live codex samples often described verification generally but did not visibly start with `계획:` or name a concrete focused verification command/fallback.
  Accepted improvement: tightened the first-response instruction in all profile prompt files and the response-eval sample request.
- Failure pattern: weak EAI response used mode-internal routing/scoring wording in a user-facing FAST answer.
  Accepted improvement: added direct-work wording discipline to all profile prompt files.
- Failure pattern: codex runner failures previously collapsed the run into one ambiguous runner state.
  Accepted improvement: runner metadata now records task-level response sources and fallback events.
- Failure pattern: real codex runs could not prove which model or safety flags were used.
  Accepted improvement: runner metadata and fake-codex assertions now record model, feature-detected safety args, unsupported safety args, and command args without storing the full prompt.
- Failure pattern: real codex runs only occupied the default response-eval result path.
  Accepted improvement: codex-requested runs now preserve a separate `.codex` JSON/MD artifact for audit.
- Failure pattern: Codex CLI 0.137.0 rejected `--ask-for-approval`, causing all codex-eligible tasks to pass through `mock_fallback`.
  Accepted improvement: the runner now detects `codex exec --help`, omits unsupported approval args, records `unsupported_safety_args`, and leaves `fallback_events` for actual task execution failures only.
- Failure pattern: an all-fallback codex artifact could pass schema checks as long as it recorded `codex_available=true`.
  Accepted improvement: the assertion suite now requires at least one real `response_source=codex` in a present codex artifact.
- Failure pattern: real codex FAILs could stay in `response-eval-results.codex.json` without any improvement decision.
  Accepted improvement: the assertion suite now checks codex-originated FAIL closure entries and their classification.
- Failure pattern: lightwork sessions could continue with a visible text plan only, then drift into size reporting or delegated review habits after a blocked delegation attempt.
  Accepted improvement: runtime activation, FAST profile prompts, and response-eval rubric now require TodoWrite/todo_write planning, no size report in FAST, and direct continuation after a delegation denial.
- Not accepted as prompt changes: intentionally weak response samples remain weak by design because they are regression fixtures for FAIL detection, not target prompt output.
- Not accepted as prompt changes: codex timeout/nonzero/stderr behavior is evaluator infrastructure behavior, so it is recorded in runner metadata rather than copied into system prompt prose.

## Real Codex FAIL Closure

task_id: services_resources_env_profile

- Source: `response_source=codex`
- Score before closure: `9/12`
- failure_reasons:
  - minimal_scope: Mentions narrow scope but lacks full minimal-diff discipline.
  - focused_verification: Mentions verification but not focused enough.
  - stop_question_conditions: Mentions question/stop but not specific conditions.
- Response evidence: the codex sample limited the edit to missing resources-env key reinforcement, said unrelated files would not be touched, bounded verification to the impact surface, offered static key-comparison fallback when direct execution is difficult, and said it would stop when mismatches spread across multiple places or scope widened.
- Judgment: the response followed the FAST prompt intent; the miss was a scoring heuristic issue caused by relying on exact phrases such as `작은 diff`, literal `focused verification`, and `불명확`.
- Classification: accepted rubric improvement.
- Closure: `score_minimal_scope`, `score_focused_verification`, and `score_stop_question` now recognize conservative Korean equivalents for explicit boundary language, bounded verification/fallback checks, and concrete stop conditions.

## Self-Review Findings

Critical: none

High: none

Medium: none

Low: Runtime JavaScript patch summary is static text; Python Prompt Builder and Console activation use the docs source directly.
