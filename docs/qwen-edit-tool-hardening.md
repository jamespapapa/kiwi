# Qwen Edit Tool Hardening

## Failure analyzed

Source logs:

- `/Users/jules/Downloads/0b5ad837-9012-461b-b29f-768c9756d06b.jsonl`
- `/Users/jules/Downloads/c8fde6f5-abde-4f83-b9bd-912fd6ea0544.jsonl`

The observed `drt-front-developer` failure was not a missing file or read failure. The agent read `D:/workspace/qwen/drt-front/dev/src/view/MainLocalView.vue`, successfully edited the `clickCobrowse` function block, then attempted to remove the `Cobrowse PoC` button with a reconstructed parent `<div class="btn-group">` block.

That block was no longer copied from the current file state. The edit tool compares `old_string` as a literal occurrence after line-ending normalization. Because the reconstructed block did not match exactly, Qwen Code returned `edit_no_occurrence_found`.

The later `c8fde...` log showed the same file-specific failure more precisely: current `MainLocalView.vue` had `<span>디지털 agent화면 </span>`, but the model reconstructed the unchanged neighbor line as `<span>디지털 agent 화면 </span>`. The intended deletion target was only the `clickCobrowse` button, but the stale neighbor context made the whole multi-line `old_string` miss.

The agent then repeated the same stale/larger `old_string` pattern after additional reads instead of copying a smaller exact current literal from the latest `read_file` result. Finally it used PowerShell regex plus `Set-Content -NoNewline` as a workaround. That corrupted Vue file newlines, caused a build failure, and forced a `git checkout` restore before retrying.

## Root cause

- Qwen3.5 can read the right file but still reconstruct `old_string` from memory or an inferred block.
- Qwen Code's edit tool does not treat `@file`/at-command prompt attachments as a `read_file` tool read. Even when the file content is visible in the user prompt, the first `edit` can fail with "has not been read in this session" unless the agent calls `read_file` in the current tool session.
- Existing DRT/CMS agent prompts did not have the stricter DCP-style stop rule for repeated edit failures.
- The implementer work order contract did not require an explicit edit recovery protocol.
- The Qwen edit tool's own no-occurrence error only said to verify with `read_file`; it did not forbid retrying the same/larger `old_string` or unsafe shell rewrite workarounds.

## Required behavior

- Read the target range immediately before every edit.
- Treat `@file` references and prompt-attached file content as context only; they do not satisfy the edit tool read gate. Call `read_file` for the exact target file/range in the current session before the first edit.
- Copy `old_string` only from the latest read_file output.
- Treat all old snippets for a file as stale after any successful edit to that file.
- For any N-line deletion or replacement, use the smallest exact current span that contains only the lines being removed/replaced; add neighboring context only when the changed span is not unique.
- If preserved boundary/context lines are included in `old_string`, copy them unchanged into `new_string`; otherwise exclude them from the span.
- On `edit_no_occurrence_found`, do not retry the same or a larger `old_string`; reread and retry once with a smaller exact literal.
- Stop after two failed edits on the same file or slice and return to Kiwi/debugger.
- Do not use PowerShell regex, `Set-Content`, sed/perl regex, or full-file shell rewrites as an edit-mismatch workaround for source files.

## Implemented controls

- All specialized developer agents now carry `Exact Edit Protocol`.
- Superpowers subagent-driven-development and kiwi-superpowers delegation templates now require the protocol in implementer work orders.
- Ultrawork/superpowers runtime policy and prompt template now include the protocol.
- Qwen runtime patching now strengthens the edit tool description, adds safe N-line span repair before `edit_no_occurrence_found`, and expands the raw error with `KIWI edit recovery protocol`.
- Offline bundle patching applies the same runtime error guidance to `app/cli.js` and chunk files.
- Runtime activation, specialized developer agents, and superpowers/ultrawork policies now explicitly warn that `@file` prompt context is not enough for edit; a real `read_file` call is required before editing.

## File path recovery hints (Korean file names)

### Failure analyzed

When a project contains Korean file names such as `파일-이름-읽기.md`, Qwen3.5 sometimes re-types the path in the `read_file`/`edit` call instead of copying it from prior tool output, inserting spaces around hyphens/underscores (`파일 - 이름 - 읽기.md`). The literal path no longer exists, the tool returns a bare `file_not_found`, and the model often retries variations or gives up instead of recovering the exact name.

### Implemented controls

