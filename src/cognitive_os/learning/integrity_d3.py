"""S21D3-081: one report over every class of D3 evidence, and four states it can be in.

D2's integrity report reads a database and an artifact store. Most of what D3 has to be able
to prove is not in either: the corrected OOD denominators, whether the holdout was read once,
whether the matrix scanned the embedding, and whether a dependent task that never ran carries a
record saying so. Those live in the committed evidence files, so this report reads those — and
that is what lets it run in CI beside the unit tests, with no database, no store and no
credential.

Four states, not two.

`CLEAN` and `FAILED` are the obvious pair. `WARNING` exists because some classes can only be
checked with an authority this process was not given — the artifact bytes need a store — and
reporting "clean" for a check nobody ran is the failure this whole sprint keeps finding.
`NOT_OPENED` exists because D3 stopped twice, and a class that was correctly never opened is
not a gap: it is a decision, and it carries the stop hash that made it.

One rule decides between `FAILED` and `NOT_OPENED`, and it is the rule the acceptance names: a
stored state claiming a pass without the evidence behind it fails closed. Absence is only
`NOT_OPENED` when something else says, by hash, that it was meant to be absent.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cognitive_os.coding.reality_integrity import fingerprint as reality_fingerprint
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    CorrectionFeatureContractV2,
)


class D3IntegrityState(StrEnum):
    """What one class of evidence is. Ordered worst-first for aggregation."""

    FAILED = "failed"
    WARNING = "warning"
    NOT_OPENED = "not_opened"
    CLEAN = "clean"


#: Every class the report covers, in the order S21D3-081 lists them. Fixed so a report that
#: silently stopped covering one is a diff rather than an absence nobody notices.
D3_INTEGRITY_CLASSES: tuple[str, ...] = (
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
)

#: The pre-registration every later D3 file must bind. Read from the file at run time; this is
#: only the name of the file that carries it.
PRE_REGISTRATION = "sprint-21d3-pre-registration.json"


@dataclass(frozen=True, slots=True)
class D3IntegrityClass:
    """One class: what it is, why, and which files were read to decide."""

    name: str
    state: D3IntegrityState
    detail: str
    evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "class": self.name,
            "state": self.state.value,
            "detail": self.detail,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class D3IntegrityReport:
    classes: tuple[D3IntegrityClass, ...]

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
            "covered": list(D3_INTEGRITY_CLASSES),
            "failed": list(self.failed),
            "warnings": list(self.warnings),
            "not_opened": list(self.not_opened),
            "clean": list(self.clean),
            "healthy": self.healthy,
        }


class _Evidence:
    """The committed evidence directory, read lazily and cached.

    A file that is absent is `None` rather than an exception: which classes that makes
    `NOT_OPENED` and which it makes `FAILED` is a decision each check makes for itself.
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

    def present(self, *names: str) -> tuple[str, ...]:
        return tuple(name for name in names if (self.directory / name).is_file())


def _class(name: str, state: D3IntegrityState, detail: str, *evidence: str) -> D3IntegrityClass:
    return D3IntegrityClass(name=name, state=state, detail=detail, evidence=evidence)


def _missing(name: str, *files: str) -> D3IntegrityClass:
    """No evidence at all. Failed, not not-opened: nothing declared this class closed."""
    return _class(
        name,
        D3IntegrityState.FAILED,
        f"no evidence to check: {', '.join(files)} is absent",
        *files,
    )


# ------------------------------------------------------------------ the eleven classes


def _explicit_member_selection(read: _Evidence) -> D3IntegrityClass:
    name = "explicit_member_selection"
    seals = read("sprint-21d3-sealed-manifests.json")
    campaign = read("sprint-21d3-self-play-campaign.json")
    selection = read("sprint-21d3-learner-selection.json")
    files = ("sprint-21d3-sealed-manifests.json", "sprint-21d3-self-play-campaign.json")
    if seals is None or campaign is None or selection is None:
        return _missing(name, *files, "sprint-21d3-learner-selection.json")

    declared = {key: value["content_hash"] for key, value in seals["catalogues"].items()}
    datasets = campaign["snapshot"]["datasets"]
    drift = [
        f"{partition}: campaign names {row.get('example_manifest_hash', '')[:12]}"
        for partition, row in datasets.items()
        if not row.get("rebuilt_identically", False)
    ]
    unresolved = [
        partition
        for partition, row in datasets.items()
        if not row.get("split_manifest_hash") or not row.get("example_manifest_hash")
    ]
    if drift or unresolved:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"datasets that do not rebuild or name their members: {sorted(drift + unresolved)}",
            *files,
        )
    if selection["selection"]["split_manifest_hash"] not in {
        row.get("split_manifest_hash") for row in datasets.values()
    }:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "the selection names a split manifest no campaign dataset resolved",
            *files,
            "sprint-21d3-learner-selection.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(datasets)} datasets rebuild identically from {len(declared)} sealed catalogues",
        *files,
        "sprint-21d3-learner-selection.json",
    )


