/**
 * Kiwi — OpenCode plugin for Qwen tool call stabilization.
 *
 * Phase 1 Hooks:
 *   1. experimental.chat.system.transform → inject tool usage guide
 *   2. tool.execute.after → truncate oversized tool output
 *   3. experimental.session.compacting → re-inject guide after compaction
 *
 * Phase 2 Hooks:
 *   4. event → route session events to SessionManager
 *   5. tool → 4 custom tools (explore_files, background_task, background_result, background_cancel)
 */

import type { Plugin } from "@opencode-ai/plugin"
import { getToolGuide } from "./prompt/tool-guide.js"
import { createToolOutputGuard } from "./hooks/tool-output-guard.js"
import { createPostCompactionReinject } from "./hooks/post-compaction-reinject.js"
import { SessionManager } from "./orchestration/session-manager.js"
import {
  createExploreFilesTool,
  createBackgroundTaskTool,
  createBackgroundResultTool,
  createBackgroundCancelTool,
} from "./orchestration/tools.js"

const kiwi: Plugin = async (input) => {
  // Phase 1
  const toolOutputGuard = createToolOutputGuard()
  const { compactingHook } = createPostCompactionReinject()

  // Phase 2: session manager for background sub-agents
  const manager = new SessionManager(input.client, input.directory)

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

    // Hook 3: Re-inject tool guide after compaction (+ running task state)
    "experimental.session.compacting": async (inp, out) => {
      await compactingHook(inp, out, manager)
    },

    // Hook 4: Route session events to manager (completion detection)
    event: async ({ event }) => {
      try {
        manager.handleEvent(event)
      } catch {
        // Graceful degradation
      }
    },

    // Hook 5: Custom tools for sub-agent orchestration
    tool: {
      explore_files: createExploreFilesTool(manager),
      background_task: createBackgroundTaskTool(manager),
      background_result: createBackgroundResultTool(manager),
      background_cancel: createBackgroundCancelTool(manager),
    },
  }
}

export { kiwi as default, kiwi as Kiwi }
