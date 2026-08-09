"""S21D5-081: the twelve classes over D5's evidence, nine of them the released implementations.

`integrity_d4.py` reads D4's committed evidence and reports twelve classes in four states. D5
needs the same report over its own files, and by construction it reads the same documents: the
snapshot writer, the campaign runner and the seal machinery are D4's, run under a D5 prefix. So
nine of the twelve checks differ from D4's by four characters of a sprint name, and copying them
would give the two sprints twelve checks that agree only by inspection.

They are shared instead. `Evidence` addresses a file by its suffix, this module supplies the
prefix, and what is written here is only the three classes that read genuinely different bytes:

*`feature_schema`.* D4 asks whether the frozen v2 feature contract still hashes to what the
contract record froze. D5 asks that too — the encoder did not move — and one more thing, because
D5's whole subject is a new function fitted on top of it: the hypothesis class the contract names
must be one a loader implements, and the module constant must still be that name. A contract
naming a class no loader implements is the failure S21D5-037 made condition 20 refuse; the same
question asked of the sealed contract belongs here.

*`matrix_embedding_scans`.* D4 fitted one matrix. D5 fits two — a fitting matrix and a
calibration matrix that share no group — so the record carries `fitted_matrices` and the check
has a second question: the two must be disjoint, and the dimensions must be the contract's on
both.

*`lifecycle`.* D4's clock was the pre-final checkpoint. D5's is the continuation decision, which
records a *typed* stop rather than an unauthorised access: `selective_margin_bound` under §3.3
step 5, twenty-six dependent items and fifteen Gate L2 conditions bound to one stop hash. A stop
kind that is not one of the four the contract published is a stop somebody chose after the fact.

The retrieval branch passed and the correction branch stopped, so this report is the first in the
series whose subject is two different answers. Nothing in the twelve classes decides an outcome —
they decide whether the record of one is internally honest.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from cognitive_os.learning.correction_artifact import IMPLEMENTED_HYPOTHESIS_CLASSES
from cognitive_os.learning.correction_protocol import CorrectionFeatureContractV2
from cognitive_os.learning.integrity_d3 import D3IntegrityState, path_and_size_fingerprint
from cognitive_os.learning.integrity_d4 import (
    D4_INTEGRITY_CLASSES,
    D4IntegrityClass,
    D4IntegrityReport,
    Evidence,
    artifact_bytes,
    chronology,
    decision_independence,
    duplicate_executions_or_seals,
    explicit_member_selection,
    find_hash,
    holdout_access,
    integrity_class,
    isolation,
    missing_evidence,
    ood_units,
    retrieval_one_read,
)
from cognitive_os.learning.pairwise_contrastive import HYPOTHESIS_CLASS

#: The same twelve, in the same order. A thirteenth class would be D5 answering a question the
#: backlog did not ask; a missing one would be a silent narrowing rather than a diff.
D5_INTEGRITY_CLASSES = D4_INTEGRITY_CLASSES
D5IntegrityClass = D4IntegrityClass
D5IntegrityReport = D4IntegrityReport
D5IntegrityState = D3IntegrityState

PREFIX = "sprint-21d5"

#: D5's clocked record. D4 named the pre-final checkpoint; D5 stopped before there was one, and
#: the continuation decision is where the same field is written.
CHECKPOINT = "continuation"

#: The four endings §3.3 published before any D5 number existed. A fifth would be an ending
#: chosen after the measurement.
DECISION_TREE_ENDINGS = frozenset(
    {"select", "volume_bound", "selective_margin_bound", "hypothesis_class_bound"}
)

#: Every scan `correction_matrix.scan_matrices` emits for a v2 matrix pair. Named here rather
#: than taken from the record, because a required count read out of the record it is checking is
#: the vacuity shape this sprint has now caught five times: D4's snapshots declared `required`
#: beside `count` and D5's do not, so a check that fell back to `count` could never fail.
REQUIRED_SCANS = frozenset(
    {
        "no_forbidden_field_reaches_the_matrix",
        "every_fitted_dimension_is_finite_and_in_range",
        "every_row_has_one_encoder_identity",
        "every_feature_record_precedes_its_outcome",
        "every_row_resolves_to_one_pre_outcome_source_chain",
        "no_group_crosses_the_split",
        "no_identical_row_carries_two_labels",
        "no_near_duplicate_crosses_the_split",
        "no_column_derives_the_label",
    }
)


def _feature_schema(read: Evidence) -> D5IntegrityClass:
    """The encoder did not move, and the class that moved is one a loader implements."""
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
            "revision-5 contract record does not contain",
            read.name("contracts"),
        )

    named = str((contracts.get("contracts") or {}).get("hypothesis_class", {}).get("name", ""))
    if named not in IMPLEMENTED_HYPOTHESIS_CLASSES:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the sealed contract names hypothesis class {named!r}, which no loader implements; "
            f"known: {sorted(IMPLEMENTED_HYPOTHESIS_CLASSES)}",
            read.name("contracts"),
        )
    if named != HYPOTHESIS_CLASS:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the sealed contract names {named!r} and the module now declares "
            f"{HYPOTHESIS_CLASS!r}; the class was renamed after it was frozen",
            read.name("contracts"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"the released v2 feature contract still hashes to the frozen {declared[:12]}, and the "
        f"sealed hypothesis class {named!r} is the one the loader implements",
        read.name("contracts"),
    )


def _matrix_embedding_scans(read: Evidence) -> D5IntegrityClass:
    """Both fitted matrices carry every contract dimension, and they share no group."""
    name = "matrix_embedding_scans"
    snapshots = read("snapshots")
    if snapshots is None:
        return missing_evidence(name, read.name("snapshots"))

    matrices = snapshots.get("fitted_matrices") or {}
    scans = snapshots.get("scans") or {}
    results = list(scans.get("results") or [])
    dimensions = int(matrices.get("fitted_dimensions", 0))
    expected = int(matrices.get("fitted_dimensions_expected", 0))
    ran = {str(item.get("name")) for item in results}
    failed = sorted(
        {str(item.get("name")) for item in results if not item.get("passed")}
        | {str(item) for item in (scans.get("failed") or [])}
    )
    if not expected or dimensions != expected:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the fitted matrices scanned {dimensions} dimensions against the contract's "
            f"{expected}",
            read.name("snapshots"),
        )
    if not matrices.get("channels_are_the_v2_allowlist_in_order"):
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "the fitted channels are not the v2 allowlist in order, so a column moved under a "
            "name that did not",
            read.name("snapshots"),
        )
    if not matrices.get("fit_and_calibration_share_no_group"):
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "the fitting and calibration matrices share a group; a threshold derived there is "
            "derived on the split it is meant to be honest about",
            read.name("snapshots"),
        )
    missing = sorted(REQUIRED_SCANS - ran)
    if missing or failed or not scans.get("all_passed"):
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"scans that never ran {missing}; scans that failed {failed}; "
            f"all_passed={scans.get('all_passed')!r}",
            read.name("snapshots"),
        )
    return integrity_class(
        name,
        D3IntegrityState.CLEAN,
        f"both fitted matrices carry all {expected} contract dimensions, embedding included, "
        f"share no group, and all {len(REQUIRED_SCANS)} required scans passed over "
        f"{len(results)} runs",
        read.name("snapshots"),
    )


def _lifecycle(read: Evidence) -> D5IntegrityClass:
    """No component was registered, and the stop that explains it is one the contract published.

    D5 stopped at a *typed* ending rather than at an unauthorised access, so this class checks
    the type. Twenty-six dependent items and fifteen Gate L2 conditions hang off one stop hash;
    a second hash would mean two stops were written and only one of them is being read.
    """
    name = "lifecycle"
    record = read(CHECKPOINT)
    if record is None:
        return missing_evidence(name, read.name(CHECKPOINT))

    decision = record.get("decision") or {}
    kind = str(decision.get("stop_kind") or decision.get("kind") or "")
    stop = str(record.get("stop_hash") or "")
    items = list((record.get("not_opened") or {}).get("items") or [])
    conditions = list((record.get("not_opened") or {}).get("gate_l2_conditions") or [])
    files = read.name(CHECKPOINT)

    if kind not in DECISION_TREE_ENDINGS:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the continuation record ends at {kind!r}, which is not one of the four endings "
            f"§3.3 published: {sorted(DECISION_TREE_ENDINGS)}",
            files,
        )
    if kind == "select":
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            "the continuation record selects a candidate, which no later D5 evidence supports",
            files,
        )
    if len(stop) != 64:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"the stop is bound to {stop!r}, which is not a content hash",
            files,
        )
    unbound = [
        str(item.get("item"))
        for item in items
        if not str(item.get("why", "")).strip() or not str(item.get("wave", "")).strip()
    ]
    if not items or unbound:
        return integrity_class(
            name,
            D3IntegrityState.FAILED,
            f"{len(items)} dependent items, of which {len(unbound)} name no wave or no reason: "
            f"{sorted(unbound)[:5]}",
            files,
        )
    return integrity_class(
        name,
        D3IntegrityState.NOT_OPENED,
        f"no component was registered; {len(items)} dependent items and {len(conditions)} Gate "
        f"L2 conditions bound to stop {stop[:12]} of kind {kind!r}",
        files,
    )


def d5_integrity(
    evidence_directory: Path,
    *,
    blob_hashes: Mapping[str, str | None] | None = None,
    predecessor_fingerprints: Mapping[str, str] | None = None,
) -> D5IntegrityReport:
    """Read the committed D5 evidence and report every class. Never writes, never connects.

    Both authorities are optional and both report `WARNING` when absent, for the reason the D4
    command records: this report has to be runnable in a lane that has neither, and a lane that
    reported them clean anyway would be worse than a lane that did not run.
    """
    read = Evidence(evidence_directory, prefix=PREFIX)
    classes = (
        explicit_member_selection(read),
        duplicate_executions_or_seals(read),
        chronology(read),
        _feature_schema(read),
        _matrix_embedding_scans(read),
        ood_units(read),
        holdout_access(read, CHECKPOINT),
        retrieval_one_read(read),
        artifact_bytes(blob_hashes),
        _lifecycle(read),
        isolation(read, predecessor_fingerprints),
        decision_independence(read),
    )
    ordered = {item.name: item for item in classes}
    return D5IntegrityReport(classes=tuple(ordered[name] for name in D5_INTEGRITY_CLASSES))


__all__ = [
    "D5_INTEGRITY_CLASSES",
    "D5IntegrityClass",
    "D5IntegrityReport",
    "D5IntegrityState",
    "d5_integrity",
    "path_and_size_fingerprint",
]
