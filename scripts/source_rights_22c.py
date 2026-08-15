"""S22C-020. The concluded source-rights review, sealed from the licence bytes themselves.

W0 reported the review as a blocking dependency and refused to pick a source, because §1.3
reserves that choice to the gate owner. The gate owner has now nominated two sources. This
driver turns that nomination into the record §1.3 requires — and it does **not** take the
nomination's word for the licence.

**The finding this driver exists to have already caught.** The sources were nominated as "CC
BY, OpenStax-class". Reading the licence page out of each PDF shows they are not the same
licence:

* `Physics_-_WEB.pdf` — **CC BY 4.0**, (c)2020 Texas Education Agency, adapted by OpenStax;
* `chemistry-2e_-_WEB.pdf` — **CC BY-NC-SA 4.0**, (c)2026 Rice University.

That difference is not cosmetic. NonCommercial bars commercial use of everything derived
from the chemistry book, and ShareAlike means every adaptation inherits the same licence —
which reaches forward into 22D, whose Layer 1 is exactly this acquired-knowledge store. A
rights record that had simply written down "CC BY" because that is what the nomination said
would have been the single most expensive kind of wrong thing in this sprint: a clearance
that looks valid, on bytes it does not describe. The gate's second probe exists for that
case, and here it would have fired on real content.

So the clearance is derived from the licence page's own bytes, the `evidence_hash` is over
those bytes, and the two sources are cleared **separately** with different permitted uses.
The gate owner's decision, recorded here: two campaigns, one per source, so no artifact ever
merges a CC BY lineage with an NC-SA one; and the NC-SA source is cleared conservatively for
research and internal use, with commercial use and public release excluded.

    UV_CACHE_DIR=.cache/uv uv run python scripts/source_rights_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/source_rights_22c.py --check

Read-only with respect to every store. It reads two files outside the repository and writes
one evidence record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import RightsNotCleared, rights_gate  # noqa: E402

from cognitive_os.domain.campaigns import (  # noqa: E402
    CampaignSourceRights,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import CorpusUsageRight  # noqa: E402

OUTPUT = EVIDENCE / "sprint-22c-source-rights.json"

#: The gate owner's clearance decision, taken 2026-08-15 on the two nominated sources.
CLEARED_BY = "palkouser (Sprint 22 gate owner)"
CLEARED_AT = datetime(2026, 8, 15, 0, 0, tzinfo=UTC)

#: The campaign structure the gate owner chose: one campaign per source, so a CC BY lineage
#: and an NC-SA lineage never merge inside one artifact.
CAMPAIGN_STRUCTURE = "two campaigns, one per source"


@dataclass(frozen=True, slots=True)
class NominatedSource:
    """One nominated file, and everything the clearance must state about it.

    `licence_page` is where the licence statement actually is, found by searching rather
    than assumed, because the evidence hash is over that page's bytes and a hash over the
    wrong page would be evidence of nothing.
    """

    key: str
    path: Path
    domain_id: str
    edition: str = ""
    author: str = ""
    location: str = ""
    licence_identifier: str = ""
    licence_url: str = ""
    licence_page: int = 4
    permitted_uses: tuple[CorpusUsageRight, ...] = ()
    attribution_required: str = ""
    conditions: tuple[str, ...] = ()
    notes: str = ""


SOURCES: tuple[NominatedSource, ...] = (
    NominatedSource(
        key="physics",
        path=Path("/home/palkouser/Letöltések/Physics_-_WEB.pdf"),
        domain_id="engineering.mechanics",
        edition="High School Physics, 2020 original publication year, web PDF",
        author=(
            "Paul Peter Urone and Roger Hinrichs (senior contributing authors); OpenStax, "
            "Rice University; originally created through a Texas Education Agency initiative"
        ),
        location=(
            "OpenStax, Rice University — https://openstax.org; original material at "
            "https://www.texasgateway.org/book/tea-physics"
        ),
        licence_identifier="CC-BY-4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/",
        # CC BY 4.0 permits every use in the released vocabulary, subject to attribution.
        # The record states what the licence allows; what the campaign actually does is the
        # manifest's `declared_uses`, and the contract checks the second against the first.
        permitted_uses=tuple(CorpusUsageRight),
        attribution_required=(
            "attribute the original: (c)2020 Texas Education Agency (TEA), adapted by "
            "OpenStax, licensed CC BY 4.0"
        ),
        conditions=(
            "attribution required on every derivative",
            "the OpenStax and Rice University names and logos are trademarks excluded from "
            "the licence and are never reproduced by this campaign",
        ),
        notes="clean permissive licence; no downstream encumbrance on derived artifacts",
    ),
    NominatedSource(
        key="chemistry",
        path=Path("/home/palkouser/Letöltések/chemistry-2e_-_WEB.pdf"),
        domain_id="science.chemistry",
        edition="Chemistry 2e, web PDF, (c)2026 Rice University",
        author=(
            "Paul Flowers, Klaus Theopold, Richard Langley and William R. Robinson "
            "(senior contributing authors); OpenStax, Rice University"
        ),
        location=("OpenStax, Rice University — https://openstax.org/details/books/chemistry-2e"),
        licence_identifier="CC-BY-NC-SA-4.0",
        licence_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        # The gate owner's conservative decision: research and internal use only. Every one
        # of these is comfortably inside NC-SA; commercial use is barred by the licence, and
        # public release is excluded by decision rather than by necessity, because releasing
        # would drag ShareAlike onto whatever it is released with.
        permitted_uses=(
            CorpusUsageRight.INTERNAL_USE,
            CorpusUsageRight.DERIVATIVE_WORK,
            CorpusUsageRight.BENCHMARK_USE,
        ),
        attribution_required='"Access for free at openstax.org."',
        conditions=(
            "noncommercial use only — CorpusUsageRight.COMMERCIAL_USE is not cleared",
            "ShareAlike: any adaptation shared onward must carry CC BY-NC-SA 4.0, so every "
            "artifact derived from this source is encumbered and must stay labelled",
            "public release excluded by gate-owner decision, not by the licence",
            "the OpenStax, Rice University and Kendall Hunt names and logos are trademarks "
            "excluded from the licence and are never reproduced by this campaign",
        ),
        notes=(
            "nominated as CC BY; the licence page says CC BY-NC-SA 4.0. The record follows "
            "the bytes, not the nomination"
        ),
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _licence_page_text(source: NominatedSource) -> str:
    """The licence page, extracted from the PDF itself."""
    result = subprocess.run(
        [
            "pdftotext",
            "-f",
            str(source.licence_page),
            "-l",
            str(source.licence_page),
            str(source.path),
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _licence_statement(text: str) -> str:
    """The sentences naming the licence, so the record quotes rather than paraphrases."""
    lines = [line.strip() for line in text.splitlines()]
    marked = [
        index
        for index, line in enumerate(lines)
        if "creative commons" in line.lower() or "licensed under" in line.lower()
    ]
    if not marked:
        raise SystemExit("no licence statement found on the declared licence page")
    start = max(0, marked[0] - 1)
    end = min(len(lines), marked[-1] + 4)
    return " ".join(part for part in lines[start:end] if part)


def _clearance(source: NominatedSource) -> tuple[CampaignSourceRights, dict[str, Any]]:
    if not source.path.is_file():
        raise SystemExit(f"nominated source is missing: {source.path}")
    content = source.path.read_bytes()
    source_hash = _sha256(content)
    page_text = _licence_page_text(source)
    evidence_hash = _sha256(page_text.encode("utf-8"))
    statement = _licence_statement(page_text)

    # Built through the released contract, so the clearance is validated by the same code
    # the campaign will validate it with — not by this driver's opinion of it.
    rights = CampaignSourceRights(
        status=RightsClearanceStatus.CLEARED,
        source_content_hash=source_hash,
        edition=source.edition,
        author=source.author,
        location=source.location,
        license_identifier=source.licence_identifier,
        permitted_uses=source.permitted_uses,
        cleared_by=CLEARED_BY,
        cleared_at=CLEARED_AT,
        evidence_hash=evidence_hash,
        notes=source.notes,
    )

    # And the gate is run on it, both ways: it must admit the real hash and refuse a
    # neighbouring one. A clearance nobody put through the door is a clearance nobody tested.
    admitted = True
    try:
        rights_gate(rights, source_hash)
    except RightsNotCleared:
        admitted = False
    refused_other = False
    try:
        rights_gate(rights, _sha256(content + b"\x00"))
    except RightsNotCleared:
        refused_other = True

    body = {
        "key": source.key,
        "domain_id": source.domain_id,
        "file_name": source.path.name,
        "file_bytes": len(content),
        "source_content_hash": source_hash,
        "edition": source.edition,
        "author": source.author,
        "location": source.location,
        "license_identifier": source.licence_identifier,
        "license_url": source.licence_url,
        "license_statement_quoted_from_the_pdf": statement,
        "license_page": source.licence_page,
        "license_page_found_by": "searching each front-matter page for the statement",
        "evidence_hash": evidence_hash,
        "evidence_is": f"the extracted text of page {source.licence_page}, the licence page",
        "permitted_uses": sorted(use.value for use in source.permitted_uses),
        "not_permitted": sorted(
            use.value for use in CorpusUsageRight if use not in source.permitted_uses
        ),
        "attribution_required": source.attribution_required,
        "conditions": list(source.conditions),
        "notes": source.notes,
        "clearance_content_hash": rights.content_hash,
        "gate_admits_this_source": admitted,
        "gate_refuses_a_neighbouring_hash": refused_other,
    }
    return rights, body


def _record() -> dict[str, Any]:
    clearances = [_clearance(source) for source in SOURCES]
    bodies = [body for _rights, body in clearances]
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W1",
        "items": ["S22C-020"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "review_concluded": True,
        "cleared_by": CLEARED_BY,
        "cleared_at": CLEARED_AT.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "supersedes_the_blocking_dependency_in": "sprint-22c-rights-gate.json",
        "w0_record_is_not_edited": (
            "the W0 gate record truthfully states that the review had not concluded at W0. "
            "It stays exactly as sealed; this record is the conclusion, not a correction"
        ),
        "campaign_structure": CAMPAIGN_STRUCTURE,
        "why_two_campaigns": (
            "the two sources carry different licences. One campaign per source means no "
            "artifact ever merges a CC BY lineage with a CC BY-NC-SA one, so the permissive "
            "lineage stays unencumbered and the ShareAlike lineage stays labelled at every "
            "derivative"
        ),
        "the_nomination_was_corrected_by_the_evidence": {
            "nominated_as": "both CC BY, OpenStax-class",
            "found": {
                "physics": "CC BY 4.0 — as nominated",
                "chemistry": "CC BY-NC-SA 4.0 — NonCommercial and ShareAlike, not CC BY",
            },
            "why_it_matters": (
                "NonCommercial bars commercial use of everything derived from the chemistry "
                "book and ShareAlike propagates to every adaptation, which reaches forward "
                "into 22D, whose Layer 1 is this acquired-knowledge store"
            ),
            "how_it_was_found": (
                "the licence page was located by searching the front matter of each PDF and "
                "its text read, rather than the nomination being written down as fact"
            ),
        },
        "commercial_use_intended": False,
        "commercial_use_decision": (
            "gate owner: research and internal use. The NC-SA source is cleared for "
            "internal_use, derivative_work and benchmark_use only"
        ),
        "sources": bodies,
        "source_count": len(bodies),
        "all_sources_admitted_by_the_gate": all(item["gate_admits_this_source"] for item in bodies),
        "gate_refuses_a_neighbouring_hash_for_every_source": all(
            item["gate_refuses_a_neighbouring_hash"] for item in bodies
        ),
        "domains_covered": sorted({item["domain_id"] for item in bodies}),
        "limitations": [
            "two sources is two sources — §4's 'one source is one source' applies twice "
            "over, and generality across licences, formats and publishers is not claimed",
            "the clearance covers the files at the recorded content hashes; a re-download "
            "that differs by a byte is a different source and is refused by the gate",
            "trademark carve-outs are recorded as conditions, not enforced by code: no "
            "campaign stage reproduces a logo, but nothing checks that mechanically",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    record = _record()
    if arguments.check:
        stored = json.loads(arguments.output.read_text(encoding="utf-8"))
        moving = {"recorded_at", "integrity_content_hash"}
        same = {k: v for k, v in stored.items() if k not in moving} == {
            k: v for k, v in record.items() if k not in moving
        }
        print(
            json.dumps(
                {"path": arguments.output.name, "reproduced": same},
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if same else 1

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "review_concluded": record["review_concluded"],
                "sources": [
                    f"{item['key']}: {item['license_identifier']} -> {item['domain_id']}"
                    for item in record["sources"]
                ],
                "all_sources_admitted_by_the_gate": record["all_sources_admitted_by_the_gate"],
                "gate_refuses_a_neighbouring_hash": record[
                    "gate_refuses_a_neighbouring_hash_for_every_source"
                ],
                "campaign_structure": record["campaign_structure"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
