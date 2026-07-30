"""The frozen retrieval benchmark, §S21C3-053.

Two records per repair task, sixty in all across the six families:

* a **task** record — what the module is for, what was reported, what is expected;
* a **correction** record — why the code was wrong and which edges the repair has to hold.

The split is not decoration. It is what makes the benchmark able to fail: with one record per
task, any query that lands in the right group is automatically correct, and recall@5 over
thirty records measures nothing. With two, a query about a *symptom* and a query about a
*cause* point at different records inside the same group, and a retriever that only understands
which topic it is looking at scores worse than one that understands what is being asked.

`split_group_key` from S21C3-035 is the group here too — one repository group per task — so a
relevant record is always inside its own group and §4.15's cross-group leakage check is a
property this construction can be audited against rather than an outcome to hope for.

The manifest hash covers every document, every query and every relevance judgment. It is what
a later run cites to say it measured the same benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .reality_retrieval_queries import QUERIES, QUERY_KINDS
from .reality_task_specs import TASK_SPECS, TaskSpec

BENCHMARK_PROFILE_ID = "sprint21c3-retrieval-benchmark-v1"

#: Which record each query shape is asking for. A query never names a document, so retargeting
#: relevance means changing this table — one visible edit, not sixty invisible ones.
RELEVANT_KINDS: dict[str, tuple[str, ...]] = {
    "terminology": ("task",),
    "symptom": ("task",),
    "failure": ("correction",),
    "correction": ("correction",),
    "analogous": ("task", "correction"),
}


@dataclass(frozen=True, slots=True)
class BenchmarkDocument:
    """One retrievable record."""

    document_id: str
    group: str
    family: str
    kind: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One query and the records that answer it."""

    case_id: str
    group: str
    family: str
    kind: str
    text: str
    relevant: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalBenchmark:
    documents: tuple[BenchmarkDocument, ...]
    cases: tuple[BenchmarkCase, ...]
    manifest_hash: str


def _task_document(spec: TaskSpec) -> BenchmarkDocument:
    return BenchmarkDocument(
        document_id=f"{spec.template_id}:task",
        group=spec.repository_group,
        family=str(spec.family),
        kind="task",
        title=f"{spec.module}: reported defect",
        text="\n".join((spec.module_doc, spec.issue, spec.expected)),
    )


def _correction_document(spec: TaskSpec) -> BenchmarkDocument:
    return BenchmarkDocument(
        document_id=f"{spec.template_id}:correction",
        group=spec.repository_group,
        family=str(spec.family),
        kind="correction",
        title=f"{spec.module}: cause and repair",
        text="\n".join((f"Cause: {spec.baseline_reason}", *spec.edge_cases)),
    )


def build_benchmark() -> RetrievalBenchmark:
    """The whole benchmark, derived. Regenerating it on another machine is the same hash."""
    documents = tuple(
        document
        for spec in TASK_SPECS
        for document in (_task_document(spec), _correction_document(spec))
    )
    by_template = {spec.template_id: spec for spec in TASK_SPECS}
    cases = []
    for index, (template_id, kind, text) in enumerate(QUERIES):
        spec = by_template[template_id]
        cases.append(
            BenchmarkCase(
                case_id=f"q{index:03d}:{template_id}:{kind}",
                group=spec.repository_group,
                family=str(spec.family),
                kind=kind,
                text=text,
                relevant=tuple(
                    f"{template_id}:{document_kind}" for document_kind in RELEVANT_KINDS[kind]
                ),
            )
        )
    return RetrievalBenchmark(
        documents=documents,
        cases=tuple(cases),
        manifest_hash=_manifest_hash(documents, tuple(cases)),
    )


def _manifest_hash(
    documents: tuple[BenchmarkDocument, ...], cases: tuple[BenchmarkCase, ...]
) -> str:
    lines = [f"{document.document_id}|{document.group}|{document.text}" for document in documents]
    lines += [
        f"{case.case_id}|{case.group}|{case.text}|{','.join(case.relevant)}" for case in cases
    ]
    return sha256("\n".join(lines).encode()).hexdigest()


def cross_group_leakage(benchmark: RetrievalBenchmark) -> tuple[str, ...]:
    """Cases whose relevant records live outside the case's own group. Must be empty. §4.15."""
    groups = {document.document_id: document.group for document in benchmark.documents}
    return tuple(
        case.case_id
        for case in benchmark.cases
        if any(groups.get(document_id) != case.group for document_id in case.relevant)
    )


def kind_counts(benchmark: RetrievalBenchmark) -> dict[str, int]:
    return {kind: sum(1 for case in benchmark.cases if case.kind == kind) for kind in QUERY_KINDS}
