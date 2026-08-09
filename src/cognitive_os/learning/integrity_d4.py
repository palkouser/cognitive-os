"""S21D4-081: the eleven released classes over D4's evidence, and a twelfth for the denominator.

`integrity_d3.py` reads D3's committed evidence and reports eleven classes in four states. D4
needs the same report over its own files and one class D3 could not have had, so this module is
the D4 half rather than a rewrite: the four states, the class record, the report shape and the
predecessor fingerprint are all imported from the released module and none of them is
reimplemented. What is written here is only what reads different bytes.

The twelfth class is `decision_independence`, and it exists because of the erratum. D3 reported
120 metamorphic ranking decisions that were 20 decisions replicated six times, and every rate in
that sprint was taken over the 120. Revision 4's rule is that a rate names its denominator and
that denominator is the independent count -- so this class fails when any committed D4 file
names a different one, when a census does not add up, or when a record claims more distinct
decisions than it counted.

It also fails when it finds nothing to check. A class that reports `clean` over an empty scan is
the defect this sprint has now caught four times, and a denominator check that never found a
denominator is exactly that shape.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    INDEPENDENT_DENOMINATOR,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.integrity_d3 import (
    D3IntegrityClass,
    D3IntegrityState,
    path_and_size_fingerprint,
)

#: The four states are the released four. A fifth state would be a second answer to the only
#: question this report asks, and `warning` versus `not_opened` is the distinction that carries
#: both waves: one is a check nobody ran, the other is a decision something made by hash.
D4IntegrityState = D3IntegrityState
D4IntegrityClass = D3IntegrityClass

#: Every class, in the order S21D4-081 lists them: the eleven released ones, then the new one.
#: Fixed, so a report that silently stopped covering one is a diff rather than an absence.
D4_INTEGRITY_CLASSES: tuple[str, ...] = (
    "explicit_member_selection",
    "duplicate_executions_or_seals",
    "chronology",
    "feature_schema",
    "matrix_embedding_scans",
    "ood_units",
    "holdout_access",
    "retrieval_one_read",
    "artifact_bytes",
    "lifecycle",
    "isolation",
    "decision_independence",
)

PRE_REGISTRATION = "pre-registration"


@dataclass(frozen=True, slots=True)
class D4IntegrityReport:
    classes: tuple[D4IntegrityClass, ...]

    def _of(self, state: D3IntegrityState) -> tuple[str, ...]:
        return tuple(item.name for item in self.classes if item.state is state)

    @property
    def failed(self) -> tuple[str, ...]:
        return self._of(D3IntegrityState.FAILED)

    @property
    def warnings(self) -> tuple[str, ...]:
        return self._of(D3IntegrityState.WARNING)

    @property
    def not_opened(self) -> tuple[str, ...]:
        return self._of(D3IntegrityState.NOT_OPENED)

    @property
    def clean(self) -> tuple[str, ...]:
        return self._of(D3IntegrityState.CLEAN)

    @property
    def healthy(self) -> bool:
        """A warning is not a failure. An unchecked class is never a pass."""
        return not self.failed

    def as_dict(self) -> dict[str, Any]:
        return {
            "classes": [item.as_dict() for item in self.classes],
            "covered": list(D4_INTEGRITY_CLASSES),
            "failed": list(self.failed),
            "warnings": list(self.warnings),
            "not_opened": list(self.not_opened),
            "clean": list(self.clean),
            "healthy": self.healthy,
        }


class Evidence:
    """One sprint's committed evidence directory, read lazily and cached.

    An absent file is `None` rather than an exception: which classes that makes `NOT_OPENED` and
    which it makes `FAILED` is a decision each check makes for itself.

    Files are addressed by their suffix — `read("snapshots")` — because the successors of this
    report read the same documents under their own prefix. S21D5-081: the checks below that only
    differed from D5's by the four characters of a sprint name are shared rather than copied,
    and the three that read genuinely different bytes are written again in `integrity_d5`.
    """

    def __init__(self, directory: Path, prefix: str = "sprint-21d4") -> None:
        self.directory = directory
        self.prefix = prefix
        self._cache: dict[str, dict[str, Any] | None] = {}

    def name(self, suffix: str) -> str:
        return f"{self.prefix}-{suffix}.json"

    def __call__(self, suffix: str) -> dict[str, Any] | None:
        name = self.name(suffix)
        if name not in self._cache:
            path = self.directory / name
            self._cache[name] = (
                json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
            )
        return self._cache[name]

    def sha256(self, suffix: str) -> str | None:
        path = self.directory / self.name(suffix)
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

    def documents(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Every committed file of this sprint, by filename, in name order."""
        for path in sorted(self.directory.glob(f"{self.prefix}-*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            self._cache.setdefault(path.name, document)
            yield path.name, document


def integrity_class(
    name: str, state: D3IntegrityState, detail: str, *evidence: str
) -> D4IntegrityClass:
    return D4IntegrityClass(name=name, state=state, detail=detail, evidence=evidence)


def missing_evidence(name: str, *files: str) -> D4IntegrityClass:
    """No evidence at all. Failed, not not-opened: nothing declared this class closed."""
    return integrity_class(
        name,
        D3IntegrityState.FAILED,
        f"no evidence to check: {', '.join(files)} is absent",
        *files,
    )


# ---------------------------------------------------------------------------- the twelve classes


def explicit_member_selection(read: Evidence) -> D4IntegrityClass:
    """Every materialised dataset names its members and rebuilds to the same bytes."""
    name = "explicit_member_selection"
    snapshots = read("snapshots")
    seals = read("sealed-manifests")
    files = (read.name("snapshots"), read.name("sealed-manifests"))
    if snapshots is None or seals is None:
        return missing_evidence(name, *files)

    datasets = snapshots.get("datasets") or []
    catalogues = seals.get("catalogues") or {}
    if not datasets or not catalogues:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{len(datasets)} datasets against {len(catalogues)} sealed catalogues; a member "
            "check over nothing is not a member check",
            *files,
        )
    drift = sorted(
        str(row.get("partition")) for row in datasets if not row.get("rebuilt_identically")
    )
    unresolved = sorted(
        str(row.get("partition"))
        for row in datasets
        if not row.get("split_manifest_hash") or not row.get("example_manifest_hash")
    )
    if drift or unresolved:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"datasets that do not rebuild {drift} or do not name their members {unresolved}",
            *files,
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(datasets)} datasets rebuild identically from {len(catalogues)} sealed catalogues",
        *files,
    )


