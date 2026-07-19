# Sprint 13 Strategy Engine baseline

The credential-free CI manifest contains 10 cases and the seed manifest contains 40 cases across
lifecycle, graph integrity, applicability, selection, cold start, plan instantiation, execution,
outcomes, statistics, Context, and access audit. Both reuse the native benchmark runner and require
no network, credentials, provider, GPU, or graph database.

The isolated PostgreSQL baseline on 2026-07-19 used the backlog target corpus: 1,000 strategy
identities, 5,000 revisions, 100,000 graph edges, 25,000 selections, 25,000 outcomes, and 250,000
accesses. Thirty CPU-only iterations measured:

- registry load p50/p95: 1.206/2.992 ms;
- candidate query p50/p95: 1.224/1.273 ms;
- applicability p50/p95: 0.438/0.473 ms;
- deterministic selection projection p50/p95: 9.000/11.206 ms;
- neighbourhood p50/p95: 0.236/0.299 ms;
- lineage p50/p95: 0.272/0.366 ms;
- statistics rebuild p50/p95: 4.779/5.658 ms;
- graph snapshot p50/p95: 0.290/0.313 ms.

Core projection of 10,000 edges measured 0.998/1.007 ms p50/p95; optional NetworkX measured
4.015/4.060 ms for the same rows. Maximum process RSS was 67,780 KiB, strategy relations occupied
149,258,240 bytes, and the test database occupied 160,741,055 bytes. The machine-readable report
at `docs/benchmarks/sprint-13-scale-baseline.json` retains all query plans and environment details.
The fixture is restricted to an `_test` database, needs no network or GPU, and is removed after the
measurement run.
