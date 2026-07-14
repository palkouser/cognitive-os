# ADR 0021: Tool risk and approval policy

Status: Accepted

R0 is read-only without external side effects and may run in configured scope. R1 is a reversible
local write and may run only in the sandbox. R2 performs network or external side effects and
requires approval. R3 is destructive or privileged and is denied. Deny rules override allow rules;
a tool description or provider proposal never grants authority.
