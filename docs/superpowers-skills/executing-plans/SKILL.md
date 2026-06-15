---
name: executing-plans
description: Use when a written implementation plan should be executed task by task with verification and review checkpoints.
---

# Executing Plans

## When to use

Use this in superpowers mode when a written plan exists and the user wants it implemented in the current session.

Do not use this in FAST/lightwork. FAST/lightwork does not execute superpowers plans or quote this skill.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists.
2. Read the full plan and verify it has exact files, exact steps, verification, and stop conditions.
3. Critically review the plan before edits. If it has a blocking gap, ask instead of guessing.
4. Create `todo_write` items that mirror the plan.
5. For `xsmall`, Kiwi may execute directly after the skill and Project Info checks. For non-xsmall, delegate mutating slices with `agent` to the selected implementation agent.
6. Execute one task or slice at a time. Mark in progress, inspect files, edit, verify, then mark complete.
7. Run the specified verification after each task. If verification fails, switch to `systematic-debugging`.
8. Use `requesting-code-review` after non-xsmall implementation results.
9. Use `verification-before-completion` before reporting completion. Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, visual completion needs DOM/CSS/text evidence plus human review points.

## Stop conditions

- Stop if the plan lacks exact files, steps, or verification.
- Stop if a planned step conflicts with current repository evidence.
- Stop if verification fails twice without a root-cause hypothesis.
- Stop if implementation would require external fetch or unbundled dependency.
- Stop if non-xsmall work would mutate files outside the selected implementation agent.

## Verification

- Keep todos synchronized with the plan.
- For each task, record files read, files changed, command run, output summary, and residual risk.
- Confirm reviewer findings are resolved or explicitly accepted by the user.
- Confirm final status uses fresh verification evidence.

## Qwen tool mapping

- `skill`: load plan execution, debugging, review, and verification skills as needed.
- `read_file`: read central docs, plan, source, and tests.
- `grep_search`: trace symbols and plan references.
- `glob`: locate plan files and test suites.
- `list_directory`: confirm module boundaries.
- `todo_write`: mirror plan progress.
- `agent`: delegate non-xsmall mutating work and reviews.
- `edit` and `write_file`: direct only for policy-allowed xsmall or implementation-agent context.
- `run_shell_command`: run verification and safe discovery.
- `ask_user_question`: resolve blockers.
