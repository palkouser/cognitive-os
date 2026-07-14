# MiniMax live validation

Keep provider credentials only in `~/.config/cognitive-os/providers.env` with mode `0600`. Run live
checks through `scripts/run_with_provider_secrets.sh`; the helper validates permissions and uses
`exec` without printing credentials. Local capability flags may be enabled only after live success.