def duplicate_executions_or_seals(read: Evidence) -> D4IntegrityClass:
    """Both campaigns sealed once, resumed to an empty remainder, and started no container."""
    name = "duplicate_executions_or_seals"
    suffixes = ("self-play-campaign", "calibration-campaign")
    files = tuple(read.name(item) for item in suffixes)
    absent = sorted(read.name(item) for item in suffixes if read(item) is None)
    if absent:
        return missing_evidence(name, *absent)
    campaigns = {
        read.name(item): document for item in suffixes if (document := read(item)) is not None
    }

    contradicted: list[str] = []
    unfinished: list[str] = []
    repeated: list[str] = []
    for label, campaign in campaigns.items():
        resume = campaign.get("resume") or {}
        if not resume.get("receipt_is_resumable", False):
            contradicted.append(label)
        if resume.get("receipt_effective_remainder"):
            unfinished.append(label)
        if resume.get("containers_started_on_the_replay", 0):
            repeated.append(label)
    if contradicted or unfinished or repeated:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"contradicted receipts {contradicted}, unfinished {unfinished}, "
            f"re-executed on replay {repeated}",
            *files,
        )
    replayed = sum(
        int(campaign.get("resume", {}).get("runs_replayed", 0)) for campaign in campaigns.values()
    )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(campaigns)} partitions sealed once; {replayed} runs replayed from receipts with "
        "nothing remaining and no container started",
        *files,
    )


def chronology(read: Evidence) -> D4IntegrityClass:
    name = "chronology"
    pre = read(PRE_REGISTRATION)
    if pre is None:
        return missing_evidence(name, read.name(PRE_REGISTRATION))
    digest = read.sha256(PRE_REGISTRATION)
    published = datetime.fromisoformat(str(pre["recorded_at"]).replace("Z", "+00:00"))

    bound: list[str] = []
    unbound: list[str] = []
    early: list[str] = []
    for filename, document in read.documents():
        if filename == read.name(PRE_REGISTRATION):
            continue
        if "pre_registration_sha256" not in document:
            continue
        bound.append(filename)
        if document["pre_registration_sha256"] != digest:
            unbound.append(filename)
        elif (
            datetime.fromisoformat(str(document["recorded_at"]).replace("Z", "+00:00")) < published
        ):
            early.append(filename)
    if not bound:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "no committed file binds the pre-registration, so nothing was checked",
            read.name(PRE_REGISTRATION),
        )
    if unbound or early:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"bound to other bytes {sorted(unbound)}, recorded before publication {sorted(early)}",
            read.name(PRE_REGISTRATION),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(bound)} files bind {digest[:12] if digest else ''} and follow it",
        read.name(PRE_REGISTRATION),
        *bound,
    )


