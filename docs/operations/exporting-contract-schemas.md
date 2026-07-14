# Exporting contract schemas

Regenerate the tracked v1 schema set after an approved contract change:

```bash
./scripts/export_contract_schemas.sh
```

Check for drift without modifying tracked files:

```bash
./scripts/export_contract_schemas.sh --check
```

The exporter writes deterministic JSON Schema documents and `schemas/manifest.json`. The
manifest contains model names, event types, file paths, and SHA-256 digests. It intentionally
contains no generation timestamp.
