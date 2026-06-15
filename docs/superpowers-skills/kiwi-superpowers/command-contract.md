# KIWI Superpowers Command Contract

## Activation Commands

- Primary prefix: `superpowers`
- Short alias: `spw`
- KIWI UI owns prefix injection for Prompt Builder output.
- Manual console input may start with either prefix, but the first activation locks the session mode.

## Required Metadata

- Non-FAST superpowers submissions must carry selected task_size metadata from KIWI UI.
- The selected task_size is the source of truth for role composition.
- If selected task_size is missing, stop and ask the user to choose a size in KIWI before continuing.

## Command Body

The command body must include or imply:

- central docs read requirement.
- `kiwi-superpowers` skill-first requirement.
- impact map requirement.
- verification surface.
- stop conditions for missing business meaning, unclear API/storage carrier, or unsafe shared-file impact.

## No Remote Bootstrap

- Do not run remote installer commands.
- Do not fetch runtime skill content from the public network.
- Use the locally installed Qwen extension assets.
