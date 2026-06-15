---
name: writing-skills
description: Use when creating, editing, or verifying local Qwen skill documents for KIWI or another closed-network coding workflow.
---

# Writing Skills

## When to use

Use this in superpowers mode when adding or changing local Qwen skills, trigger metadata, or skill verification fixtures.

Do not use this in FAST/lightwork. FAST/lightwork must not receive superpowers skill-authoring content.

## Core rule

Writing skills is TDD for process documentation. No skill without a failing test first: create a pressure scenario or deterministic assertion, observe the baseline failure, then write the minimal SKILL.md that prevents that failure.

Closed-network KIWI skills must be concise, searchable, progressively disclosed, and executable with Qwen tool names only.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` only if that central directory exists, and existing skill directories.
2. Define the exact behavior the skill should trigger and the failure or anti-pattern it should prevent.
3. Write deterministic trigger fixtures or pressure scenarios before or alongside the skill. For discipline skills, include time, sunk cost, authority, or convenience pressure.
4. Apply best-practices for concise trigger design: the frontmatter description says when to use the skill, not the whole workflow; include concrete symptoms, keywords, and context.
5. Use progressive disclosure: keep SKILL.md focused on rules, steps, stop conditions, verification, and Qwen tool mapping; move heavy references or reusable scripts to separate local files only when needed.
6. Use persuasion only for user-serving discipline: clear authority language, commitment through `todo_write`, specific and actionable anti-rationalization counters, and no vague encouragement.
7. Include examples when they clarify behavior. Prefer one good example and one bad example over many weak examples.
8. Include anti-patterns: vague trigger, long undifferentiated narrative, remote bootstrap, platform-only commands, too many examples, graph code used where markdown is clearer, or rules without verification.
9. Decide graph/render format deliberately. Use graphviz only for non-obvious branching or loops; use markdown tables/lists for reference material. If rendering is needed, keep it local and record file paths because Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, use DOM/CSS/text evidence and screenshot paths.
10. Verify with testing with subagents when the skill controls judgment: run a baseline without the skill, then a pressure run with the skill, and record whether subagent skill testing shows the agent follows the rule.
11. Update inventory, parity matrix, and review evidence when the skill ports upstream behavior.

## Good and bad authoring examples

Good example: concise trigger plus executable guardrail.

```yaml
description: Use when tests are flaky, order-dependent, or race-prone.
```

Bad example: workflow summary that invites shortcutting.

```yaml
description: Use to debug by reproducing, tracing, hypothesizing, fixing, and verifying.
```

Good SKILL.md structure: `When to use`, `Steps`, `Stop conditions`, `Verification`, `Qwen tool mapping`, plus a small example if it prevents a real anti-pattern.

Bad SKILL.md structure: a long story about a past session, generic advice, no trigger fixture, and no command that proves compliance.

## Stop conditions

- Stop if the skill trigger is vague or overlaps an existing skill without priority rules.
- Stop if no failing assertion, pressure scenario, or subagent skill testing plan exists.
- Stop if the body contains remote bootstrap, external dependency, or non-Qwen tool names.
- Stop if the skill leaks into FAST/lightwork assets.
- Stop if graphviz/render output would be treated as machine-read visual proof; use text evidence and human review instead.

## Verification

- Run the local assertion script that checks skill structure, forbidden text, and required concepts.
- Confirm every skill has required sections and Qwen tool mapping.
- Confirm trigger fixtures cover positive and negative cases.
- Confirm backend/offline installer discovers the folder automatically.
- Confirm subagent skill testing or deterministic assertions cover the anti-pattern the skill is meant to prevent.

## Qwen tool mapping

- `skill`: load this and the skill being edited.
- `read_file`: read central docs, existing skills, docs, and assertions.
- `grep_search`: find trigger wording, forbidden terms, required concepts, and installer references.
- `glob`: list skill folders and fixture files.
- `list_directory`: inspect local skill structure.
- `edit`: update existing skill and assertion files.
- `write_file`: create new skill folders or fixture docs when policy permits.
- `run_shell_command`: run deterministic assertions and local render checks.
- `todo_write`: track authoring and verification steps.
- `agent`: use reviewer or tester for non-xsmall independent checks and subagent skill testing.
- `ask_user_question`: resolve unclear trigger or scope decisions.