def _duplicate_executions_or_seals(read: _Evidence) -> D3IntegrityClass:
    name = "duplicate_executions_or_seals"
    campaign = read("sprint-21d3-self-play-campaign.json")
    if campaign is None:
        return _missing(name, "sprint-21d3-self-play-campaign.json")

    resume = campaign["resume"]
    contradicted = [
        partition
        for partition, row in resume.items()
        if row.get("refused") or not row.get("is_resumable", True)
    ]
    unfinished = [
        partition
        for partition, row in resume.items()
        if row.get("effective_remainder", 0) or not row.get("is_complete", True)
    ]
    if contradicted or unfinished:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"contradicted receipts {sorted(contradicted)}, unfinished {sorted(unfinished)}",
            "sprint-21d3-self-play-campaign.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(resume)} partitions sealed once, no receipt contradicted, nothing remaining",
        "sprint-21d3-self-play-campaign.json",
    )


def _chronology(read: _Evidence) -> D3IntegrityClass:
    name = "chronology"
    pre = read(PRE_REGISTRATION)
    if pre is None:
        return _missing(name, PRE_REGISTRATION)
    digest = read.sha256(PRE_REGISTRATION)
    published = datetime.fromisoformat(str(pre["recorded_at"]).replace("Z", "+00:00"))

    bound: list[str] = []
    unbound: list[str] = []
    early: list[str] = []
    for path in sorted(read.directory.glob("sprint-21d3-*.json")):
        if path.name == PRE_REGISTRATION:
            continue
        document = read(path.name)
        if document is None or "pre_registration_sha256" not in document:
            continue
        bound.append(path.name)
        if document["pre_registration_sha256"] != digest:
            unbound.append(path.name)
        elif (
            datetime.fromisoformat(str(document["recorded_at"]).replace("Z", "+00:00")) <= published
        ):
            early.append(path.name)
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


def _feature_schema(read: _Evidence) -> D3IntegrityClass:
    name = "feature_schema"
    contracts = read("sprint-21d3-contracts.json")
    if contracts is None:
        return _missing(name, "sprint-21d3-contracts.json")
    declared = CorrectionFeatureContractV2().content_hash
    recorded = _find_hash(contracts, declared)
    if recorded is None:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the released v2 feature contract hashes to {declared[:12]}, which the frozen "
            "contract record does not contain",
            "sprint-21d3-contracts.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"the released v2 feature contract still hashes to the frozen {declared[:12]}",
        "sprint-21d3-contracts.json",
    )


def _matrix_embedding_scans(read: _Evidence) -> D3IntegrityClass:
    name = "matrix_embedding_scans"
    slice_ = read("sprint-21d3-vertical-slice.json")
    if slice_ is None:
        return _missing(name, "sprint-21d3-vertical-slice.json")
    columns = int(slice_.get("fitted_columns", 0))
    expected = len(FITTED_FEATURE_V2_ALLOWLIST)
    if columns != expected:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the fitted matrix scanned {columns} columns against the contract's {expected}",
            "sprint-21d3-vertical-slice.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"all {expected} fitted columns are in the scanned matrix, embedding included",
        "sprint-21d3-vertical-slice.json",
    )


def _ood_units(read: _Evidence) -> D3IntegrityClass:
    name = "ood_units"
    metamorphic = read("sprint-21d3-calibration-metamorphic.json")
    if metamorphic is None:
        return _missing(name, "sprint-21d3-calibration-metamorphic.json")
    decisions = int(metamorphic.get("valid_decisions", 0))
    outcomes = int(metamorphic.get("candidate_outcomes", 0))
    floor = int(metamorphic.get("minimum_valid_decisions", 0))
    if decisions == outcomes:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"decisions and candidate outcomes are both {decisions}; the corrected contract "
            "counts one ranking decision per case and four candidate labels under it",
            "sprint-21d3-calibration-metamorphic.json",
        )
    if decisions < floor:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{decisions} valid ranking decisions against a floor of {floor}",
            "sprint-21d3-calibration-metamorphic.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{decisions} ranking decisions and {outcomes} candidate outcomes, counted apart",
        "sprint-21d3-calibration-metamorphic.json",
    )


def _holdout_access(read: _Evidence) -> D3IntegrityClass:
    name = "holdout_access"
    checkpoint = read("sprint-21d3-pre-final-checkpoint.json")
    claimed: list[str] = []
    checked: list[str] = []
    for path in sorted(read.directory.glob("sprint-21d3-*.json")):
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
            "sprint-21d3-pre-final-checkpoint.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"{len(checked)} files report zero final or canary access",
        *checked,
    )


def _retrieval_one_read(read: _Evidence) -> D3IntegrityClass:
    name = "retrieval_one_read"
    holdout = read("sprint-21d3-retrieval-holdout-result.json")
    if holdout is None:
        return _missing(name, "sprint-21d3-retrieval-holdout-result.json")
    benchmark = holdout.get("benchmark", {})
    executions = benchmark.get("executions", benchmark.get("passes", 1))
    if int(executions) != 1:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"the holdout benchmark was executed {executions} times; the protocol allows one",
            "sprint-21d3-retrieval-holdout-result.json",
        )
    decision = holdout["decision"]
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"read once; winning arm {decision.get('winning_arm')!r}, first failed floor "
        f"{decision.get('first_failed_floor')!r}",
        "sprint-21d3-retrieval-holdout-result.json",
    )


