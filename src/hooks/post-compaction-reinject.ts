/**
 * Post-Compaction Reinject — re-injects tool usage guide and work-state
 * preservation instructions when a session is compacted.
 *
 * Compaction summarizes the conversation to reclaim context window space,
 * but Qwen loses tool usage knowledge in the process. This hook ensures
 * the model receives the guide again immediately after compaction.
 */

import { getToolGuide } from "../prompt/tool-guide.js"

interface CompactingInput {
  sessionID: string
}

interface CompactingOutput {
  context: string[]
  prompt?: string
}

export function createPostCompactionReinject() {
  const compactingHook = async (
    _input: CompactingInput,
    output: CompactingOutput
  ): Promise<void> => {
    try {
      if (!Array.isArray(output.context)) return

      // Re-inject the tool usage guide so Qwen remembers how to use tools
      output.context.push(getToolGuide())

      // Add structured work-state preservation instructions
      output.context.push(getWorkStatePreservationPrompt())
    } catch {
      // Graceful degradation: compaction must not fail
    }
  }

  return { compactingHook }
}

function getWorkStatePreservationPrompt(): string {
  return `## Work State Preservation (include in your summary)

When summarizing this session, you MUST preserve the following in your summary:

1. **User's Original Request**: Quote the user's request exactly as stated.
2. **Goal**: What the user ultimately wants to achieve.
3. **Work Completed**: Files created or modified, features implemented, problems solved.
4. **Remaining Tasks**: What still needs to be done from the original request.
5. **Active Files**: Exact paths of files currently being edited or referenced.
6. **Key Constraints**: Any constraints the user explicitly stated (quote verbatim, do not paraphrase).

Do NOT omit any of these sections. Empty sections should say "None" rather than being skipped.`
}
