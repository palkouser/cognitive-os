# MiniMax live validation

- Validation date: 2026-07-14
- Key type: subscription
- API base URL: `https://api.minimax.io/v1`
- Configured model: `MiniMax-M3`
- Resolved model: `MiniMax-M3`
- Health status: available
- Completion result: passed
- Tool-call capability: passed with normalized `math.add` arguments
- Structured-output capability: passed with local JSON-Schema validation
- Safe errors observed: bounded structured output initially required a larger output budget and
  normalization of the model's reasoning prefix and optional JSON code fence.

No credential, key prefix, account metadata, private request, or raw provider response is retained.