def _feature_schema(read: Evidence) -> D4IntegrityClass:
    name = "feature_schema"
    contracts = read("contracts")
    if contracts is None:
        return missing_evidence(name, read.name("contracts"))
    declared = CorrectionFeatureContractV2().content_hash
    if find_hash(contracts, declared) is None:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the released v2 feature contract hashes to {declared[:12]}, which the frozen "
            "revision-4 contract record does not contain",
            read.name("contracts"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"the released v2 feature contract still hashes to the frozen {declared[:12]}",
        read.name("contracts"),
    )


def _matrix_embedding_scans(read: Evidence) -> D4IntegrityClass:
    name = "matrix_embedding_scans"
    snapshots = read("snapshots")
    if snapshots is None:
        return missing_evidence(name, read.name("snapshots"))
    matrix = snapshots.get("fitted_matrix") or {}
    scans = snapshots.get("scans") or {}
    dimensions = int(matrix.get("fitted_dimensions", 0))
    expected = len(FITTED_FEATURE_V2_ALLOWLIST)
    required = int(scans.get("required", 0))
    ran = int(scans.get("count", 0))
    failed = list(scans.get("failed") or [])
    if dimensions != expected:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the fitted matrix scanned {dimensions} dimensions against the contract's {expected}",
            read.name("snapshots"),
        )
    if not required or ran < required or failed:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{ran} of {required} scans ran and {len(failed)} failed: {failed}",
            read.name("snapshots"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"all {expected} fitted dimensions are in the scanned matrix, embedding included, and "
        f"{ran} scans passed",
        read.name("snapshots"),
    )


def ood_units(read: Evidence) -> D4IntegrityClass:
    """D4's form of the erratum: a transformed case is a replica, not a new decision.

    D3 asked whether ranking decisions and candidate outcomes were counted apart. D4 asks the
    sharper question the erratum forced, on the record that measured it: the invariance sample
    encodes forty transformed decisions onto twenty clean vectors, and a census reporting those
    as forty independent decisions would be D3's collapse happening again.
    """
    name = "ood_units"
    regression = read("invariance-regression")
    if regression is None:
        return missing_evidence(name, read.name("invariance-regression"))
    independence = regression.get("independence") or {}
    census = independence.get("census_over_clean_and_transformed") or {}
    nominal = int(census.get("nominal_decisions", 0))
    independent = int(census.get("independent_decisions", 0))
    replicated = int(census.get("replicated_decisions", 0))
    if not nominal:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "the invariance record carries no census, so nothing counted the transformed cases",
            read.name("invariance-regression"),
        )
    if nominal == independent:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"all {nominal} counted decisions are reported as distinct; a semantics-preserving "
            "transform that produced a new fitted vector is an encoder regression, and one that "
            "did not is a replica the census must name",
            read.name("invariance-regression"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{nominal} counted decisions over {independent} distinct fitted vectors, "
        f"{replicated} named as replicas",
        read.name("invariance-regression"),
    )


def holdout_access(
    read: Evidence, checkpoint_suffix: str = "pre-final-checkpoint"
) -> D4IntegrityClass:
    """Nobody looked at a final or canary outcome, and the record that clocks it agrees.

    The clocked record is D4's pre-final checkpoint and D5's continuation decision: two names
    for the same field, so the suffix is an argument rather than two copies of the check.
    """
    name = "holdout_access"
    checkpoint = read(checkpoint_suffix)
    claimed: list[str] = []
    checked: list[str] = []
    for filename, document in read.documents():
        if "final_outcomes_inspected" not in document:
            continue
        checked.append(filename)
        if document["final_outcomes_inspected"]:
            claimed.append(filename)
    if not checked:
        return missing_evidence(name, "any file recording final_outcomes_inspected")
    if claimed:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"files reporting that a final outcome was inspected: {sorted(claimed)}",
            *claimed,
        )
    if checkpoint is not None and checkpoint["final_or_canary_outcomes_inspected"] != 0:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{read.name(checkpoint_suffix)} counted a final or canary outcome at its clock",
            read.name(checkpoint_suffix),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(checked)} files report zero final or canary access",
        *checked,
    )


