/**
 * Kiwi — OpenCode plugin for Qwen tool call stabilization.
 *
 * Hooks:
 *   1. experimental.chat.system.transform → inject tool usage guide
 *   2. tool.execute.after → truncate oversized tool output
 *   3. experimental.session.compacting → re-inject guide after compaction
 */

import type { Plugin } from "@opencode-ai/plugin"
import { getToolGuide } from "./prompt/tool-guide.js"
import { createToolOutputGuard } from "./hooks/tool-output-guard.js"
import { createPostCompactionReinject } from "./hooks/post-compaction-reinject.js"

const kiwi: Plugin = async (_input) => {
  const toolOutputGuard = createToolOutputGuard()
  const { compactingHook } = createPostCompactionReinject()

  return {
    // Hook 1: Inject Qwen tool usage guide into system prompt
    "experimental.chat.system.transform": async (_input, output) => {
      if (Array.isArray(output.system)) {
        output.system.push(getToolGuide())
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
  }
}

export { kiwi as default, kiwi as Kiwi }
