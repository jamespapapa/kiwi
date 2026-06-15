---
name: receiving-code-review
description: Use when code review findings, reviewer feedback, or tester findings need triage and follow-up fixes.
---

# Receiving Code Review

## When to use

Use this in superpowers mode after a reviewer, tester, or user returns findings on an implementation.

Do not use this in FAST/lightwork. FAST/lightwork handles direct feedback without importing superpowers review workflow text.

## Core rule

External feedback is a set of suggestions to evaluate, not orders to obey. Verify before implementing, ask before assuming, and use technical correctness over performative agreement.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` only if that central directory exists, and the reviewed files.
2. Read all feedback before reacting. Restate unclear requirements in technical terms or ask.
3. Triage every finding as Critical, High, Medium, Low, Question, or Out-of-scope.
4. Critical, High, and Medium findings block completion until fixed, proven false, or explicitly accepted by the user as residual risk.
5. For each finding, evaluate against codebase reality: current behavior, local patterns, compatibility, selected `task_size`, closed-network constraints, and user decisions.
6. Implement one at a time. Do not batch unrelated review fixes; run focused verification after each blocking fix when practical.
7. Use `systematic-debugging` if root cause is unclear.
8. Use `test-driven-development` if a regression assertion can protect the fix.
9. Push back when a suggestion breaks existing behavior, violates YAGNI, ignores compatibility, conflicts with user direction, or is technically incorrect for this stack. Use technical reasoning, file/line evidence, and tests, not defensiveness.
10. Avoid performative agreement and no gratitude language. When feedback is correct, state the fix or make the change; when your pushback was wrong, say what evidence changed your conclusion and fix it.
11. Ask the reviewer again when the fix changes architecture, public API, persistence, or shared files. Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, visual findings need DOM/CSS/text evidence and human confirmation points.

## Stop conditions

- Stop if a finding is ambiguous and changes behavior; ask the user or reviewer.
- Stop if you cannot explain why a finding is accepted or rejected.
- Stop if a proposed fix would exceed the original scope.
- Stop if verification fails after a fix.
- Stop if Critical, High, or Medium findings remain unresolved.

## Verification

- Maintain a finding-resolution table in the response or todos.
- Each blocking finding must have action taken and verification evidence.
- Rejected findings must include a technical reason and residual risk.
- Each accepted fix must be checked against the original implementation verification.
- Completion still requires `verification-before-completion`.

## Anti-patterns

- Blind implementation before verification.
- Partial implementation while other review items are unclear.
- Batch fixing without testing.
- Assuming reviewer context is complete.
- Avoiding pushback when the suggestion is wrong.
- Performative agreement, flattery, or thanks instead of technical action.

## Qwen tool mapping

- `skill`: load receiving-review, debugging, TDD, and verification skills as needed.
- `read_file`: read central docs, review notes, source, and tests.
- `grep_search`: locate affected symbols and previous fixes.
- `glob`: find relevant test and doc files.
- `list_directory`: confirm ownership boundaries.
- `todo_write`: track each finding and resolution status.
- `agent`: call reviewer, debugger, tester, or implementation agent for non-xsmall follow-up.
- `edit`: apply minimal accepted fixes when policy permits.
- `write_file`: update tests or docs for accepted findings.
- `run_shell_command`: run focused and broader verification.
- `ask_user_question`: resolve ambiguous tradeoffs.
