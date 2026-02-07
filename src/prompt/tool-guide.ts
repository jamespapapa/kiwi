/**
 * Qwen-specific tool usage guide.
 *
 * This guide compensates for Qwen's inability to infer correct tool usage
 * from JSON Schema alone. Every rule here addresses a real failure pattern
 * observed during testing with qwen3-235b-a22b.
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

### list — List directory contents
- Parameters: path (optional, absolute path), ignore (optional, glob patterns to ignore)
- Use to explore directory structure.

### todowrite — Update the task list
- Parameters: todos (required, array of todo objects)
- Use to track multi-step tasks.

### todoread — Read the task list
- No parameters required.

### webfetch — Fetch web content
- Parameters: url (required), format (optional: "text", "markdown", "html"), timeout (optional seconds)

### FORBIDDEN — Do NOT use these tools
- task: You lack the ability to delegate to subagents reliably. Do all work yourself directly.
- question: Do not call this tool. If you need to ask the user something, write your question as regular text output.

### General Rules
1. One tool call at a time. Wait for the result before making the next call.
2. If a tool call fails, read the error message carefully. Fix the issue and retry once.
3. After two consecutive failures on the same tool, stop and explain the problem in text.
4. Prefer specific, narrow operations over broad ones. Read 50 lines, not 2000. Search one directory, not the whole project.
5. Always verify your changes: after edit, read the modified section to confirm correctness.`
}
