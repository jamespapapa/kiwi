---
name: requesting-code-review
description: Use after implementation or plan execution when the diff needs independent review before completion.
---

# Requesting Code Review

## When to use

Use this in superpowers mode after code changes, before branch finishing, between subagent implementation slices, or whenever the user asks for review.

Do not use this in FAST/lightwork. FAST/lightwork does not load superpowers reviewer prompts.

## Core rule

Request independent review with a fresh reviewer, enough context to verify the work, and a severity-first output format. A review without file/line evidence is not sufficient for completion.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` only if that central directory exists, and the relevant implementation context.
2. Gather diff and changed file list with read-only commands.
3. Summarize the request, intended behavior, requirements/plan, touched files, verification already run, and known risks.
4. For non-xsmall work, call `agent` with `reviewer-35` and a self-contained reviewer prompt. For xsmall work, still use the same checklist yourself unless the user only asked for a quick direct answer.
5. Ask the reviewer to prioritize correctness, regressions, missing tests, security, data flow, requirement gaps, and closed-network/runtime constraints.
6. Require severity buckets: Critical, High, Medium, Low. Critical/High/Medium findings block a 100/100 review packet until resolved or technically rejected with evidence.
7. Do not ask for style-only review unless style affects behavior, maintainability, or consistency with a local pattern.
8. When review returns, route findings to `receiving-code-review`.
9. For visual changes, state that Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, ask reviewer to use DOM/CSS/text and screenshot-path evidence.

## Review request template

```text
REVIEW REQUEST TEMPLATE
Role: reviewer-35 independent code reviewer.
Objective: <what was intended>
Requirements or plan: <source text or file path>
Changed files: <paths>
Diff range or status: <base/head or git diff command output summary>
Verification already run: <commands and results>
Known risks: <uncertainties>
Closed-network constraints: no external fetch; Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, use DOM/CSS/text evidence and screenshot paths.

Review priorities:
1. Correctness and regressions
2. Requirement/spec compliance
3. Missing tests or weak tests
4. Security, data flow, persistence, and runtime/offline impact
5. Maintainability and local pattern fit

Return Critical, High, Medium, and Low findings. Each finding must include file/line evidence, why it matters, and a concrete fix.
```

## Stop conditions

- Stop if there is no diff or implementation result to review.
- Stop if verification evidence is missing and should be run first.
- Stop if reviewer scope is too broad or lacks changed files.
- Stop before completion if Critical, High, or Medium findings are unresolved.
- Stop if an internet dependency, marketplace command, or non-Qwen tool is required.

## Verification

- Confirm the reviewer prompt includes objective, files, constraints, verification, and expected output.
- Confirm all findings are classified by severity.
- Confirm each actionable finding has file/line evidence.
- Confirm the response is acted on or explicitly rejected with technical reason.
- Confirm a fresh verification pass follows fixes.

## Qwen tool mapping

- `skill`: load review and receiving-review skills.
- `read_file`: read central docs, changed files, and review context.
- `grep_search`: locate affected symbols and test coverage.
- `glob`: list changed or related files when needed.
- `list_directory`: verify module boundaries.
- `run_shell_command`: run read-only diff/status and verification.
- `agent`: dispatch `reviewer-35` or tester for non-xsmall review.
- `todo_write`: track findings and resolutions.
- `edit`: only for policy-allowed fixes after findings.
- `write_file`: update docs or tests after accepted findings.
- `ask_user_question`: ask when accepting a tradeoff requires user judgment.
