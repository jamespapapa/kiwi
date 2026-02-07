/**
 * Type definitions for background sub-agent orchestration.
 */

export type TaskStatus = "pending" | "running" | "completed" | "error" | "cancelled"

export interface BackgroundTask {
  id: string
  sessionID?: string
  parentSessionID: string
  description: string
  status: TaskStatus
  startedAt?: Date
  completedAt?: Date
  result?: string
  error?: string
  /** Message count at last poll — for stability detection */
  lastMsgCount?: number
  /** Consecutive polls with unchanged message count */
  stablePolls?: number
}

export interface LaunchInput {
  description: string
  prompt: string
  parentSessionID: string
  system?: string
  tools?: Record<string, boolean>
}

export interface OrchestrationConfig {
  /** Max concurrent sub-agent sessions (default: 3) */
  maxConcurrent: number
  /** Polling interval in ms (default: 3000) */
  pollingIntervalMs: number
  /** Task timeout in ms (default: 120000) */
  taskTimeoutMs: number
  /** Max chars for result summary (default: 8000) */
  summaryMaxChars: number
}

export const DEFAULT_CONFIG: OrchestrationConfig = {
  maxConcurrent: 3,
  pollingIntervalMs: 3_000,
  taskTimeoutMs: 120_000,
  summaryMaxChars: 8_000,
}
