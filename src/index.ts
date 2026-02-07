/**
 * Kiwi — OpenCode plugin for Qwen tool call stabilization.
 *
 * Hooks:
 *   1. experimental.chat.system.transform → inject tool usage guide
 *   2. tool.execute.after → truncate oversized tool output
 *   3. experimental.session.compacting → re-inject guide after compaction
 *   4. tool → explore_files custom tool
 */

import type { Plugin } from "@opencode-ai/plugin"
import { getToolGuide, getSubAgentToolGuide } from "./prompt/tool-guide.js"
import { createToolOutputGuard } from "./hooks/tool-output-guard.js"
import { createPostCompactionReinject } from "./hooks/post-compaction-reinject.js"
import { ExploreRunner, createExploreFilesTool } from "./orchestration/explore.js"

const kiwi: Plugin = async (input) => {
  const toolOutputGuard = createToolOutputGuard()
  const { compactingHook } = createPostCompactionReinject()
  const runner = new ExploreRunner(input.client, input.directory)

  return {
    // Hook 1: Inject tool guide (reduced version for sub-agents)
    "experimental.chat.system.transform": async (hookInput, output) => {
      if (Array.isArray(output.system)) {
        const guide = runner.isSubAgentSession(hookInput.sessionID)
          ? getSubAgentToolGuide()
          : getToolGuide()
        output.system.push(guide)
      }
    },

    // Hook 2: Truncate oversized tool output
    "tool.execute.after": async (input, output) => {
      await toolOutputGuard(input, output)
    },

    // Hook 3: Re-inject tool guide after compaction
    "experimental.session.compacting": async (input, output) => {
      await compactingHook(input, output)
    },

    // Hook 4: Custom tools
    tool: {
      explore_files: createExploreFilesTool(runner),
    },
  }
}

export { kiwi as default, kiwi as Kiwi }
