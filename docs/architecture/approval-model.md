# Approval model

Approvals bind task run, tool ID, version, scope, and optional argument hash. `allow_once` is
single-use; `allow_for_task` cannot escape its task. CI uses deterministic deny-all or preconfigured
providers and never prompts interactively.
