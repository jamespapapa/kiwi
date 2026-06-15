---
name: writing-plans
description: Use when an approved design or concrete requirements need a step-by-step implementation plan before code changes.
---

# Writing Plans

## When to use

Use this in superpowers mode after brainstorming approval or when the user provides enough requirements to plan a multi-step implementation.

Do not use this in FAST/lightwork. FAST/lightwork stays direct and does not import superpowers planning content.

## Core rule

Write plans for another worker with zero context. The plan must be executable without guessing: exact files, exact code or checks, exact commands, expected outcomes, TDD steps, review gates, and non-goals.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` only if that central directory exists, and the approved design or requirements.
2. Scope check: if the request covers independent subsystems, split into separate specs/plans before detailed tasking.
3. Map file structure before defining tasks: create/modify/test docs, ownership boundaries, data flow, and interfaces.
4. Use the selected `task_size` as source of truth. Keep `xsmall` plans compact and direct; split non-xsmall work into agent-sized slices.
5. Write bite-sized tasks, roughly 2-5 minutes per concrete step, with checkbox steps.
6. Prefer a failing assertion or test before production code when behavior changes.
7. Include review gates after each implementation slice for non-xsmall work.
8. Include stop conditions for unclear business meaning, API/storage carrier, shared-file ownership, closed-network dependency, or verification failure.
9. Save the plan only when it is specific enough for another worker to execute without guessing.
10. If visual validation is needed, state that Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, include DOM/CSS/text checks plus screenshot paths for human review.

## Plan header template

```markdown
# <Feature Name> Implementation Plan

> Required execution skill: use `subagent-driven-development` for non-xsmall work, or `executing-plans` for inline approved execution.

**Goal:** <one sentence>
**Architecture:** <2-3 sentences>
**Tech Stack:** <local stack and tools>

---
```

## Task template

```markdown
### Task N: <component or behavior>

**Files:**
- Create: `<exact/path>`
- Modify: `<exact/path>`
- Test: `<exact/path>`

- [ ] Step 1: Write the failing test or assertion.
  - Command: `<focused command>`
  - Expected RED: `<specific failure>`
- [ ] Step 2: Implement the minimum change.
- [ ] Step 3: Run focused GREEN verification.
  - Command: `<focused command>`
  - Expected GREEN: `<specific pass>`
- [ ] Step 4: Run broader verification.
- [ ] Step 5: Request review or mark the slice ready.
```

## No placeholders

These are plan failures: `TBD`, `TODO`, "implement later", "similar to previous", "add appropriate error handling", "write tests for the above", references to undefined functions, or commands without expected output.

If code is needed for a step, show the relevant code or the exact location to copy an existing local pattern. If a task changes behavior, include the red-green-refactor path.

## Execution handoff

After saving the plan, present exactly two execution options:

1. Subagent-Driven: use `subagent-driven-development`; fresh implementer per task and two-stage review.
2. Inline Execution: use `executing-plans`; same-session execution with checkpoints.

Ask which approach the user wants unless they already specified one.

## Stop conditions

- Stop if no approved design or sufficiently concrete requirements exist.
- Stop if files, verification commands, or acceptance criteria are unknown.
- Stop if a task says "TODO", "TBD", or "similar to previous" instead of exact steps.
- Stop if non-xsmall tasks cannot be delegated without overlapping file ownership.
- Stop if the plan would require external fetch, remote installer, or unbundled dependency.

## Verification

- Re-read the plan against the design or request and list coverage gaps.
- Search for placeholders and ambiguous steps.
- Confirm every task has files, steps, verification, expected output, and non-goals.
- Confirm non-xsmall tasks can be delegated without overlapping file ownership.
- Confirm the next skill is `subagent-driven-development` or `executing-plans`, not ad hoc implementation.

## Qwen tool mapping

- `skill`: load `using-superpowers`, then this skill, then `subagent-driven-development` or `executing-plans`.
- `read_file`: read central docs, specs, current source, and test files.
- `grep_search`: find existing patterns and verification commands.
- `glob`: locate relevant files, docs, and tests.
- `list_directory`: map module layout.
- `write_file`: create the plan document after it is complete.
- `edit`: update an existing plan when revising.
- `todo_write`: track plan-writing tasks.
- `agent`: optional reviewer for plan specificity in non-xsmall work.
- `run_shell_command`: read-only discovery, status, and command availability checks.
- `ask_user_question`: resolve blocking plan gaps.
