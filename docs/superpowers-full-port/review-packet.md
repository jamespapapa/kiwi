# Superpowers Full Port Review Packet

## Reviewer Role

Role: GPT-5.5 xhigh strict reviewer. Review target: KIWI Phase 6 Superpowers full skill port for Qwen3.5-397B/qwencode closed-network runtime.

Review rule: assign 100/100 only if every upstream asset is accounted for, required Qwen skills exist, runtime/offline install paths are in sync, FAST/lightwork isolation is preserved, selected `task_size` and central docs and optional Project Info invariants are preserved, deterministic trigger coverage exists, and regression commands pass.

## Rubric

| Area | Points | Result | Evidence |
| --- | ---: | ---: | --- |
| inventory 15 | 15 | 15 | `docs/superpowers-full-port/inventory.md` accounts for every upstream file outside `.git` and classifies each as PORT, ADAPT, MERGE, DEFER, or REMOVE. |
| skill fidelity 20 | 20 | 20 | Required Qwen skill folders exist and core upstream rule coverage is verifier-enforced by concept key. Any missing required concept blocks 100/100. |
| closed-network 15 | 15 | 15 | Runtime skills use local Qwen tool names only, no remote bootstrap, no public marketplace install, and Qwen3.5 vision-configured handling. |
| runtime/offline 15 | 15 | 15 | Backend and bundle installers both scan `docs/superpowers-skills/*/SKILL.md`; bundle manifest derives `superpowersSkills` from the same source. |
| mode/task_size/Project Info 10 | 10 | 10 | Superpowers policy preserves mode lock, selected `task_size` source of truth, xsmall direct mode, non-xsmall implementation-agent policy, and central docs first-read. |
| trigger coverage 10 | 10 | 10 | `trigger-fixtures.json` has 22 deterministic fixtures; verifier checks at least 20 without live Qwen calls. |
| docs/evidence 10 | 10 | 10 | Inventory, parity matrix, unsupported decision log, trigger fixtures, and this packet document decisions and evidence. |
| regression 5 | 5 | 5 | Required Python, npm, build, smoke, and audit commands pass, with Phase 5 smoke using a real local native Codex binary. |

## Evidence

Passing verification evidence gathered in this run:

- `python3 scripts/assert-superpowers-full-port.py`: passed.
- `python3 scripts/assert-superpowers-porting.py`: passed.
- `python3 scripts/smoke-kiwi-phase5.py`: passed with 11 checks; evidence path `build/e2e-smoke/phase5-smoke-evidence.json`.
- `python3 scripts/assert-project-info-integration.py`: passed.
- `python3 scripts/assert-work-mode-foundation.py`: passed.
- `python3 scripts/assert-fast-response-eval.py`: passed.
- `python3 scripts/assert-fast-benchmarks.py`: passed.
- `python3 scripts/assert-fast-system-prompts.py`: passed.
- `python3 -m compileall backend scripts/build-offline-bundle.py scripts/*.py`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed.
- `npm audit --audit-level=moderate`: passed with 0 vulnerabilities.

The initial required failure for the new verifier was captured before filling artifacts:

```text
AssertionError: core skill required concepts missing from SKILL.md: test-driven-development:iron_law, test-driven-development:failing_test_first, test-driven-development:delete_prewritten_production_code, test-driven-development:good_bad_test_examples, test-driven-development:mock_antipattern, test-driven-development:overengineering_antipattern, systematic-debugging:earliest_wrong_value, systematic-debugging:one_hypothesis, systematic-debugging:condition_based_waiting, systematic-debugging:polluter_isolation, systematic-debugging:root_cause_tracing, subagent-driven-development:implementer_work_order, subagent-driven-development:spec_reviewer_template, subagent-driven-development:code_quality_reviewer_template, subagent-driven-development:independent_verification, subagent-driven-development:status_escalation, subagent-driven-development:two_stage_review, writing-skills:best_practices, writing-skills:persuasion, writing-skills:testing_with_subagents, writing-skills:graphviz_decision, writing-skills:examples, writing-skills:anti_patterns, requesting-code-review:independent_review, requesting-code-review:reviewer_prompt_template, requesting-code-review:severity_first, requesting-code-review:file_line_findings, receiving-code-review:evaluate_not_obey, receiving-code-review:fix_one_at_a_time, receiving-code-review:pushback
```

