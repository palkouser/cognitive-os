# Optimistic stream concurrency

Every append supplies `expected_version`. Version zero requires an empty stream; version N
requires the current stream version to equal N. The adapter conditionally advances the row
and never offers an unrestricted mode. A unique stream-version constraint is the final
database safeguard. On conflict, the application must reload, reevaluate, create new events,
and explicitly retry.

```text
Writer A             PostgreSQL              Writer B
   | expected=4          |                       | expected=4
   |-------------------->|                       |
   | conditional 4->5 OK |<----------------------|
   | insert v5           | conditional 4->5: 0 rows
   | commit              |---- WrongExpectedVersion --->
```

`WrongExpectedVersionError` exposes stream ID, expected version, and actual version.
`StreamTypeMismatchError` is distinct because stream type cannot change after creation.
