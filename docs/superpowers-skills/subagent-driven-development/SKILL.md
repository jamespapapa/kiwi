---
name: subagent-driven-development
description: Use when a written plan or non-xsmall implementation should be executed through scoped Qwen agents with review checkpoints.
---

# Subagent Driven Development

## When to use

Use this in superpowers mode for `small`, `medium`, `large`, or `xlarge` implementation when mutation should be delegated rather than done by main Kiwi.

Do not use this in FAST/lightwork. FAST/lightwork has no subagents and must not receive this skill content. Do not use this for `xsmall`; xsmall is Kiwi direct work after central docs and skill checks.

## Core rule

Fresh subagent per task plus two-stage review: spec compliance first, code quality second. Independent verification is mandatory; the implementer report is evidence to inspect, not proof.

Main Kiwi coordinates, reads results, manages `todo_write`, and verifies. In non-xsmall work, mutating implementation is performed by the selected implementation agent: DCP Front uses `dcp-front-developer`, DCP Services uses `dcp-backend-developer`, DRT Front uses `drt-front-developer`, DRT API uses `drt-backend-developer`, DRT CMS frontend uses `drt-cms-front-developer`, DRT CMS backend uses `drt-cms-backend-developer`, otherwise `coder-35`.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists.
2. If `D:/aiops/docs/<project-key>/knowledge/00-index.md` exists, read it and the relevant pack docs as seed knowledge; verify against current files before dispatch.
3. Read the approved plan or construct a narrow work order from the user request.
4. Confirm selected `task_size` and implementation agent.
5. Split work into slices with non-overlapping file ownership. Do not dispatch parallel implementation unless `dispatching-parallel-agents` proves independence.
6. For each slice, send an implementer work order with objective, scope, full task text, files, required reading, exact steps, the Exact Edit Protocol, non-goals, verification, stop conditions, and response format.
7. Handle implementer status: `DONE` proceeds to review, `DONE_WITH_CONCERNS` requires concern triage, `NEEDS_CONTEXT` requires more context and re-dispatch, `BLOCKED` requires escalation or task decomposition. Escalate if the plan is wrong, the agent needs a stronger model, or the user must choose.
8. Dispatch a spec compliance reviewer prompt. It must read actual code/diff and compare line by line to the requested task, reporting missing work, extra work, or misunderstandings with file/line evidence.
9. Only after spec compliance passes, dispatch a code quality reviewer prompt. It checks maintainability, tests, architecture, file responsibility, and regressions.
10. If a reviewer finds issues, send the same slice back for fixes and repeat review. Do not move to the next dependent task while review is open.
11. After every slice and after the whole plan, use `verification-before-completion`. Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, visual slices need DOM/CSS/text evidence and screenshot paths for human review.

## Implementer work order template

```text
IMPLEMENTER WORK ORDER
Agent: <dcp-front-developer | dcp-backend-developer | drt-front-developer | drt-backend-developer | drt-cms-front-developer | drt-cms-backend-developer | coder-35>
Objective: <one task outcome>
Required central docs: D:/aiops/docs/<project-key>/knowledge first when present; optional D:/aiops/docs/<project-key>/project-info only if that central directory exists, plus <specific files>
Task text: <paste full task; do not make agent infer from plan filename>
Files in scope: <create/modify/test paths>
Non-goals: <explicitly forbidden extra work>
Steps: <TDD/red-green-refactor steps when behavior changes>
Exact Edit Protocol: read the target range immediately before every edit; `@file` references and prompt-attached file content do not satisfy the edit tool read gate; copy old_string only from the latest read_file output; reread after each successful edit to the same file; for any N-line deletion/replacement use the smallest exact current span that contains only the changed lines, adding neighboring context only if needed for uniqueness; if preserved boundary/context lines are included in old_string, copy them unchanged into new_string, otherwise exclude them from the span; on edit_no_occurrence_found do not retry the same/larger old_string, reread and retry once smaller, then stop; do not use PowerShell regex/Set-Content or full-file shell rewrites as an edit-mismatch workaround.
Verification: <focused and broader commands>
Stop conditions: ask if requirements, architecture, ownership, or dependencies are unclear
Report format: Status DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED; files changed; tests run; concerns; self-review
```

## Spec compliance reviewer prompt

```text
SPEC COMPLIANCE REVIEWER PROMPT
Review whether the implementation matches the task exactly.
Do not trust the implementer report.
Read the diff and changed files.
Check missing requirements, extra features, wrong interpretation, and unverified claims.
Return: PASS or FAIL, with file/line evidence for every issue.
```

## Code quality reviewer prompt

```text
CODE QUALITY REVIEWER PROMPT
Run only after spec compliance passes.
Review correctness, tests, data flow, error handling, architecture, file responsibility, maintainability, and regressions.
Classify issues as Critical, High, Medium, or Low.
Return: strengths, issues with file/line evidence, recommendations, and ready/not-ready assessment.
```

## Stop conditions

- Stop if selected `task_size` is `xsmall`.
- Stop if file ownership overlaps without an explicit integration plan.
- Stop if an implementation prompt lacks verification or non-goals.
- Stop if an agent edits outside scope, skips required reading, or reports success without evidence.
- Stop if `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` is unresolved.
- Stop if external fetch or unbundled dependency is required.

## Verification

- Confirm every non-xsmall mutating change came from the selected implementation agent.
- Confirm spec compliance review and code quality review run after each implementation result.
- Confirm failed verification routes through debugging before another fix loop.
- Confirm final evidence covers all plan tasks and no reviewer Critical/High/Medium finding remains.

## Qwen tool mapping

- `skill`: load planning, review, debugging, dispatch, and verification skills.
- `read_file`: read central docs, plan, changed files, and agent results.
- `grep_search`: trace ownership and affected symbols.
- `glob`: locate files for each slice.
- `list_directory`: confirm module boundaries.
- `todo_write`: track slices, review gates, and verification.
- `agent`: dispatch implementation, spec compliance reviewer, code quality reviewer, explorer, debugger, and tester agents.
- `run_shell_command`: run read-only status and verification commands.
- `edit` and `write_file`: allowed only in implementation-agent context or xsmall direct policy, not main non-xsmall Kiwi.
- `ask_user_question`: resolve ownership or behavior blockers.
