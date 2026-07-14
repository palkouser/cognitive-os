# MiniMax configuration

The default OpenAI-compatible base URL is `https://api.minimax.io/v1`, and the example model
alias is `MiniMax-M3`. Configure the API key only through `COGOS_MINIMAX_API_KEY`. Set
`key_type` explicitly to `pay_as_you_go` or `subscription`; the adapter never infers account
type from secret format.

The health check lists models without generation and reports degraded health when the
configured alias is absent. SDK retries are zero; bounded Cognitive OS retries are
authoritative. The initial context budget is conservative and cannot exceed 131,072 tokens.
Tool-call and structured-output capabilities remain false until confirmed for the configured
model.

Run the live bounded smoke test only after reading the key without shell history:

```bash
read -rsp "MiniMax API key: " COGOS_MINIMAX_API_KEY
export COGOS_MINIMAX_API_KEY
COGOS_RUN_MINIMAX_LIVE=1 uv run python scripts/minimax_smoke_test.py \
  --config config/providers.local.yaml
unset COGOS_MINIMAX_API_KEY
```
