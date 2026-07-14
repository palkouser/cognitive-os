# Provider event persistence

`ProviderEventService` reuses the Sprint 2 model-call events and appends them to the Sprint 3
event store. The stream ID is the `model_call_id`, the stream type is `model_call`, and every
version is contiguous.

Typical sequences are:

```text
requested → started → completed
requested → started → retried → started → completed
requested → started → timed_out
```

The compact event payload records provider and model identity, attempt transitions, usage,
latency, finish reason, sanitized error information, and artifact references. Failure to
persist requested or started state prevents external execution. Failure to persist a
terminal event raises `ProviderPersistenceError` and never repeats a successful provider
call.
