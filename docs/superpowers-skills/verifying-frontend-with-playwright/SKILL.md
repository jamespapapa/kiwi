---
name: verifying-frontend-with-playwright
description: Use after any front-end implementation slice with visible UI impact, before claiming the change works, to capture the real browser with the bundled Playwright runtime and verify the rendered result.
---

# Verifying Frontend With Playwright

## When to use

Use this in `superpowers` mode whenever an implementation slice changes visible UI: routes, views, components, modals, layout, CSS/DOM, grids, or any screen the user can see. Front-end implementation is not complete until the rendered screen has been captured and verified, or the capture was attempted and the blocker was reported.

Front-end projects in scope: `dcp-front` (Vue 2), `drt-front` (Vue 3/Vite, app dir `dev/`), `drt-cms` frontend (`frontend/`), and any other project with a local web dev server.

Do not use this in FAST/lightwork. FAST/lightwork keeps its own direct focused verification and must not import superpowers skill content.

## Steps

1. Identify the changed screen: route path, entry view/component, and what should now be visible. Write the expected result in one sentence before capturing.
2. Resolve the local dev server URL from current files, not from memory: the dev script in `package.json`, `vue.config.js` (dcp-front), `vite.config.ts` (drt-front under `dev/`), or `quasar.config`/`vite.config` (drt-cms under `frontend/`). Combine host, port, base path, and the changed route into one URL.
3. Check the dev server is reachable with `run_shell_command`: `powershell -NoProfile -Command "(Invoke-WebRequest -UseBasicParsing -Uri '<dev-server-url>').StatusCode"`. If it is not running, do not start a long-lived server from this session; ask the user (or Kiwi) to start it through the KIWI runtime action panel, then continue once reachable.
4. Create the evidence directory once: `<project-root>\.qwen\screenshots\`.
5. Resolve the local Playwright launcher, then capture the real browser via `run_shell_command`:
   - Prefer the project-local binary when the repo ships one: `<app-dir>\node_modules\.bin\playwright.cmd` (or the repo's own harness, for example `dcp-front` `tools/playwright`).
   - Otherwise use the bundled runtime launcher `D:\aiops\qwencode\runtimes\node\playwright.cmd` when present.
   - Capture command: `<playwright-launcher> screenshot --viewport-size=1440,900 --full-page "<dev-server-url-with-route>" "<project-root>\.qwen\screenshots\<slice-name>.png"`.
   - For mobile-channel screens, capture a second shot with `--viewport-size=390,844`. Add `--wait-for-timeout=3000` when the screen loads data asynchronously.
6. Read the captured PNG with `read_file` using the exact absolute path. Qwen3.5 image input is enabled through provider modalities, so the screenshot becomes visual evidence in this session.
7. Verify against the expected result from step 1: the requested change is visible; layout/grid/typography around it is intact; no overlap, clipping, missing asset, or blank screen; no obvious error page. State pass or fail explicitly.
8. If the rendered result is wrong, do not claim completion. Route the failure to `systematic-debugging`, fix through the selected implementation agent, then re-capture and re-verify.
9. Report evidence: screenshot absolute path(s), the URL captured, expected vs observed in one or two sentences, and pass/fail. Keep central docs context in mind: screen and flow knowledge lives under `D:/aiops/docs/<project-key>/knowledge` when present, and verification guidance may exist under `D:/aiops/docs/<project-key>/project-info` (optional Project Info Layer, only if that central directory exists).

## Stop conditions

- Stop and report if the dev server cannot be made reachable; the visual check stays pending and the slice is not complete.
- Stop and report if no Playwright launcher or browser binaries exist. Never run `playwright install` or any other network install in the closed network; report the bundle gap (and the KIWI runtime check Playwright item) instead.
- Stop if the captured screen cannot be matched to the changed route (wrong app, login wall, system block page); resolve the route or report the blocker.
- Stop if the session is FAST/lightwork or the change has no visible UI impact; say so instead of capturing meaningless screenshots.

## Verification

- A pass claim must name the screenshot path, the captured URL, and the observed rendering that matches the expected result.
- If the serving adapter rejects image media, fall back without blocking: report the screenshot path plus DOM/CSS/text evidence (grep the rendered template/style and the changed component) and mark the visual check as pending human review.
- Evidence must be fresh: re-capture after every fix loop; an old screenshot does not prove the current code.
- Combine with `verification-before-completion` before the final completion claim.

## Qwen tool mapping

- `read_file`: read the captured PNG (image input), plus `package.json`/`vue.config.js`/`vite.config.ts` to resolve the dev server URL.
- `grep_search`: locate the changed route/view/component and base path or port settings.
- `glob`: find config files and previous screenshots under `.qwen/screenshots`.
- `list_directory`: confirm the screenshot file was written.
- `run_shell_command`: reachability check, screenshot directory creation, and the Playwright capture command.
- `todo_write`: track capture -> read -> verify as explicit steps in the plan.
- `agent`: send fix slices back to the selected implementation agent when the rendering is wrong.
- `ask_user_question`: ask the user to start the dev server through the KIWI runtime action, or to confirm visual intent when the expected rendering is ambiguous.
- `skill`: load `systematic-debugging` on rendering failures and `verification-before-completion` before the final claim.
