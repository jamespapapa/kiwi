# KIWI Superpowers Workflow Map

This support file condenses the upstream Superpowers workflows into KIWI/qwencode terms.

## Bootstrap

- Treat `kiwi-superpowers` as the already selected bootstrap skill for this session.
- Check whether another skill-like workflow applies before acting: design clarification, plan writing, test-first implementation, debugging, review, verification, or branch finish.
- User and repository instructions remain higher priority than this workflow map.

## Design And Planning

- Ambiguous feature work starts with a short design conversation before implementation.
- Broad work gets a written plan with exact files, steps, verification, and stop conditions.
- If the user already supplied a concrete task and selected task_size, keep the plan proportional to that size.

## Test-First Implementation

- For behavior changes, prefer a failing assertion or focused test before production code.
- If the repository has no practical test harness for the slice, state the fallback verification before editing.
- Do not add speculative behavior beyond the failing check and user request.

## Debugging

- Reproduce or identify the failure surface first.
- Trace data flow backward to the earliest bad value or wrong branch.
- Test one hypothesis at a time and avoid stacked fixes.

## Review And Verification

- Review each implementation result against the request, impact map, and verification evidence.
- Critical and high findings block completion.
- Completion claims require fresh verification evidence or an explicit explanation of why verification could not run.

## Delegation

- `xsmall`: no delegation.
- `small`: one narrow implementation slice.
- `medium`: explorer, implementation, and reviewer.
- `large`/`xlarge`: planner and architect before implementation slices; reviewer after each implementation result; debugger before fix loops; tester for verification review.

## Local Evidence

- Start from `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; use optional `D:/aiops/docs/<project-key>/project-info/` summaries only if that central directory exists.
- Verify against current files before changing behavior.
- Keep prompts and agent work orders small enough for Qwen3.5 to follow reliably.
