# KIWI Superpowers Skills

이 디렉터리는 KIWI `superpowers` work mode에서 Qwen runtime extension으로 설치할 skill 원본이다.

런타임 설치 위치:

- `portable-user/.qwen/extensions/superpowers/qwen-extension.json`
- `portable-user/.qwen/extensions/superpowers/skills/<skill-name>/SKILL.md`
- `portable-user/.qwen/skills/<skill-name>/SKILL.md`
- `templates/project/.qwen/skills/<skill-name>/SKILL.md`
- fallback 호환용 `extensions/superpowers/skills/<skill-name>/SKILL.md`

Qwen Code 0.17은 `.qwen/skills/<name>/SKILL.md`와 active extension의 `skills/`를 skill source로 읽는다. 따라서 `superpowers`는 별도 프로세스가 아니라 Qwen의 `skill` tool로 실제 호출 가능한 구조다.

현재 구조:

- `kiwi-superpowers`: 기존 KIWI 호환 entrypoint.
- `using-superpowers`: full skill library router.
- `brainstorming`, `writing-plans`, `executing-plans`.
- `test-driven-development`, `systematic-debugging`, `verification-before-completion`.
- `requesting-code-review`, `receiving-code-review`.
- `subagent-driven-development`, `dispatching-parallel-agents`.
- `finishing-a-development-branch`, `using-git-worktrees`.
- `writing-skills`: 로컬 Qwen skill 작성/검증용 보조 skill.

FAST/lightwork prompt에는 이 skill 본문을 주입하지 않는다.
