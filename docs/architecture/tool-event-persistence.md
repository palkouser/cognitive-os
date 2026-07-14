# Tool event persistence

Tool calls use their UUID as a `tool_call` stream. Requested, authorized or denied, started, and one
terminal event are appended contiguously. Persistence failure before execution aborts; terminal
persistence failure never triggers automatic re-execution.
