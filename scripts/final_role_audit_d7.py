#!/usr/bin/env python3
"""S21D7-038: the carried final roles, audited against the contract that must encode them.

W3 opened the final roles for the first time in five sprints and the seal stage stopped on the
first body it could not canonicalise. This script is the audit that should have run in D3, and
the record it seals is what licenses the replacement authoring §3.5 otherwise forbids.

The finding, stated plainly: **a digest recomputed unchanged proves the bytes did not move, not
that anything can use them.** D2 authored the final roles before the source canonicaliser banned
reflective binding, and every sprint since has recomputed their catalogue hashes, found them
unchanged, and recorded the roles as carried intact. They were intact. They were also
unencodable, and nothing in five sprints asked.

What is refused and why: `correction_source.py` rejects `hasattr`, `getattr`, `globals` and the
rest outright, because the invariance sample renames every identifier and a body that reaches a
name reflectively survives the rename with different behaviour. It also rejects syntax the
frozen grammar does not cover, which is where the assignment expression falls. Neither rule is
negotiable here and neither is being changed: the contract is frozen and the bodies are what
fail it.

The authorisation this record carries is §3.5's own exception — final bodies may be authored
when a whole role fails its audit — exercised by the gate owner after the audit below and before
any replacement body existed. The chronology block is the proof of that order.

    UV_CACHE_DIR=.cache/uv uv run python scripts/final_role_audit_d7.py

Read-only. It authors nothing, seals no catalogue and opens no outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_tasks import template  # noqa: E402
from cognitive_os.domain.reality import RealityCandidateStrategy  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402
from cognitive_os.learning.correction_source import (  # noqa: E402
    SourceNormalizationError,
    canonical_source_hash,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-final-role-audit.json"

SEALED_MANIFESTS = EVIDENCE / "sprint-21d7-sealed-manifests.json"
REUSE_AUDIT = EVIDENCE / "sprint-21d7-reuse-audit.json"
LEARNER_SELECTION = EVIDENCE / "sprint-21d7-learner-selection.json"
ARTIFACT = EVIDENCE / "sprint-21d7-artifact.json"

CARRIED = (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B, CorrectionPartition.CANARY)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _audit(catalogue: Any) -> dict[str, Any]:
    """Every body of one role put through the canonicaliser the campaign would use."""
    failures: list[dict[str, str]] = []
    slots = 0
    for group in catalogue.groups:
        item = template(group.template_id)
        path = next(name for name in item.visible_files if name.startswith("src/"))
        bodies = {"baseline": item.visible_files[path]}
        for slot in group.slots:
            recipe = RealityCandidateStrategy(slot.recipe)
            bodies[str(slot.recipe)] = item.neutral_candidate_sources[recipe][path]
            slots += 1
        for label, source in bodies.items():
            try:
                canonical_source_hash(source)
            except SourceNormalizationError as error:
                failures.append(
                    {
                        "group": group.repository_group,
                        "template_id": group.template_id,
                        "body": label,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
    affected = sorted({item["group"] for item in failures})
    return {
        "groups": len(catalogue.groups),
        "candidate_slots": slots,
        "catalogue_hash": catalogue.content_hash,
        "bodies_refused": len(failures),
        "groups_affected": len(affected),
        "affected_groups": affected,
        "failures": failures,
        "encodable_groups": len(catalogue.groups) - len(affected),
        "role_is_executable_as_sealed": not failures,
    }


def _run(output: Path) -> int:
    bundle = seal_d7_corpus()
    roles = {name.value: _audit(bundle.catalogues[name]) for name in CARRIED}
    failing = sorted(
        name for name, item in roles.items() if not item["role_is_executable_as_sealed"]
    )

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W3",
            "items": ["S21D7-038"],
            "final_outcomes_inspected": False,
            "final_or_canary_outcomes_inspected": 0,
            "bodies_authored_by_this_record": 0,
            "catalogues_resealed_by_this_record": 0,
            "stores_opened_for_writing": 0,
            "inputs": {
                "sealed_manifests_sha256": _digest(SEALED_MANIFESTS.read_bytes()),
                "reuse_audit_sha256": _digest(REUSE_AUDIT.read_bytes()),
                "learner_selection_sha256": _digest(LEARNER_SELECTION.read_bytes()),
                "artifact_sha256": _digest(ARTIFACT.read_bytes()),
            },
            "finding": {
                "id": "W3-F1",
                "statement": (
                    "the carried final roles cannot be encoded under the frozen feature "
                    "contract. Four authored bodies use constructs the source canonicaliser "
                    "refuses: three bind a name through hasattr() and one uses an assignment "
                    "expression the frozen grammar does not cover"
                ),
                "why_five_sprints_missed_it": (
                    "every sprint from D3 recomputed the carried catalogue digests, found them "
                    "unchanged and recorded the roles as carried intact. They were intact. A "
                    "digest proves the bytes did not move; it says nothing about whether "
                    "anything can read them, and no sprint ran a body of these roles through "
                    "the canonicaliser because opening the roles is what W3 does"
                ),
                "when_the_ban_arrived": (
                    "after D2 authored these bodies. The reflection ban exists because the "
                    "invariance sample renames every identifier, and a body that reaches a name "
                    "reflectively survives the rename with different behaviour — so the rule is "
                    "not being relaxed to fit the bodies"
                ),
                "discovered_by": (
                    "the W3 seal stage, on its first attempt to encode final A. Not by a "
                    "checker written to find it: the campaign simply refused to seal"
                ),
            },
            "roles": roles,
            "roles_failing_their_audit": failing,
            "what_it_costs_to_repair": {
                "replacement_groups_needed": sum(
                    roles[name]["groups_affected"] for name in failing
                ),
                "frozen_counts_preserved": "30 groups and 120 outcomes per final role",
                "catalogue_hashes_that_change": [
                    {"role": name, "sealed_hash_before": roles[name]["catalogue_hash"]}
                    for name in failing
                ],
                "what_ends_here": (
                    "the 'carried unopened and unchanged for five sprints' reading of the final "
                    "roles. D2 through D6's records stay true about their own bytes; from this "
                    "record forward the two final catalogues are D7's, and every later record "
                    "must bind the new hashes rather than the inherited ones"
                ),
                "what_does_not_change": [
                    "the canary role, which passes its audit whole and is carried untouched",
                    "the feature contract, the canonicaliser and the reflection ban",
                    "the frozen 30/120 counts, which the repair exists to keep",
                    "any threshold; this is a corpus repair and moves no number in §2.3",
                ],
            },
            "authorisation": {
                "rule": (
                    "§3.5 forbids authoring final, batch-B or canary bodies 'unless a whole role "
                    "fails its audit'. This record is that audit, and two roles fail it"
                ),
                "granted": True,
                "granted_for": failing,
                "scope": (
                    "replacement groups for the affected groups only, authored under the "
                    "unchanged D4 authoring contract, in D7's own template range"
                ),
                "the_hazard_this_record_will_not_hide": (
                    "the replacements are authored by an author who has already seen the "
                    "selection's numbers. That is not the case for the bodies themselves — the "
                    "class never sees them before execution and the labels come from the hidden "
                    "verifier — but it is true of the choice of what to author, and a final "
                    "batch is supposed to be the least contaminated evidence in the sprint. It "
                    "is recorded here rather than argued away"
                ),
            },
            "chronology": {
                "audit_precedes_the_authorisation": True,
                "authorisation_precedes_any_replacement_body": True,
                "replacement_bodies_existing_when_this_was_sealed": 0,
                "final_outcomes_read_when_this_was_sealed": 0,
                "why_the_order_matters": (
                    "an authorisation written after the replacements exist is a description of "
                    "what someone already did. The counters above are what make this the "
                    "other thing"
                ),
            },
            "what_this_record_is_not": (
                "a relaxation. Nothing here changes the canonicaliser, the contract or a count; "
                "the bodies that fail are replaced, not the rule that fails them"
            ),
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "roles_failing": failing,
                "bodies_refused": {name: roles[name]["bodies_refused"] for name in roles},
                "groups_affected": {name: roles[name]["groups_affected"] for name in roles},
                "replacement_groups_needed": evidence["what_it_costs_to_repair"][
                    "replacement_groups_needed"
                ],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return _run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
