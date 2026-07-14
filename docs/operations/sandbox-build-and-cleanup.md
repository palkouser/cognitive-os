# Sandbox build and cleanup

Build and verify with `scripts/sandbox_build.sh`, `scripts/sandbox_smoke_test.sh`, and
`scripts/sandbox_inspect.sh`. List managed containers before cleanup; removal requires
`scripts/sandbox_cleanup.sh --confirm` and affects only `cogos.managed=true` containers.
