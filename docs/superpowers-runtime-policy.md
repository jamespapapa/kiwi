# KIWI Superpowers Runtime Policy

Policy id: `SUPERPOWERS_POLICY`

This file is installed into the Qwen `superpowers` extension as `SUPERPOWERS_POLICY.md` and `QWEN.md`.

## Source Of Truth

- In `superpowers` mode, this superpowers policy, the compatibility entrypoint `kiwi-superpowers`, and the individual `using-superpowers` skill library are the source of truth for the first analysis pass.
- The selected task_size from the KIWI UI is the source of truth for execution scale.
- Prompt Builder recommended sizing is advisory context only.
- The ultrawork agent loop is available only as a delegated execution substrate after skill-first impact mapping is complete.

## Startup Contract

- A `superpowers` or `spw` prefix locks the session to superpowers mode.
- Do not switch to `lightwork` or `ultrawork` inside the same Qwen session.
- Before broad analysis, implementation, or any `agent` call, read central project docs from `D:/aiops/docs/<project-key>/`. Start with `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present.
- Optional Project Info Layer summaries live only under `D:/aiops/docs/<project-key>/project-info/`. Read them only if that absolute central directory exists.
- Never try project-relative `docs/<project-key>/...` or `docs/kiwi/project-info/...` paths for central docs.
- Treat `D:/aiops/docs/<project-key>/knowledge/*` as seed project knowledge only; verify every relevant claim against current files.
- If optional Project Info is missing or stale, report that refresh is needed and continue from central knowledge plus current-file evidence.
- Do not paste full `project-info.json` or large EAI markdown into prompts. Use summary artifacts and targeted evidence paths.

## Skill-First Contract

- First tool actions after superpowers activation must call the built-in `skill` tool before planning or work: first `skill="kiwi-superpowers"`, then `skill="using-superpowers"`, then the task-specific skill when applicable.
- This skill-tool gate applies to every superpowers size, including `large` and `xlarge`; role composition starts only after the skill-tool gate.
- Do not call `todo_write`, read broad repository files, implement, or call `agent` until the `skill` tool has been called for `kiwi-superpowers` and `using-superpowers`, or the fallback policy file has been read.
- Do not call tools named `kiwi-superpowers` or `using-superpowers`; those are values for the `skill` tool's `skill` parameter.
- If the built-in `skill` tool reports unavailable/unknown skill, read project `.qwen/skills/<skill>/SKILL.md`; if absent, read `D:/aiops/qwencode/portable-user/.qwen/skills/<skill>/SKILL.md`; if both are absent, report the missing skill files once and use this installed policy file as the fallback without blocking.
- The first superpowers response must include the selected task_size, a short impact map, the selected role composition, and the verification surface.
- Do not call `agent` before central docs and skill-first checks are done.
- For front-end implementation with visible UI impact, load `verifying-frontend-with-playwright` through the built-in `skill` tool before any completion claim: capture the real browser with the bundled Playwright runtime, read the screenshot with read_file, and verify the rendered change.

## Individual Skill Library

- `using-superpowers`: session router and skill selection.
- `brainstorming`: design-before-implementation.
- `writing-plans`: detailed implementation plans.
- `executing-plans`: task-by-task plan execution.
- `test-driven-development`: red-green-refactor for behavior changes.
- `systematic-debugging`: root-cause investigation.
- `verification-before-completion`: evidence before completion claims.
- `requesting-code-review` and `receiving-code-review`: review request and finding resolution.
- `subagent-driven-development` and `dispatching-parallel-agents`: scoped Qwen agent execution.
- `finishing-a-development-branch` and `using-git-worktrees`: branch/worktree completion workflows.
- `verifying-frontend-with-playwright`: mandatory real-browser capture and visual verification for front-end implementation.

## Size Roles

- `xsmall`: Kiwi direct work after central docs and skill check; no agent delegation.
- `small`: Kiwi plus one narrow implementation agent when needed; review only if shared files, data risk, or verification failure appears.
- `medium`: explorer plus implementation agent, with reviewer after implementation and architect only for data/API/shared risk.
- `large`: planner, architect, explorer, implementation agent, reviewer, and tester/debugger as needed.
- `xlarge`: phase the work; separate planning, implementation slices, review, and final verification.

## Mutation Policy

- `superpowers` `xsmall` is Kiwi direct work: Kiwi may make the smallest direct edit after central docs and skill-first checks, and must not delegate agents.
- Non-xsmall `superpowers` and `ultrawork` team modes keep Kiwi orchestration-first and delegate mutation to the selected implementation agent.
- Mutating tools should be used by the selected implementation agent. Runtime hooks currently treat subagent identity mismatch as advisory rather than a hard deny because Qwen can omit or drift subagent identity in hook payloads.
- Selected implementation agents include `coder-35`, `dcp-front-developer`, `dcp-backend-developer`, `drt-front-developer`, `drt-backend-developer`, `drt-cms-front-developer`, and `drt-cms-backend-developer` when selected by project profile.
- Planner, architect, reviewer, debugger, explorer, tester, and the main Kiwi orchestrator remain read-only by prompt contract for direct mutation in non-xsmall team modes.

## Tool Mapping

- local skills: call the built-in `skill` tool with `kiwi-superpowers`, `using-superpowers`, and the task-specific superpowers skill. Use SKILL.md file reads only as fallback when the `skill` tool reports unavailable/unknown skill.
- agent: pass `description`, `prompt`, and `subagent_type`; delegate one narrow slice at a time.
- read_file: use absolute `file_path`; confirm uncertain paths with glob or grep first. Copy paths character-for-character from prior tool output or the user message; never re-type Korean file names and never insert spaces around `-`/`_`. If the tool answers `File not found. Did you mean: <path>`, retry once with exactly that suggested path. Read large files in offset/limit slices.
- edit Exact Edit Protocol: use `file_path`, `old_string`, and `new_string`. Immediately read the target range first; `@file` references and prompt-attached file content do not satisfy the edit tool read gate. Copy `old_string` from that latest read_file output, not memory. After any successful edit to the same file, previous snippets are stale and must be reread. For any N-line deletion or replacement, use the smallest exact current span that contains only the lines being removed/replaced; add neighboring context only when the changed span is not unique. If preserved boundary/context lines are included in `old_string`, copy them unchanged into `new_string`; otherwise exclude them from the span. On `edit_no_occurrence_found`, do not retry the same or larger `old_string`; reread and retry once with a smaller exact literal, then stop and return to Kiwi/debugger. Do not use PowerShell regex/`Set-Content` or full-file shell rewrites as an edit-mismatch workaround.
- write_file: use only for new files or intentional full replacement. Do not write a long document in one write_file call: max_tokens truncation produces a cut-off file. Write the skeleton plus the first section first, then append the remaining sections with edit.
- run_shell_command: use non-mutating commands unless the authorized implementation agent owns the mutation.
- ask_user_question: before calling it, load/check the tool usage or schema; use a `questions` array with 1-3 question objects, each with `question`, `header`, `id`, and 2-3 options.
- `todo_write` tool: required before substantive work and after major decisions; keep plan status current for all superpowers sizes.

## Offline Boundary

- Do not require remote plugin installation, remote package fetches, or live web documentation to activate this mode.
- Use the local installed skills, this local policy, copied `D:/aiops/docs/<project-key>/knowledge` packs when present, optional central Project Info artifacts when present, KK docs MCP when available, and current repository reads/searches.
