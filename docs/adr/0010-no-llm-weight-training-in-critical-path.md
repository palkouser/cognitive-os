# ADR-0010: No LLM weight training in the critical path

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

The core value is harness learning and durable knowledge, not mandatory model training.

## Decision

Do not require LLM weight training for core operation or self-improvement. Neural memory
and learned routing remain optional experiments gated by measured benefit.

## Alternatives considered

Fine-tuning or online weight updates as the primary learning mechanism.

## Consequences

The system remains model-independent and easier to reproduce; improvement focuses on
memory, skills, strategy, routing, and verified harness changes.

## Verification

Core acceptance tests run without a GPU or model-training pipeline.

## References

Cognitive OS Development Plan, Sprints 19–21.
