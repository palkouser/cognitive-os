# The local embedding model

The production embedding provider reads one model from a local directory. It never downloads
anything. Getting that directory onto a host is a deliberate operator step, run once:

```bash
scripts/embedding_model.py prefetch \
  --destination /srv/cognitive-os/models/all-MiniLM-L6-v2 \
  --allow-network
```

`--allow-network` is required and there is no prompt: this is the only command in the
repository that opens an outbound connection for a model, and it should be obvious in shell
history that somebody asked for it. The destination must be absolute, and must not be inside
the working tree — the model is ~88 MB and is never committed.

The command prints the tree digest. Put it in the configuration:

```yaml
    sentence-transformers-local:
      provider_type: sentence_transformers
      model_id: sentence-transformers/all-MiniLM-L6-v2
      dimension: 384
      enabled: true
      local_model_path: /srv/cognitive-os/models/all-MiniLM-L6-v2
      local_model_digest: "<the tree digest the prefetch printed>"
```

Then verify, on the host that will run it and with no network:

```bash
scripts/embedding_model.py health --destination /srv/cognitive-os/models/all-MiniLM-L6-v2
```

| Report | What it means | What to do |
| ------ | ------------- | ---------- |
| `healthy` | every declared file hashes to the manifest and the model encodes 384 dimensions | nothing |
| `missing` | no manifest, or files absent | run `prefetch` |
| `dependency_missing` | the `local-embeddings` extra is not installed | `pip install -e '.[local-embeddings]'` |
| `digest_mismatch` | bytes on disk differ from the manifest, or the revision is not the frozen one | re-run `prefetch` into a clean directory; do not repair in place |
| `dimension_mismatch` | the model loads but does not produce 384 dimensions | the directory is not this model |

## What is frozen, and why it matters

The revision is a commit SHA (`1110a243…`), not a branch. A branch is a pointer somebody else
can move, and every retrieval number recorded in Sprint 21C3 is only reproducible against an
identity that cannot move. `prefetch` refuses any other revision; changing it is an ADR, not a
flag.

Only the eleven files a CPU SentenceTransformer actually loads are fetched. The upstream
repository also ships ONNX, OpenVINO, TensorFlow and Rust weights — roughly 400 MB this
runtime cannot use.

## There is no fallback

`build_embedding_provider` raises `EmbeddingUnavailableError` when the local model is missing,
mismatched, or the wrong dimension. It does not quietly return `DeterministicEmbeddingProvider`
instead.

That provider is a hashing vector with no semantic content. Falling back to it would not make
retrieval a bit worse — it would replace retrieval, while the evidence file went on naming the
real model. On the frozen benchmark the difference is recall@5 0.917 against 0.458. See
[ADR 0089](../adr/0089-frozen-local-embedding-model-and-vector-storage-precision.md).

## Measuring retrieval

```bash
scripts/retrieval_benchmark.py \
  --model /srv/cognitive-os/models/all-MiniLM-L6-v2 \
  --evidence /tmp/retrieval.json
```

Runs the frozen 60-query benchmark through the Memory Plane against `COGOS_DATABASE_URL`, in
four arms — the plane's text mode, the same text mode with an `OR`-joined query, the
deterministic hashing provider at 384 dimensions, and MiniLM — then compares `vector(384)`
against `halfvec(384)` in temporary tables it drops before exiting. It exits non-zero if any
§4.15 threshold fails. It writes benchmark records into the
`project:cognitive-os-retrieval-benchmark` scope, idempotently, so re-running adds no records.
