# Lifecycle transitions

Same-state transitions are not allowed. Terminal states have no outgoing transitions.

## Task

| From | Allowed targets |
| --- | --- |
| created | ready, cancelled |
| ready | running, cancelled |
| running | waiting, completed, failed, cancelled |
| waiting | running, failed, cancelled |
| completed, failed, cancelled | none |

## Task run

| From | Allowed targets |
| --- | --- |
| pending | running, cancelled |
| running | waiting_for_approval, completed, failed, cancelled |
| waiting_for_approval | running, failed, cancelled |
| completed, failed, cancelled | none |

## Execution step

| From | Allowed targets |
| --- | --- |
| pending | ready, skipped, cancelled |
| ready | running, skipped, cancelled |
| running | completed, failed, cancelled |
| completed, failed, skipped, cancelled | none |
