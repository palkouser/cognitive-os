"""S22C-W1: the concluded source-rights review, and the history W0 keeps.

The rights review concluded between W0 and W1, which is the one state change this sprint was
designed to wait for. What has to be true of it:

*The clearance follows the bytes, not the nomination.* Both sources were nominated as "CC
BY". One of them is CC BY-NC-SA 4.0, and the record says so. A test that only asserted "two
sources are cleared" would pass just as happily on a record that had written the nomination
down as fact, so these assert the licence identifiers and the *consequences* of the
restrictive one.

*The restrictive source is cleared restrictively.* NonCommercial and ShareAlike are not
footnotes: `commercial_use` and `public_release` must be absent from the chemistry source's
permitted uses, and the campaign's declared uses must stay inside what is cleared.

*W0's record is history and stays true.* It says the review had not concluded. That was so at
W0 and is still so about W0, so it is not edited — and W1-F1's corrected validator is what
lets both records be right at once.

These read the sealed records, never the PDFs, so they run in CI where the sources do not
exist.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"

SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"
W0_RIGHTS_GATE = EVIDENCE / "sprint-22c-rights-gate.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _source(key: str) -> dict[str, Any]:
    return next(item for item in _load(SOURCE_RIGHTS)["sources"] if item["key"] == key)


def test_the_source_rights_seal_is_over_its_own_content() -> None:
    document = _load(SOURCE_RIGHTS)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    assert _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_the_review_concluded_on_two_sources_one_per_pilot_domain() -> None:
    record = _load(SOURCE_RIGHTS)
    assert record["review_concluded"] is True
    assert record["source_count"] == 2
    assert record["domains_covered"] == ["engineering.mechanics", "science.chemistry"]
    assert record["cleared_by"]
    assert record["cleared_at"]


def test_the_clearance_followed_the_bytes_rather_than_the_nomination() -> None:
    """The finding, held where deleting it would fail."""
    record = _load(SOURCE_RIGHTS)
    correction = record["the_nomination_was_corrected_by_the_evidence"]
    assert correction["nominated_as"].startswith("both CC BY")
    assert correction["found"]["physics"].startswith("CC BY 4.0")
    assert (
        "NC-SA" in correction["found"]["chemistry"]
        or "NonCommercial" in (correction["found"]["chemistry"])
    )
    assert _source("physics")["license_identifier"] == "CC-BY-4.0"
    assert _source("chemistry")["license_identifier"] == "CC-BY-NC-SA-4.0"


def test_every_clearance_quotes_the_licence_page_it_hashed() -> None:
    for key in ("physics", "chemistry"):
        source = _source(key)
        assert len(source["evidence_hash"]) == 64
        assert len(source["source_content_hash"]) == 64
        assert source["license_page"] >= 1
        # The quoted statement must actually name the licence it claims, so a record cannot
        # cite a page that says something else.
        statement = source["license_statement_quoted_from_the_pdf"].lower()
        assert "creative commons" in statement or "licensed under" in statement
        if key == "chemistry":
            assert "non-commercial" in statement or "noncommercial" in statement


def test_the_noncommercial_source_is_cleared_restrictively() -> None:
    chemistry = _source("chemistry")
    permitted = set(chemistry["permitted_uses"])
    assert "commercial_use" not in permitted
    assert "public_release" not in permitted
    assert permitted == {"internal_use", "derivative_work", "benchmark_use"}
    assert "commercial_use" in chemistry["not_permitted"]
    # ShareAlike is recorded as a condition that reaches every derivative, not as a note.
    assert any("ShareAlike" in condition for condition in chemistry["conditions"])
    assert _load(SOURCE_RIGHTS)["commercial_use_intended"] is False


def test_the_permissive_source_is_not_needlessly_encumbered() -> None:
    physics = _source("physics")
    permitted = set(physics["permitted_uses"])
    assert "commercial_use" in permitted
    assert "public_release" in permitted
    assert physics["not_permitted"] == []
    assert any("attribution" in condition.lower() for condition in physics["conditions"])


def test_the_two_licences_are_kept_in_separate_campaigns() -> None:
    record = _load(SOURCE_RIGHTS)
    assert record["campaign_structure"] == "two campaigns, one per source"
    assert "no artifact ever merges" in record["why_two_campaigns"]
    assert "unencumbered" in record["why_two_campaigns"]


def test_the_gate_admitted_each_source_and_refuses_a_neighbouring_hash() -> None:
    record = _load(SOURCE_RIGHTS)
    assert record["all_sources_admitted_by_the_gate"] is True
    assert record["gate_refuses_a_neighbouring_hash_for_every_source"] is True
    for key in ("physics", "chemistry"):
        assert _source(key)["gate_admits_this_source"] is True
        assert _source(key)["gate_refuses_a_neighbouring_hash"] is True


def test_the_w0_record_still_says_the_review_had_not_concluded() -> None:
    """W0's observation is history, and history is not edited to match the present."""
    w0 = _load(W0_RIGHTS_GATE)
    assert w0["source_rights_review"]["concluded"] is False
    assert w0["blocking_dependency"] is not None
    assert _load(SOURCE_RIGHTS)["supersedes_the_blocking_dependency_in"] == (
        "sprint-22c-rights-gate.json"
    )
    assert "stays exactly as sealed" in _load(SOURCE_RIGHTS)["w0_record_is_not_edited"]


def test_the_w0_seal_still_reproduces_over_its_unchanged_body() -> None:
    document = _load(W0_RIGHTS_GATE)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    assert _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_the_clearance_names_a_content_hash_so_a_redownload_is_a_different_source() -> None:
    record = _load(SOURCE_RIGHTS)
    hashes = {item["source_content_hash"] for item in record["sources"]}
    assert len(hashes) == 2
    assert any("different source" in limitation for limitation in record["limitations"])
