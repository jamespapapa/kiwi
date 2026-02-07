/**
 * Custom tools for background sub-agent orchestration.
 *
 * 4 tools:
 *   - explore_files: blocking file exploration + summary
 *   - background_task: fire-and-forget async task
 *   - background_result: query task result
 *   - background_cancel: cancel running task
 */

import { tool } from "@opencode-ai/plugin"
import type { SessionManager } from "./session-manager.js"

const z = tool.schema

export function createExploreFilesTool(manager: SessionManager) {
  return tool({
    description:
      "Explore files and directories using a background sub-agent. " +
      "Returns a concise summary. Blocks until done.",
    args: {
      paths: z
        .string()
        .describe("Comma-separated file or directory paths to explore"),
      instruction: z
        .string()
        .describe("What to look for or analyze in the files"),
    },
    async execute(args, context) {
      try {
        const pathList = args.paths
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean)

        if (pathList.length === 0) {
          return "[ERROR] No valid paths provided."
        }

        const prompt = [
          `Explore the following files/directories and answer the instruction.`,
          ``,
          `Files: ${pathList.join(", ")}`,
          ``,
          `Instruction: ${args.instruction}`,
          ``,
          `Return a concise structured summary with file paths and line numbers.`,
        ].join("\n")

        const task = await manager.launchAndWait({
          description: `explore: ${pathList.slice(0, 3).join(", ")}`,
          prompt,
          parentSessionID: context.sessionID,
          parentMessageID: context.messageID,
        })

        if (task.status === "error") {
          return `[ERROR] Exploration failed: ${task.error ?? "unknown error"}`
        }
        if (task.status === "cancelled") {
          return `[CANCELLED] Exploration was cancelled or timed out.`
        }

        return task.result ?? "(no output)"
      } catch (err) {
        return `[ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
  })
}

export function createBackgroundTaskTool(manager: SessionManager) {
  return tool({
    description:
      "Launch a background sub-agent task. Returns immediately with a task ID. " +
      "The system will notify you when the task completes.",
    args: {
      prompt: z
        .string()
        .describe("The detailed prompt for the sub-agent to execute"),
      description: z
        .string()
        .describe("Short label for this task (e.g. 'analyze auth flow')"),
    },
    async execute(args, context) {
      try {
        const task = await manager.launch({
          description: args.description,
          prompt: args.prompt,
          parentSessionID: context.sessionID,
          parentMessageID: context.messageID,
        })

        if (task.status === "error") {
          return `[ERROR] Failed to launch: ${task.error ?? "unknown error"}`
        }

        return [
          `Task launched successfully.`,
          `  ID: ${task.id}`,
          `  Status: ${task.status}`,
          `  Description: ${task.description}`,
          ``,
          `Do NOT poll for results. Wait for the system notification.`,
          `When notified, use background_result with task_id="${task.id}" to get the result.`,
        ].join("\n")
      } catch (err) {
        return `[ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
  })
}

export function createBackgroundResultTool(manager: SessionManager) {
  return tool({
    description: "Get the result of a background task by its ID.",
    args: {
      task_id: z.string().describe("The task ID returned by background_task"),
    },
    async execute(args) {
      try {
        const task = manager.getTask(args.task_id)
        if (!task) {
          return `[ERROR] Task not found: ${args.task_id}`
        }

        const lines = [
          `Task: ${task.id}`,
          `Status: ${task.status}`,
          `Description: ${task.description}`,
        ]

        if (task.startedAt) {
          lines.push(`Started: ${task.startedAt.toISOString()}`)
        }
        if (task.completedAt) {
          lines.push(`Completed: ${task.completedAt.toISOString()}`)
        }
        if (task.error) {
          lines.push(`Error: ${task.error}`)
        }
        if (task.result) {
          lines.push(``, `--- Result ---`, task.result)
        } else if (task.status === "running" || task.status === "pending") {
          lines.push(``, `Task is still ${task.status}. Wait for the completion notification.`)
        }

        return lines.join("\n")
      } catch (err) {
        return `[ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
  })
}

export function createBackgroundCancelTool(manager: SessionManager) {
  return tool({
    description: "Cancel a running background task.",
    args: {
      task_id: z.string().describe("The task ID to cancel"),
    },
    async execute(args) {
      try {
        const ok = await manager.cancelTask(args.task_id)
        if (!ok) {
          const task = manager.getTask(args.task_id)
          if (!task) return `[ERROR] Task not found: ${args.task_id}`
          return `Task ${args.task_id} is already ${task.status}, cannot cancel.`
        }
        return `Task ${args.task_id} cancelled successfully.`
      } catch (err) {
        return `[ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
  })
}
