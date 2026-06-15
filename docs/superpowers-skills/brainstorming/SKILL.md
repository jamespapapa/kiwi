---
name: brainstorming
description: Use when creating or changing behavior, adding a feature, making a design choice, or exploring alternatives before implementation.
---

# Brainstorming

## When to use

Use this in superpowers mode before implementation when the user has an idea, a feature request, a broad modification, or a behavior change whose design is not already approved.

Do not use this in FAST/lightwork. FAST/lightwork must not receive superpowers design gates or skill text.

## Hard gate

HARD GATE: do not invoke an implementation skill, write code, scaffold files, dispatch implementation agents, or take implementation action until a design has been presented and the user approval is explicit.

Anti-pattern: "This is too simple to need a design." Simple changes still need a design; it may be short, but assumptions must be surfaced before code.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present; optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` may be read only if that central directory exists before asking design questions.
2. Inspect only the current files needed to understand the idea; use repository evidence over assumptions.
3. Decide whether the request is too large for one design. If it spans independent subsystems, propose decomposition first.
4. Ask one question at a time with `ask_user_question` when purpose, constraints, success criteria, data carrier, user workflow, or ownership is unclear. Multiple choice is preferred when practical.
5. Present 2-3 approaches, meaning two or three viable approaches, with tradeoffs and a recommendation.
6. Present the design in compact sections scaled to complexity: scope, user flow, data flow, ownership, failure handling, and verification.
7. Wait for user approval before implementation, planning, or delegation.
8. After approval, write the design doc to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` if appropriate or if the work is non-xsmall.
9. Run spec self-review: placeholders, contradictions, ambiguity, scope creep, missing acceptance criteria, and unclear verification.
10. Ask the user to review the written spec when the design was saved.
11. Route only to `writing-plans` after approval. Do not jump to implementation.

## Graph/render decision

Use graph or render artifacts only when they clarify an actual visual or branching design decision. Use markdown when the choice is textual. Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, screenshots or rendered diagrams are evidence for humans; Kiwi must also report DOM/CSS/text, labels, dimensions, or graph edge lists.

## Stop conditions

- Stop if the user has not approved the design.
- Stop if the request contains independent subsystems that need separate specs.
- Stop if central docs is stale enough to make ownership or architecture uncertain.
- Stop if a visual decision would rely on Qwen reading an image directly.
- Stop before code edits, file writes unrelated to approved docs, or implementation agents.

## Verification

- Confirm central docs was checked or explicitly unavailable.
- Confirm the accepted design names files, modules, data flow, and verification surface.
- Confirm there is no unresolved question that affects behavior or scope.
- Confirm spec self-review found no placeholders, ambiguity, or contradictions.
- Confirm the next skill is `writing-plans`, not implementation.

## Qwen tool mapping

- `skill`: load `using-superpowers`, then this skill, then `writing-plans` after approval.
- `read_file`: read central docs, existing docs, and target source files.
- `grep_search`: find current workflows, APIs, and similar implementations.
- `glob`: locate docs, specs, tests, and project entrypoints.
- `list_directory`: understand module layout before proposing design.
- `ask_user_question`: ask one blocking design question at a time.
- `write_file`: write approved design docs only after user approval.
- `todo_write`: track design steps and approval gates.
- `agent`: optional non-mutating reviewer or explorer for non-xsmall broad designs.
- `run_shell_command`: read-only discovery only.
- `edit`: not used for implementation during brainstorming.
