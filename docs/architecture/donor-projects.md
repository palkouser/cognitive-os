# Donor project registry

## Sprint 6 controller design references

LangGraph, Pydantic AI, and LightFlow were reviewed for stateful workflow, interrupt,
structured-output, human-approval, retry, checkpoint, and resume patterns. Their usage is
pattern-only: none is a runtime dependency and none owns authoritative state. Public
checkpoint restoration and trust-binding concerns reinforce typed checkpoint validation and
explicit continuation scope. Cognitive OS retains its event store, provider execution, Tool
Plane, approval, artifact, telemetry, replay, and recovery boundaries.

| Project | Repository | License | Reviewed commit | Role | Imported files | Adapted concepts | Modifications | Audit status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightAgent | https://github.com/wanxingai/LightAgent | Apache-2.0 | `8ea4db3c9d8791e0977eea2a4481824441b4ba82` | Runtime foundation | Upstream repository snapshot | Agent loop, tool calling, workflows, hooks, tracing, provider integration | Translated README files removed. Sprint 1 adds narrow lazy imports for MCP and boto3 so optional integrations do not enter the core environment; no runtime behavior changes when their extras are installed. | Contract-tested |

Imported donor source may retain its original-language comments and messages. New and
modified Cognitive OS-owned content remains English-only, and donor exceptions stay within
the registered upstream boundary.

## Sprint 7 verification and evaluation references

| Project | Reviewed release | License | Use | Imported files | Security and update policy |
| --- | --- | --- | --- | --- | --- |
| sympy/sympy | 1.14.0 | BSD-3-Clause | Optional direct dependency for typed symbolic verification | None | Only manually constructed AST objects enter SymPy; update within the constrained major version after adversarial tests |
| Z3Prover/z3 | 4.16.0 | MIT | Optional direct dependency for typed logic verification | None | Raw SMT-LIB and arbitrary solver options are rejected; update after SAT/UNSAT/UNKNOWN regression |
| hgrecco/pint | 0.25.3 | BSD-3-Clause | Optional direct dependency for units and dimensions | None | Packaged definitions only; update after offset-unit and registry-sealing tests |
| UKGovernmentBEIS/inspect_ai | 0.3.246 | MIT | Export-format reference; runtime deferred | None | Never authoritative; current Click constraint is security-incompatible |
| UKGovernmentBEIS/inspect_evals | reviewed 2026-07-14 | MIT | Evaluation pattern reference only | None | No runtime dependency or automatic registration |
| swe-bench/SWE-bench | reviewed 2026-07-14 | MIT | Dataset metadata compatibility | None | No clone, download, execution, or gold-patch disclosure; revisions and dataset licenses are mandatory |

## Sprint 9 memory references

| Project | Reviewed release | License | Use | Authority status |
| --- | --- | --- | --- | --- |
| pgvector/pgvector | 0.8.2 | PostgreSQL | Direct PostgreSQL vector type and exact cosine operator | Infrastructure dependency; PostgreSQL remains authoritative |
| sentence-transformers | 5.x | Apache-2.0 | Optional preconfigured local embedding adapter | Non-authoritative; model output is revision-specific derived data |
| Cognee | reviewed 2026-07-15 | Apache-2.0 | Architecture reference only | Not a runtime dependency or store |
| Graphiti | reviewed 2026-07-15 | Apache-2.0 | Temporal-memory reference only | Deferred; not a runtime dependency or store |
| LangMem | reviewed 2026-07-15 | MIT | Governance reference only | No autonomous extraction or persistence |
| agentmemory | reviewed 2026-07-15 | MIT | Adapter-pattern reference only | Not a backend or authority |

## Sprint 10 semantic-memory references

| Project | Reviewed release | License | Use | Authority status |
| --- | --- | --- | --- | --- |
| LLM Wiki | Sprint 10 concept specification | Project specification | Deterministic page layout and lineage concept | Derived projection only |
| Graphiti | reviewed 2026-07-15 | Apache-2.0 | Temporal graph algorithm and reference donor | No runtime dependency or store |
| Cognee | reviewed 2026-07-15 | Apache-2.0 | Ingestion and graph architecture reference | No runtime dependency or store |
| NetworkX | 3.6.1 | BSD-3-Clause | Optional bounded in-process graph analysis | Non-authoritative `semantic-graph` extra; removable |

## Sprint 11 context-retrieval references

| Project | License | Use | Security, maintenance, and removal decision |
| --- | --- | --- | --- |
| Haystack | Apache-2.0 | Pipeline-pattern donor only | No runtime dependency; host services replace it completely |
| LlamaIndex | MIT | Retriever-pattern donor only | No runtime dependency; host ports replace it completely |
| Sentence Transformers CrossEncoder | Apache-2.0 | Optional local reranker experiment | Preconfigured local model only; removable extra if promoted |
| RAGatouille | Apache-2.0 | Rejected experimental reranker candidate | No core dependency; transitive and model risks exceed unmeasured value |
| pgvector | PostgreSQL | Existing exact cosine retrieval | Existing `memory-postgres` extra; no ANN index by default |
| NetworkX | BSD-3-Clause | Existing optional bounded graph projection | PostgreSQL remains authoritative; removable without core changes |

