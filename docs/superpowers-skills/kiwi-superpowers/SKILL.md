---
name: kiwi-superpowers
description: Use in KIWI superpowers mode before broad analysis, code changes, or verification planning to build a stronger impact map and execution contract.
allowedTools:
  - read_file
  - grep_search
  - glob
  - list_directory
  - run_shell_command
  - agent
  - edit
  - write_file
---

# KIWI Superpowers Mode

Use this skill only after the console session has activated `superpowers` mode. The session mode is locked; do not switch to `lightwork` or `ultrawork` inside the same Qwen session.

This is a compatibility entrypoint for the full Qwen superpowers skill library. The purpose is to make Kiwi stop, load the local superpowers method, read project facts, choose the correct role composition from the selected task_size, route to the specific workflow skill, and only then implement or delegate.

## Work Mode Lock

- This skill runs only under the KIWI `superpowers` work mode lock.
- FAST/lightwork must never load this superpowers skill or use its delegated-agent workflow.
- Do not change mode inside the same Qwen session. If the task needs a different mode, ask the user to start a new console session.

## Operating Contract

1. Restate the user request in repository terms.
2. First read central project docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then use relevant `D:/aiops/docs/<project-key>/knowledge/*` files as seed knowledge only.
3. Optional Project Info Layer summaries live only under `D:/aiops/docs/<project-key>/project-info/`; read them only if that absolute central directory exists. Never try project-relative `docs/<project-key>/...` or `docs/kiwi/project-info/...` paths.
4. If central docs is missing or stale, report that central docs refresh is needed. Do not invent a default project overview.
5. Build an impact map before implementation: entrypoint, producer, carrier, API/request/response, persistence/cache/session, downstream consumer, and verification surface.
6. Confirm the selected task_size from the KIWI prompt. The selected task_size is the source of truth; do not replace it with a Kiwi recommendation.
7. Identify whether the task can remain direct work or needs delegated agents. Use `agent` only after this skill-driven map is clear.
8. If implementation is needed, delegate one narrow repair slice at a time. Include Objective, Scope, Files/ownership, Required reading, Exact steps, Non-goals, Verification, Required response, and stop conditions.
9. Keep user-visible reporting concise: mode, sizing/impact, current plan, verification evidence, remaining risks.

## Skill-First Rules