- Runtime patch `_patch_file_path_recovery_hints` (mirrored in `scripts/build-offline-bundle.py` as `patch_file_path_recovery_hints`) extends the `read_file` ENOENT branch and the edit tool missing-file branch: each missing path segment is re-resolved against its parent directory with whitespace-stripped, NFC-normalized, case-insensitive matching. A single unique candidate produces `File not found. Did you mean: <path>` plus an llm-facing instruction to retry with exactly that path; ambiguous or unrelated misses keep the original error.
- The hint deliberately does not auto-redirect the read: the model must re-call the tool with the corrected path so its own tool history carries the right path for later `edit`/`write_file` calls.
- Prompt-side guard added everywhere tool rules live (activation contexts, tool cheatsheet, runtime policies, all developer agents): copy file paths character-for-character from prior tool output, never re-type Korean file names, never insert spaces around `-`/`_`, follow `Did you mean` hints verbatim, and read large files in offset/limit slices.
- `scripts/assert-edit-tool-hardening.py` runs the patched helper in Node against Korean fixture files (spaced hyphen, spaced directory, ambiguous candidates) and asserts backend/offline patch parity and idempotency.

## Console paste-enter guard bypass

### Failure analyzed

Qwen 0.17's InputPrompt enables `pasteWorkaround` on win32 and swallows the return key while `recentPasteTime` is set (re-armed on every paste event, cleared 500ms later). The KIWI command bar sends bracketed-paste text followed by a submit CR after an estimated delay; when ink processed a large paste slowly, the CR landed inside the guard window and was silently dropped, so text appeared in the composer but never submitted.

### Implemented controls

- Runtime patch `_patch_console_paste_guard` (mirrored as `patch_console_paste_guard`) makes the guard skip when `KIWI_ULTRAWORK_CONSOLE=1`, which KIWI always sets for console sessions. Inside the KIWI console every paste is bracketed, so a stray paste-trailing Enter cannot occur and the bypass is safe; standalone `qwen.cmd` sessions keep stock behavior.
- `ultrawork_console.py` detects the patched runtime via `QWEN_PASTE_GUARD_BYPASS_MARKER` in `app/cli.js` at session start and submits with a near-instant delay (`PASTE_SUBMIT_BYPASS_SECONDS`); unpatched runtimes keep the legacy estimated-delay fallback.
- `scripts/assert-edit-tool-hardening.py` asserts the patch applies to the runtime cli.js fixture, stays idempotent, matches between backend and offline bundler, and that the console marker constant stays in sync.

## Whitespace-tolerant edit span repair (v2)

### Failure analyzed

Closed-network session logs (2026-06-11, `dcp-front` superpowers_xlarge publishing run) show four `edit_no_occurrence_found` failures where `old_string` was copied from a fresh read but Qwen3.5 inserted single spaces at Korean word boundaries while re-typing: file `병명이 2개 이상인 통원(외래진료비)` became `병명이 2 개 이상인 통원 (외래진료비)`, file `MY삼성생명`/`개발자ID` became `MY 삼성생명`/`개발자 ID`. Two or three corrupted context lines inside a 50-77 line span made the whole literal match fail; the first delegated implementer burned three attempts and the slice had to be re-delegated. The same generation artifact produced 17 consecutive `read_file` misses on `슬라이드N.PNG` re-typed as `슬라이드 N.PNG`.

### Implemented controls

- `kiwiWhitespaceTolerantRepair` (injected next to `kiwiDeriveSafeEditSpan`, mirrored in the offline bundler) runs only after exact, normalized, line-based, and safe-span matching all fail. It collapses every whitespace run per line (`normalizeBasicCharacters` + `\s+` removal), slides the old_string line window over the file, and accepts only a single matching window whose exact text is also unique in the file; ambiguity or weak signals (< 8 collapsed chars) return null and keep the stock failure path.
- The repaired `old_string` is always the byte-exact file window. The repaired `new_string` is merged line-by-line: lines the model kept identical between old/new (preserved context, including its own spacing typos) are replaced by the file's actual lines, so the typo is never written into the file; lines the model intentionally changed are kept verbatim from new_string.
- `calculateEdit` wiring upgraded from v1 (`kiwiDeriveSafeEditSpan` only) to v2 with an in-place migration for runtimes already carrying v1; backend and bundler patchers stay byte-identical and idempotent.
- `scripts/assert-edit-tool-hardening.py` replays the real-log failure class in Node (typo context + real change, ambiguity refusal, weak-signal refusal, exact-match bypass) and asserts the v1→v2 migration produces the same output as a fresh patch. All four real-log failures replayed from the session transcripts recover via ws-repair with zero typo characters written.
