---
name: test-driven-development
description: Use when adding behavior, fixing a regression, changing outputs, or making code changes that can be protected by a focused failing test or assertion.
---

# Test Driven Development

## When to use

Use this in superpowers mode before behavior-changing implementation when a test, assertion, fixture, smoke check, or deterministic verifier can prove the requested behavior.

Do not use this in FAST/lightwork. FAST/lightwork may run focused checks, but it must not import this superpowers workflow.

Exceptions are narrow and must be stated before edits: throwaway prototypes, generated code, pure config changes, or a repository with no practical executable check. Even then, record the fallback verification.

## Iron Law

NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.

If production code was written before a failing test first, delete prewritten production code and start over. Do not keep it as reference, do not adapt it while writing tests, and do not look at it to reverse-fit assertions. Delete it, prove the behavior with a red check, then implement fresh.

Violating the letter of this rule is violating the spirit of the rule. A test that passes immediately is not RED; it is unproven coverage.

## Steps

1. Read central docs at `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present, then optional Project Info Layer summaries under `D:/aiops/docs/<project-key>/project-info` only if that central directory exists, and current files before choosing the test surface.
2. Define the behavior in one sentence and identify the smallest check that should fail now.
3. Write or update the failing test/assertion first. Use real behavior, clear names, and one behavior per test.
4. Run only the focused command and confirm it fails for the expected reason: feature missing, bug reproduced, or assertion not yet satisfied.
5. If the test passes immediately or fails for setup/typo reasons, fix the test until the RED result is meaningful.
6. Implement the minimum production change needed for GREEN. No extra options, no broad refactor, no unrelated cleanup.
7. Run the focused command again and confirm it passes.
8. Run the broader relevant verification from central docs or repository scripts.
9. Refactor only after green verification, then re-run the same checks. This is the red-green-refactor loop.
10. If a visual behavior is involved, remember Qwen3.5 image input is enabled through provider modalities. If the serving adapter rejects image media, assert DOM/CSS/text state and record screenshot paths for human review.

## Good and bad test examples

Good test: tests real behavior and makes the desired API obvious.

```ts
test("retries a failing operation three times before succeeding", async () => {
  let attempts = 0;
  const result = await retryOperation(async () => {
    attempts += 1;
    if (attempts < 3) throw new Error("not yet");
    return "ok";
  });

  expect(result).toBe("ok");
  expect(attempts).toBe(3);
});
```

Bad test: vague name and tests mock behavior instead of product behavior.

```ts
test("retry works", async () => {
  const operation = vi.fn().mockResolvedValue("ok");
  await retryOperation(operation);
  expect(operation).toHaveBeenCalled();
});
```

The mock anti-pattern is asserting that a mock exists, that a mock was called, or that a partial fake behaved as scripted while the real code path stays untested. Over-mocking makes tests mock setup instead of user-visible behavior. Mock only unavoidable slow or external boundaries, and preserve side effects the behavior depends on.

The over-engineering anti-pattern is adding unused options, abstractions, retries, settings, or callbacks just because they might be useful. YAGNI: write only what the red test demands.

## Stop conditions

- Stop if no practical failing check exists and state the fallback verification before editing.
- Stop if the first failure is unrelated to the intended behavior.
- Stop if production code already exists without RED evidence; delete prewritten production code before continuing.
- Stop if a dependency must be fetched from outside the closed network.
- Stop if implementation requires changing broad behavior not covered by the check.
- Stop if the only test available would verify mocks, implementation details, or test-only methods.

## Verification

- Evidence must include RED result, GREEN result, and any broader verification.
- The RED failure must prove the test is meaningful, not just broken setup.
- The GREEN result must be fresh after the production change.
- Tests must exercise real code; mocks are allowed only for unavoidable external boundaries.
- Before completion, combine this with `verification-before-completion`.

## Red flags

- "I will write tests after."
- "It is too simple to test."
- "Manual testing is enough."
- "The test passes already."
- "Keep the implementation as a reference."
- "This case is different."
- "Add a flexible framework now."

All of these mean stop and return to RED.

## Qwen tool mapping

- `skill`: load this skill before implementation and verification skill before completion.
- `read_file`: read central docs, test files, and target source.
- `grep_search`: find existing tests, assertions, fixtures, and behavior names.
- `glob`: locate test directories and verifier scripts.
- `list_directory`: inspect test layout.
- `edit`: update tests and production code when policy permits.
- `write_file`: create new focused test files when needed.
- `run_shell_command`: run red, green, and broader commands.
- `todo_write`: track red-green-refactor stages.
- `agent`: delegate non-xsmall test/implementation slices to selected agents.
- `ask_user_question`: ask when expected behavior is ambiguous.
