#!/usr/bin/env python3
"""S21D7-044: W4-F1. The W1 seal still claims three carried roles D7 no longer has.

    UV_CACHE_DIR=.cache/uv uv run python scripts/protected_role_rebinding_d7.py

The release matrix found it, which is what a release matrix is for. `sealed_manifests_d7.py
--check` stopped on `sealed_manifests_protected_role_drift`, and the stop is **correct**: the two
final catalogue hashes no longer equal the bytes D6 released. What is stale is not the world, it
is the rule. W1 sealed "all three carried roles are byte-identical to D6's" when that was true,
and S21D7-038 ended it for two of them in W3 — with the gate owner's authorisation, under §3.5's
own exception, and with the audit sealed before any replacement body existed.

So this record rebinds, and it does **not** rewrite the W1 seal. That is the pattern the sprint
already established at W2 step 0: S21D7-027 superseded S21D7-011 without touching it, so
revision 7's children hashes stayed valid and the superseded ruling stayed readable as what it
was. Editing a sealed record to agree with a later decision is how an evidence chain becomes a
narrative — and here it would also break the `sealed_manifests_sha256` binding in every W2 and W3
record that reads it.

What the rebinding is willing to be wrong about, in order:

* the **canary** role must still be byte-identical to D6's. It was audited and passed, no
  authorisation was granted for it, and a canary that moved would be an unauthorised change to
  the subset a live activation routes;
* each moved role must be **named in the audit's grant**. A role that drifted without an
  authorisation is the failure the original stop exists to catch, and it still stops;
* each audit entry's `sealed_hash_before` must equal **D6's released hash**, so the audit was
  taken about these exact bytes rather than about some other version of them;
* each new hash must equal the `campaign_manifest_hash` the W3 campaign **actually executed
  against**, in both the feature seal and the campaign record. This is the load-bearing one: it
  is what makes the rebinding a statement about bytes that ran rather than about a catalogue
  someone recomputed afterwards;
* the frozen counts must survive — 30 groups and 120 candidate slots per final role.

Read-only with respect to every store, and it authors nothing.
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

from cognitive_os.learning.correction_catalogue_d7 import seal_d7_corpus  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
OUTPUT = EVIDENCE / "sprint-21d7-protected-role-rebinding.json"

D6_SEALED = EVIDENCE / "sprint-21d6-sealed-manifests.json"
D7_SEALED = EVIDENCE / "sprint-21d7-sealed-manifests.json"
AUDIT = EVIDENCE / "sprint-21d7-final-role-audit.json"
FINAL_SEALS = EVIDENCE / "sprint-21d7-final-feature-seals.json"
CAMPAIGNS = {
    "final_a": EVIDENCE / "sprint-21d7-final-a-campaign.json",
    "final_b": EVIDENCE / "sprint-21d7-final-b-campaign.json",
}

CARRIED = (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B, CorrectionPartition.CANARY)

#: The frozen shape a repair exists to keep. A rebinding that let these move would be a corpus
#: change wearing a repair's authorisation.
FROZEN_GROUPS = 30
FROZEN_SLOTS = 120


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "integrity_content_hash": _digest(_canonical(value))}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _executed_hashes() -> dict[str, dict[str, str]]:
    """Where each repaired catalogue's hash is bound in the bytes that actually ran."""
    seals = {row["partition"]: row for row in _read(FINAL_SEALS)["partitions"]}
    rows: dict[str, dict[str, str]] = {}
    for name, path in CAMPAIGNS.items():
        campaign = _read(path)
        rows[name] = {
            "feature_seal": str(seals[name]["campaign_manifest_hash"]),
            "campaign": str(campaign["campaign_manifest_hash"]),
            "outcomes": int(campaign["execution"]["unique_outcomes"]),
            "groups": int(campaign["execution"]["groups"]),
        }
    return rows