def retrieval_one_read(read: Evidence) -> D4IntegrityClass:
    name = "retrieval_one_read"
    holdout = read("retrieval-holdout-result")
    decision = read("retrieval-decision")
    files = (read.name("retrieval-holdout-result"), read.name("retrieval-decision"))
    if holdout is None or decision is None:
        return missing_evidence(name, *files)
    executions = int(holdout.get("executions", 0))
    if executions != 1:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the holdout benchmark was executed {executions} times; the protocol allows one",
            *files,
        )
    opened = decision.get("no_alternative_opened") or {}
    reopened = sorted(key for key, value in opened.items() if value)
    if reopened:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the negative holdout was followed by reopened choices: {reopened}",
            *files,
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"read once; winning arm {decision.get('winning_arm')!r}, first failed floor "
        f"{decision.get('first_failed_floor')!r}, {len(opened)} classes of alternative reopened "
        "zero times",
        *files,
    )


def artifact_bytes(blobs: Mapping[str, str | None] | None) -> D4IntegrityClass:
    """Declared address to observed hash. `None` means a row with no bytes behind it."""
    name = "artifact_bytes"
    if blobs is None:
        return integrity_class(
            name,
            D3IntegrityState.WARNING,
            "not checked: this report was run without an artifact store, and a class nobody "
            "checked is never reported as clean",
        )
    if not blobs:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "the store was opened and holds no blobs at all, which is a rehash of nothing "
            "rather than a clean store",
        )
    absent = sorted(key for key, observed in blobs.items() if observed is None)
    mismatched = sorted(
        key for key, observed in blobs.items() if observed is not None and observed != key
    )
    if absent or mismatched:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{len(absent)} declared blobs have no bytes {[item[:12] for item in absent[:5]]}; "
            f"{len(mismatched)} do not hash to their name "
            f"{[item[:12] for item in mismatched[:5]]}",
        )
    return integrity_class(
        name, D3IntegrityState.CLEAN, f"{len(blobs)} blobs rehash to their content address"
    )


def _lifecycle(read: Evidence) -> D4IntegrityClass:
    name = "lifecycle"
    checkpoint = read("pre-final-checkpoint")
    if checkpoint is None:
        return missing_evidence(name, read.name("pre-final-checkpoint"))
    decision = checkpoint["decision"]
    records = checkpoint["not_opened"]
    if decision["authorised"]:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "final access is recorded as authorised, which no later evidence supports",
            read.name("pre-final-checkpoint"),
        )
    stops = {item["stop_hash"] for item in records}
    untyped = [item["item"] for item in records if item.get("status") != "not_opened"]
    if len(stops) != 1 or untyped:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{len(stops)} stop hashes across the not-opened map; untyped records {untyped}",
            read.name("pre-final-checkpoint"),
        )
    return integrity_class(
        name,
        D3IntegrityState.NOT_OPENED,
        f"no component was registered; {len(records)} dependent tasks bound to stop "
        f"{next(iter(stops))[:12]}",
        read.name("pre-final-checkpoint"),
    )


