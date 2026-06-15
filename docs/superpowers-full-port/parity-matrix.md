# Superpowers Full Port Parity Matrix

## Skill Parity

| Upstream skill | KIWI Qwen skill | Status | Parity notes |
| --- | --- | --- | --- |
| `skills/using-superpowers/SKILL.md` | `docs/superpowers-skills/using-superpowers/SKILL.md` | PORT | Skill router for superpowers mode, central docs first-read, selected_task_size source of truth, FAST/lightwork isolation, and Qwen tool mapping. |
| `skills/brainstorming/SKILL.md` | `docs/superpowers-skills/brainstorming/SKILL.md` | PORT | Preserves design-before-implementation gate, one-question flow, alternatives, user approval, and vision-enabled fallback. |
| `skills/writing-plans/SKILL.md` | `docs/superpowers-skills/writing-plans/SKILL.md` | PORT | Preserves detailed executable plans, exact files, verification, stop conditions, and reviewer handoff. |
| `skills/executing-plans/SKILL.md` | `docs/superpowers-skills/executing-plans/SKILL.md` | PORT | Preserves plan review, todo tracking, task-by-task execution, verification, and branch finishing handoff. |
| `skills/test-driven-development/SKILL.md` | `docs/superpowers-skills/test-driven-development/SKILL.md` | PORT | Preserves red-green-refactor, behavior assertions, anti-patterns, and evidence requirements. |
| `skills/systematic-debugging/SKILL.md` | `docs/superpowers-skills/systematic-debugging/SKILL.md` | PORT | Preserves reproduce, trace root cause, one hypothesis at a time, condition-based waiting, polluter isolation, and defense-in-depth. |
| `skills/verification-before-completion/SKILL.md` | `docs/superpowers-skills/verification-before-completion/SKILL.md` | PORT | Preserves evidence-before-claims with fresh command output and explicit fallback if verification cannot run. |
| `skills/requesting-code-review/SKILL.md` | `docs/superpowers-skills/requesting-code-review/SKILL.md` | PORT | Preserves independent review request with objective, files, verification, and severity-oriented findings. |
| `skills/receiving-code-review/SKILL.md` | `docs/superpowers-skills/receiving-code-review/SKILL.md` | PORT | Preserves finding triage, blocking severity handling, debug/TDD loop, and re-verification. |
| `skills/subagent-driven-development/SKILL.md` | `docs/superpowers-skills/subagent-driven-development/SKILL.md` | PORT | Preserves agent-per-slice execution, selected implementation agent policy, reviewer checkpoints, and no xsmall delegation. |
| `skills/dispatching-parallel-agents/SKILL.md` | `docs/superpowers-skills/dispatching-parallel-agents/SKILL.md` | PORT | Preserves independent-domain proof, parallel dispatch, conflict review, and combined verification. |
| `skills/finishing-a-development-branch/SKILL.md` | `docs/superpowers-skills/finishing-a-development-branch/SKILL.md` | PORT | Preserves final verification, status review, integration choices, and explicit user approval before merge/push/cleanup. |
| `skills/using-git-worktrees/SKILL.md` | `docs/superpowers-skills/using-git-worktrees/SKILL.md` | PORT | Preserves isolated branch/worktree workflow with user approval and ownership boundaries. |
| `skills/writing-skills/SKILL.md` | `docs/superpowers-skills/writing-skills/SKILL.md` | PORT | Additional full-port coverage for local Qwen skill authoring and deterministic trigger fixtures. |

All ported skills include Qwen tool mapping for `skill`, `agent`, `todo_write`, `read_file`, `grep_search`, `glob`, `list_directory`, `edit`, `write_file`, `run_shell_command`, and `ask_user_question`.

## Required Concept Coverage

These keys are verifier-enforced. A `PORT` claim is valid only when the target `SKILL.md` includes the required concepts below and this matrix records the coverage.

