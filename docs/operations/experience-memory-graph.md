# Experience Memory Graph operations

Every command here reads. None of them writes to a graph set, and none of them activates
anything: the Experience Memory Graph is advisory evidence and Gate L2 is closed.

## The commands

All five live in the existing `scripts/experience.py`. There is no second operator entry point.

Project a compiled fixture into a graph. Needs no store and no database:

```bash
uv run python scripts/experience.py graph-build --fixture repaired-bug-fix
```

The remaining four read a persisted graph set. Both stores must be named — neither is guessed —
either as arguments or as `COGOS_GRAPH_ROOT` and `COGOS_ARTIFACT_ROOT`:

```bash
uv run python scripts/experience.py graph-verify \
  --graph-root docs/sprints/sprint-21/evidence/sprint-21d1-emg-root.json \
  --artifact-root /absolute/path/to/artifacts-s21d1

uv run python scripts/experience.py graph-health \
  --graph-root <root manifest> --artifact-root <store>

uv run python scripts/experience.py graph-query \
  --graph-root <root manifest> --artifact-root <store> \
  --arm lexical --query-text "a failing boundary sequence step" \
  --exclude-group boundary-sequence-head

uv run python scripts/experience.py graph-benchmark \
  --graph-root <root manifest> --artifact-root <store> \
  --queries docs/sprints/sprint-21/evidence/sprint-21d1-graph-queries.json
```

Output is canonical JSON on stdout. `graph-verify` and `graph-health` exit non-zero when the
set is not intact, so they compose in a script without parsing.

## Arms that need the model

`--arm minilm_vector` and `--arm minilm_shortlist_plus_bounded_ged` require `--model` pointing
at the frozen local model directory, and the graph arm also needs `--pair-id` because that pair
supplies the query graph. Without `--model` the command exits non-zero and says so. It never
falls back to the deterministic hashing provider: a benchmark number produced by a hash and
labelled with a model's name is a lie the evidence file cannot detect. See
[the local embedding model](local-embedding-model.md).

`graph-benchmark` without `--model` runs the three arms that need no embedding, which is what
the credential-free CI lane does.

## Reading the health report

`graph-health` returns the same checks the unified integrity report carries. Four are failures
and tell you where to look:

| check | what it means |
|---|---|
| `experience_graph_bytes_resolve` | the root names an artifact the store does not hold. Bytes were lost. |
| `experience_graph_bytes_are_uncorrupted` | the store holds bytes that do not hash to their name, or that the contract refuses. Bytes changed. |
| `experience_graph_authority_links_agree` | the pair is sound but a hash the root declared about it disagrees. Root and store describe different evidence. |
| `experience_graph_edit_paths_round_trip` | applying an edit path no longer reproduces its successful graph. |

Three are warnings and do not condemn the store:

| check | what it means |
|---|---|
| `experience_graph_legacy_recompilation` | historical pairs whose original runs cannot be recompiled byte for byte. Their graphs and edit paths are intact. |
| `experience_graph_retriever_is_available` | an empty set. The advisory retriever offers nothing and the deterministic path is unaffected. |
| `experience_graph_is_configured` | no graph root was given. An unconfigured host is not a broken one. |

The distinction is the point. A missing model or a legacy pair going amber on every run teaches
an operator to stop reading the report on the day it means something.

## Backup, restart and recovery

Use the existing operational path; nothing about graphs needs its own:

```bash
COGOS_POSTGRES_ENV_FILE=.env.<pair>.local scripts/backup_event_store.sh
COGOS_POSTGRES_ENV_FILE=.env.<pair>.local scripts/restore_event_store.sh --test-restore
```

The backup covers the database dump and the artifact archive with their SHA-256 sums. Restore
only ever targets an isolated `_test` database.

To confirm graph bytes survived, extract the artifact archive to a scratch directory and run
`graph-verify` and `graph-benchmark` against it. D1 did exactly that: the verify output, the
eighty-query benchmark and a lexical query were byte-identical before the backup, after a
container restart, and after restoring the archive. See
`docs/sprints/sprint-21/evidence/sprint-21d1-w6b-operations.json`.

## When bytes are damaged

Practise on a copy, never on the store:

```bash
cp -r <store> /tmp/damaged-copy
printf 'x' >> /tmp/damaged-copy/sha256/ab/abcdef...
uv run python scripts/experience.py graph-verify --graph-root <root> --artifact-root /tmp/damaged-copy
```

An appended byte is reported under `corrupt_bytes`, a deleted file under `missing_bytes`, each
exiting 1. The two are kept apart because a lost file and a changed file need different
remedies.

