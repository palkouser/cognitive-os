# Provider retry policy

Cognitive OS retries are authoritative; MiniMax SDK retries are set to zero. The default
policy allows three total attempts with bounded exponential backoff, optional deterministic
jitter, injectable sleep, and explicit attempt numbering.

Connection, timeout, rate-limit, and unavailable errors may be retried. Configuration,
authentication, authorization, invalid-request, unsupported-capability, content-policy,
budget, and cancellation errors are not retried. Cancellation interrupts an active call or
backoff wait and becomes a typed cancelled error.

The lifecycle sequence is `requested → started → completed` for success and
`requested → started → retried → started → completed` for one recovered failure. A final
timeout uses `model_call.timed_out`; other terminal failures use `model_call.failed`.
