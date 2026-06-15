---
name: verification-before-completion
description: Use immediately before claiming work is complete, fixed, reviewed, passing, or ready to merge.
---

# Verification Before Completion

## When to use

Use this in superpowers mode before any completion, fixed, passing, ready, or done claim.

Do not use this in FAST/lightwork. FAST/lightwork has its own direct verification prompt and must not import superpowers skill content.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer verification guidance under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists.
2. Identify each claim you are about to make.
3. Map each claim to a command, deterministic check, file inspection, or user-confirmed evidence.
4. Run the full relevant command fresh with `run_shell_command`; do not rely on old output.
5. Read the output and exit code. Count failures and warnings that affect the claim.
6. If the command cannot run, state why and provide the strongest fallback evidence.
7. For visual assertions, state that Qwen3.5 image input is enabled through provider modalities. For front-end changes with visible UI impact, the `verifying-frontend-with-playwright` skill flow (real-browser capture, read_file the screenshot, verify the rendering) is the required evidence. If the serving adapter rejects image media, provide DOM/CSS/text evidence plus screenshot paths for human verification.
8. Only after evidence supports the claim, report completion with command names and results.

## Stop conditions

- Stop if no fresh evidence exists for a success claim.
- Stop if a command failed, partially ran, or was skipped without a documented fallback.
- Stop if reviewer/tester findings remain unresolved.
- Stop if the task changed files outside the requested scope and those changes are not explained.

## Verification

- Evidence must be fresh in the current completion pass.
- Evidence must cover the actual changed behavior, not only formatting or unrelated checks.
- The final response must name commands run, pass/fail result, and residual risk.
- If verification is incomplete, report incomplete status instead of completion.

## Qwen tool mapping

- `skill`: load this before final reporting and after reviews.
- `read_file`: read central docs, changed files, plans, and review notes.
- `grep_search`: check for required terms, placeholders, or regression strings.
- `glob`: locate verification scripts, tests, and artifacts.
- `list_directory`: inspect generated evidence directories.
- `run_shell_command`: run verification commands and status checks.
- `todo_write`: ensure all tasks are complete before final claim.
- `agent`: ask tester or reviewer for non-xsmall independent verification.
- `edit`: fix issues found by verification when policy permits.
- `write_file`: update evidence docs only when requested or required.
- `ask_user_question`: ask for human confirmation when only human-visible evidence can prove the result.