## Isolation rules D1 held, and you should too

* The truncating PostgreSQL integration suite gets a database of its own. `_test` as a suffix
  is a naming convention, not consent: `COGOS_TRUNCATABLE_DATABASE` must name the database you
  actually mean, and the fixture fails loudly when the nomination and the connection disagree.
* Point `COGOS_ARTIFACT_ROOT` at a scratch directory before running any suite. The suites write
  artifacts, and a run pointed at an evidence pair will quietly add files to it.
* Fingerprint the evidence pairs before and after anything long-running:
  `uv run python scripts/artifact_store_fingerprint.py <root>`. Compare; do not assume.

---

## Sprint 21D3: the fixed fusion arm, and why the holdout says nothing about the arms

Sprint 21D3 added one arm and one refusal, and then measured a result that is about this
document's subject rather than about retrieval.

**The arm.** `reciprocal_rank_fusion` is equal-weight lexical + MiniLM RRF, constant 60, one
post-fusion truncation, no sweeps. An arm that contributes no rank for a candidate contributes
zero rather than a penalty; ties break on pair id.

**The refusal.** `graph-benchmark` no longer runs without `--policy-hash`, and the hash must
resolve against the two frozen graph resource policies. A revision *name* is not accepted:
naming a revision lets the policy behind the name change, which is what makes a benchmark
irreproducible six months later.

```bash
uv run python scripts/experience.py graph-benchmark --graph-root <root> \
  --artifact-root <store> --queries <manifest> --model <frozen-minilm> \
  --policy-hash d0e8520e3d3bc3637ce75f632c79aa00c1f456a8af1a4956601dad359c8474ab
```

### Two fields that used to be one

`timeouts` counts comparisons the per-pair edit-distance timeout expired on. `budget_cutoffs`
counts comparisons the *query* budget refused to start. D1 reported sixty of the second under
the first's name. They need different remedies — a longer per-pair timeout against a larger
query budget — so a single number could not have told anyone which to change.

### The arm that cannot reproduce itself

`minilm_shortlist_plus_bounded_ged` is an anytime search under a wall-clock timeout, so its
score is a function of how much search fits in 90 ms on the host that ran it. Four identical
runs of one command on one host produced four different metric triples:

```text
0.5875 / 0.3600 / 0.2226
0.5750 / 0.3475 / 0.2109
0.5750 / 0.3505 / 0.2204
0.5750 / 0.3489 / 0.2147
```

**The D1 and D2 published numbers for this arm are not reproducible by anyone**, including by
the hosts that produced them. The benchmark now reports `repeated_ranking_agreement` per arm
rather than per run, and records the second pass's own metrics beside the first. Either the
comparator gets a deterministic budget or the arm leaves the frozen set; D3 did neither,
because revision 3 had already frozen both.

### What the holdout measured, and what it did not

Sixty distinct unseen queries, read once. No arm cleared either floor, and **every arm sits at
or below the chance baseline on recall** (0.5768 / 0.3317).

The cause is a property of this document's subject:

```text
distinct_searchable_texts:                        60
distinct_after_removing_domain_and_signature:      1
```

`ActionDecisionGraph.search_text()` is domain, task signature, node labels and edge kinds. It
carries no repaired source, no issue text and no provenance hash — so sixty structurally
identical trajectories are **one document** to every arm, and the lexical arm's ranking is the
pair-id tie-break for all sixty queries.

This is not a statement that fusion, vectors or graph distance do not work. The same fusion arm
reached 0.7750 / 0.4478 on a development set with real complementarity — lexical 42, vector 43,
both 25, union 60, fusion 62. **Improving an arm cannot widen a surface.** A successor that
wants to close Gate D1 condition 15 has to change what `search_text()` carries, and that is a
contract change to this graph rather than a retrieval tuning exercise.

### One thing never to do to a query set

The first D3 holdout resolution returned a perfect 1.0000 / 1.0000 on the vector arm. The graph
task signature spelled the task family, `search_text()` puts the signature in front of every
arm, and the relevance judgement *is* the family — so the arm was reading its own label.

The signature is now the executed task's uuid5 identity, and a fail-closed guard
(`reality_leakage.judgement_leaks`) refuses to rank any text that names the label it is scored
against. Run it before ranking, not after:

```python
leaks = judgement_leaks(searchable_by_pair, labels_by_pair)
if leaks:
    raise SystemExit(f"refusing to rank text that names its own judgement: {leaks[:5]}")
```

A perfect score on a retrieval holdout is a leak until proven otherwise.
