# Controller configuration

Copy `config/controller.example.yaml` to ignored `config/controller.local.yaml`. Configure
provider IDs and positive host budgets; credentials remain in the existing provider secret
file. Sprint 6 rejects non-sequential execution, unlimited call budgets, TTL values below one
second, invalid confidence thresholds, and unknown configuration fields.
