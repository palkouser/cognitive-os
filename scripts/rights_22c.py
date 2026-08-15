"""S22C-002. The source-rights gate, and the blocking dependency it currently reports.

§1.3 puts a gate in front of the whole sprint: *no extraction touches a source whose license
evidence is not sealed, and the sprint has no source until the rights record exists.* §3.2
says what W0 does when the review has not concluded — surface it as a blocking dependency
with a named owner, **never** substitute a "temporary" source, because a campaign run on an
unclear source is evidence that cannot be released and work that cannot be kept.

This record does three things and refuses to do a fourth:

1. It reports the state of the clearance, read from the repository rather than assumed. The
   allocation's §7 permitted the review to begin during the scale sprint; nothing in 22B's
   execution record, and no evidence file, concludes it.
2. It **executes the gate** rather than describing it, four ways: no clearance at all, a
   clearance issued against different bytes, a clearance whose permitted uses are narrower
   than the campaign's declared uses, and a clearance that passes. A gate that has never
   refused anything is a gate nobody has tested, and 22A W4-F2's lesson is that a check
   which cannot notice a change proves nothing when it passes.
3. It names the owner and the exact artefact W1 needs.

What it does not do is choose the source. §1.3 states the choice is the gate owner's, and a
wave that picked a chapter because it was convenient would have decided the one question the
plan reserved.

    UV_CACHE_DIR=.cache/uv uv run python scripts/rights_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/rights_22c.py --check
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
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import (  # noqa: E402
    SLICE_TIME,
    RightsNotCleared,
    fixture_manifest,
    fixture_rights,
    fixture_source_hash,
    rights_gate,
)

from cognitive_os.domain.campaigns import (  # noqa: E402
    CampaignManifestV1,
    CampaignSourceRights,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import CorpusUsageRight  # noqa: E402

#: The evidence file a concluded review must produce before W1 registers anything. Its
#: absence is the blocking dependency; its presence is what unblocks the wave.
REAL_SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"

#: Every field §1.3 requires of the record, named here so the owner is asked for a list
#: rather than for "the rights".
REQUIRED_OF_A_CONCLUDED_REVIEW = (
    "source_content_hash — the exact bytes cleared, so a clearance cannot drift onto a "
    "different edition",
    "edition",
    "author",
    "location",
    "license_identifier",
    "permitted_uses — from the released CorpusUsageRight vocabulary, at least "
    "internal_use and derivative_work for a campaign that compiles knowledge",
    "cleared_by — a named authority, not a role",
    "cleared_at",
    "evidence_hash — the licence text or acquisition record the clearance rests on",
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _refusal(label: str, call: Any) -> dict[str, Any]:
    """Run one gate probe and record what it did. A probe that passes is a failed probe."""
    try:
        call()
    except (RightsNotCleared, ValueError) as error:
        return {"probe": label, "refused": True, "reason": str(error)[:400]}
    return {"probe": label, "refused": False, "reason": "the gate admitted this and should not"}


def _gate_probes() -> list[dict[str, Any]]:
    cleared = fixture_rights()
    other_bytes = _sha256(b"a different chapter entirely")

    def _no_clearance() -> None:
        rights_gate(None, fixture_source_hash())

    def _wrong_bytes() -> None:
        rights_gate(cleared, other_bytes)

    def _not_cleared_status() -> None:
        # The contract refuses to *hold* a non-clearance at all: an unfinished review is the
        # absence of the record, not an instance of it carrying status=not_cleared.
        CampaignSourceRights(
            status=RightsClearanceStatus.NOT_CLEARED,
            source_content_hash=fixture_source_hash(),
            edition="1",
            author="unknown",
            location="unknown",
            license_identifier="unknown",
            permitted_uses=(CorpusUsageRight.INTERNAL_USE,),
            cleared_by="nobody",
            cleared_at=SLICE_TIME,
            evidence_hash=_sha256(b""),
        )

    def _use_beyond_clearance() -> None:
        # A manifest may not declare a use its clearance does not permit. The fixture
        # clearance permits no public release, so a campaign asking for one is refused.
        manifest = fixture_manifest()
        CampaignManifestV1(
            **{
                **manifest.model_dump(exclude={"content_hash"}),
                "declared_uses": (CorpusUsageRight.PUBLIC_RELEASE,),
            }
        )

    probes = [
        _refusal("no rights record at all", _no_clearance),
        _refusal("a clearance issued against different bytes", _wrong_bytes),
        _refusal("a record carrying an unconcluded review", _not_cleared_status),
        _refusal("a campaign use the clearance does not permit", _use_beyond_clearance),
    ]
    # And the positive control: the gate must also let a real clearance through, or it is
    # refusing everything rather than refusing the right things.
    passed = True
    try:
        rights_gate(cleared, fixture_source_hash())
    except RightsNotCleared:
        passed = False
    probes.append(
        {
            "probe": "a matching clearance for the fixture chapter",
            "refused": not passed,
            "reason": "admitted, as it must be" if passed else "the gate refused a valid clearance",
        }
    )
    return probes


def _record() -> dict[str, Any]:
    concluded = REAL_SOURCE_RIGHTS.exists()
    probes = _gate_probes()
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W0",
        "items": ["S22C-002"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_rights_review": {
            "concluded": concluded,
            "expected_evidence": str(REAL_SOURCE_RIGHTS.relative_to(REPO)),
            "read_from": "the repository, not from the plan's expectation",
            "authorised_to_begin_by": (
                "execution-sprint-allocation.md §7: 'Sprint 22C source-rights review may "
                "begin during the scale sprint'"
            ),
            "concluded_by_22b": False,
            "why_not_concluded_by_22b": (
                "22B's execution record names no rights work; §7 permitted the review to "
                "begin, and permission to begin is not a conclusion"
            ),
        },
        "blocking_dependency": None
        if concluded
        else {
            "blocks": "W1 — the real source's registration, and therefore cycles 1 through 3",
            "does_not_block": (
                "the rest of W0. The fixture-scale slice runs against an in-repository "
                "chapter by design (§3.1), so every driver, freeze and test in this wave is "
                "complete and none of them touched an uncleared source"
            ),
            "owner": "the Sprint 22 gate owner",
            "required_of_a_concluded_review": list(REQUIRED_OF_A_CONCLUDED_REVIEW),
            "substitution_refused": (
                "§3.2: a campaign run on an unclear source is evidence that cannot be "
                "released and work that cannot be kept. This wave registers no substitute "
                "source and picks no chapter — §1.3 reserves that choice to the gate owner"
            ),
            "natural_candidates_named_by_the_plan": (
                "openly licensed technical material matching the two pilots — a mechanics "
                "text and a chemistry text, or one source both can consume"
            ),
        },
        "gate_is_executable": {
            "probes": probes,
            "probes_run": len(probes),
            "refusals": sum(1 for probe in probes if probe["refused"]),
            "every_probe_behaved": all(
                probe["refused"] != (probe["probe"].startswith("a matching")) for probe in probes
            ),
            "why_probes": (
                "a gate that has never refused anything is a gate nobody has tested. The "
                "four refusals and the one admission are run here so 'W0 blocks on rights' "
                "is a demonstrated behaviour rather than a sentence in a plan"
            ),
        },
        "fixture_clearance": {
            "content_hash": fixture_rights().content_hash,
            "source_content_hash": fixture_source_hash(),
            "clears_nothing_about_the_real_source": True,
            "why_it_exists": (
                "the fixture chapter is authored in this repository, so its rights are a "
                "fact about the repository rather than a review's outcome. It exists so the "
                "gate can be exercised at fixture scale, and it is not a substitute source"
            ),
        },
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


#: **W1-F1.** This record mixes two kinds of field, and `--check` used to recompute both.
#:
#: *Invariants* — the gate probes and the fixture clearance — are deterministic, and a
#: `--check` that recomputes them is worth having: if the gate stops refusing, the check
#: fails.
#:
#: *Observations* — whether the rights review had concluded, and the blocking dependency
#: that followed — describe the world at W0. The world then moved, exactly as the plan
#: intended it to: the gate owner nominated two sources and W1 sealed the clearance. From
#: that moment a `--check` that re-derived `concluded` from today's filesystem reported the
#: W0 record as unreproducible, which is false. The record is intact and it is true; it
#: states what was so at W0.
#:
#: This is 22B's own S22B-002 split — invariants recomputed, observations recorded and
#: compared by nothing — and the same family as its W3-F4: *a summary may bind only what
#: cannot move underneath it*. Fixing the validator is not editing the evidence, and the W0
#: record is left byte-for-byte as sealed.
OBSERVED_AT_W0 = ("source_rights_review", "blocking_dependency")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-22c-rights-gate.json")
    arguments = parser.parse_args()

    record = _record()
    if arguments.check:
        stored = json.loads(arguments.output.read_text(encoding="utf-8"))
        moving = {"recorded_at", "integrity_content_hash", *OBSERVED_AT_W0}
        invariants_same = {k: v for k, v in stored.items() if k not in moving} == {
            k: v for k, v in record.items() if k not in moving
        }
        # And the seal is still over the stored body, observations included — so the fields
        # this check no longer recomputes are still protected against being edited.
        body = {k: v for k, v in stored.items() if k != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "reproduced": invariants_same and sealed,
                    "invariants_recomputed": invariants_same,
                    "stored_seal_intact": sealed,
                    "recorded_not_recomputed": list(OBSERVED_AT_W0),
                    "world_has_moved_since_w0": (
                        stored["source_rights_review"]["concluded"]
                        != record["source_rights_review"]["concluded"]
                    ),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if invariants_same and sealed else 1

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "rights_review_concluded": record["source_rights_review"]["concluded"],
                "blocking": record["blocking_dependency"] is not None,
                "blocks": (record["blocking_dependency"] or {}).get("blocks"),
                "gate_probes": record["gate_is_executable"]["probes_run"],
                "gate_refusals": record["gate_is_executable"]["refusals"],
                "every_probe_behaved": record["gate_is_executable"]["every_probe_behaved"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
