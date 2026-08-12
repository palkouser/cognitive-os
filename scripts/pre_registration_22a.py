"""S22A-013 through S22A-019. Revision 1, frozen before any 22A domain is registered.

Sprint 21's D-series pre-registered *learners*: a hypothesis class, an admission rule, the
thresholds under them. 22A fits nothing, so this document freezes a different kind of thing —
**a vocabulary and a refusal**. The descriptor schema is frozen so a pilot cannot widen the
contract it registers through; the enum reading is frozen so the seam cannot quietly become a
refactor; the two pilot ids are frozen so the sprint cannot answer "does a domain register?"
by choosing an easier domain after seeing the answer; and the four compatibility hashes are
frozen so "the released domains are unchanged" is a comparison rather than an opinion.

The contract text is **imported from the modules and read from the sealed records** that
implement it, never retyped, so a rule that drifts in code drifts in this record too and
`--check` catches it. Nothing here re-globs a directory or reads a clock into a sealed field
(W2-F1/F2), so a reproduction failure means something moved rather than that time passed.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22a.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22a.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22a.py --check-chronology \\
        --later docs/sprints/sprint-22/evidence/sprint-22a-<later>.json

Publishing this closes the window in which the schema, the reading and the pilots could be
chosen. Everything after it is execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.domain.descriptors import (  # noqa: E402
    DOMAIN_ID_MAX_LENGTH,
    DOMAIN_ID_PATTERN,
    DOMAIN_PACKAGE_MAX_BYTES,
    RELEASED_DOMAIN_IDS,
    SCHEMA_VERSION,
    DomainDescriptorV1,
    DomainLifecycleState,
)

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-22a-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22a-pre-registration.json",
}

#: The W0 authority records this publication rests on. Every one establishes authority; none
#: of them registers a domain or measures anything.
W0_CHILDREN = (
    "sprint-22a-domain-survey.json",
    "sprint-22a-baseline.json",
    "sprint-22a-decisions.json",
)

SURVEY = EVIDENCE / "sprint-22a-domain-survey.json"

#: The two pilots, frozen here so the sprint cannot answer "does a domain register?" by
#: choosing an easier domain after seeing how the first one went.
PILOT_DOMAIN_IDS = ("engineering.mechanics", "science.chemistry")

MIGRATION_HEAD = "0015"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _schema_hash() -> str:
    """The frozen descriptor schema, hashed from the model rather than described."""
    return _sha256(_canonical(DomainDescriptorV1.model_json_schema()))


def _contracts() -> dict[str, Any]:
    """The six frozen revision-1 contracts, S22A-013 through S22A-018."""
    survey = _load(SURVEY)
    coupling = survey["enum_coupling"]
    derived = survey["released_domains_as_descriptors"]

    return {
        "descriptor_schema_v1": _seal(
            {
                "item": "S22A-013",
                "name": "DomainDescriptorV1",
                "module": "src/cognitive_os/domain/descriptors.py",
                "module_sha256": _sha256(
                    (REPO / "src/cognitive_os/domain/descriptors.py").read_bytes()
                ),
                "module_note": (
                    "the bytes as W0 merges them, which are not the bytes the baseline "
                    "fingerprinted: W0-F2 and W0-F4 were fixed inside the wave, after the "
                    "baseline was taken and before this publication. A baseline that moved to "
                    "match would not be a baseline"
                ),
                "schema_version": SCHEMA_VERSION,
                "json_schema_sha256": _schema_hash(),
                "fields": sorted(DomainDescriptorV1.model_fields),
                "identity": ["domain_id", "revision"],
                "id_grammar": DOMAIN_ID_PATTERN.pattern,
                "id_max_length": DOMAIN_ID_MAX_LENGTH,
                "package_max_bytes": DOMAIN_PACKAGE_MAX_BYTES,
                "lifecycle_states": [state.value for state in DomainLifecycleState],
                "closed_world": (
                    "unknown fields are refused, and every cross-reference — parent, related "
                    "domain, shared concept, transfer target — must resolve inside the "
                    "package's own declared world"
                ),
                "package_may_claim_lifecycle": [DomainLifecycleState.PILOT.value],
                "why_only_pilot": (
                    "every other state is reached by a governed promotion with evidence behind "
                    "it, so a package arriving as `active` claims the promotion as well as the "
                    "domain. W0-F2: the module documented this rule and enforced it nowhere"
                ),
                "re_registration_rule": (
                    "the registry refuses re-registration of an existing (domain_id, revision) "
                    "rather than replacing it. W1-F2's lesson: a duplicate key that silently "
                    "replaces its predecessor is the failure mode of every registry"
                ),
                "supersession_rule": (
                    "a changed domain is a new revision with the old one intact; revision "
                    "supersession is a governance path, never a package upload"
                ),
                "may_be_widened_by_a_wave": False,
                "why_frozen_now": (
                    "a schema a pilot may widen is not a boundary. Both pilots register "
                    "through this exact contract or they are the finding"
                ),
            }
        ),
        "enum_reading": _seal(
            {
                "item": "S22A-014",
                "section": "§2.3, the one reading W0 freezes",
                "reading": (
                    "DomainKind survives as the adapter's closed vocabulary for the four "
                    "released domains, and everything general moves behind the descriptor "
                    "boundary"
                ),
                "new_domains_exist_only_as_descriptors": True,
                "new_enum_member_may_be_added": False,
                "released_ids_are_the_enum_values_verbatim": {
                    kind.value: identifier
                    for kind, identifier in sorted(
                        RELEASED_DOMAIN_IDS.items(), key=lambda item: item[0].value
                    )
                },
                "why_verbatim": (
                    "so every stored record that says 'coding' today resolves to the "
                    "descriptor of the same name without a migration"
                ),
                "coupling_at_publication": {
                    "modules": coupling["module_count"],
                    "references": coupling["reference_count"],
                    "counted_from": "the AST of src/cognitive_os, sealed in the survey record",
                },
                "coupling_may_grow": False,
                "silo_regression": (
                    "registering both pilots adds zero new branches on DomainKind; the AST "
                    "count is recomputed in W3 and must not have grown"
                ),
                "in_scope_for_the_seam": [
                    "the per-domain metadata tables in domains/registry.py",
                    "the adapter boundary in domain/descriptors.py",
                ],
                "out_of_scope": (
                    "every other DomainKind reference. 57 references invite a refactor crusade; "
                    "the exit needs the released four unchanged and the pilots possible, and "
                    "nothing else"
                ),
                "the_fence_is_a_finding_not_an_exception": (
                    "the day a fifth domain needs what only the enum's members get, that is a "
                    "finding belonging to a successor sprint's contract, not a quiet exception"
                ),
            }
        ),
        "pilot_domains": _seal(
            {
                "item": "S22A-015",
                "domain_ids": list(PILOT_DOMAIN_IDS),
                "revision": 1,
                "lifecycle": DomainLifecycleState.PILOT.value,
                "chosen_before_any_registration_exists": True,
                "may_be_substituted_after_a_failure": False,
                "why_not": (
                    "answering 'does a domain register?' by choosing an easier domain after "
                    "seeing the answer measures the chooser, not the registry"
                ),
                "honesty_floor": (
                    "a problem type enters a pilot only if a deterministic kernel can judge "
                    "it. A domain whose verifier cannot actually verify is a silo wearing a "
                    "lifecycle field"
                ),
                "planned_surfaces": {
                    "engineering.mechanics": (
                        "statics equilibrium and uniform-motion/force-balance checks — "
                        "unit-carrying computations the released physics.dimension and "
                        "physics.quantity verifiers already judge"
                    ),
                    "science.chemistry": (
                        "stoichiometric mass balance and molar-quantity conversion — exact "
                        "arithmetic over declared atomic masses with unit dimensions, judged "
                        "by the existing quantity/dimension verifiers plus one new capability "
                        "name whose verifier is a deterministic kernel, not a model"
                    ),
                },
                "a_candidate_that_cannot_be_verified_is_recorded_as_excluded": True,
                "the_w3_record_must_show_a_failure": (
                    "a chemistry candidate failing verification for a real reason, not only "
                    "candidates passing — a verifier that has never failed is a hope"
                ),
                "shared_concepts": (
                    "declared into physics; multi-domain membership is stored once and exposed "
                    "through both governed views, never copied into a second domain"
                ),
            }
        ),
        "backward_compatibility": _seal(
            {
                "item": "S22A-016",
                "claim": (
                    "the four released domains resolve identically after the seam exists; "
                    "their derived descriptors and the registry snapshot are unchanged"
                ),
                "compat_hashes": {
                    domain_id: body["content_hash"]
                    for domain_id, body in sorted(derived["descriptors"].items())
                },
                "registry_snapshot_hash": derived["registry_snapshot_hash"],
                "read_from": SURVEY.name,
                "read_from_sha256": _sha256(SURVEY.read_bytes()),
                "a_changed_hash_is_a_changed_released_behaviour": True,
                "an_authorised_change_re_binds_rather_than_edits": (
                    "W4-F1: a validator can outlive the claim it enforces. If a wave is "
                    "authorised to change a released domain, it re-binds this contract in a "
                    "new record naming what changed and why; it does not edit the hash here"
                ),
                "what_these_hashes_cannot_prove": (
                    "that no caller depended on DomainKind in a way the §2.3 reading breaks. "
                    "The W1 replay over the whole released surface is the strongest available "
                    "evidence, and W3-F1 says to run it rather than reason about it"
                ),
            }
        ),
        "storage_without_a_schema": _seal(
            {
                "item": "S22A-017",
                "rule": (
                    "descriptors are HashedExperienceContracts: they persist as "
                    "content-addressed artifacts and evidence records through the released "
                    "artifact service, exactly as every Sprint 21 sealed object did"
                ),
                "migration_head": MIGRATION_HEAD,
                "planned_22a_migration": None,
                "0016_is_a_refusal": (
                    "the exit criterion forbids a storage-schema change, so a wave that finds "
                    "itself allocating a migration has left the sprint's own contract; that is "
                    "a stop to surface, not a plan item"
                ),
                "startup_rebuild": (
                    "the registry's loaded state is rebuilt from artifact bytes at startup and "
                    "refuses a descriptor whose stored hash does not match its content"
                ),
                "the_seam_the_slice_must_cross": (
                    "separate processes, because the startup rebuild is the one place "
                    "'storage without a schema' can silently become 'state in memory' — D7's "
                    "lifecycle lesson: separate processes or it proved nothing"
                ),
                "core_controller_changed": False,
            }
        ),
        "exit_and_decision_tree": _seal(
            {
                "item": "S22A-018",
                "the_gate_is_the_sprints_own_exit": (
                    "no Gate L2 or D1 threshold, no amendment, no migration, no new learner. "
                    "The exit criteria were frozen in the execution sprint allocation"
                ),
                "exit_criteria": [
                    "both new domains register without changing the core controller or the "
                    "storage schema",
                    "cross-domain items are stored once and exposed through multiple governed "
                    "views",
                    "global and per-domain replay remain green",
                    "invalid domain packages fail closed",
                ],
                "endings": {
                    "1_pass": (
                        "all four criteria hold on executed evidence; annotated tag "
                        "sprint-22a-domain-baseline after exact-head CI, never moved"
                    ),
                    "2_verification_floor_not_met": (
                        "a pilot's honest verification floor cannot be met by deterministic "
                        "kernels. A typed negative under sprint-22a-evidence-baseline; this is "
                        "a finding about the boundary between 22A and 22C, not a reason to "
                        "lower the floor"
                    ),
                    "3_storage_schema_reached_for": (
                        "a wave finds itself allocating migration 0016. Stop and surface: the "
                        "exit criterion has been left, and no wave may take that decision"
                    ),
                    "4_released_behaviour_moved": (
                        "a compat hash, the registry snapshot hash or the released replay "
                        "changes. Stop: the four released domains must not be able to tell the "
                        "seam exists"
                    ),
                    "5_silo": (
                        "the pilots register but the coupling count grows, or a cross-domain "
                        "item is stored twice. The registry is a silo generator wearing a "
                        "descriptor schema, and the negative says so"
                    ),
                },
                "no_ending_may_be_chosen_after_the_evidence": True,
                "two_pilots_prove_extensibility_not_generality": (
                    "both lean on unit-carrying deterministic verification, the substrate the "
                    "released physics domain built. A domain whose verification is not "
                    "reducible to deterministic kernels is the 22C question and is deliberately "
                    "not attempted here"
                ),
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contracts = _contracts()

    contracts_document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W0",
        "items": [f"S22A-{number:03d}" for number in range(13, 19)],
        "recorded_at": recorded_at,
        "revision": 1,
        "contracts": contracts,
        "inherited_unchanged": {
            "execution_contract": (
                "sections 0.1 through 0.4 of the Sprint 21D4 technical backlog, incorporated "
                "by reference: the meaning of done, the wave discipline, the evidence-record "
                "shape, and the rule that a wave's defects are fixed inside the wave"
            ),
            "gate_l2": "passes at 29 of 29; 22A opens no condition and closes none",
            "gate_d1": "conditions 6, 7 and 15 closed by D7; untouched here",
            "migration_head": MIGRATION_HEAD,
            "learning_surface": (
                "the live correction component keeps routing its five canary groups; 22A "
                "replays that surface and changes nothing in it"
            ),
        },
        "what_this_revision_freezes": [
            "the descriptor schema v1 and its package boundary",
            "the §2.3 enum reading",
            "the two pilot domain ids",
            "the four backward-compatibility hashes and the registry snapshot hash",
        ],
        "thresholds_changed": {"count": 0, "amendments_made_by_22a": 0},
        "measured_values": 0,
    }
    contracts_document["integrity_content_hash"] = _sha256(_canonical(contracts_document))
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts_document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pre: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W0",
        "items": ["S22A-019"],
        "recorded_at": recorded_at,
        "revision": 1,
        "supersedes": None,
        "why_revision_1": (
            "22A is the first sprint of the 22 series and inherits no pre-registration. The "
            "D-series revisions belong to the learning gate and are not carried here"
        ),
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "evidence_children_sha256": {
            name: _sha256((EVIDENCE / name).read_bytes()) for name in W0_CHILDREN
        },
        "predecessor": {
            "tag": "sprint-21-learning-baseline",
            "commit": "3f5d7379caf85290da45885e22138506211bee2e",
            "verified_live_in": "sprint-22a-baseline.json",
        },
        "chronology": {
            "domains_registered": 0,
            "pilot_packages_authored": 0,
            "problem_types_solved": 0,
            "replays_claimed": 0,
            "registry_seams_built": 0,
            "descriptors_persisted": 0,
            "migrations_allocated": 0,
        },
        "measured_values": 0,
        "outcome_tags": {
            "pass": "sprint-22a-domain-baseline",
            "stop": "sprint-22a-evidence-baseline",
        },
        "what_this_publication_forbids": [
            "widening the descriptor schema, its grammar or its package ceiling to admit a pilot",
            "substituting either pilot domain id after a registration has been attempted",
            "adding a DomainKind member, or growing the sealed coupling count",
            "allocating migration 0016, or any other storage-schema change",
            "editing a compatibility hash rather than re-binding it in a new record",
            "registering a domain by any path other than validate_domain_package",
            "re-registering an existing (domain_id, revision) as a replacement",
            "extending the learned component to a new domain, or promoting it to steady state",
            "moving the conformal bar, the admitted set or the routed canary groups",
            "declaring replay green from a digest rather than from an executed run",
        ],
    }
    pre["integrity_content_hash"] = _sha256(_canonical(pre))
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "revision": 1,
                "contracts": sorted(contracts),
                "contracts_sha256": pre["contracts_sha256"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "descriptor_schema_sha256": _schema_hash(),
                "pilot_domain_ids": list(PILOT_DOMAIN_IDS),
                "compat_hashes": len(contracts["backward_compatibility"]["compat_hashes"]),
                "measured_values": 0,
                "thresholds_changed": 0,
                "migration_head": MIGRATION_HEAD,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _verify_seal(path: Path, document: dict[str, Any]) -> None:
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != document.get("integrity_content_hash"):
        raise SystemExit(f"{path.name} integrity hash does not match its content")


def _check() -> None:
    documents = {name: _load(path) for name, path in OUTPUTS.items()}
    for name, document in documents.items():
        _verify_seal(OUTPUTS[name], document)

    pre = documents["pre_registration"]
    if _sha256(OUTPUTS["contracts"].read_bytes()) != pre["contracts_sha256"]:
        raise SystemExit("the contracts file changed after the pre-registration was published")
    for name, expected in pre["evidence_children_sha256"].items():
        if _sha256((EVIDENCE / name).read_bytes()) != expected:
            raise SystemExit(f"W0 authority record changed after publication: {name}")
    for name, expected in pre["contract_hashes"].items():
        body = dict(documents["contracts"]["contracts"][name])
        if body.pop("content_hash") != expected or _sha256(_canonical(body)) != expected:
            raise SystemExit(f"contract {name} does not reproduce its frozen hash")

    contracts = documents["contracts"]["contracts"]
    schema = contracts["descriptor_schema_v1"]
    if schema["json_schema_sha256"] != _schema_hash():
        raise SystemExit(
            "DomainDescriptorV1 has drifted from the schema frozen in the pre-registration"
        )
    if schema["id_grammar"] != DOMAIN_ID_PATTERN.pattern:
        raise SystemExit("the domain id grammar has drifted from the frozen contract")
    if schema["package_max_bytes"] != DOMAIN_PACKAGE_MAX_BYTES:
        raise SystemExit("the package ceiling has drifted from the frozen contract")
    if contracts["pilot_domains"]["domain_ids"] != list(PILOT_DOMAIN_IDS):
        raise SystemExit("the frozen pilot domain ids do not match this script's constants")

    survey = _load(SURVEY)
    sealed_hashes = {
        domain_id: body["content_hash"]
        for domain_id, body in survey["released_domains_as_descriptors"]["descriptors"].items()
    }
    if contracts["backward_compatibility"]["compat_hashes"] != sealed_hashes:
        raise SystemExit("a compatibility hash does not match the sealed survey record")

    if any(pre["chronology"].values()) or pre["measured_values"]:
        raise SystemExit("the pre-registration contains measured values")
    if documents["contracts"]["thresholds_changed"]["count"]:
        raise SystemExit("revision 1 moves a threshold; 22A moves none")

    print(
        json.dumps(
            {
                "checked": sorted(OUTPUTS),
                "contracts_verified": len(pre["contract_hashes"]),
                "w0_children_verified": len(pre["evidence_children_sha256"]),
                "compat_hashes_verified": len(sealed_hashes),
                "descriptor_schema_unchanged": True,
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values_before_publication": 0,
                "thresholds_changed": 0,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check_chronology(later: tuple[Path, ...]) -> None:
    pre_path = OUTPUTS["pre_registration"]
    pre = _load(pre_path)
    _verify_seal(pre_path, pre)
    expected = _sha256(pre_path.read_bytes())
    published = datetime.fromisoformat(pre["recorded_at"].replace("Z", "+00:00"))

    accepted = []
    for path in later:
        document = _load(path)
        if document.get("pre_registration_sha256") != expected:
            raise SystemExit(f"{path.name} does not carry the pre-registration sha256")
        recorded = datetime.fromisoformat(document["recorded_at"].replace("Z", "+00:00"))
        if recorded < published:
            raise SystemExit(f"{path.name} predates the pre-registration it claims to follow")
        accepted.append(path.name)

    print(
        json.dumps(
            {"pre_registration_sha256": expected, "accepted": sorted(accepted)},
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-chronology", action="store_true")
    parser.add_argument("--later", nargs="*", default=[])
    arguments = parser.parse_args()

    if arguments.check:
        _check()
    if arguments.check_chronology:
        _check_chronology(tuple(Path(item) for item in arguments.later))
    if not arguments.check and not arguments.check_chronology:
        _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