def _run(output: Path) -> int:
    released = _read(D6_SEALED)["catalogues"]
    audit = _read(AUDIT)
    granted = set(audit["authorisation"]["granted_for"])
    before = {
        row["role"]: row["sealed_hash_before"]
        for row in audit["what_it_costs_to_repair"]["catalogue_hashes_that_change"]
    }
    executed = _executed_hashes()
    bundle = seal_d7_corpus()

    roles: dict[str, Any] = {}
    findings: list[str] = []
    for partition in CARRIED:
        name = partition.value
        catalogue = bundle.catalogues[partition]
        now = catalogue.content_hash
        d6 = str(released[name]["content_hash"])
        moved = now != d6
        row: dict[str, Any] = {
            "d6_released_hash": d6,
            "d7_hash_now": now,
            "moved": moved,
            "authorised": name in granted,
            "groups": len(catalogue.groups),
            "candidate_slots": catalogue.candidate_slots,
        }
        if not moved:
            row["reading"] = (
                "carried unchanged, and required to be: no authorisation was granted for this "
                "role and it passed its encodability audit whole"
            )
            if name in granted:
                findings.append(f"{name} was authorised to change and did not")
        else:
            if name not in granted:
                findings.append(f"{name} moved without an authorisation naming it")
            if before.get(name) != d6:
                findings.append(
                    f"{name}'s audit names {str(before.get(name))[:16]} as the hash before the "
                    f"repair, which is not D6's released {d6[:16]}"
                )
            row["audit_sealed_hash_before"] = before.get(name)
            row["audit_names_d6s_bytes"] = before.get(name) == d6
            row["executed_against"] = executed.get(name)
            bound = executed.get(name, {})
            row["hash_is_the_one_that_executed"] = (
                bound.get("feature_seal") == now and bound.get("campaign") == now
            )
            if not row["hash_is_the_one_that_executed"]:
                findings.append(
                    f"{name}'s repaired catalogue hash is not the one its W3 campaign executed "
                    "against"
                )
            if len(catalogue.groups) != FROZEN_GROUPS or catalogue.candidate_slots != FROZEN_SLOTS:
                findings.append(
                    f"{name} holds {len(catalogue.groups)} groups and "
                    f"{catalogue.candidate_slots} slots, not {FROZEN_GROUPS}/{FROZEN_SLOTS}"
                )
            row["reading"] = (
                "repaired under S21D7-038 after failing its encodability audit, and rebound here "
                "to the hash its W3 campaign executed against"
            )
        roles[name] = row

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D7",
            "wave": "W4",
            "items": ["S21D7-044"],
            "finding": {
                "id": "W4-F1",
                "found_by": (
                    "scripts/verification_matrix_d7.py, on the `sealed_manifests` row: "
                    "`sealed_manifests_d7.py --check` stopped on "
                    "`sealed_manifests_protected_role_drift`"
                ),
                "statement": (
                    "the W1 seal claims all three carried roles are byte-identical to D6's "
                    "released catalogues. W3 repaired two of them under S21D7-038, so the claim "
                    "is false from that moment on — and the checker that enforces it is right to "
                    "stop, because nothing had yet told it the change was authorised"
                ),
                "what_is_stale": "the rule, not the world",
                "why_it_surfaced_at_w4": (
                    "the validator runs in the release matrix and nowhere else. W3 had no reason "
                    "to re-run a W1 seal check, and the repair it performed was recorded in the "
                    "audit rather than in the seal. A release matrix that skipped its own "
                    "sprint's validators would have shipped the contradiction"
                ),
            },
            "supersedes": {
                "record": "sprint-21d7-sealed-manifests.json",
                "record_sha256": _digest(D7_SEALED.read_bytes()),
                "the_sentence": "protected_roles.all_identical, and the three rows under it",
                "not_rewritten": True,
                "why_not_rewritten": (
                    "the same reason S21D7-027 did not rewrite S21D7-011: a sealed record edited "
                    "to agree with a later decision stops being evidence of what was known when "
                    "it was written, and every W2 and W3 record that binds "
                    "`sealed_manifests_sha256` would break"
                ),
                "what_it_still_says_correctly": (
                    "everything else — the fitting pool, the conformal half, role disjointness, "
                    "the volume point, the invariance and promotion submanifests and the "
                    "capability revocation are untouched by the repair"
                ),
            },
            "authorisation_read_from": {
                "record": "sprint-21d7-final-role-audit.json",
                "record_sha256": _digest(AUDIT.read_bytes()),
                "integrity_content_hash": audit["integrity_content_hash"],
                "granted_for": sorted(granted),
                "rule": audit["authorisation"]["rule"],
                "bodies_authored_when_the_audit_was_sealed": audit[
                    "bodies_authored_by_this_record"
                ],
            },
            "roles": roles,
            "canary_unchanged": not roles["canary"]["moved"],
            "roles_moved": sorted(name for name, row in roles.items() if row["moved"]),
            "roles_moved_without_authorisation": sorted(
                name for name, row in roles.items() if row["moved"] and not row["authorised"]
            ),
            "frozen_counts_preserved": all(
                row["groups"] == FROZEN_GROUPS and row["candidate_slots"] == FROZEN_SLOTS
                for name, row in roles.items()
                if name != "canary"
            ),
            "findings": findings,
            "clean": not findings,
            "what_this_record_is_not": (
                "an authorisation. The authorisation is S21D7-038's, taken in W3 before any "
                "replacement body existed. This record only binds the result of it to the bytes "
                "that ran, and tells the W1 validator which drift it has already been told about"
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
                "roles_moved": evidence["roles_moved"],
                "roles_moved_without_authorisation": evidence["roles_moved_without_authorisation"],
                "canary_unchanged": evidence["canary_unchanged"],
                "frozen_counts_preserved": evidence["frozen_counts_preserved"],
                "findings": findings,
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return _run(parser.parse_args().output)


if __name__ == "__main__":
    raise SystemExit(main())
