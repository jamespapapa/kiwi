# Windows qwencode Validation

This checklist validates KIWI Phase 5 on the closed-network Windows 11 target where real Qwen3.5/qwencode is available. Mac smoke tests prove the HTTP flow and shims; this procedure proves the actual `D:\aiops\qwencode` runtime, hooks, Project Info, and offline bundle.

## Preconditions

- Windows 11 closed-network workstation.
- Python 3.13.5 available as `py -3.13`.
- Node/npm available from `D:\aiops\qwencode\runtimes\node`.
- KIWI offline bundle copied to the target:
  - `qwencode-win11-v0.17.1.zip`
  - `qwencode-win11-v0.17.1.zip.sha256`
  - `kiwi-offline-win11-py313.zip`
  - `kiwi-offline-win11-py313.zip.sha256`
- Qwen Code runtime installed at `D:\aiops\qwencode`.
- A writable validation project outside KIWI, for example `D:\aiops\validation\phase5-fixture`.

## Offline Bundle Verification

1. Verify the SHA256:

   ```powershell
   Get-FileHash .\kiwi-offline-win11-py313.zip -Algorithm SHA256
   Get-Content .\kiwi-offline-win11-py313.zip.sha256
   ```

2. Expand both bundles under `D:\aiops` and run:

   ```powershell
   cd /d D:\aiops\qwencode
   .\install-path.cmd

   cd /d D:\aiops\kiwi
   .\install-offline.cmd
   .\verify-offline.cmd
   ```

3. Confirm the standalone qwencode runtime keeps fixed Samsung Life values:

   ```powershell
   Get-Content D:\aiops\qwencode\config\env.cmd
   Get-Content D:\aiops\qwencode\templates\project\.qwen\env.cmd
   Get-Content D:\aiops\qwencode\bundle-manifest.json
   ```

   Expected values include:

   - Orchestrator API: `https://api.t.drt.samsunglife.kr/llmproxy/v1`
   - Orchestrator model: `Qwen3.5-397B`
   - Coder API: `https://vllm-qwen3-coder-next-svc-route-vllm-direct.apps.wca.samsunglife.kr/v1`
   - Coder model: `qwen3-coder-next`
   - `NODE_OPTIONS=--max-old-space-size=8192`
   - `modalities.image=true`
   - `splitToolMedia=true`

## qwen-init and qwen.cmd

1. Confirm runtime files:

   ```powershell
   Test-Path D:\aiops\qwencode\qwen-init.cmd
   Test-Path D:\aiops\qwencode\run-qwen.cmd
   Test-Path D:\aiops\qwencode\app\cli.js
   Test-Path D:\aiops\qwencode\portable-user\.qwen\skills\kiwi-superpowers\SKILL.md
   Test-Path D:\aiops\qwencode\portable-user\.qwen\skills\using-superpowers\SKILL.md
   Test-Path D:\aiops\qwencode\templates\project\.qwen\agents\dcp-backend-developer.md
   ```

2. Create or choose the validation project, then initialize:

   ```powershell
   D:\aiops\qwencode\qwen-init.cmd D:\aiops\validation\phase5-fixture
   ```

3. Confirm project harness:

   ```powershell
   Test-Path D:\aiops\validation\phase5-fixture\qwen.cmd
   Test-Path D:\aiops\validation\phase5-fixture\qwen-init.cmd
   Test-Path D:\aiops\validation\phase5-fixture\.qwen\env.cmd
   Test-Path D:\aiops\validation\phase5-fixture\.qwen\settings.json
   Test-Path D:\aiops\validation\phase5-fixture\QWEN.md
   ```

4. Inspect `qwen.cmd` and verify it resolves to `D:\aiops\qwencode\run-qwen.cmd`.

## KIWI Startup

1. Start KIWI:

   ```powershell
   .\start-kiwi.cmd
   ```

2. In the web UI, run diagnostics:

   - `메인 테스트` must succeed for Qwen3.5 endpoint/model/auth/TLS.
   - `코더 테스트` must succeed for qwen3-coder-next endpoint/model/auth/TLS.

3. Initialize the validation project from KIWI. Confirm:

   - `KIWI.md` exists.
   - `docs/architecture.md` exists.
   - Project Info status is `ready`, `missing`, `invalid`, or `stale` with an explicit action message.
   - If Project Info is missing or stale and this validation requires it, run the Project Info refresh action and then confirm:
     - `D:/aiops/docs/<project-key>/project-info/project-info.json` exists.
     - `D:/aiops/docs/<project-key>/project-info/project-summary.md` exists.

## Work Mode Hook Validation

Run each mode in a fresh console session. Do not switch modes inside one session.

### lightwork / FAST

1. Select FAST/lightwork.
2. Send:

   ```text
   문구 한 줄을 수정하지 말고 현재 프로젝트 구조만 짧게 요약해줘.
   ```

3. Expected:

   - Console receives a `lightwork` activation prefix.
   - Kiwi works directly without subagent delegation.
   - Central docs path appears as `D:/aiops/docs/<project-key>/knowledge/00-index.md` when present.
   - Sending `ultrawork` or `superpowers` as a later prefix in the same session is blocked with 409 or an equivalent clear UI error.

### ultrawork

1. Start a new console and select `medium` task size.
2. Send an ultrawork Prompt Builder prompt.
3. Expected:

   - Backend rejects Prompt Builder or console initial prompts if selected task size is missing.
   - Final prompt includes `## 티셔츠 사이징`.
   - `사용자 선택: medium` remains the source of truth.
   - `medium` maps to balanced execution.
   - Agent Timeline shows readable `PreToolUse` and result events with subagent type, description, prompt, command, or target details.

### superpowers

1. Start a new console and select `medium` task size.
2. Send a superpowers Prompt Builder prompt.
3. Expected:

   - Final prompt includes the superpowers skill-first contract.
   - Built-in `skill` tool is invoked first with `skill="kiwi-superpowers"`, then `skill="using-superpowers"`.
   - `tool_search select:kiwi-superpowers` is not required and is not the success criterion; `tool_search` searches tools, not `.qwen/skills`.
   - If the `skill` tool reports unavailable/unknown skill, Kiwi reports extension installation gap and falls back to local SKILL.md or `SUPERPOWERS_POLICY.md`.
   - Delegated agent work only starts after skill-driven impact map and validation plan.

## team-events.jsonl

After ultrawork or superpowers execution, inspect:

```powershell
Get-Content D:\aiops\qwencode\portable-runtime\team-events.jsonl -Tail 80
```

Confirm events include:

- `PreToolUse`
- `PostToolUse` or `PostToolUseFailure`
- `tool_name`
- `tool_input.subagent_type`
- `tool_input.description`
- `tool_input.prompt`
- `tool_input.command`, `tool_input.file_path`, `tool_input.path`, or another target field when relevant

## Evidence Collection

From the KIWI repo root on Windows, run:

```powershell
py -3.13 scripts\collect-windows-validation-evidence.py --project-root D:\aiops\validation\phase5-fixture --runtime-dir D:\aiops\qwencode --bundle build\offline\kiwi-offline-win11-py313.zip --strict
```

The collector writes:

- `windows-validation-report.json`
- `team-events.tail.jsonl`
- `runtime-env.cmd.txt`
- `project-template-env.cmd.txt`
- `project-qwen.cmd.txt`
- `project-info-tree.txt`
- A zipped evidence archive under `build\windows-validation-evidence\`

Attach the archive to the Phase 5 review packet after real Windows execution.