- Prefer current repository evidence over profile assumptions.
- Do not paste full optional Project Info JSON or large EAI markdown into prompts; use summary artifacts, central knowledge docs, and targeted evidence paths.
- Call the built-in `skill` tool for `using-superpowers` after this compatibility entrypoint, then call task-specific skills such as `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, review skills, or subagent skills as needed.
- Do not call tools named `using-superpowers` or a task-specific skill name directly; those names are values for the `skill` tool's `skill` parameter. If the `skill` tool reports unavailable/unknown skill, read `.qwen/skills/<skill>/SKILL.md`; if absent, read `D:/aiops/qwencode/portable-user/.qwen/skills/<skill>/SKILL.md`.
- Read `superpowers-workflows.md` when the task needs design, plan, test-first, debugging, review, verification, or delegation discipline.
- Read `command-contract.md` and `hook-policy.md` if activation, selected task_size, or skill availability is unclear.
- The superpowers policy and skill are the source of truth for this mode. The delegated agent loop is only the execution substrate after the skill-first map is complete.
- For DCP Front, trace route/view/component/Vuex DataStore/Axios/CSS and use `dcp-front-developer` for implementation.
- For DCP Services, trace controller/service/Redis/EAI/mapper and use `dcp-backend-developer` for implementation.
- For DRT Front, trace route/view/component/Pinia/DrtHttpClient/service and use `drt-front-developer` for implementation.
- For DRT API, trace controller/service/biz/mapper XML/profile config and use `drt-backend-developer` for implementation.
- For DRT CMS frontend, trace frontend route/view/service/model/grid/store and use `drt-cms-front-developer` for implementation.
- For DRT CMS backend, trace backend REST resource/service/repository/MyBatis XML/security/batch and use `drt-cms-backend-developer` for implementation.
- For generic projects, use `coder-35` when delegated implementation is needed.
- If a screenshot or image is mentioned, remember current Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, report DOM/CSS/text evidence and screenshot paths for human review.
- For any front-end implementation slice with visible UI impact, the `verifying-frontend-with-playwright` skill is mandatory before completion: capture the real browser with the bundled Playwright runtime, read the screenshot with read_file, and verify the rendered change.
- Reuse-first: publishing, mockup, and UI revision work modifies the existing screens, components, and styles in place. Do not create a new view or a parallel mock screen unless the user or work order explicitly names the new file path. Existing bottom sheets, confirm dialogs, and shared flows are reused as-is.
- If the work is small and clear, finish directly without delegated agents. If it is broad, use the delegated agent loop after the impact map is complete.

## Task Size Role Composition

- `xsmall`: Kiwi direct work after central docs and skill check. No agent delegation.
- `small`: Kiwi plans and may delegate one narrow implementation slice to the project implementation agent. Review is required only for shared files, data risk, or verification failure.
- `medium`: Use explorer for missing file/symbol context, implementation agent for one or two slices, and reviewer after implementation. Use architect only if data/API/shared risk appears.
- `large`: Use planner for requirements and acceptance criteria, architect for impact/order, explorer for targeted context, implementation agent for slices, reviewer after each slice, tester/debugger when verification or failures require it.
- `xlarge`: Split into phases. Plan, implement, review, and verify phase by phase; avoid overlapping file ownership.

## Local Superpowers Workflow Map

Use `superpowers-workflows.md` as the local adaptation of the upstream superpowers method:

- ambiguous feature work -> design and approval before implementation;
- multi-step work -> written plan with exact files and verification;
- behavior changes -> failing test or assertion before production code when practical;
- bugs or failures -> root-cause investigation before fixes;
- completed implementation -> review and verification before completion claims.

## Individual Skill Routing

- Session start or explicit superpowers request -> `using-superpowers`.
- New/ambiguous feature -> `brainstorming`.
- Approved design or multi-step work -> `writing-plans`.
- Existing plan -> `executing-plans` or `subagent-driven-development`.
- Behavior change -> `test-driven-development`.
- Failure or unclear regression -> `systematic-debugging`.
- Review request or review findings -> `requesting-code-review` or `receiving-code-review`.
- Front-end change with visible UI impact -> `verifying-frontend-with-playwright` before the completion claim.
- Completion claim -> `verification-before-completion`.
- Branch/worktree flow -> `finishing-a-development-branch` or `using-git-worktrees`.

## Delegation Work Order Template

When delegation is needed, keep the work order narrow:

- Objective: one concrete outcome.
- Scope: exact files or symbols owned by this slice.
- Required reading: `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, optional central Project Info summaries only if present, and current files.
- Exact steps: read, impact map, edit, focused verification.
- Exact Edit Protocol: read the target range immediately before every edit; `@file` references and prompt-attached file content do not satisfy the edit tool read gate; copy `old_string` only from the latest read_file output; reread after each successful edit to the same file; for any N-line deletion/replacement use the smallest exact current span that contains only the changed lines, adding neighboring context only if needed for uniqueness; if preserved boundary/context lines are included in `old_string`, copy them unchanged into `new_string`, otherwise exclude them from the span; on `edit_no_occurrence_found` do not retry the same/larger `old_string`, reread and retry once smaller, then stop; do not use PowerShell regex/`Set-Content` or full-file shell rewrites as an edit-mismatch workaround.
- Non-goals: unrelated refactor, broad formatting, unrelated behavior.
- Verification: command or fallback evidence.
- Required response: files read, files changed, impact map, verification result, remaining risks, exact question if blocked.

## Qwen tool mapping

- Use `read_file`, `grep_search`, `glob`, and `list_directory` for central knowledge docs, optional central Project Info summaries, and current repository evidence.
- Use `run_shell_command` only for non-mutating inspection or focused verification unless this session is direct `xsmall` work.
- Use `ask_user_question` when task_size metadata is missing, ownership is ambiguous, or a requested visual/image path cannot be validated by the current serving adapter.
- Use `agent` only in non-`xsmall` superpowers work, after the impact map and selected implementation agent are clear.
- Use `edit` and `write_file` directly only when policy allows Kiwi direct work; otherwise delegate mutation to the selected implementation agent (`coder-35`, DCP, DRT, or CMS developer agent).
- Use `todo_write` for multi-step plans that need visible progress tracking.

## Response Shape

Return a compact plan with these headings:

- Request
- Impact Map
- Mode Decision
- Execution Plan
- Verification
- Risks Or Questions
