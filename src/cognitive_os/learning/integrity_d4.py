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

PRE_REGISTRATION = "sprint-21d4-pre-registration.json"
EVIDENCE_GLOB = "sprint-21d4-*.json"


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


class _Evidence:
    """The committed evidence directory, read lazily and cached.

    An absent file is `None` rather than an exception: which classes that makes `NOT_OPENED` and
    which it makes `FAILED` is a decision each check makes for itself.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._cache: dict[str, dict[str, Any] | None] = {}

    def __call__(self, name: str) -> dict[str, Any] | None:
        if name not in self._cache:
            path = self.directory / name
            self._cache[name] = (
                json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
            )
        return self._cache[name]

    def sha256(self, name: str) -> str | None:
        path = self.directory / name
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _class(name: str, state: D3IntegrityState, detail: str, *evidence: str) -> D4IntegrityClass:
    return D4IntegrityClass(name=name, state=state, detail=detail, evidence=evidence)


def _missing(name: str, *files: str) -> D4IntegrityClass:
    """No evidence at all. Failed, not not-opened: nothing declared this class closed."""
    return _class(
        name,
        D3IntegrityState.FAILED,
        f"no evidence to check: {', '.join(files)} is absent",
        *files,
    )


# ---------------------------------------------------------------------------- the twelve classes


def _explicit_member_selection(read: _Evidence) -> D4IntegrityClass:
    """Every materialised dataset names its members and rebuilds to the same bytes."""
    name = "explicit_member_selection"
    snapshots = read("sprint-21d4-snapshots.json")
    seals = read("sprint-21d4-sealed-manifests.json")
    files = ("sprint-21d4-snapshots.json", "sprint-21d4-sealed-manifests.json")
    if snapshots is None or seals is None:
        return _missing(name, *files)

    datasets = snapshots.get("datasets") or []
    catalogues = seals.get("catalogues") or {}
    if not datasets or not catalogues:
        return _class(
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
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"datasets that do not rebuild {drift} or do not name their members {unresolved}",
            *files,
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(datasets)} datasets rebuild identically from {len(catalogues)} sealed catalogues",
        *files,
    )


def _duplicate_executions_or_seals(read: _Evidence) -> D4IntegrityClass:
    """Both campaigns sealed once, resumed to an empty remainder, and started no container."""
    name = "duplicate_executions_or_seals"
    files = ("sprint-21d4-self-play-campaign.json", "sprint-21d4-calibration-campaign.json")
    absent = sorted(item for item in files if read(item) is None)
    if absent:
        return _missing(name, *absent)
    campaigns = {item: document for item in files if (document := read(item)) is not None}

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
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"contradicted receipts {contradicted}, unfinished {unfinished}, "
            f"re-executed on replay {repeated}",
            *files,
        )
    replayed = sum(
        int(campaign.get("resume", {}).get("runs_replayed", 0)) for campaign in campaigns.values()
    )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(campaigns)} partitions sealed once; {replayed} runs replayed from receipts with "
        "nothing remaining and no container started",
        *files,
    )


def _chronology(read: _Evidence) -> D4IntegrityClass:
    name = "chronology"
    pre = read(PRE_REGISTRATION)
    if pre is None:
        return _missing(name, PRE_REGISTRATION)
    digest = read.sha256(PRE_REGISTRATION)
    published = datetime.fromisoformat(str(pre["recorded_at"]).replace("Z", "+00:00"))

    bound: list[str] = []
    unbound: list[str] = []
    early: list[str] = []
    for path in sorted(read.directory.glob(EVIDENCE_GLOB)):
        if path.name == PRE_REGISTRATION:
            continue
        document = read(path.name)
        if document is None or "pre_registration_sha256" not in document:
            continue
        bound.append(path.name)
        if document["pre_registration_sha256"] != digest:
            unbound.append(path.name)
        elif (
            datetime.fromisoformat(str(document["recorded_at"]).replace("Z", "+00:00")) < published
        ):
            early.append(path.name)
    if not bound:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "no committed file binds the pre-registration, so nothing was checked",
            PRE_REGISTRATION,
        )
    if unbound or early:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"bound to other bytes {sorted(unbound)}, recorded before publication {sorted(early)}",
            PRE_REGISTRATION,
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(bound)} files bind {digest[:12] if digest else ''} and follow it",
        PRE_REGISTRATION,
        *bound,
    )


def _feature_schema(read: _Evidence) -> D4IntegrityClass:
    name = "feature_schema"
    contracts = read("sprint-21d4-contracts.json")
    if contracts is None:
        return _missing(name, "sprint-21d4-contracts.json")
    declared = CorrectionFeatureContractV2().content_hash
    if _find_hash(contracts, declared) is None:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the released v2 feature contract hashes to {declared[:12]}, which the frozen "
            "revision-4 contract record does not contain",
            "sprint-21d4-contracts.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"the released v2 feature contract still hashes to the frozen {declared[:12]}",
        "sprint-21d4-contracts.json",
    )


def _matrix_embedding_scans(read: _Evidence) -> D4IntegrityClass:
    name = "matrix_embedding_scans"
    snapshots = read("sprint-21d4-snapshots.json")
    if snapshots is None:
        return _missing(name, "sprint-21d4-snapshots.json")
    matrix = snapshots.get("fitted_matrix") or {}
    scans = snapshots.get("scans") or {}
    dimensions = int(matrix.get("fitted_dimensions", 0))
    expected = len(FITTED_FEATURE_V2_ALLOWLIST)
    required = int(scans.get("required", 0))
    ran = int(scans.get("count", 0))
    failed = list(scans.get("failed") or [])
    if dimensions != expected:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the fitted matrix scanned {dimensions} dimensions against the contract's {expected}",
            "sprint-21d4-snapshots.json",
        )
    if not required or ran < required or failed:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{ran} of {required} scans ran and {len(failed)} failed: {failed}",
            "sprint-21d4-snapshots.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"all {expected} fitted dimensions are in the scanned matrix, embedding included, and "
        f"{ran} scans passed",
        "sprint-21d4-snapshots.json",
    )


def _ood_units(read: _Evidence) -> D4IntegrityClass:
    """D4's form of the erratum: a transformed case is a replica, not a new decision.

    D3 asked whether ranking decisions and candidate outcomes were counted apart. D4 asks the
    sharper question the erratum forced, on the record that measured it: the invariance sample
    encodes forty transformed decisions onto twenty clean vectors, and a census reporting those
    as forty independent decisions would be D3's collapse happening again.
    """
    name = "ood_units"
    regression = read("sprint-21d4-invariance-regression.json")
    if regression is None:
        return _missing(name, "sprint-21d4-invariance-regression.json")
    independence = regression.get("independence") or {}
    census = independence.get("census_over_clean_and_transformed") or {}
    nominal = int(census.get("nominal_decisions", 0))
    independent = int(census.get("independent_decisions", 0))
    replicated = int(census.get("replicated_decisions", 0))
    if not nominal:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "the invariance record carries no census, so nothing counted the transformed cases",
            "sprint-21d4-invariance-regression.json",
        )
    if nominal == independent:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"all {nominal} counted decisions are reported as distinct; a semantics-preserving "
            "transform that produced a new fitted vector is an encoder regression, and one that "
            "did not is a replica the census must name",
            "sprint-21d4-invariance-regression.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{nominal} counted decisions over {independent} distinct fitted vectors, "
        f"{replicated} named as replicas",
        "sprint-21d4-invariance-regression.json",
    )


def _holdout_access(read: _Evidence) -> D4IntegrityClass:
    name = "holdout_access"
    checkpoint = read("sprint-21d4-pre-final-checkpoint.json")
    claimed: list[str] = []
    checked: list[str] = []
    for path in sorted(read.directory.glob(EVIDENCE_GLOB)):
        document = read(path.name)
        if document is None or "final_outcomes_inspected" not in document:
            continue
        checked.append(path.name)
        if document["final_outcomes_inspected"]:
            claimed.append(path.name)
    if not checked:
        return _missing(name, "any file recording final_outcomes_inspected")
    if claimed:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"files reporting that a final outcome was inspected: {sorted(claimed)}",
            *claimed,
        )
    if checkpoint is not None and checkpoint["final_or_canary_outcomes_inspected"] != 0:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "the pre-final checkpoint counted a final or canary outcome at its clock",
            "sprint-21d4-pre-final-checkpoint.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(checked)} files report zero final or canary access",
        *checked,
    )


def _retrieval_one_read(read: _Evidence) -> D4IntegrityClass:
    name = "retrieval_one_read"
    holdout = read("sprint-21d4-retrieval-holdout-result.json")
    decision = read("sprint-21d4-retrieval-decision.json")
    files = ("sprint-21d4-retrieval-holdout-result.json", "sprint-21d4-retrieval-decision.json")
    if holdout is None or decision is None:
        return _missing(name, *files)
    executions = int(holdout.get("executions", 0))
    if executions != 1:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the holdout benchmark was executed {executions} times; the protocol allows one",
            *files,
        )
    opened = decision.get("no_alternative_opened") or {}
    reopened = sorted(key for key, value in opened.items() if value)
    if reopened:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the negative holdout was followed by reopened choices: {reopened}",
            *files,
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"read once; winning arm {decision.get('winning_arm')!r}, first failed floor "
        f"{decision.get('first_failed_floor')!r}, {len(opened)} classes of alternative reopened "
        "zero times",
        *files,
    )


def _artifact_bytes(blobs: Mapping[str, str | None] | None) -> D4IntegrityClass:
    """Declared address to observed hash. `None` means a row with no bytes behind it."""
    name = "artifact_bytes"
    if blobs is None:
        return _class(
            name,
            D3IntegrityState.WARNING,
            "not checked: this report was run without an artifact store, and a class nobody "
            "checked is never reported as clean",
        )
    if not blobs:
        return _class(
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
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{len(absent)} declared blobs have no bytes {[item[:12] for item in absent[:5]]}; "
            f"{len(mismatched)} do not hash to their name "
            f"{[item[:12] for item in mismatched[:5]]}",
        )
    return _class(
        name, D3IntegrityState.CLEAN, f"{len(blobs)} blobs rehash to their content address"
    )


def _lifecycle(read: _Evidence) -> D4IntegrityClass:
    name = "lifecycle"
    checkpoint = read("sprint-21d4-pre-final-checkpoint.json")
    if checkpoint is None:
        return _missing(name, "sprint-21d4-pre-final-checkpoint.json")
    decision = checkpoint["decision"]
    records = checkpoint["not_opened"]
    if decision["authorised"]:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "final access is recorded as authorised, which no later evidence supports",
            "sprint-21d4-pre-final-checkpoint.json",
        )
    stops = {item["stop_hash"] for item in records}
    untyped = [item["item"] for item in records if item.get("status") != "not_opened"]
    if len(stops) != 1 or untyped:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{len(stops)} stop hashes across the not-opened map; untyped records {untyped}",
            "sprint-21d4-pre-final-checkpoint.json",
        )
    return _class(
        name,
        D3IntegrityState.NOT_OPENED,
        f"no component was registered; {len(records)} dependent tasks bound to stop "
        f"{next(iter(stops))[:12]}",
        "sprint-21d4-pre-final-checkpoint.json",
    )


def _isolation(read: _Evidence, fingerprints: Mapping[str, str] | None) -> D4IntegrityClass:
    name = "isolation"
    baseline = read("sprint-21d4-baseline.json")
    if baseline is None:
        return _missing(name, "sprint-21d4-baseline.json")
    declared = {
        key: value["path_and_size_fingerprint_sha256"]
        for key, value in baseline["predecessor_artifact_stores"].items()
    }
    if fingerprints is None:
        return _class(
            name,
            D3IntegrityState.WARNING,
            f"not checked: {len(declared)} predecessor fingerprints are declared but no data "
            "root was given to re-take them",
            "sprint-21d4-baseline.json",
        )
    unchecked = sorted(set(declared) - set(fingerprints))
    moved = sorted(
        key for key, value in declared.items() if fingerprints.get(key) not in (None, value)
    )
    if moved:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"predecessor stores whose fingerprint changed: {moved}",
            "sprint-21d4-baseline.json",
        )
    if unchecked:
        return _class(
            name,
            D3IntegrityState.WARNING,
            f"{len(declared) - len(unchecked)} of {len(declared)} predecessor stores reproduce "
            f"their released fingerprint; not present to re-take: {unchecked}",
            "sprint-21d4-baseline.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"all {len(declared)} predecessor stores reproduce their released fingerprint",
        "sprint-21d4-baseline.json",
    )


def _decision_independence(read: _Evidence) -> D4IntegrityClass:
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

    for path in sorted(read.directory.glob(EVIDENCE_GLOB)):
        document = read(path.name)
        if document is None:
            continue
        touched = False
        for where, node in _objects(document):
            declared = node.get("rate_denominator")
            if isinstance(declared, str):
                denominators += 1
                touched = True
                if declared != INDEPENDENT_DENOMINATOR:
                    wrong_denominator.append(f"{path.name}{where}={declared}")
            nominal = node.get("nominal_decisions")
            independent = node.get("independent_decisions")
            if not isinstance(nominal, int) or not isinstance(independent, int):
                continue
            censuses += 1
            touched = True
            if independent > nominal:
                impossible.append(f"{path.name}{where}: {independent} of {nominal}")
            replicated = node.get("replicated_decisions")
            if isinstance(replicated, int) and nominal != independent + replicated:
                broken.append(f"{path.name}{where}: {nominal} != {independent} + {replicated}")
        if touched:
            files.append(path.name)

    if not censuses and not denominators:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "no committed file reports a decision count or names a denominator, so this class "
            "checked nothing and must not report that nothing is wrong",
        )
    if wrong_denominator or broken or impossible:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"rates over a nominal denominator {sorted(wrong_denominator)[:5]}; censuses that do "
            f"not add up {sorted(broken)[:5]}; more distinct than counted "
            f"{sorted(impossible)[:5]}",
            *files,
        )
    return _class(
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


def _find_hash(document: Any, wanted: str) -> str | None:
    """Whether `wanted` appears anywhere in a committed contract record, at any depth."""
    if isinstance(document, str):
        return wanted if document == wanted else None
    if isinstance(document, dict):
        for value in document.values():
            found = _find_hash(value, wanted)
            if found is not None:
                return found
    if isinstance(document, list):
        for value in document:
            found = _find_hash(value, wanted)
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
    read = _Evidence(evidence_directory)
    classes = (
        _explicit_member_selection(read),
        _duplicate_executions_or_seals(read),
        _chronology(read),
        _feature_schema(read),
        _matrix_embedding_scans(read),
        _ood_units(read),
        _holdout_access(read),
        _retrieval_one_read(read),
        _artifact_bytes(blob_hashes),
        _lifecycle(read),
        _isolation(read, predecessor_fingerprints),
        _decision_independence(read),
    )
    ordered = {item.name: item for item in classes}
    return D4IntegrityReport(classes=tuple(ordered[name] for name in D4_INTEGRITY_CLASSES))


__all__ = [
    "D4_INTEGRITY_CLASSES",
    "D4IntegrityClass",
    "D4IntegrityReport",
    "D4IntegrityState",
    "d4_integrity",
    "path_and_size_fingerprint",
]
