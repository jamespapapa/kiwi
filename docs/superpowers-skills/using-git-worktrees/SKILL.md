---
name: using-git-worktrees
description: Use when parallel branches, isolated implementation spaces, or branch-safe execution need git worktree planning.
---

# Using Git Worktrees

## When to use

Use this in superpowers mode when a task benefits from an isolated worktree, parallel branch, risky experiment, or separate implementation track.

Do not use this in FAST/lightwork. FAST/lightwork should not create worktrees or import this superpowers workflow.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists to understand repository boundaries.
2. Inspect current git status before proposing worktree operations.
3. Confirm the user wants a separate worktree if creation, deletion, or branch changes are needed.
4. Choose a clear worktree path outside the selected project root only when the backend/project boundary allows it; otherwise stop and ask.
5. Create or use a worktree with explicit branch name and purpose.
6. Keep each worktree assigned to non-overlapping file ownership when used with agents.
7. Run verification inside the worktree that contains the changes.
8. Use `finishing-a-development-branch` before merge, cleanup, or deletion.
9. Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, visual verification in worktrees still needs DOM/CSS/text evidence and screenshot paths for human review.

## Stop conditions

- Stop if git status has unexpected user changes.
- Stop before creating, deleting, or pruning worktrees without explicit user approval.
- Stop if the worktree path would violate the selected project root boundary.
- Stop if parallel branches would edit overlapping files without a merge plan.

## Verification

- Confirm current branch, status, and worktree list before and after operations.
- Confirm each worktree has a clear branch and ownership scope.
- Confirm verification commands ran in the intended worktree.
- Confirm cleanup is user-approved.

## Qwen tool mapping

- `skill`: load branch finishing and dispatch skills as needed.
- `read_file`: read central docs and any branch/worktree plan.
- `grep_search`: find files that define ownership and verification.
- `glob`: locate repo files and plans.
- `list_directory`: inspect worktree and project roots.
- `run_shell_command`: run git status, worktree list, branch, and verification commands.
- `todo_write`: track setup, execution, integration, and cleanup.
- `agent`: assign agents to separate worktrees only after ownership is clear.
- `edit` and `write_file`: only inside the correct worktree and allowed mutation context.
- `ask_user_question`: get approval for branch/worktree operations.
