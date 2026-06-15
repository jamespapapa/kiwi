# Superpowers Porting Analysis

This document records the Phase 3 porting analysis for adapting the upstream Superpowers project into KIWI's closed-network qwencode runtime. The upstream reference available in this workspace is `../ref/superpowers-main`; it is the extracted source that corresponds to the requested upper `ref/superpowers` reference.

## Upstream Structure

The upstream project is a zero-dependency skills methodology packaged for multiple agent harnesses.

- Plugin metadata lives under `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.opencode/`, and `gemini-extension.json`.
- The executable startup layer is hook based. `hooks/hooks.json` registers a `SessionStart` hook, `hooks/run-hook.cmd` dispatches to the cross-platform hook runner, and `hooks/session-start` injects the `using-superpowers` bootstrap into the new session.
- The primary behavioral assets are under `skills/*/SKILL.md`. Key workflows are `using-superpowers`, `brainstorming`, `writing-plans`, `subagent-driven-development`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `requesting-code-review`, `receiving-code-review`, `verification-before-completion`, and `finishing-a-development-branch`.
- The OpenCode plugin shows the non-Claude pattern: register a local skills directory and inject bootstrap text at session start so the native `skill` tool discovers the skills.
- Tests are harness-specific and mostly validate skill triggering, hook/bootstrap behavior, and subagent-driven development transcripts.

## Claude And Internet Dependencies

Upstream Superpowers assumes one of several public harness installation flows. Those flows do not fit KIWI's Windows 11 closed-network runtime.

- Claude plugin marketplace commands and `CLAUDE_PLUGIN_ROOT` are Claude-only. KIWI cannot rely on them.
- Gemini/OpenCode/Cursor install instructions reference remote package or plugin managers. KIWI cannot require a live internet fetch inside the target network.
- `SessionStart` hook injection assumes the harness supports plugin hooks that can add context before the first response. In KIWI, the equivalent control point is the Qwen runtime policy patch and the work-mode activation context.
- Upstream skill examples often refer to Claude tool names such as Task, Skill, TodoWrite, Read, Write, Edit, and Bash. KIWI must translate the behavior to Qwen tool names: `skill`, `agent`, `todo_write`, `read_file`, `edit`, `write_file`, `run_shell_command`, and `ask_user_question`.

## Skill And Workflow Model

The core model is not a single prompt. It is a skill-first workflow:

- `using-superpowers` is the bootstrap. It forces the agent to check and invoke relevant skills before acting.
- `brainstorming` gates unclear feature work behind design conversation and user approval.
- `writing-plans` turns an approved design into exact implementation steps.
- `test-driven-development` requires a failing test before production code for behavior changes.
- `systematic-debugging` requires root-cause investigation before fixes.
- `subagent-driven-development` and `dispatching-parallel-agents` isolate tasks and reviews across focused agents.
- `requesting-code-review`, `receiving-code-review`, and `verification-before-completion` make review and evidence gates mandatory before completion claims.

For KIWI, the reusable concept is the workflow discipline, not the upstream marketplace, hook runner, or Claude-specific command syntax.

## KIWI Qwencode Porting Decisions

KIWI implements Superpowers as a real work mode rather than a text-only appendix.

- The `superpowers` prefix activates a locked KIWI work mode in the same way `lightwork` and `ultrawork` do.
- The runtime installs a Qwen extension at `extensions/superpowers` and `portable-user/.qwen/extensions/superpowers`.
- The extension contains the compatibility `kiwi-superpowers` entrypoint, the `using-superpowers` router, and the individual Superpowers skill library. Qwen's built-in `skill` tool loads these skills; `tool_search` is not the skill discovery path.
- The session activation context instructs Kiwi to read central project docs under `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present before broad analysis, skill invocation, or delegation. Optional Project Info summaries under `D:/aiops/docs/<project-key>/project-info/` are read only if that central directory exists.
- The UI-selected `task_size` remains the source of truth for non-FAST Prompt Builder output. Prompt Builder recommendations are advisory only.
- Superpowers may use the ultrawork agent loop only after the `kiwi-superpowers` skill has established an impact map, execution contract, and verification plan. Ultrawork is the delegation substrate, not the source of truth for superpowers mode.
- FAST/lightwork remains isolated. FAST prompts, intent prompts, compose prompts, and console activation text must not mention superpowers, ultrawork, team, subagent, or task_size concepts.

## Runtime Asset Mapping

The final KIWI runtime assets are:

- `docs/superpowers-skills/kiwi-superpowers/SKILL.md`: Qwen compatibility entrypoint and skill-first operating contract for the mode.
- `docs/superpowers-skills/using-superpowers/SKILL.md`: upstream-style router that selects the relevant local skill.
- `docs/superpowers-skills/*/SKILL.md`: local Qwen ports of the Superpowers workflow library.
- `docs/superpowers-skills/kiwi-superpowers/superpowers-workflows.md`: local workflow map adapted from upstream skills.
- `docs/superpowers-runtime-policy.md`: policy source installed as `SUPERPOWERS_POLICY.md` and `QWEN.md` in the Qwen superpowers extension.
- `backend/app/qwencode_runtime.py`: patches live Qwen runtime scripts and installs superpowers extension assets.
- `scripts/build-offline-bundle.py`: applies the same patch/install behavior to the offline bundle.
- `backend/app/prompt_builder.py`: renders superpowers prompts with central docs context, selected task_size source of truth, and the skill-first contract.
- `backend/app/ultrawork_console.py`: injects the work-mode lock, central docs context, selected size gate, and superpowers skill gate on direct console prompts.

## Removed Or Replaced Dependencies

The port removes or replaces these upstream assumptions:

- Marketplace installation is replaced by copying local extension assets into the bundled Qwen runtime.
- Hook-script context injection is replaced by patched Qwen runtime activation context and policy files.
- Claude-only Skill/Task command wording is replaced with Qwen `skill` and `agent` tool contracts.
- Remote documentation lookups are replaced with local `docs/superpowers-*` assets plus current repository evidence.
- Public internet update flows are omitted from runtime assets. Updates happen by rebuilding the KIWI offline bundle.
- Upstream worktree and branch-finish workflows are treated as optional local discipline. KIWI must still respect the user's existing worktree and never revert unrelated changes.

## Verification Assertions

`scripts/assert-superpowers-porting.py` verifies the porting contract:

- The analysis document exists and contains the upstream structure, dependency, workflow, KIWI mapping, replacement, and verification sections.
- Superpowers skill and policy assets exist and include Project Info Layer, work mode lock, selected task_size, source of truth, and skill-first language.
- Prompt Builder superpowers output includes central docs context, selected task_size as source of truth, and `kiwi-superpowers` skill-first instructions.
- Backend runtime and offline bundle patches inject central docs paths, built-in `skill` tool calls for `kiwi-superpowers`/`using-superpowers`, and `SUPERPOWERS_POLICY.md` fallback instructions.
- FAST final prompt, intent prompt, compose prompt, and console activation text do not leak superpowers/ultrawork/team/subagent/task_size concepts.
- Runtime-facing superpowers assets do not retain remote install requirements or Claude-only execution commands.
