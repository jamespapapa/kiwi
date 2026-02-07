/**
 * Tool Output Guard — truncates oversized tool output to preserve context window.
 *
 * Strategy per tool:
 *   bash  → keep last N lines (errors appear at the end)
 *   grep  → keep first N matches + suggest narrowing
 *   read  → keep first N lines + suggest offset/limit
 *   other → keep first N lines
 */

/** Default maximum output in characters (~8K tokens) */
const DEFAULT_MAX_CHARS = 32_000

/** Tool-specific maximum output in characters */
const TOOL_MAX_CHARS: Record<string, number> = {
  bash: 32_000,
  grep: 20_000,
  read: 40_000,
  webfetch: 16_000,
  websearch: 16_000,
  codesearch: 16_000,
  explore_files: 16_000,
  background_result: 16_000,
}

/** Number of lines to preserve from the end for bash output */
const BASH_TAIL_LINES = 200

/** Number of lines to preserve from the start as header */
const HEADER_LINES = 3

/** Truncation hints per tool */
const TRUNCATION_HINTS: Record<string, string> = {
  grep: "Narrow your search: use a more specific pattern or add include/path filters.",
  read: "Use offset and limit parameters to read a specific range.",
}

interface GuardInput {
  tool: string
  sessionID: string
  callID: string
}

interface GuardOutput {
  title: string
  output: string
  metadata: unknown
}

export function createToolOutputGuard() {
  return async (input: GuardInput, output: GuardOutput): Promise<void> => {
    if (!output.output || typeof output.output !== "string") return

    const maxChars = TOOL_MAX_CHARS[input.tool] ?? DEFAULT_MAX_CHARS
    if (output.output.length <= maxChars) return

    try {
      output.output = truncateOutput(input.tool, output.output, maxChars)
    } catch {
      // Graceful degradation: if truncation itself fails, keep original
    }
  }
}

function truncateOutput(tool: string, text: string, maxChars: number): string {
  if (tool === "bash") {
    return truncateBash(text, maxChars)
  }
  const hint = TRUNCATION_HINTS[tool]
  return truncateLines(text, maxChars, hint)
}

/**
 * bash: preserve the last N lines (errors/results are at the end).
 * Also keep a small header from the top for context.
 */
function truncateBash(text: string, maxChars: number): string {
  const lines = text.split("\n")
  if (lines.length <= BASH_TAIL_LINES + HEADER_LINES) {
    return truncateLines(text, maxChars)
  }

  const header = lines.slice(0, HEADER_LINES)
  const tail = lines.slice(-BASH_TAIL_LINES)
  const omitted = lines.length - HEADER_LINES - BASH_TAIL_LINES

  const result = [
    ...header,
    "",
    `[... ${omitted} lines omitted — showing last ${BASH_TAIL_LINES} lines ...]`,
    "",
    ...tail,
  ].join("\n")

  if (result.length > maxChars) {
    return truncateLines(result, maxChars)
  }
  return result
}

/**
 * Generic line-based head truncation with optional hint message.
 */
function truncateLines(text: string, maxChars: number, hint?: string): string {
  const lines = text.split("\n")
  const kept: string[] = []
  let chars = 0

  for (const line of lines) {
    if (chars + line.length + 1 > maxChars) break
    kept.push(line)
    chars += line.length + 1
  }

  const omitted = lines.length - kept.length
  if (omitted > 0) {
    const suffix = hint
      ? `[${omitted} more lines truncated. ${hint}]`
      : `[${omitted} more lines truncated.]`
    kept.push("", suffix)
  }
  return kept.join("\n")
}
