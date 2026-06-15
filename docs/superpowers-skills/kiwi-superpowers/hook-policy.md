# KIWI Superpowers Hook Policy

## Hook Replacement

Upstream hook-style startup is replaced by KIWI runtime activation and pre-tool policy patches.

- `superpowers` or `spw` activates the locked session mode.
- Runtime activation context injects central docs and skill-first instructions.
- Runtime activation instructs Kiwi to use the built-in `skill` tool for `kiwi-superpowers` and `using-superpowers`.
- Agent delegation is allowed only after Kiwi has used those skills or explicitly fallen back to the local superpowers policy.

## First Response

The first response after activation must:

- announce superpowers mode in Korean;
- read or cite `D:/aiops/docs/<project-key>/knowledge/00-index.md` first when present, and optional `D:/aiops/docs/<project-key>/project-info/` summaries only if that central directory exists;
- use the built-in `skill` tool for `kiwi-superpowers` and `using-superpowers`;
- report selected task_size and role composition;
- build an impact map before implementation or delegation.

## Policy Files

- Runtime extension policy: `SUPERPOWERS_POLICY.md`
- Runtime extension context: `QWEN.md`
- Skill entrypoint: `skills/kiwi-superpowers/SKILL.md`

## Offline Boundary

- All hook behavior must come from bundled files and patched runtime scripts.
- Missing skill or policy files are installation gaps, not prompts to fetch from outside the closed network.
