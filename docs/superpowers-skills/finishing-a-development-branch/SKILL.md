---
name: finishing-a-development-branch
description: Use when implementation and review are complete and the branch needs final verification, cleanup choices, or integration guidance.
---

# Finishing A Development Branch

## When to use

Use this in superpowers mode after implementation, review, and verification work appears complete but before final integration, merge, or handoff.

Do not use this in FAST/lightwork. FAST/lightwork reports direct completion evidence without loading this superpowers branch workflow.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer verification guidance under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists.
2. Check repository status and changed files with read-only commands.
3. Ensure implementation tasks, review findings, and debugging follow-ups are complete.
4. Run `verification-before-completion` with all required commands.
5. Summarize changed files, behavior, verification, and residual risk.
6. Present integration choices when needed: keep branch as-is, prepare patch, merge, or clean up. Do not merge, push, or delete branches without explicit user confirmation.
7. If worktree usage is relevant, route to `using-git-worktrees`.
8. For visual changes, state that Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, include DOM/CSS/text evidence plus human review points.

## Stop conditions

- Stop if verification is missing, stale, or failed.
- Stop if critical or high review findings remain.
- Stop if git status shows unexpected user changes not related to the task.
- Stop before merge, push, branch deletion, or cleanup without explicit user approval.

## Verification

- Fresh verification evidence must support every completion claim.
- Diff summary must match the requested scope.
- Unexpected untracked or modified files must be identified and left untouched unless the user instructs otherwise.
- Final response must include commands run and residual risk.

## Qwen tool mapping

- `skill`: load verification, review-receiving, and worktree skills as needed.
- `read_file`: read central docs, plan, review notes, and changed files.
- `grep_search`: check for placeholders or required updated terms.
- `glob`: locate generated evidence and docs.
- `list_directory`: inspect docs and artifact directories.
- `run_shell_command`: run git status, diff summaries, and verification.
- `todo_write`: ensure all tasks are complete.
- `agent`: request final tester or reviewer for non-xsmall work.
- `edit` and `write_file`: only for final accepted fixes in allowed context.
- `ask_user_question`: request explicit integration or cleanup choices.