def isolation(read: Evidence, fingerprints: Mapping[str, str] | None) -> D4IntegrityClass:
    name = "isolation"
    baseline = read("baseline")
    if baseline is None:
        return missing_evidence(name, read.name("baseline"))
    declared = {
        key: value["path_and_size_fingerprint_sha256"]
        for key, value in baseline["predecessor_artifact_stores"].items()
    }
    if fingerprints is None:
        return integrity_class(
            name,
            D3IntegrityState.WARNING,
            f"not checked: {len(declared)} predecessor fingerprints are declared but no data "
            "root was given to re-take them",
            read.name("baseline"),
        )
    unchecked = sorted(set(declared) - set(fingerprints))
    moved = sorted(
        key for key, value in declared.items() if fingerprints.get(key) not in (None, value)
    )
    if moved:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"predecessor stores whose fingerprint changed: {moved}",
            read.name("baseline"),
        )
    if unchecked:
        return integrity_class(
            name,
            D3IntegrityState.WARNING,
            f"{len(declared) - len(unchecked)} of {len(declared)} predecessor stores reproduce "
            f"their released fingerprint; not present to re-take: {unchecked}",
            read.name("baseline"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"all {len(declared)} predecessor stores reproduce their released fingerprint",
        read.name("baseline"),
    )


def decision_independence(read: Evidence) -> D4IntegrityClass:
    """S21D4-081's new class: no rate over a nominal denominator, anywhere in the evidence.

    Three ways the erratum could come back, and one way this check could be worthless:

    *A named nominal denominator.* Revision 4 makes every rate carry `rate_denominator`, so a
    record taking a rate over the counted decisions rather than the distinct ones says so in its
    own bytes.

    *A census that does not add up.* Nominal must be independent plus replicated. A triple that
    does not is a census someone wrote rather than computed.

    *More distinct decisions than counted ones.* Independence is a partition of what was
    counted; it cannot exceed it.

    And the fourth: finding nothing. A denominator check that scanned no denominators is the
    same defect as an `all()` over an empty set, so it fails rather than passing.
    """
    name = "decision_independence"
    wrong_denominator: list[str] = []
    broken: list[str] = []
    impossible: list[str] = []
    censuses = 0
    denominators = 0
    files: list[str] = []

    for filename, document in read.documents():
        touched = False
        for where, node in _objects(document):
            declared = node.get("rate_denominator")
            if isinstance(declared, str):
                denominators += 1
                touched = True
                if declared != INDEPENDENT_DENOMINATOR:
                    wrong_denominator.append(f"{filename}{where}={declared}")
            nominal = node.get("nominal_decisions")
            independent = node.get("independent_decisions")
            if not isinstance(nominal, int) or not isinstance(independent, int):
                continue
            censuses += 1
            touched = True
            if independent > nominal:
                impossible.append(f"{filename}{where}: {independent} of {nominal}")
            replicated = node.get("replicated_decisions")
            if isinstance(replicated, int) and nominal != independent + replicated:
                broken.append(f"{filename}{where}: {nominal} != {independent} + {replicated}")
        if touched:
            files.append(filename)

    if not censuses and not denominators:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "no committed file reports a decision count or names a denominator, so this class "
            "checked nothing and must not report that nothing is wrong",
        )
    if wrong_denominator or broken or impossible:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"rates over a nominal denominator {sorted(wrong_denominator)[:5]}; censuses that do "
            f"not add up {sorted(broken)[:5]}; more distinct than counted "
            f"{sorted(impossible)[:5]}",
            *files,
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"{censuses} decision counts and {denominators} named denominators across {len(files)} "
        f"files, every rate over {INDEPENDENT_DENOMINATOR}",
        *files,
    )


def _objects(node: Any, where: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    """Every JSON object in a document, with the path that reaches it."""
    if isinstance(node, dict):
        yield where, node
        for key, value in node.items():
            yield from _objects(value, f"{where}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _objects(value, f"{where}[{index}]")


def find_hash(document: Any, wanted: str) -> str | None:
    """Whether `wanted` appears anywhere in a committed contract record, at any depth."""
    if isinstance(document, str):
        return wanted if document == wanted else None
    if isinstance(document, dict):
        for value in document.values():
            found = find_hash(value, wanted)
            if found is not None:
                return found
    if isinstance(document, list):
        for value in document:
            found = find_hash(value, wanted)
            if found is not None:
                return found
    return None


def d4_integrity(
    evidence_directory: Path,
    *,
    blob_hashes: Mapping[str, str | None] | None = None,
    predecessor_fingerprints: Mapping[str, str] | None = None,
) -> D4IntegrityReport:
    """Read the committed evidence and report every class. Never writes, never connects.

    Both authorities are optional and both report `WARNING` when absent, because this report has
    to be runnable in a lane that has neither — and a lane that reported them clean anyway would
    be worse than a lane that did not run.
    """
    read = Evidence(evidence_directory)
    classes = (
        explicit_member_selection(read),
        duplicate_executions_or_seals(read),
        chronology(read),
        _feature_schema(read),
        _matrix_embedding_scans(read),
        ood_units(read),
        holdout_access(read),
        retrieval_one_read(read),
        artifact_bytes(blob_hashes),
        _lifecycle(read),
        isolation(read, predecessor_fingerprints),
        decision_independence(read),
    )
    ordered = {item.name: item for item in classes}
    return D4IntegrityReport(classes=tuple(ordered[name] for name in D4_INTEGRITY_CLASSES))


#: The nine checks below the line are shared with `integrity_d5`; the three above it —
#: `_feature_schema`, `_matrix_embedding_scans` and `_lifecycle` — stay private because D5 reads
#: different bytes for them and writes its own.
__all__ = [
    "D4_INTEGRITY_CLASSES",
    "D4IntegrityClass",
    "D4IntegrityReport",
    "D4IntegrityState",
    "Evidence",
    "artifact_bytes",
    "chronology",
    "d4_integrity",
    "decision_independence",
    "duplicate_executions_or_seals",
    "explicit_member_selection",
    "find_hash",
    "holdout_access",
    "integrity_class",
    "isolation",
    "missing_evidence",
    "ood_units",
    "path_and_size_fingerprint",
    "retrieval_one_read",
]
