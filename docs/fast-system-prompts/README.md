# FAST System Prompts

This directory is the source of truth for KIWI FAST/lightwork direct-work system prompts.

FAST is not only "no subagent mode." It is a profile-aware direct-work mode where Kiwi reads the Project Info Layer, verifies claims against current files, makes the smallest practical change, and runs focused verification before reporting.

## Files

- `fast-system-prompt.dcp-front.md`: Vue/DCP front-end direct-work prompt source.
- `fast-system-prompt.dcp-services.md`: DCP backend services direct-work prompt source.
- `fast-system-prompt.generic.md`: fallback direct-work prompt source.
- `evaluation-rubric.md`: objective rubric and benchmark packet.
- `evaluation-report.md`: self-improvement report and evaluator packet.

## Runtime Contract

Each profile prompt has two explicit sections:

- `Runtime Injection Summary`: compact content injected by backend, console activation, and Qwen runtime patch paths.
- `Human-Review Final Prompt`: readable full source for human review.

The runtime chooses the prompt by project profile:

- `dcp-front`: front-end route/view/component/state/API/CSS/Playwright surface.
- `dcp-services`: controller/service/repository/MyBatis/EAI/config/profile surface.
- `generic`: project-neutral entrypoint/config/test surface.

The prompt source is copied into the offline bundle under the Qwen runtime extension area so Windows closed-network deployments can inspect the same source without network access.
