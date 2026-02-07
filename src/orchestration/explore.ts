/**
 * ExploreRunner — minimal session runner for explore_files tool.
 *
 * Creates a read-only sub-agent session, sends a prompt,
 * polls until done, and extracts the result.
 */

/* eslint-disable no-var */
declare var setTimeout: (cb: () => void, ms: number) => unknown

import type { createOpencodeClient } from "@opencode-ai/sdk"
import { tool } from "@opencode-ai/plugin"
import { getSubAgentPrompt } from "./sub-agent-prompt.js"

type Client = ReturnType<typeof createOpencodeClient>

const z = tool.schema

/** Read-only tool allow/deny list for sub-agents */
const SUB_AGENT_TOOLS: Record<string, boolean> = {
  read: true,
  grep: true,
  glob: true,
  bash: true,
  write: false,
  edit: false,
  apply_patch: false,
  multiedit: false,
  task: false,
  question: false,
  batch: false,
  skill: false,
  todowrite: false,
  webfetch: false,
  websearch: false,
  codesearch: false,
  lsp: false,
  explore_files: false,
}

/** Max result size in characters (~2K tokens) */
const RESULT_MAX_CHARS = 8_000

/** Default timeout for exploration */
const DEFAULT_TIMEOUT_MS = 120_000

export class ExploreRunner {
  private client: Client
  private directory: string
  private subAgentSessions = new Set<string>()

  constructor(client: Client, directory: string) {
    this.client = client
    this.directory = directory
  }

  /** Check if a sessionID belongs to a Kiwi sub-agent */
  isSubAgentSession(sessionID: string | undefined): boolean {
    if (!sessionID) return false
    return this.subAgentSessions.has(sessionID)
  }

  /** Run exploration: create session → prompt → poll → extract result */
  async explore(
    prompt: string,
    parentSessionID: string,
    timeoutMs = DEFAULT_TIMEOUT_MS
  ): Promise<string> {
    const createRes = await this.client.session.create({
      body: {
        parentID: parentSessionID,
        title: `[kiwi] explore`,
      },
      query: { directory: this.directory },
    } as any)

    const session = (createRes as any).data ?? createRes
    if (!session || typeof session !== "object" || !("id" in session)) {
      throw new Error("Failed to create sub-agent session")
    }

    const sessionID = (session as { id: string }).id
    this.subAgentSessions.add(sessionID)

    try {
      await this.client.session.promptAsync({
        path: { id: sessionID },
        body: {
          system: getSubAgentPrompt(),
          tools: SUB_AGENT_TOOLS,
          parts: [{ type: "text" as const, text: prompt }],
        },
        query: { directory: this.directory },
      } as any)

      // Poll until session is idle or timeout
      const deadline = Date.now() + timeoutMs
      await sleep(3_000)

      while (Date.now() < deadline) {
        try {
          const res = await this.client.session.status({
            query: { directory: this.directory },
          } as any)
          const statuses = (res as any).data ?? res
          if (statuses && typeof statuses === "object") {
            const status = (statuses as Record<string, { type: string }>)[sessionID]
            if (status?.type === "idle") break
          }
        } catch {
          // Polling failure is non-fatal
        }
        await sleep(2_000)
      }

      return await this.extractResult(sessionID)
    } finally {
      this.subAgentSessions.delete(sessionID)
    }
  }

  private async extractResult(sessionID: string): Promise<string> {
    const res = await this.client.session.messages({
      path: { id: sessionID },
      query: { directory: this.directory },
    } as any)

    const messages = (res as any).data ?? res
    if (!Array.isArray(messages)) return "(no output)"

    // Get text from last assistant message
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg?.info?.role !== "assistant") continue
      if (!Array.isArray(msg.parts)) continue

      const texts: string[] = []
      for (const part of msg.parts) {
        if (part && typeof part === "object" && "type" in part && part.type === "text" && "text" in part) {
          texts.push(part.text as string)
        }
      }

      if (texts.length > 0) {
        let result = texts.join("\n\n")
        if (result.length > RESULT_MAX_CHARS) {
          result = result.slice(0, RESULT_MAX_CHARS) + "\n\n[... truncated]"
        }
        return result
      }
    }

    return "(no output)"
  }
}

/** Create the explore_files tool definition */
export function createExploreFilesTool(runner: ExploreRunner) {
  return tool({
    description:
      "Explore files and directories using a sub-agent. " +
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

        return await runner.explore(prompt, context.sessionID)
      } catch (err) {
        return `[ERROR] ${err instanceof Error ? err.message : String(err)}`
      }
    },
  })
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
