# ADR 0020: Typed Tool Registry

Status: Accepted

Tool descriptors and executable implementations are separate. Tool IDs and versions are stable,
input and output schemas are authoritative, and registration is explicit. The registry freezes at
startup and exposes a deterministic, filtered provider-visible view. Dynamic tool generation is
deferred.
