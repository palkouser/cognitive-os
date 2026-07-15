# Semantic-memory configuration

Copy `config/semantic_memory.example.yaml` to a host-controlled location and pass it to
`scripts/semantic.py --config`. Unknown fields and unsafe feature flags fail validation. The host
owns observation, claim, evidence, relation, source-span, excerpt, statement, subject, object,
graph, temporal-result, Wiki, provider-call, elapsed-time, contradiction, and confidence limits.

Automatic extraction and automatic supported promotion are false. Provider direct commit,
unknown predicates, graph databases, generated Wiki narrative, and hybrid retrieval cannot be
enabled in Sprint 10. Provider responses cannot increase any limit or change scope and sensitivity.
Access-audit failure defaults to fail closed.

Core semantic contracts require no extra. PostgreSQL persistence uses `memory-postgres`. Optional
NetworkX analysis uses `semantic-graph`; persistence and the bounded stdlib graph traversal work
without it. No model, network download, GPU, Graphiti, or Cognee package is required.
