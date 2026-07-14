# ADR 0030: Deterministic acceptance policy

Status: Accepted

Completion is decided only from registered verifier results and a typed `AcceptancePolicy`. Required failures reject or request bounded repair; unavailable required verifiers are unverifiable; infrastructure errors produce `verification_error`. Optional results use explicit weights. Provider confidence and model-judge opinions are excluded from authoritative acceptance. Advisory model judges may never be the sole required verifier.