| KIWI Qwen skill | Required concept coverage |
| --- | --- |
| `test-driven-development` | Required concept coverage: iron_law, failing_test_first, delete_prewritten_production_code, red_green_refactor, good_bad_test_examples, mock_antipattern, overengineering_antipattern. |
| `systematic-debugging` | Required concept coverage: reproduce, earliest_wrong_value, one_hypothesis, condition_based_waiting, polluter_isolation, defense_in_depth_after_root_cause, root_cause_tracing. |
| `subagent-driven-development` | Required concept coverage: implementer_work_order, spec_reviewer_template, code_quality_reviewer_template, independent_verification, status_escalation, two_stage_review. |
| `writing-skills` | Required concept coverage: best_practices, persuasion, testing_with_subagents, graphviz_decision, examples, anti_patterns. |
| `requesting-code-review` | Required concept coverage: independent_review, reviewer_prompt_template, severity_first, file_line_findings, no_style_only_review. |
| `receiving-code-review` | Required concept coverage: evaluate_not_obey, triage_all_findings, fix_one_at_a_time, pushback, no_performative_agreement. |
| `writing-plans` | Required concept coverage: zero_context_engineer, file_structure_first, bite_sized_tasks, plan_header, no_placeholders, execution_handoff. |
| `brainstorming` | Required concept coverage: hard_gate, anti_pattern_simple_design, one_question_at_a_time, two_three_approaches, write_design_doc, spec_self_review, graph_render_decision. |

## Hook And Command Parity

| Upstream behavior | Upstream assets | KIWI replacement | Status |
| --- | --- | --- | --- |
| Session-start injection of using-superpowers | `hooks/session-start`, `hooks/hooks.json`, `hooks/hooks-cursor.json`, `hooks/run-hook.cmd` | Runtime activation context from `team-log-lib.js` patch and local Qwen extension policy. | MERGE |
| Plugin manifest and skills folder discovery | `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.opencode/plugins/superpowers.js`, `gemini-extension.json` | `install_kiwi_superpowers_extension()` writes local `qwen-extension.json` and copies every local `SKILL.md` folder. | ADAPT/REMOVE |
| Public command/install/update path | public plugin metadata and docs | Removed; offline bundle copies local assets. | REMOVE |

## Runtime And Offline Parity

- Backend runtime and offline bundle both discover all `docs/superpowers-skills/*/SKILL.md` folders by directory scan.
- Both install to `portable-user/.qwen/skills/<name>/SKILL.md`, `templates/project/.qwen/skills/<name>/SKILL.md`, `portable-user/.qwen/extensions/superpowers/skills/<name>/SKILL.md`, and fallback `extensions/superpowers/skills/<name>/SKILL.md`.
- Runtime policy allows Qwen `skill` in superpowers mode.
- FAST/lightwork blocks agent delegation and has no superpowers skill content.
- `selected_task_size` is persisted by activation state and remains source of truth.
- `xsmall` superpowers remains Kiwi direct work; non-xsmall team mode blocks main Kiwi mutation and uses selected implementation agents.
- Central knowledge docs are required before broad analysis, skill loading, or delegation; optional Project Info Layer summaries are read only when present.
- The closed network has no internet runtime dependency.

## Test And Fixture Parity

Upstream live-model trigger tests are represented by deterministic trigger metadata and prompt checks in `docs/superpowers-full-port/trigger-fixtures.json` and `scripts/assert-superpowers-full-port.py`.

## Unsupported Or Removed Behavior

- Browser visual companion is DEFER because Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, use DOM/CSS/text evidence and screenshot paths.
- Public marketplace metadata and update/install commands are REMOVE.
- Other-platform harnesses are REMOVE.
- Release and governance assets are REMOVE.

## Upstream Asset References

The following skill, hook, and test assets are directly represented by PORT, ADAPT, MERGE, DEFER, or REMOVE decisions:

