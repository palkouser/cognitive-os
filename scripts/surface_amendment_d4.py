#!/usr/bin/env python3
"""S21D4-040. Amendment 2: the searchable-surface contract cannot mean both of its sentences.

The frozen `searchable_surface` contract says `search_terms` is included in `content_hash` and
that old stored graphs deserialise unchanged under the default. `seal_content` recomputes a
graph's canonical hash on load and refuses a mismatch, so an unconditional field satisfies the
first sentence by breaking the second — measured, not argued: the D3 pair blob's failed graph
moves from a8db90af88181437… to 399a7fc9276870c5… and all 140 stored pairs stop loading.

The sealed record is not edited. This is the successor record the programme's own convention
requires, on the same pattern as amendment 1.

    UV_CACHE_DIR=.cache/uv uv run python scripts/surface_amendment_d4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"
SURFACE = EVIDENCE / "sprint-21d4-surface.json"
OUTPUT = EVIDENCE / "sprint-21d4-contracts-amendment-2.json"


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    contracts = json.loads(CONTRACTS.read_text())
    frozen = contracts["contracts"]["searchable_surface"]
    surface = json.loads(SURFACE.read_text())
    measured = next(row for row in surface["findings"] if row["id"] == "W3-D1")

    amendment: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W3",
        "amendment": 2,
        "items": ["S21D4-013", "S21D4-040"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "amends": {
            "contract": "searchable_surface",
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "frozen_content_hash": frozen["content_hash"],
            "bytes_modified": 0,
        },
        "defect": {
            "id": "W3-D1",
            "sealed_sentences": [
                "included_in: content_hash",
                "old stored graphs deserialise unchanged under the default",
            ],
            "why_they_cannot_both_hold_as_written": (
                "HashedExperienceContract.seal_content recomputes the canonical hash of every "
                "contract on load and refuses a mismatch. A field that is unconditionally part "
                "of that hash therefore changes the identity of every graph stored before it "
                "existed, and those graphs stop loading rather than deserialising unchanged."
            ),
            "found_by": (
                "implementing it at S21D4-040; the stored D3 blob was rehashed both ways before "
                "the field was written, rather than after a benchmark failed to load its root"
            ),
            "measured": {
                "graph": measured["measured_on"],
                "hash_as_stored": measured["hash_as_stored"],
                "hash_if_the_empty_field_were_included": measured[
                    "hash_if_the_empty_field_were_included"
                ],
                "stored_pairs_that_would_stop_loading": measured[
                    "stored_pairs_that_would_stop_loading"
                ],
            },
        },
        "amended_sentence": (
            "search_terms is included in content_hash when it carries a term and absent from "
            "the canonical dump when it is empty, at every nesting depth"
        ),
        "operative_rule": (
            "A graph that carries search terms is new bytes and hashes differently from the "
            "graph it was derived from, which is what the sealed contract's inclusion clause "
            "exists to guarantee. A graph that carries none serialises, and therefore hashes, "
            "exactly as it did before the field existed, which is what the sealed contract's "
            "deserialisation clause exists to guarantee. Everything else in the contract — the "
            "exclusion from structural_hash and from ExperienceGraphNode.label, the derivation "
            "through canonical_source_bytes, the character bound, the forbidden-marker guard "
            "and the fail-closed judgement-leak guard — is unchanged."
        ),
        "what_this_does_not_change": [
            "the excluded_from list",
            "the derivation",
            "the excluded_inputs list",
            "the leak_guard",
            "any number published by D1, D2 or D3",
        ],
        "chronology": {
            "d4_retrieval_measurements_at_amendment_time": 0,
            "d4_retrieval_holdout_resolved": False,
            "d4_retrieval_pool_read": False,
            "why_this_matters": (
                "Pre-registration exists to stop a rule being chosen after its result is known. "
                "No D4 retrieval holdout exists yet and no arm has ranked anything under the "
                "widened surface, so this amendment cannot have been steered by a ranking."
            ),
        },
        "surface_evidence_sha256": _digest(SURFACE.read_bytes()),
        "sealed_record_amended_not_edited": True,
        "affects_any_published_number": False,
    }
    sealed = dict(amendment)
    sealed["integrity_content_hash"] = _digest(_canonical(amendment))
    arguments.output.write_text(
        json.dumps(sealed, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{arguments.output.relative_to(REPOSITORY)}")
    print(f"  amends searchable_surface {frozen['content_hash'][:16]}… bytes_modified=0")
    print(f"  seal {sealed['integrity_content_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
