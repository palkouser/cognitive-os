# Claude Code advisory mode

Claude Code is a bounded `cli_agent` adapter. Availability requires an executable, a
successful version command, and a readable explicit working directory. Calls are
non-interactive, use JSON output, set mandatory timeout and maximum turns, and may set a
maximum USD budget.

The runner uses an argument array and no shell, creates a process group, captures stdout and
stderr separately, and terminates the group on timeout. Its environment is an allowlist that
excludes secret-like provider variables. Permission-bypass flags are forbidden.

Every advisory prompt says to analyze only and not create, edit, or destructively modify
files. Git status is captured before and after execution. Any difference raises a typed
policy violation and is preserved for owner review; user files are not automatically
deleted. Write-capable execution is deferred to the Coding Agent sprint.
