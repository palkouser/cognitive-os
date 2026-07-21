# Static routing

Static routing is the default execution authority. It rejects inactive or unavailable providers,
insufficient Context limits, missing structured-output or tool-call support, disallowed providers,
unsupported domains and risk constraints before scoring. Remaining models use operator order and a
canonical identity tie-break. Every exclusion and fallback is retained in the immutable decision.

The router never performs a provider call. The Controller creates the routing request, receives the
decision, builds and revalidates a provider-specific Context Bundle, and then creates a
`ModelProviderRequest` carrying the exact `RoutingReference`.
