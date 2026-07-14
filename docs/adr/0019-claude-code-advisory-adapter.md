# ADR 0019: Claude Code advisory adapter

Status: Accepted

Date: 2026-07-14

Claude Code is represented as a `cli_agent`, not as a chat-completion API. Sprint 4 permits
only bounded, non-interactive, read-only advisory execution with an explicit working
directory, timeout, maximum turns, structured output, environment allowlist, and separate
stdout and stderr capture.

Invocation uses argument arrays without a shell. Permission-bypass flags are forbidden. The
adapter records Git status before and after execution; any tracked or untracked change is a
typed policy violation and is not automatically deleted. Missing executables and unusable
authentication produce normalized availability results.

Write-capable Claude Code execution, persistent sessions, autonomous tools, and coding-agent
workflows are deferred to a later sprint.
