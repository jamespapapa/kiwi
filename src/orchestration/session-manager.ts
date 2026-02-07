/**
 * SessionManager — orchestrates background sub-agent sessions.
 *
 * Uses OpenCode SDK (v1) to create child sessions, run them asynchronously,
 * and collect results via event handling + polling fallback.
 *
 * SDK v1 API convention:
 *   session.create({ body: { ... }, query: { directory } })
 *   session.abort({ path: { id }, query: { directory } })
 *   session.promptAsync({ path: { id }, body: { ... }, query: { directory } })
 *   session.messages({ path: { id }, query: { directory } })
 *   session.status({ query: { directory } })
 */

/* eslint-disable no-var */
declare var setTimeout: (cb: () => void, ms: number) => unknown
declare var setInterval: (cb: () => void, ms: number) => unknown
declare var clearInterval: (id: unknown) => void
declare var process: { on(event: string, cb: () => void): void } | undefined

import type { createOpencodeClient } from "@opencode-ai/sdk"
import { ConcurrencyLimiter } from "./concurrency.js"
import { getSubAgentPrompt } from "./sub-agent-prompt.js"
import {
  type BackgroundTask,
  type LaunchInput,
  type OrchestrationConfig,
  DEFAULT_CONFIG,
} from "./types.js"

type Client = ReturnType<typeof createOpencodeClient>

/** Tools allowed for read-only sub-agents */
const SUB_AGENT_TOOLS: Record<string, boolean> = {
  read: true,
  grep: true,
  glob: true,
  bash: true,
  write: false,
  edit: false,
  task: false,
  question: false,
  // Block recursive delegation
  explore_files: false,
  background_task: false,
  background_result: false,
  background_cancel: false,
}

/** Stable-poll threshold: complete after N consecutive unchanged polls */
const STABLE_POLL_THRESHOLD = 3

let taskCounter = 0

export class SessionManager {
  private tasks = new Map<string, BackgroundTask>()
  private concurrency: ConcurrencyLimiter
  private config: OrchestrationConfig
  private pollTimer: unknown
  private client: Client
  private directory: string

  constructor(client: Client, directory: string, config?: Partial<OrchestrationConfig>) {
    this.client = client
    this.directory = directory
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.concurrency = new ConcurrencyLimiter(this.config.maxConcurrent)

    this.startPolling()
    this.registerCleanup()
  }

  // ── Launch (fire-and-forget) ─────────────────────────────────────

  async launch(input: LaunchInput): Promise<BackgroundTask> {
    const task = this.createTask(input)

    // Acquire concurrency slot (may wait)
    try {
      await this.concurrency.acquire()
    } catch {
      task.status = "error"
      task.error = "Failed to acquire concurrency slot"
      return task
    }

    try {
      await this.startSession(task, input)
    } catch (err) {
      task.status = "error"
      task.error = err instanceof Error ? err.message : String(err)
      this.concurrency.release()
    }

    return task
  }

  // ── Launch and wait (blocking, for explore_files) ────────────────

  async launchAndWait(input: LaunchInput, timeoutMs?: number): Promise<BackgroundTask> {
    const task = await this.launch(input)
    if (task.status === "error") return task

    const timeout = timeoutMs ?? this.config.taskTimeoutMs
    const deadline = Date.now() + timeout

    while (task.status === "running" || task.status === "pending") {
      if (Date.now() > deadline) {
        await this.cancelTask(task.id)
        task.error = "Task timed out"
        break
      }
      await sleep(1_000)
      await this.pollTask(task)
    }

    return task
  }

  // ── Event handler (called from plugin event hook) ────────────────

  handleEvent(event: { type: string; properties?: Record<string, unknown> }): void {
    if (event.type !== "session.idle") return
    const sessionID = event.properties?.sessionID as string | undefined
    if (!sessionID) return

    const task = this.findBySessionID(sessionID)
    if (!task || task.status !== "running") return

    // Defer completion slightly to let final messages settle
    setTimeout(() => {
      this.tryComplete(task).catch(() => {})
    }, 500)
  }

  // ── Task CRUD ────────────────────────────────────────────────────

  getTask(id: string): BackgroundTask | undefined {
    return this.tasks.get(id)
  }

  async cancelTask(id: string): Promise<boolean> {
    const task = this.tasks.get(id)
    if (!task) return false
    if (task.status === "completed" || task.status === "cancelled" || task.status === "error") {
      return false
    }

    task.status = "cancelled"
    task.completedAt = new Date()

    if (task.sessionID) {
      try {
        await this.client.session.abort({
          path: { id: task.sessionID },
          query: { directory: this.directory },
        } as any)
      } catch {
        // Session may already be gone
      }
    }

    this.concurrency.release()
    return true
  }

  /** Summary of running tasks for compaction context injection */
  getRunningTasksSummary(): string | undefined {
    const running = [...this.tasks.values()].filter(
      (t) => t.status === "running" || t.status === "pending"
    )
    if (running.length === 0) return undefined

    const lines = running.map(
      (t) => `- Task ${t.id} [${t.status}]: ${t.description}`
    )
    return `## Active Background Tasks\n\n${lines.join("\n")}\n\nThese tasks are still running. Use background_result to check their status.`
  }

  // ── Internal: session lifecycle ──────────────────────────────────

  private createTask(input: LaunchInput): BackgroundTask {
    const id = `kiwi-${++taskCounter}`
    const task: BackgroundTask = {
      id,
      parentSessionID: input.parentSessionID,
      description: input.description,
      prompt: input.prompt,
      status: "pending",
    }
    this.tasks.set(id, task)
    return task
  }

