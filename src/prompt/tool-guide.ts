/**
 * Qwen-specific tool usage guide.
 *
 * This guide compensates for Qwen's inability to infer correct tool usage
 * from JSON Schema alone. Every rule here addresses a real failure pattern
 * observed during testing with qwen3-235b-a22b.
 *
 * Available tools (from OpenCode runtime):
 *   bash, read, glob, grep, edit, write, task, webfetch, todowrite, question, skill
 *   explore_files, background_task, background_result, background_cancel (Kiwi plugin)
 */

export function getToolGuide(): string {
  return `## Tool Usage Rules (MANDATORY)

You have access to tools via function calling. You MUST call tools using the proper function call mechanism. NEVER output tool calls as plain text.

### read — Read file contents
- Parameters: filePath (required), offset (optional, 0-based line number), limit (optional, default 2000)
- ALWAYS specify offset and limit for large files. Read only the lines you need.
- Example: To read lines 100-150, use offset=100, limit=50.
- If output says "truncated", narrow your range and read again.

### edit — Modify file contents via string replacement
- Parameters: filePath (required), oldString (required), newString (required), replaceAll (optional boolean)
- BEFORE calling edit, you MUST call read on the same file first. Never edit a file you haven't read.
- oldString must be an EXACT substring copied from the file. Do not type it from memory.
- If edit fails with "multiple matches" or "not found", call read again to get the exact text.
- oldString and newString must be different.
- For multiple changes in one file, make separate edit calls for each change.

### write — Create or overwrite a file
- Parameters: filePath (required, absolute path), content (required)
- Use ONLY for creating new files. To modify existing files, use edit instead.
- filePath must be an absolute path starting with /.

### bash — Execute shell commands
- Parameters: command (required), description (required), timeout (optional ms), workdir (optional)
- description: Write a clear 5-10 word summary of what the command does.
- Use bash for: git, npm, bun, make, curl, test runners, build commands, any CLI tool.
- NEVER run interactive commands: vim, nano, less, more, top, htop, python REPL, node REPL.
- NEVER use commands that require user input (y/n prompts). Add -y or equivalent flags.
- If a command may produce large output, pipe through head or tail.

### grep — Search file contents with regex
- Parameters: pattern (required regex), path (optional directory), include (optional file glob)
- ALWAYS specify path to limit search scope. Do not search the entire project unless necessary.
- ALWAYS specify include to filter file types (e.g., include="*.ts").
- If results exceed 100 matches, narrow your pattern or path.
- Example: pattern="function.*export", path="src", include="*.ts"

### glob — Find files by name pattern
- Parameters: pattern (required glob), path (optional directory)
- Use to find files before reading them.
- Example: pattern="*.ts", path="src/hooks"
- Do NOT pass "undefined" or "null" as path. Omit it to use current directory.

### task — Delegate work to a subagent
- Parameters: description (required string), prompt (required string)
- Use for complex, independent subtasks that can run in parallel.
- Provide a clear, self-contained prompt — the subagent has no access to your conversation context.

### todowrite — Update the task list
- Parameters: todos (required, array of todo objects)
- Use to track multi-step tasks.

### question — Ask the user a question
- Parameters: question (required string)
- Use when you need clarification, confirmation, or user input to proceed.
- Prefer this tool over plain text when a clear answer is needed before continuing work.

### webfetch — Fetch web content
- Parameters: url (required), format (optional: "text", "markdown", "html"), timeout (optional seconds)

### skill — Execute a predefined skill
- Parameters: skill (required string)
- Use to invoke registered skills by name.

### explore_files — Explore files and get a summary
- Parameters: paths (required, comma-separated file paths or directories), instruction (required)
- Blocks until exploration is done. Use for understanding code before making changes.
- The result is a concise summary with file paths and line numbers.
- Example: paths="src/hooks,src/index.ts", instruction="Find where tool output is truncated"

### background_task — Run a task in background
- Parameters: prompt (required, detailed instruction), description (required, short label)
- Returns task_id immediately. Continue your current work while it runs.
- After 10-30 seconds, use background_result to check status and get the result.

### background_result — Get background task result
- Parameters: task_id (required, the ID returned by background_task)
- Use after launching a background task to check status or retrieve the result.

### background_cancel — Cancel a background task
- Parameters: task_id (required)
- Cancels a running background task and frees the slot.

### General Rules
1. One tool call at a time. Wait for the result before making the next call.
2. If a tool call fails, read the error message carefully. Fix the issue and retry once.
3. After two consecutive failures on the same tool, stop and explain the problem in text.
4. Prefer specific, narrow operations over broad ones. Read 50 lines, not 2000. Search one directory, not the whole project.
5. Always verify your changes: after edit, read the modified section to confirm correctness.
6. Use explore_files for multi-file exploration instead of reading files one by one. It saves context.
7. Use background_task for independent subtasks that can run in parallel.`
}
