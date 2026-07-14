# Controller budget

`ControllerBudget` is immutable host configuration; `ControllerUsage` is a separately
persistable ledger projection. Remaining values saturate at zero. Provider, tool, plan,
repair, clarification, elapsed, token, and optional cost limits are checked without consulting
the model. The 256-iteration ceiling prevents no-progress loops even if semantic accounting
is corrupted or incomplete.
