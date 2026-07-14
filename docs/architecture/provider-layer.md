# Provider layer

The asynchronous `ModelProviderPort` is the only application boundary for model execution.
It exchanges Cognitive OS request, response, stream, capability, health, and error contracts;
HTTP, OpenAI SDK, and subprocess objects remain inside adapters.

`ProviderRegistry` is explicitly constructed and performs deterministic static selection.
It has no plugin scanning, scoring, adaptive routing, fallback chain, voting, or orchestration.
`ModelExecutionService` selects one provider, checks capabilities before external execution,
applies the Cognitive OS retry policy, records monotonic latency, and coordinates optional
event and artifact persistence.

Mock and replay providers are deterministic and offline. MiniMax uses the OpenAI-compatible
SDK adapter. Claude Code uses the distinct `cli_agent` category and is restricted to
read-only advisory operation. Adaptive routing is deferred.
