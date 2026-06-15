---
name: systematic-debugging
description: Use when a failure, flaky test, runtime symptom, regression, or reviewer/tester finding needs root-cause investigation before a fix.
---

# Systematic Debugging

## When to use

Use this in superpowers mode for bugs, failed verification, flaky behavior, unexplained output, repeated tool failures, build failures, integration failures, or any fix request where the cause is not already proven.

Do not use this in FAST/lightwork. FAST/lightwork can do narrow diagnosis but must not load this superpowers skill body.

## Iron Law

NO FIX WITHOUT ROOT CAUSE INVESTIGATION FIRST.

Do not patch symptoms, stack another guess on top of a failed guess, or change multiple variables at once. Root-cause tracing comes before implementation.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists to identify entrypoints, data flow, and verification surfaces.
2. Reproduce the failure or identify the smallest observable symptom. Capture command, exit code, logs, expected result, and actual result.
3. Read error messages and stack traces completely before proposing a fix.
4. Check recent changes and compare against a nearby working example.
5. Trace backward from the symptom to the earliest wrong value, branch, state, API carrier, persistence write, environment value, or external boundary.
6. State one hypothesis at a time: "I think X is the root cause because Y." Treat it as a single hypothesis and test one variable at a time with the smallest observation or assertion.
7. For async or flaky failures, use condition-based waiting: poll until the actual condition is true with a timeout and clear failure message. No fixed sleep unless testing timing itself, and then document why.
8. If a test polluter is suspected, do polluter isolation: clean state, run subsets, bisect order-dependent tests, and identify the exact test or fixture that leaves pollution behind.
9. When the root cause is proven, use `test-driven-development` to add a regression check if practical.
10. Fix at the source. Add defense-in-depth only after root cause is known: entry validation, business validation, environment guards, and debug instrumentation where real boundaries exist.
11. If a visual bug is involved, remember Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, use DOM/CSS/text evidence and screenshot paths for human review.

## Stop conditions

- Stop if the symptom cannot be reproduced or observed after reasonable focused attempts.
- Stop if you are about to change more than one hypothesis variable.
- Stop before applying a fix without a root-cause explanation.
- Stop after three failed fix attempts and question the architecture or assumptions before trying another fix.
- Stop if the required environment or dependency is unavailable in the closed network.

## Verification

- Record reproduction evidence before the fix.
- Record the root cause and the exact evidence that proved it.
- Record the earliest wrong value and where it came from.
- Run the failing check after the fix and then a broader relevant check.
- Confirm defense-in-depth guards protect real boundaries and do not mask a still-broken source.

## Anti-patterns

- Guessing "probably X" and editing before evidence.
- Adding sleeps instead of condition-based waiting.
- Fixing where the error appears while the bad value originates elsewhere.
- Skipping root-cause tracing instead of using trace data flow evidence and fix at source discipline.
- Treating polluter isolation as optional when tests pass alone and fail in suite order.
- Adding validation everywhere before knowing which value is wrong.

## Qwen tool mapping

- `skill`: load debugging, TDD, and verification skills as the loop progresses.
- `read_file`: read central docs, source, tests, logs, and config.
- `grep_search`: trace symbols, state keys, routes, APIs, and error strings.
- `glob`: locate related tests, generated logs, and runtime files.
- `list_directory`: inspect modules and artifact directories.
- `run_shell_command`: reproduce, bisect, run focused checks, and inspect status.
- `edit`: apply the minimum fix after root cause is proven.
- `write_file`: add focused regression checks when needed.
- `todo_write`: track hypotheses and outcomes.
- `agent`: use debugger, explorer, tester, or implementation agents according to task size.
- `ask_user_question`: ask for missing repro details or business expectations.
