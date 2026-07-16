# Context Builder configuration

`config/context.example.yaml` is the fail-closed host example. Load it with
`load_context_configuration`; unknown fields and out-of-range limits are rejected. Provider output
cannot mutate this model.

The main ceilings are 24 retriever calls, four parallel retrievers, 1,000 candidates, 128 hydrated
candidates, 64 selected items, 12 items per source, 32 KiB per excerpt, 1 MiB total hydration and
trace size, three graph hops, 500 graph nodes, and 30 seconds. Provider output space, system/task
tokens, and a 1,024-token safety margin are reserved before retrieval.

Ranking defaults to RRF `k=60` with nine-place Decimal quantization and explicit modifier weights.
Network retrieval, ANN, learned ranking, provider query expansion/retriever selection, and automatic
memory writes are permanently false in the Sprint 11 model. CrossEncoder loading is optional,
local-only, digest-recorded, and not part of core installation.

Schema snapshots are exported under `schemas/v1/config/context-configuration.schema.json` using the
repository-wide schema exporter.
