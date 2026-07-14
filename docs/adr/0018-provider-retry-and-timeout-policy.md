# ADR 0018: Provider retry and timeout policy

Status: Accepted

Date: 2026-07-14

Cognitive OS owns bounded retries. Provider SDK automatic retries are disabled or minimized
so hidden attempts cannot multiply cost. Authentication, authorization, configuration,
invalid-request, unsupported-capability, content-policy, budget, and cancellation failures
are not retried. Connection, timeout, rate-limit, unavailable, and explicitly temporary
server failures may be retried.

One logical `model_call_id` spans every physical attempt. Backoff is bounded exponential
delay with injectable jitter and sleep functions. Cancellation interrupts active calls and
pending delay and is never retried. Each actual attempt receives a distinct lifecycle event
sequence.

Failure to persist requested or started state aborts before external execution. Failure to
persist a terminal event after a successful response raises a persistence error and never
causes the provider call to run again.
