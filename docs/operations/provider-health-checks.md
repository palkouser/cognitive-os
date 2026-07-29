# Provider operator commands

`scripts/provider.py` is the single entry point for the governed provider boundary. Five of
its six commands cannot reach a network, read a credential, or write to any store. The
sixth, `live-smoke`, can, and it is documented separately in
[provider-live-smokes.md](provider-live-smokes.md).

Exit status is the same for every command:

| Code | Meaning |
| ---- | ------- |
| `0` | the command succeeded and what it checked is healthy |
| `1` | a check failed, a provider is misconfigured, or a live answer was wrong |
| `2` | invalid usage |
| `3` | the named provider, fixture or store does not exist |
| `4` | refused on policy — live execution without both opt-ins, or outside an isolated root |

Every command prints one line of sorted JSON, so output can be diffed between runs and
parsed without knowing this file exists.

## List configured providers

```bash
uv run python scripts/provider.py list --config config/providers.example.yaml
```

Prints the provider ID, adapter, kind, enabled and live-smoke flags, model or route,
executable, working directory and default retention mode. Credentials appear only as the
*name* of the environment variable they would come from — never a value, and never whether
one happens to be set.

## Health

```bash
uv run python scripts/provider.py health --config config/providers.example.yaml
uv run python scripts/provider.py health --config config/providers.example.yaml --provider openrouter
```

Offline by default. A network adapter is reported `unavailable` with
`network probe not attempted` unless `--allow-network` is passed; CLI adapters run a local
version probe, which needs no credential and no network either way. A disabled provider
reports `unavailable` with a disabled message rather than failing.

The exit status follows the same two-category split the governance ledger uses:
`misconfigured` is a defect in this repository's control of the boundary and exits `1`,
while `unavailable` and `unauthenticated` are facts about the outside world and exit `0`.
Pass `--require-available` when you want any non-available status to fail — for example in a
pre-live-smoke check.

## Offline replay

```bash
uv run python scripts/provider.py replay
```

Runs the reviewed replay fixtures through `ReplayProvider`. No process, no network, no
credential.

## Advisory fixture and verifier

```bash
uv run python scripts/provider.py fixture
```

Re-hashes every file of `tests/fixtures/providers/advisory` against its manifest, then scores
two canned answers — one correct, one well-formed but empty — to prove the verifier still
discriminates. Checking the fixture alone would miss the failure that matters most: a
verifier that accepts everything makes every live smoke pass.

## Governance ledger integrity

```bash
COGOS_DATABASE_URL=... uv run python scripts/provider.py governance-verify
```

Read-only. Reports migration revision, table, trigger and controlled-function presence,
revision-chain continuity, retained-artifact and completed-event linkage, and how many stored
payloads re-validated. Exits `1` on any integrity failure, `3` when no database URL is set.
Provider availability is reported separately and never makes this command fail.