No donor becomes the central Context Builder runtime. Optional rerankers require measured relevance,
latency, provenance, scope, and sensitivity results before promotion.

## Sprint 13 strategic-memory references

| Project | License | Use | Authority and dependency decision |
| --- | --- | --- | --- |
| NetworkX | BSD-3-Clause | Optional disposable strategy-graph comparison | Existing `semantic-graph` extra only; PostgreSQL and the core traversal remain authoritative |
| LangGraph | MIT | Strategy/workflow architecture reference only | No runtime dependency, state ownership, planner, or execution authority |
| Graphiti | Apache-2.0 | Evolution-graph terminology reference only | No graph database, ingestion path, or authority |

Sprint 13 adds no dependency. The Strategy Evolution Graph reuses the standard library,
SQLAlchemy Core, PostgreSQL, Pydantic, existing Controller contracts, and the Sprint 12 Skill
Registry.

## Sprint 14 experience-compilation references

| Project | License | Use | Authority, maintenance, and removal decision |
| --- | --- | --- | --- |
| LangMem | MIT | Reflection and memory-candidate pattern donor | No dependency, persistence, extraction runtime, or promotion authority; concepts are replaced by deterministic host code |
| agentmemory | MIT | Coding-session capture and trajectory-hook reference | No dependency or backend; existing event and artifact contracts replace it |
| Cognee | Apache-2.0 | Ingest and semantic-extraction pipeline reference | No dependency, graph store, source resolver, or destination authority |
| GEPA | Apache-2.0 | Trajectory reflection and feedback-pattern reference | No optimization runtime, provider authority, or automatic harness change; deferred to later proposal work |

Sprint 14 adds no dependency. The compiler uses the standard library, Pydantic, existing SQLAlchemy
Core and PostgreSQL extras, existing provider boundaries, and existing event, artifact, verifier,
benchmark, skill, and strategy contracts. Every donor is pattern-only and can be removed without a
runtime or schema change.

## Sprint 16 routing references

| Project | License | Use | Authority and dependency decision |
| --- | --- | --- | --- |
| RouteLLM | Apache-2.0 | Routing algorithm and benchmark pattern donor | No dependency, provider runtime, learned policy, or capability authority |
| LiteLLM | MIT | Optional provider-normalization reference | Not adopted; the existing Cognitive OS provider layer remains primary |

Sprint 16 adds no dependency. Deterministic host-owned scoring, `Decimal`, standard-library
statistics, existing Pydantic contracts, SQLAlchemy Core, PostgreSQL, provider, Controller, Context,
and verifier boundaries cover the required scope. Either reference can be removed without changing
the runtime or schema.

## Sprint 17 weakness-mining references

| Project | License | Use | Authority and dependency decision |
| --- | --- | --- | --- |
| Langfuse | MIT | Trace-input adapter and observability pattern | Optional input pattern only; not a source authority or dependency |
| Inspect AI | MIT | Evaluation and benchmark reference | Existing reference only; no diagnostic authority |
| NetworkX | BSD-3-Clause | Optional bounded cluster comparison | Existing optional extra; PostgreSQL and exact groups remain authoritative |
| scikit-learn | BSD-3-Clause | Experimental clustering candidate | Not added; requires benchmark and dependency review |
| HDBSCAN | BSD-3-Clause | Experimental density clustering candidate | Not added; requires benchmark and dependency review |
| GEPA | Apache-2.0 | Sprint 18 proposal-pattern donor | Deferred; no Sprint 17 runtime, optimizer, or authority |

Sprint 17 adds no dependency. Standard-library hashing, sorting and `Decimal`, Pydantic,
SQLAlchemy Core, PostgreSQL, and existing host services implement the core. Optional clustering can
be removed without changing exact grouping, persistence, lifecycle, or queue semantics.

## Sprint 18 proposal-engine references

| Project | License | Use | Authority and dependency decision |
| --- | --- | --- | --- |
| EvoAgentX | MIT | Proposal and workflow research patterns | Conceptual study only; no dependency, copied code, optimizer, or authority |
| GEPA | Apache-2.0 | Reflective proposal pattern | Conceptual study only; no runtime, model download, or authority |
| DSPy | MIT | Declarative optimization pattern | Conceptual study only; no dependency, teleprompter, or provider authority |

Sprint 18 adds no dependency and changes no lockfile. Existing Pydantic, SQLAlchemy, Alembic,
asyncpg, pytest, and Hypothesis surfaces are sufficient. Any future code reuse requires exact file
and commit provenance, license and notice review, dependency justification, and a separate ADR.
