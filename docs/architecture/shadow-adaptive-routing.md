# Shadow and bounded adaptive routing

Shadow routing evaluates host-owned, versioned `Decimal` weights against exact statistics
snapshots. The static decision still executes. A shadow-selected model receives no request, tool
call, Context Bundle, budget, or outcome. Its actual outcome is always unknown; expected scores are
not counterfactual success claims.

Promotion requires minimum measured samples and shadow cases, deterministic benchmark improvement,
zero configured safety and policy regression, bounded latency and cost, tested fallback, replayable
decisions, explicit operator approval, and an exact TaskSignature scope. Approval and enablement are
separate append-only revisions. Disablement immediately restores static control without deleting
history. Learned weights, exploration, and automatic promotion are not implemented.
