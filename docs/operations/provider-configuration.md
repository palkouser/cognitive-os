# Provider configuration

Copy `config/providers.example.yaml` to ignored `config/providers.local.yaml` and adjust only
non-secret settings. Provider credentials are named by environment variable and never stored
in YAML. The default provider ID selects one explicit registry entry; there is no automatic
fallback or adaptive routing.

MiniMax and Claude Code providers can be disabled independently. A disabled provider appears
as a safe health status and cannot be selected for execution. Keep local configuration and
all credential values untracked.