  private async startSession(task: BackgroundTask, input: LaunchInput): Promise<void> {
    // Create child session
    const createRes = await this.client.session.create({
      body: {
        parentID: input.parentSessionID,
        title: `[kiwi] ${task.description}`,
      },
      query: { directory: this.directory },
    } as any)

    const session = (createRes as any).data ?? createRes
    if (!session || typeof session !== "object" || !("id" in session)) {
      throw new Error("Failed to create sub-agent session")
    }

    task.sessionID = (session as { id: string }).id
    task.status = "running"
    task.startedAt = new Date()

    // Fire async prompt (returns immediately)
    await this.client.session.promptAsync({
      path: { id: task.sessionID },
      body: {
        system: input.system ?? getSubAgentPrompt(),
        tools: input.tools ?? SUB_AGENT_TOOLS,
        parts: [{ type: "text" as const, text: input.prompt }],
      },
      query: { directory: this.directory },
    } as any)
  }

  // ── Internal: completion ─────────────────────────────────────────

  private async tryComplete(task: BackgroundTask): Promise<void> {
    if (task.status !== "running") return
    if (!task.sessionID) return

    try {
      const result = await this.extractResult(task.sessionID)
      task.status = "completed"
      task.completedAt = new Date()
      task.result = result
    } catch (err) {
      task.status = "error"
      task.completedAt = new Date()
      task.error = err instanceof Error ? err.message : String(err)
    } finally {
      this.concurrency.release()
    }
  }

  private async extractResult(sessionID: string): Promise<string> {
    const res = await this.client.session.messages({
      path: { id: sessionID },
      query: { directory: this.directory },
    } as any)

    const messages = (res as any).data ?? res
    if (!Array.isArray(messages)) return "(no output)"

    // Collect text parts from assistant messages (reverse order, get latest)
    const textParts: string[] = []
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg?.info?.role !== "assistant") continue
      if (!Array.isArray(msg.parts)) continue

      for (const part of msg.parts) {
        if (part && typeof part === "object" && "type" in part && part.type === "text" && "text" in part) {
          textParts.push(part.text as string)
        }
      }
      // Only take the last assistant message
      break
    }

    if (textParts.length === 0) return "(no output)"

    let result = textParts.join("\n\n")
    if (result.length > this.config.summaryMaxChars) {
      result = result.slice(0, this.config.summaryMaxChars) + "\n\n[... truncated]"
    }
    return result
  }

  // ── Internal: polling fallback ───────────────────────────────────

  private startPolling(): void {
    this.pollTimer = setInterval(() => {
      this.pollRunningTasks().catch(() => {})
    }, this.config.pollingIntervalMs)

    // Prevent timer from blocking process exit
    if (this.pollTimer && typeof this.pollTimer === "object" && "unref" in (this.pollTimer as object)) {
      (this.pollTimer as { unref(): void }).unref()
    }
  }

  private async pollRunningTasks(): Promise<void> {
    const running = [...this.tasks.values()].filter((t) => t.status === "running")
    if (running.length === 0) return

    // Get session statuses
    let statuses: Record<string, { type: string }> = {}
    try {
      const res = await this.client.session.status({
        query: { directory: this.directory },
      } as any)
      const data = (res as any).data ?? res
      if (data && typeof data === "object") {
        statuses = data as Record<string, { type: string }>
      }
    } catch {
      return
    }

    for (const task of running) {
      if (!task.sessionID) continue
      await this.pollTask(task, statuses)
    }
  }

  private async pollTask(
    task: BackgroundTask,
    statuses?: Record<string, { type: string }>
  ): Promise<void> {
    if (task.status !== "running" || !task.sessionID) return

    // Check timeout
    if (task.startedAt) {
      const elapsed = Date.now() - task.startedAt.getTime()
      if (elapsed > this.config.taskTimeoutMs) {
        await this.cancelTask(task.id)
        task.error = "Task timed out"
        return
      }
    }

    // Check session status if available
    if (statuses) {
      const status = statuses[task.sessionID]
      if (status?.type === "idle") {
        await this.tryComplete(task)
        return
      }
    }

    // Stability detection via message count
    try {
      const res = await this.client.session.messages({
        path: { id: task.sessionID },
        query: { directory: this.directory, limit: 1 },
      } as any)
      const data = (res as any).data ?? res
      const msgCount = Array.isArray(data) ? data.length : 0

      if (task.lastMsgCount !== undefined && msgCount === task.lastMsgCount) {
        task.stablePolls = (task.stablePolls ?? 0) + 1
        if (task.stablePolls >= STABLE_POLL_THRESHOLD) {
          await this.tryComplete(task)
          return
        }
      } else {
        task.lastMsgCount = msgCount
        task.stablePolls = 0
      }
    } catch {
      // Polling failure is non-fatal
    }
  }

  // ── Internal: utility ────────────────────────────────────────────

  private findBySessionID(sessionID: string): BackgroundTask | undefined {
    for (const task of this.tasks.values()) {
      if (task.sessionID === sessionID) return task
    }
    return undefined
  }

  private registerCleanup(): void {
    const cleanup = () => {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = undefined
      }
      this.concurrency.clear()

      // Abort all running sessions (best effort)
      for (const task of this.tasks.values()) {
        if (task.status === "running" && task.sessionID) {
          task.status = "cancelled"
          this.client.session
            .abort({
              path: { id: task.sessionID },
              query: { directory: this.directory },
            } as any)
            .catch(() => {})
        }
      }
    }

    process?.on("beforeExit", cleanup)
    process?.on("SIGINT", cleanup)
    process?.on("SIGTERM", cleanup)
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
