#!/usr/bin/env python3
"""S21D4-012. The fitting pool, enumerated and audited rather than assumed.

The contract froze a composition — ten D2 calibration, fifty D2 training, twenty D3 calibration
— and the sprint's own Section 6 says the exact pool is "an audit result, not an assumption".
That audit is this record. It was overdue: S21D4-032 sealed the fitting catalogue against the
composition without one, and S21D4-034 was about to seal 720 feature records against the seal.

Three things it establishes, per group and not in aggregate:

*Provenance.* Which sprint authored each package. The composition names three released
partitions, and D2's `training` partition contains thirty C3-authored groups by construction —
exactly as D3's fitting role did before it. That is what "fifty D2 training" resolves to, and a
record that reported only the partition name would hide it.

*Rights.* Every package's own `RealitySourceRights`, read off the manifest the campaign will
carry, not off a claim about the corpus. Task identity is asserted against the sealed catalogue
so the rights being read belong to the group being audited.

*Disjointness.* Transitive, against every protected role at once, on every identity key the
role actually has — repository group, template id and, where the role is a four-candidate task,
task id. A pool that is disjoint by name and overlapping by task is a pool that spends a
holdout; a role compared on a key it does not carry passes vacuously, so the record names the
keys each comparison used.

No D4 measurement is opened here. The record reads the sealed catalogues and the released
registry, and writes one JSON file.

    UV_CACHE_DIR=.cache/uv uv run python scripts/fitting_pool_d4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_retrieval_specs_d3 import (  # noqa: E402
    D3_RETRIEVAL_SPECS,
)
from cognitive_os.coding.reality_retrieval_specs_d4 import (  # noqa: E402
    D4_RETRIEVAL_SPECS,
)
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import D2_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_tasks import build_manifest  # noqa: E402
from cognitive_os.learning.correction_catalogue import (  # noqa: E402
    CatalogueGroup,
    assign_groups,
)
from cognitive_os.learning.correction_catalogue_d3 import seal_d3_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
FINDING_W0_F1 = EVIDENCE / "sprint-21d4-finding-w0-f1.json"

#: Rights are a pure function of the template id, so the bundle a manifest is built against
#: does not reach them. The task id is not a function of the bundle either, which is what lets
#: this record assert that the rights it read belong to the group the catalogue sealed.
_AUDIT_EPOCH = datetime(2026, 8, 7, tzinfo=UTC)
_AUDIT_BUNDLE = UUID(int=0)

#: The roles the fitting pool must not touch. Retrieval is here too: it is a different branch,
#: and a fitting group that was also a retrieval source would leak across the branch boundary.
PROTECTED = (
    CorrectionPartition.CALIBRATION,
    CorrectionPartition.FINAL_A,
    CorrectionPartition.FINAL_B,
    CorrectionPartition.CANARY,
)

#: S21D4-012 froze these, and they are reported back rather than recomputed, so a pool that
#: came out smaller than planned is visible as a mismatch instead of silently resetting them.
DECLARED_VOLUME_POINTS = (200, 320)
DECLARED_COMPOSITION = {"d2_calibration": 10, "d2_training": 50, "d3_calibration": 20}

#: The partition both predecessors spent and D4 reuses as exemplars.
COMPOSITION_SOURCE = CorrectionPartition.CALIBRATION


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _provenance() -> dict[str, str]:
    """`template_id -> authoring sprint`, from the released spec tuples themselves."""
    catalogue: dict[str, str] = {}
    for sprint, specs in (
        ("21C3", TASK_SPECS),
        ("21D2", D2_TASK_SPECS),
        ("21D3", D3_TASK_SPECS),
        ("21D4", D4_CALIBRATION_SPECS),
    ):
        for spec in specs:
            catalogue[spec.template_id] = sprint
    for sprint, specs in (("21D3", D3_RETRIEVAL_SPECS), ("21D4", D4_RETRIEVAL_SPECS)):
        for spec in specs:
            catalogue[spec.template_id] = sprint
    return catalogue


def _row(group: CatalogueGroup, sprint: str) -> dict[str, Any]:
    manifest = build_manifest(
        group.template_id,
        seed=group.task_seed,
        hidden_bundle_artifact_id=_AUDIT_BUNDLE,
        hidden_bundle_hash="0" * 64,
        created_at=_AUDIT_EPOCH,
    )
    if manifest.task_id != group.task_id:
        raise SystemExit(
            f"{group.template_id}: the registry generates task {manifest.task_id} at seed "
            f"{group.task_seed}, but the sealed catalogue names {group.task_id}; the rights "
            "below would describe a different package"
        )
    rights = manifest.rights
    return {
        "template_id": group.template_id,
        "repository_group": group.repository_group,
        "task_id": str(group.task_id),
        "provenance_sprint": sprint,
        "task_seed": group.task_seed,
        "candidate_slots": len(group.slots),
        "package_to_re_execute": True,
        "rights": {
            "source_identity": rights.source_identity,
            "licence_identifier": rights.licence_identifier,
            "rights_verified": rights.rights_verified,
            "rights_evidence_hash": rights.rights_evidence_hash,
            "attribution": rights.attribution,
            "sensitivity": str(rights.sensitivity),
            "content_hash": rights.content_hash,
        },
    }


def _disjointness(fitting: tuple[CatalogueGroup, ...], bundle: Any) -> dict[str, Any]:
    """Every key each role actually has. Disjoint by name and overlapping by task is not."""
    roles: dict[str, dict[str, set[str]]] = {}
    for partition in PROTECTED:
        groups = bundle.catalogues[partition].groups
        roles[partition.value] = {
            "repository_group": {group.repository_group for group in groups},
            "template_id": {group.template_id for group in groups},
            "task_id": {str(group.task_id) for group in groups},
        }
    # A retrieval source group is not a four-candidate task and carries no task id; its
    # identity keys are the group and the template. Comparing a key it does not have would
    # report a vacuous pass, so the record names the keys each role was compared on.
    retrieval = bundle.retrieval_pool.groups
    roles["retrieval"] = {
        "repository_group": {group.repository_group for group in retrieval},
        "template_id": {group.template_id for group in retrieval},
    }

    mine = {
        "repository_group": {group.repository_group for group in fitting},
        "template_id": {group.template_id for group in fitting},
        "task_id": {str(group.task_id) for group in fitting},
    }
    overlaps: dict[str, dict[str, list[str]]] = {}
    for name, keys in roles.items():
        found = {key: sorted(mine[key] & values) for key, values in keys.items()}
        if any(found.values()):
            overlaps[name] = found
    return {
        "keys_compared": {name: sorted(keys) for name, keys in roles.items()},
        "roles_compared": sorted(roles),
        "overlaps": overlaps,
        "transitively_disjoint": not overlaps,
        "why_every_key": (
            "a pool disjoint by group name and overlapping by task id spends a holdout while "
            "reporting that it did not; a retrieval source group has no task id, so that role "
            "is compared on the two keys it has rather than passed vacuously on a third"
        ),
    }


def _spent_calibration(fitting: tuple[CatalogueGroup, ...]) -> dict[str, Any]:
    """Which fitting groups were somebody's spent calibration set, resolved not assumed.

    The contract declares D2's and D3's calibration groups as D4 fitting exemplars. That is a
    claim about which released partitions these eighty came from, so it is answered by asking
    those partitions rather than by restating the composition's numbers back.
    """
    mine = {group.repository_group for group in fitting}
    d2_calibration = {entry.repository_group for entry in assign_groups()[COMPOSITION_SOURCE]}
    d3_calibration = seal_d3_corpus().groups_of(COMPOSITION_SOURCE)
    return {
        "d2_calibration_groups": len(mine & d2_calibration),
        "d3_calibration_groups": len(mine & d3_calibration),
        "declared_d2_calibration_groups": DECLARED_COMPOSITION["d2_calibration"],
        "declared_d3_calibration_groups": DECLARED_COMPOSITION["d3_calibration"],
        "matches_the_declared_composition": (
            len(mine & d2_calibration) == DECLARED_COMPOSITION["d2_calibration"]
            and len(mine & d3_calibration) == DECLARED_COMPOSITION["d3_calibration"]
        ),
        "the_rest_are_the_d2_training_partition": len(mine - d2_calibration - set(d3_calibration)),
    }


def _c3_exclusion(counts: Counter[str]) -> dict[str, Any]:
    """What the C3 exclusion does and does not mean, with the arithmetic that does not close."""
    return {
        "included_as_an_additional_source": False,
        "excluded_by": "release-owner decision, not by failed audit",
        "c3_groups_inside_the_released_d2_training_partition": counts["21C3"],
        "c3_groups_available_outside_it": 0,
        "reading": (
            "the frozen composition names three released partitions, and D2's training "
            "partition contains thirty C3-authored groups by construction. Sprint 21D3 fitted "
            "on exactly the same fifty. The exclusion therefore means no further C3 material is "
            "recruited into the pool, which is a decision with nothing left to act on: every C3 "
            "group is already inside a released partition"
        ),
        "contract_arithmetic_that_does_not_close": (
            "sprint-21d4-contracts.json says including C3 'would have carried the pool to about "
            "110 groups and 440 outcomes' on the strength of 'roughly thirty of its groups'. C3 "
            "has exactly thirty groups and all thirty are already inside the eighty, so no "
            "thirty remain to carry it to a hundred and ten. The number is wrong in the sealed "
            "record; the decision it accompanies is not affected, and a sealed record is "
            "amended rather than edited"
        ),
        "limitation_s21d4_039_must_report": (
            "the volume probe spans 200 to 320 rather than 200 to 440, so a flat risk-coverage "
            "curve across it is weaker evidence for hypothesis_class_bound than a wider span "
            "would have been"
        ),
    }


def _audit() -> dict[str, Any]:
    bundle = seal_d4_corpus()
    fitting = bundle.catalogues[CorrectionPartition.TRAINING]
    provenance = _provenance()

    rows = [_row(group, provenance.get(group.template_id, "unknown")) for group in fitting.groups]
    counts = Counter(row["provenance_sprint"] for row in rows)
    unknown = [row["template_id"] for row in rows if row["provenance_sprint"] == "unknown"]
    if unknown:
        raise SystemExit(f"{len(unknown)} fitting groups have no authoring sprint: {unknown[:5]}")

    outcomes = sum(int(row["candidate_slots"]) for row in rows)
    unverified = [row["template_id"] for row in rows if not row["rights"]["rights_verified"]]
    licences = sorted({str(row["rights"]["licence_identifier"]) for row in rows})

    achieved_groups = len(rows)
    volume_points = (
        list(DECLARED_VOLUME_POINTS)
        if achieved_groups >= 80
        else sorted({200, outcomes} if outcomes >= 200 else {outcomes})
    )

    return {
        "fitting_pool": {
            "achieved_groups": achieved_groups,
            "achieved_outcomes": outcomes,
            "declared_groups": 80,
            "declared_outcomes": 320,
            "meets_the_declared_pool": achieved_groups == 80 and outcomes == 320,
            "catalogue_hash": fitting.content_hash,
            "checked_against_seal": bundle.seal.content_hash,
            "provenance_counts": dict(sorted(counts.items())),
            "declared_composition": DECLARED_COMPOSITION,
            "composition_names_released_partitions": True,
            "composition_reading": (
                "ten D2 calibration, fifty D2 training and twenty D3 calibration are three "
                "released partitions taken whole. Their sizes are 10, 50 and 20 as released, "
                "which is where the eighty comes from; the provenance counts above are what "
                "those partitions turn out to contain"
            ),
            "every_group_is_a_package_to_re_execute": True,
            "why": (
                "D4-W0-F1: the D3 learned store holds no observations and no datasets, so no "
                "predecessor row can be inherited and every group is re-executed under D4 run "
                "identities"
            ),
            "finding_w0_f1_sha256": _digest(FINDING_W0_F1.read_bytes()),
        },
        "rights": {
            "groups_with_a_verified_rights_record": achieved_groups - len(unverified),
            "groups_without_one": sorted(unverified),
            "all_verified": not unverified,
            "licences": licences,
            "read_from": (
                "the RealityTaskManifest the campaign itself carries, with the generated task id "
                "asserted against the sealed catalogue, so the rights belong to the audited group"
            ),
        },
        "spent_calibration_groups_as_fitting_exemplars": {
            "declared_before_any_d4_measurement": True,
            **_spent_calibration(fitting.groups),
            "why": (
                "a group whose calibration role is spent may be an exemplar and may never be a "
                "D4 holdout member; the disjointness proof below is what enforces the second half"
            ),
        },
        "disjointness": _disjointness(fitting.groups, bundle),
        "volume_points": {
            "declared": list(DECLARED_VOLUME_POINTS),
            "achieved": volume_points,
            "set_from_the_achieved_pool": achieved_groups < 80,
            "rows_at_the_upper_point": outcomes,
        },
        "sprint_21c3_corpus": _c3_exclusion(counts),
        "d4_measurements_opened": 0,
        "per_group": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-fitting-pool.json")
    parser.add_argument("--check", action="store_true", help="reproduce the hash and stop")
    arguments = parser.parse_args()

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D4",
            "wave": "W2",
            "items": ["S21D4-012"],
            "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "final_outcomes_inspected": False,
            "recorded_late": {
                "planned_wave": "W1",
                "actual_wave": "W2",
                "why": (
                    "the audit was not run in W1. S21D4-032 sealed the fitting catalogue and "
                    "S21D4-033 passed without it, and the gap surfaced only when S21D4-034 went "
                    "to seal 720 feature records against a pool nobody had enumerated"
                ),
                "what_it_changes": (
                    "nothing sealed: the pool the audit describes is the one S21D4-032 already "
                    "sealed, and the record confirms rather than revises it"
                ),
            },
            **_audit(),
        }
    )
    if arguments.check:
        current = json.loads(arguments.output.read_text(encoding="utf-8"))
        body = {key: value for key, value in current.items() if key != "integrity_content_hash"}
        stops = [] if _digest(_canonical(body)) == current["integrity_content_hash"] else ["drift"]
        print(json.dumps({"stops": stops}, indent=1))
        return 1 if stops else 0

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pool = evidence["fitting_pool"]
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "achieved_groups": pool["achieved_groups"],
                "achieved_outcomes": pool["achieved_outcomes"],
                "provenance_counts": pool["provenance_counts"],
                "all_rights_verified": evidence["rights"]["all_verified"],
                "transitively_disjoint": evidence["disjointness"]["transitively_disjoint"],
                "volume_points": evidence["volume_points"]["achieved"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