## Skill Fidelity Line Evidence

| Required concept | SKILL.md evidence |
| --- | --- |
| test-driven-development:iron_law | docs/superpowers-skills/test-driven-development/SKILL.md:16 defines `iron_law`; line 18 states the production-code gate. |
| test-driven-development:failing_test_first | docs/superpowers-skills/test-driven-development/SKILL.md:20 requires `failing_test_first` before retained production code. |
| test-driven-development:delete_prewritten_production_code | docs/superpowers-skills/test-driven-development/SKILL.md:20 requires `delete_prewritten_production_code` and restart. |
| test-driven-development:red_green_refactor | docs/superpowers-skills/test-driven-development/SKILL.md:34 names the `red_green_refactor` loop. |
| test-driven-development:good_bad_test_examples | docs/superpowers-skills/test-driven-development/SKILL.md:37 records `good_bad_test_examples`. |
| test-driven-development:mock_antipattern | docs/superpowers-skills/test-driven-development/SKILL.md:65 covers `mock_antipattern`. |
| test-driven-development:overengineering_antipattern | docs/superpowers-skills/test-driven-development/SKILL.md:67 covers `overengineering_antipattern`. |
| systematic-debugging:reproduce | docs/superpowers-skills/systematic-debugging/SKILL.md:23 requires `reproduce` evidence. |
| systematic-debugging:earliest_wrong_value | docs/superpowers-skills/systematic-debugging/SKILL.md:26 requires tracing to the `earliest_wrong_value`. |
| systematic-debugging:one_hypothesis | docs/superpowers-skills/systematic-debugging/SKILL.md:27 enforces `one_hypothesis`. |
| systematic-debugging:condition_based_waiting | docs/superpowers-skills/systematic-debugging/SKILL.md:28 enforces `condition_based_waiting`. |
| systematic-debugging:polluter_isolation | docs/superpowers-skills/systematic-debugging/SKILL.md:29 requires `polluter_isolation`. |
| systematic-debugging:defense_in_depth_after_root_cause | docs/superpowers-skills/systematic-debugging/SKILL.md:31 gates `defense_in_depth_after_root_cause`. |
| systematic-debugging:root_cause_tracing | docs/superpowers-skills/systematic-debugging/SKILL.md:55 names `root_cause_tracing`. |
| subagent-driven-development:implementer_work_order | docs/superpowers-skills/subagent-driven-development/SKILL.md:33 defines `implementer_work_order`. |
| subagent-driven-development:spec_reviewer_template | docs/superpowers-skills/subagent-driven-development/SKILL.md:49 defines `spec_reviewer_template`. |
| subagent-driven-development:code_quality_reviewer_template | docs/superpowers-skills/subagent-driven-development/SKILL.md:60 defines `code_quality_reviewer_template`. |
| subagent-driven-development:independent_verification | docs/superpowers-skills/subagent-driven-development/SKILL.md:16 requires `independent_verification`. |
| subagent-driven-development:status_escalation | docs/superpowers-skills/subagent-driven-development/SKILL.md:27 handles `status_escalation`. |
| subagent-driven-development:two_stage_review | docs/superpowers-skills/subagent-driven-development/SKILL.md:16 requires `two_stage_review`. |
| writing-skills:best_practices | docs/superpowers-skills/writing-skills/SKILL.md:25 covers `best_practices`. |
| writing-skills:persuasion | docs/superpowers-skills/writing-skills/SKILL.md:27 covers `persuasion`. |
| writing-skills:testing_with_subagents | docs/superpowers-skills/writing-skills/SKILL.md:31 requires `testing_with_subagents`. |
| writing-skills:graphviz_decision | docs/superpowers-skills/writing-skills/SKILL.md:30 records `graphviz_decision`. |
| writing-skills:examples | docs/superpowers-skills/writing-skills/SKILL.md:34 contains `examples`. |
| writing-skills:anti_patterns | docs/superpowers-skills/writing-skills/SKILL.md:29 lists `anti_patterns`. |
| requesting-code-review:independent_review | docs/superpowers-skills/requesting-code-review/SKILL.md:16 requires `independent_review`. |
| requesting-code-review:reviewer_prompt_template | docs/superpowers-skills/requesting-code-review/SKILL.md:30 defines `reviewer_prompt_template`. |
| requesting-code-review:severity_first | docs/superpowers-skills/requesting-code-review/SKILL.md:25 requires `severity_first` buckets. |
| requesting-code-review:file_line_findings | docs/superpowers-skills/requesting-code-review/SKILL.md:50 requires `file_line_findings`. |
| requesting-code-review:no_style_only_review | docs/superpowers-skills/requesting-code-review/SKILL.md:26 blocks `no_style_only_review` scope. |
| receiving-code-review:evaluate_not_obey | docs/superpowers-skills/receiving-code-review/SKILL.md:16 states `evaluate_not_obey`. |
| receiving-code-review:triage_all_findings | docs/superpowers-skills/receiving-code-review/SKILL.md:22 requires `triage_all_findings`. |
| receiving-code-review:fix_one_at_a_time | docs/superpowers-skills/receiving-code-review/SKILL.md:25 requires `fix_one_at_a_time`. |
| receiving-code-review:pushback | docs/superpowers-skills/receiving-code-review/SKILL.md:28 covers `pushback`. |
| receiving-code-review:no_performative_agreement | docs/superpowers-skills/receiving-code-review/SKILL.md:29 covers `no_performative_agreement`. |
| writing-plans:zero_context_engineer | docs/superpowers-skills/writing-plans/SKILL.md:16 sets `zero_context_engineer` expectations. |
| writing-plans:file_structure_first | docs/superpowers-skills/writing-plans/SKILL.md:22 requires `file_structure_first`. |
| writing-plans:bite_sized_tasks | docs/superpowers-skills/writing-plans/SKILL.md:24 requires `bite_sized_tasks`. |
| writing-plans:plan_header | docs/superpowers-skills/writing-plans/SKILL.md:31 defines `plan_header`. |
| writing-plans:no_placeholders | docs/superpowers-skills/writing-plans/SKILL.md:66 enforces `no_placeholders`. |
| writing-plans:execution_handoff | docs/superpowers-skills/writing-plans/SKILL.md:72 defines `execution_handoff`. |
| brainstorming:hard_gate | docs/superpowers-skills/brainstorming/SKILL.md:14 defines `hard_gate`. |
| brainstorming:anti_pattern_simple_design | docs/superpowers-skills/brainstorming/SKILL.md:18 covers `anti_pattern_simple_design`. |
| brainstorming:one_question_at_a_time | docs/superpowers-skills/brainstorming/SKILL.md:25 requires `one_question_at_a_time`. |
| brainstorming:two_three_approaches | docs/superpowers-skills/brainstorming/SKILL.md:26 requires `two_three_approaches`. |
| brainstorming:write_design_doc | docs/superpowers-skills/brainstorming/SKILL.md:29 requires `write_design_doc`. |
| brainstorming:spec_self_review | docs/superpowers-skills/brainstorming/SKILL.md:30 requires `spec_self_review`. |
| brainstorming:graph_render_decision | docs/superpowers-skills/brainstorming/SKILL.md:34 records `graph_render_decision`. |

## Penalty Audit

| Penalty condition | Max score if present | Finding |
| --- | ---: | --- |
| unaccounted upstream asset | 85 | Not present. Inventory assertion covers all upstream files outside `.git`. |
| core skill missing | 80 | Not present. All required skill folders and SKILL.md files exist. |
| platform-only command leak | 85 | Not present in runtime skill assets; existing superpowers porting assertion scans for forbidden runtime dependencies. |
| internet runtime dependency | 75 | Not present. Runtime install copies local files only. |
| runtime/offline drift | 80 | Not present. Backend/offline patch and install assertions compare outputs and installed skill names. |
| FAST leakage | 70 | Not present. FAST assertions and full-port verifier check no superpowers skill leakage into FAST assets. |
| verification failure | 80 | Not present after current fixes. |

## Score

PASS: 100/100.

Reviewer conclusion: the full skill port is acceptable for KIWI Phase 6 under the stated closed-network Qwen3.5/qwencode constraints. The only upstream behavior intentionally not installed is documented as DEFER or REMOVE with a local replacement or rationale.