- hooks/hooks-cursor.json
- hooks/hooks.json
- hooks/run-hook.cmd
- hooks/session-start
- skills/brainstorming/SKILL.md
- skills/brainstorming/scripts/frame-template.html
- skills/brainstorming/scripts/helper.js
- skills/brainstorming/scripts/server.cjs
- skills/brainstorming/scripts/start-server.sh
- skills/brainstorming/scripts/stop-server.sh
- skills/brainstorming/spec-document-reviewer-prompt.md
- skills/brainstorming/visual-companion.md
- skills/dispatching-parallel-agents/SKILL.md
- skills/executing-plans/SKILL.md
- skills/finishing-a-development-branch/SKILL.md
- skills/receiving-code-review/SKILL.md
- skills/requesting-code-review/SKILL.md
- skills/requesting-code-review/code-reviewer.md
- skills/subagent-driven-development/SKILL.md
- skills/subagent-driven-development/code-quality-reviewer-prompt.md
- skills/subagent-driven-development/implementer-prompt.md
- skills/subagent-driven-development/spec-reviewer-prompt.md
- skills/systematic-debugging/CREATION-LOG.md
- skills/systematic-debugging/SKILL.md
- skills/systematic-debugging/condition-based-waiting-example.ts
- skills/systematic-debugging/condition-based-waiting.md
- skills/systematic-debugging/defense-in-depth.md
- skills/systematic-debugging/find-polluter.sh
- skills/systematic-debugging/root-cause-tracing.md
- skills/systematic-debugging/test-academic.md
- skills/systematic-debugging/test-pressure-1.md
- skills/systematic-debugging/test-pressure-2.md
- skills/systematic-debugging/test-pressure-3.md
- skills/test-driven-development/SKILL.md
- skills/test-driven-development/testing-anti-patterns.md
- skills/using-git-worktrees/SKILL.md
- skills/using-superpowers/SKILL.md
- skills/using-superpowers/references/codex-tools.md
- skills/using-superpowers/references/copilot-tools.md
- skills/using-superpowers/references/gemini-tools.md
- skills/verification-before-completion/SKILL.md
- skills/writing-plans/SKILL.md
- skills/writing-plans/plan-document-reviewer-prompt.md
- skills/writing-skills/SKILL.md
- skills/writing-skills/anthropic-best-practices.md
- skills/writing-skills/examples/CLAUDE_MD_TESTING.md
- skills/writing-skills/graphviz-conventions.dot
- skills/writing-skills/persuasion-principles.md
- skills/writing-skills/render-graphs.js
- skills/writing-skills/testing-skills-with-subagents.md
- tests/brainstorm-server/package-lock.json
- tests/brainstorm-server/package.json
- tests/brainstorm-server/server.test.js
- tests/brainstorm-server/windows-lifecycle.test.sh
- tests/brainstorm-server/ws-protocol.test.js
- tests/claude-code/README.md
- tests/claude-code/analyze-token-usage.py
- tests/claude-code/run-skill-tests.sh
- tests/claude-code/test-document-review-system.sh
- tests/claude-code/test-helpers.sh
- tests/claude-code/test-requesting-code-review.sh
- tests/claude-code/test-subagent-driven-development-integration.sh
- tests/claude-code/test-subagent-driven-development.sh
- tests/claude-code/test-worktree-native-preference.sh
- tests/codex-plugin-sync/test-sync-to-codex-plugin.sh
- tests/explicit-skill-requests/prompts/action-oriented.txt
- tests/explicit-skill-requests/prompts/after-planning-flow.txt
- tests/explicit-skill-requests/prompts/claude-suggested-it.txt
- tests/explicit-skill-requests/prompts/i-know-what-sdd-means.txt
- tests/explicit-skill-requests/prompts/mid-conversation-execute-plan.txt
- tests/explicit-skill-requests/prompts/please-use-brainstorming.txt
- tests/explicit-skill-requests/prompts/skip-formalities.txt
- tests/explicit-skill-requests/prompts/subagent-driven-development-please.txt
- tests/explicit-skill-requests/prompts/use-systematic-debugging.txt
- tests/explicit-skill-requests/run-all.sh
- tests/explicit-skill-requests/run-claude-describes-sdd.sh
- tests/explicit-skill-requests/run-extended-multiturn-test.sh
- tests/explicit-skill-requests/run-haiku-test.sh
- tests/explicit-skill-requests/run-multiturn-test.sh
- tests/explicit-skill-requests/run-test.sh
- tests/opencode/run-tests.sh
- tests/opencode/setup.sh
- tests/opencode/test-bootstrap-caching.mjs
- tests/opencode/test-bootstrap-caching.sh
- tests/opencode/test-plugin-loading.sh
- tests/opencode/test-priority.sh
- tests/opencode/test-tools.sh
- tests/skill-triggering/prompts/dispatching-parallel-agents.txt
- tests/skill-triggering/prompts/executing-plans.txt
- tests/skill-triggering/prompts/requesting-code-review.txt
- tests/skill-triggering/prompts/systematic-debugging.txt
- tests/skill-triggering/prompts/test-driven-development.txt
- tests/skill-triggering/prompts/writing-plans.txt
- tests/skill-triggering/run-all.sh
- tests/skill-triggering/run-test.sh
- tests/subagent-driven-dev/go-fractals/design.md
- tests/subagent-driven-dev/go-fractals/plan.md
- tests/subagent-driven-dev/go-fractals/scaffold.sh
- tests/subagent-driven-dev/run-test.sh
- tests/subagent-driven-dev/svelte-todo/design.md
- tests/subagent-driven-dev/svelte-todo/plan.md
- tests/subagent-driven-dev/svelte-todo/scaffold.sh
