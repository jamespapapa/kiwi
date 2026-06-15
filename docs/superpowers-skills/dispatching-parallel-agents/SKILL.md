---
name: dispatching-parallel-agents
description: Use when two or more independent investigations or implementation slices can run concurrently without shared state or overlapping file ownership.
---

# Dispatching Parallel Agents

## When to use

Use this in superpowers mode when multiple failures, modules, files, or research questions are independent and can be delegated concurrently.

Do not use this in FAST/lightwork. FAST/lightwork has no parallel agent workflow. Do not use this for `xsmall` direct work.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists to understand ownership and shared flows.
2. Group work by independent domain: separate files, modules, test failures, APIs, or questions.
3. Prove independence before dispatch: no shared file writes, no shared generated artifacts, no ordering dependency, no shared mutable runtime state.
4. Create one self-contained `agent` prompt per domain with scope, input evidence, non-goals, verification, and expected response.
5. Assign clear file ownership and forbid edits outside scope.
6. Dispatch only independent work in parallel. Keep dependent tasks sequential.
7. Integrate results by reading summaries, checking diffs, resolving conflicts, and running combined verification.
8. Use reviewer and tester agents after integration when task size requires.
9. If any visual evidence is involved, state that Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, require DOM/CSS/text evidence plus screenshot paths.

## Stop conditions

- Stop if domains are not independent.
- Stop if two agents would edit the same file or generated output.
- Stop if prompts are broad or omit expected output.
- Stop if combined verification is unavailable and risk cannot be bounded.

## Verification

- Document independence rationale before dispatch.
- Confirm each agent stayed within scope.
- Confirm merged results do not conflict.
- Run focused checks for each domain and a combined verification pass.

## Qwen tool mapping

- `skill`: load this with `subagent-driven-development`.
- `read_file`: read central docs, failures, source, and agent outputs.
- `grep_search`: group failures and symbols by domain.
- `glob`: locate independent files and tests.
- `list_directory`: inspect module boundaries.
- `todo_write`: track each parallel domain and integration step.
- `agent`: dispatch independent explorer, implementation, tester, debugger, or reviewer tasks.
- `run_shell_command`: run status and verification.
- `edit` and `write_file`: integration edits only in allowed implementation context.
- `ask_user_question`: ask when independence or ownership is uncertain.