def _lifecycle(read: _Evidence) -> D3IntegrityClass:
    name = "lifecycle"
    checkpoint = read("sprint-21d3-pre-final-checkpoint.json")
    if checkpoint is None:
        return _missing(name, "sprint-21d3-pre-final-checkpoint.json")
    decision = checkpoint["decision"]
    records = checkpoint["not_opened"]
    if decision["authorised"]:
        return _class(
            name,
            D3IntegrityState.FAILED,
            "final access is recorded as authorised, which no later evidence supports",
            "sprint-21d3-pre-final-checkpoint.json",
        )
    stops = {item["stop_hash"] for item in records}
    untyped = [item["item"] for item in records if item.get("status") != "not_opened"]
    if len(stops) != 1 or untyped:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{len(stops)} stop hashes across the not-opened map; untyped records {untyped}",
            "sprint-21d3-pre-final-checkpoint.json",
        )
    return _class(
        name,
        D3IntegrityState.NOT_OPENED,
        f"no component was registered; {len(records)} dependent tasks bound to stop "
        f"{next(iter(stops))[:12]}",
        "sprint-21d3-pre-final-checkpoint.json",
    )


def _artifact_bytes(read: _Evidence, blobs: Mapping[str, str | None] | None) -> D3IntegrityClass:
    """The one class that needs an authority this process may not have been given.

    The mapping is *declared address to observed hash*, and `None` means the store has a row
    and no bytes. Both halves matter and they fail differently: W7-A3 found that rehashing
    only the files that exist reports a store one blob smaller as perfectly clean, which is the
    shape of damage a partial restore actually produces.
    """
    name = "artifact_bytes"
    if blobs is None:
        return _class(
            name,
            D3IntegrityState.WARNING,
            "not checked: this report was run without an artifact store, and a class nobody "
            "checked is never reported as clean",
        )
    absent = sorted(key for key, observed in blobs.items() if observed is None)
    mismatched = sorted(
        key for key, observed in blobs.items() if observed is not None and observed != key
    )
    if absent or mismatched:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"{len(absent)} declared blobs have no bytes "
            f"{[item[:12] for item in absent[:5]]}; {len(mismatched)} do not hash to their "
            f"name {[item[:12] for item in mismatched[:5]]}",
        )
    return _class(
        name, D3IntegrityState.CLEAN, f"{len(blobs)} blobs rehash to their content address"
    )


def _isolation(read: _Evidence, fingerprints: Mapping[str, str] | None) -> D3IntegrityClass:
    name = "isolation"
    baseline = read("sprint-21d3-baseline.json")
    if baseline is None:
        return _missing(name, "sprint-21d3-baseline.json")
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
            "sprint-21d3-baseline.json",
        )
    moved = sorted(key for key, value in declared.items() if fingerprints.get(key) != value)
    if moved:
        return _class(
            name,
            D3IntegrityState.FAILED,
            f"predecessor stores whose fingerprint changed: {moved}",
            "sprint-21d3-baseline.json",
        )
    return _class(
        name,
        D3IntegrityState.CLEAN,
        f"all {len(declared)} predecessor stores reproduce their released fingerprint",
        "sprint-21d3-baseline.json",
    )


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


def d3_integrity(
    evidence_directory: Path,
    *,
    blob_hashes: Mapping[str, str | None] | None = None,
    predecessor_fingerprints: Mapping[str, str] | None = None,
) -> D3IntegrityReport:
    """Read the committed evidence and report every class. Never writes, never connects.

    `blob_hashes` maps each blob's declared content address to what it actually hashes to —
    `None` when the store has a row and no bytes — and
    `predecessor_fingerprints` maps each predecessor store to its re-taken fingerprint. Both
    are optional and both are `WARNING` when absent, because this report has to be runnable in
    a lane that has neither — and a lane that reported them clean anyway would be worse than a
    lane that did not run.
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
        _artifact_bytes(read, blob_hashes),
        _lifecycle(read),
        _isolation(read, predecessor_fingerprints),
    )
    ordered = {item.name: item for item in classes}
    return D3IntegrityReport(classes=tuple(ordered[name] for name in D3_INTEGRITY_CLASSES))


def path_and_size_fingerprint(root: Path) -> str:
    """The released predecessor fingerprint. Delegates; it does not re-derive.

    W7-A1. The first version of this reimplemented the hash from its description in the W0
    record and produced a different digest for all four stores — which reads as "every
    predecessor was mutated" and is in fact "the check disagrees with the check". A second
    implementation of a fingerprint is a second answer to the only question isolation asks.
    """
    digest, _ = reality_fingerprint(root)
    return digest
