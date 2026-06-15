---
name: using-superpowers
description: Use when a KIWI superpowers session starts, when choosing which local workflow skill should guide the task, or when the user explicitly asks for superpowers.
---

# Using Superpowers

## When to use

Use this in `superpowers` work mode before broad analysis, implementation, delegation, review, or completion claims. It is the router for the local Qwen skill library.

Do not use this in FAST/lightwork. FAST/lightwork must not load, quote, or rely on superpowers skill content; it stays direct and narrow.

## Steps

1. Confirm the session is locked to `superpowers` or `spw`.
2. First read central project docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then use relevant pack docs as seed knowledge and verify claims against current files.
3. Optional Project Info Layer summaries live only under `D:/aiops/docs/<project-key>/project-info/`; read them only if that absolute central directory exists. Never try project-relative `docs/<project-key>/...` or `docs/kiwi/project-info/...` paths.
4. If central docs is missing or stale, report that refresh is needed and continue only from current repository evidence.
5. Confirm the KIWI selected `task_size`; it is the source of truth for role composition.
6. Pick the smallest applicable workflow skill:
   - New or ambiguous design: `brainstorming`.
   - Approved design to plan: `writing-plans`.
   - Existing plan to execute: `executing-plans` or `subagent-driven-development`.
   - Behavior change: `test-driven-development`.
   - Failure or unclear bug: `systematic-debugging`.
   - Review request: `requesting-code-review` or `receiving-code-review`.
   - Front-end change with visible UI impact: `verifying-frontend-with-playwright` (mandatory before its completion claim).
   - Completion claim: `verification-before-completion`.
   - Branch integration: `finishing-a-development-branch`.
7. For `xsmall`, keep Kiwi direct after this skill check. For non-xsmall, delegate mutation only through the selected implementation agent after the impact map is clear.
8. If the task mentions screenshots or image inspection, state that Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, use DOM/CSS/text evidence plus screenshot paths for human confirmation.

## Stop conditions

- Stop if the session is FAST/lightwork or another work mode.
- Stop if non-FAST selected `task_size` metadata is absent; first load/check `ask_user_question` usage/schema, then call the native `ask_user_question` tool with a concise blocking question.
- Stop before mutation if central docs and current files disagree in a way that changes ownership, API carrier, storage, or downstream consumers.
- Stop before any non-xsmall implementation if no selected implementation agent policy is clear.

## Verification

- Report which superpowers skill or skills were selected and why.
- Show a compact impact map before editing or calling `agent`.
- For non-xsmall, verify the first mutating action is delegated to the selected implementation agent.
- Before completion, invoke or apply `verification-before-completion`.

## Qwen tool mapping

- local skills: call this router and then the specific workflow skill through the built-in `skill` tool. Use direct SKILL.md reads only when the `skill` tool reports unavailable/unknown skill.
- `read_file`: read central docs, `D:/aiops/docs/<project-key>/knowledge` seed docs when present, and current source files.
- `grep_search`: find symbols, routes, API carriers, persistence, and consumers.
- `glob`: locate docs, plans, tests, and skill files.
- `list_directory`: inspect project structure before assumptions.
- `todo_write`: track selected workflow steps.
- `agent`: delegate non-xsmall implementation, review, exploration, debugging, or testing.
- `edit` and `write_file`: allowed only when policy permits direct xsmall work or inside an implementation agent.
- `run_shell_command`: run read-only discovery or verification; mutating commands follow mode policy.
- `ask_user_question`: ask concise blocking questions.
