# Tool policy

R0 read-only tools are allowed only inside configured roots. R1 writes require the sandbox. R2
network or external effects require task-scoped approval. R3 destructive or privileged tools are
denied. Resolved-path containment is used; string-prefix path checks are forbidden.
