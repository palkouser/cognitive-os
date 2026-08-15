"""S22C-033. The real source's first segment, through all nine stages, into one domain.

§3.1: W0 ran the whole chain against a chapter this repository authored, and W1 runs it
against the chapter the gate owner cleared, before cycle 1 commits to a campaign. The two
runs share every stage function — `run_cycle` is the only way in, and the fixture is its
default rather than a separate path — so what differs between them is the source and nothing
else. That is the point: a slice whose real source travelled its own code would prove
nothing about the code the campaign runs.

**The source.** `Physics_-_WEB.pdf`, OpenStax High School Physics, CC BY 4.0, cleared in
S22C-020 against a content hash this driver re-verifies before it opens the file. One
worked example from §2.2 Speed and Velocity — Layla's displacement — into
`engineering.mechanics`. Chemistry is a separate campaign by the gate owner's decision and
is not touched here; its CC BY-NC-SA lineage never meets this one.

**What the real source found, which the fixture could not.** Every one of these is a
property of real technical prose that an authored fixture does not have, and each is
recorded with the offsets to check it by:

*The passage crosses a page boundary.* `pdftotext` puts the folio numbers, a form feed and
the running head in the **middle** of the worked example, because that is where they are in
the document. The registered bytes keep them. A campaign that quietly cleaned its sources
could never afterwards prove what it read, and the citation exit is a claim about bytes.

*The arithmetic is an image.* Under `Solution` the extracted text carries `2.2` — an
equation number — and nothing else. The computation is a figure with no text layer. So this
class of source states results and hides derivations, and the cross-check's second leg,
which compares the source's assertion against the kernel's computation, is the only thing
standing between the campaign and a number nobody checked.

*The passage asserts its answer twice, at two precisions.* "about 110 m east", and then "a
calculator shows the answer as 110.4 m". The kernel computes 552/5 exactly. Which of the
two an extraction takes decides whether a correct passage is acquired or quarantined, so the
rule is fixed here rather than per passage: **the exact value when the passage states one.**

    UV_CACHE_DIR=.cache/uv uv run python scripts/slice_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/slice_22c.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import (  # noqa: E402
    CAMPAIGN_STAGES,
    SLICE_TIME,
    Segment,
    SourceSpec,
    _canonical,
    _sha256,
    operator_clearance,
    run_cycle,
    walk_citations,
)

from cognitive_os.domain.campaigns import (  # noqa: E402
    CampaignBudget,
    CampaignCurriculum,
    CampaignHoldout,
    CampaignManifestV1,
    CampaignSourceRights,
    CampaignStopReason,
    RightsClearanceStatus,
)
from cognitive_os.domain.corpus import CorpusUsageRight  # noqa: E402
from cognitive_os.domain.semantic_memory import SemanticLiteralKind  # noqa: E402

SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"
#: **W1-D2.** `sprint-22c-w1-slice.json` records this passage being quarantined under the
#: previous licence design and keeps its seal: it is true about what it ran under. This is
#: the same passage under the gate owner's ruling, sealed beside it rather than over it.
OUTPUT = EVIDENCE / "sprint-22c-w1-slice-cleared.json"

#: The nominated file, where the gate owner put it. Named rather than searched for: a driver
#: that went looking for "a physics PDF" could find a different one and clear it by accident.
SOURCE_PATH = Path.home() / "Letöltések" / "Physics_-_WEB.pdf"

#: The passage, addressed the way a citation has to be able to address it: by page range and
#: by the text at each end, never by character offsets typed into a driver. Offsets shift
#: with every pdftotext version; these anchors are the document's own words.
PASSAGE_PAGES = (79, 80)
PASSAGE_OPENS = "WORKED EXAMPLE\nSolving for Displacement when Average Velocity and Time are Known"
PASSAGE_CLOSES = "we only used two significant figures."

#: The page furniture pdftotext interleaves into the passage, kept in the registered bytes
#: and named here so the record can point at what a reader will otherwise trip over.
FURNITURE = ("67", "68", "2 • Motion in One Dimension")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cleared_physics() -> tuple[CampaignSourceRights, dict[str, Any]]:
    """Rebuild the physics clearance through the released contract, from the sealed record.

    Not retyped: every field comes out of `sprint-22c-source-rights.json`, so a clearance
    that was narrowed after W1 opened the gate narrows this campaign too. The contract is
    the released `CampaignSourceRights`, which refuses to hold anything but a clearance.
    """
    record = _load(SOURCE_RIGHTS)
    entry = next(item for item in record["sources"] if item["key"] == "physics")
    rights = CampaignSourceRights(
        status=RightsClearanceStatus.CLEARED,
        source_content_hash=entry["source_content_hash"],
        edition=entry["edition"],
        author=entry["author"],
        location=entry["location"],
        license_identifier=entry["license_identifier"],
        permitted_uses=tuple(CorpusUsageRight(value) for value in sorted(entry["permitted_uses"])),
        cleared_by=record["cleared_by"],
        cleared_at=SLICE_TIME,
        evidence_hash=entry["evidence_hash"],
        notes=entry["notes"],
    )
    return rights, entry


def _pages_text(path: Path, first: int, last: int) -> str:
    """The document's own text layer for a page range, extracted and never edited."""
    result = subprocess.run(  # fixed argv, no shell
        ["pdftotext", "-f", str(first), "-l", str(last), str(path), "-"],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def extract_passage(path: Path) -> dict[str, Any]:
    """Locate the worked example inside the extracted pages and take it verbatim.

    The span is half-open over the *extracted text of the page range*, which is the artifact
    a citation can be checked against — the PDF's own byte offsets address a compressed
    content stream and address nothing a reader could verify.
    """
    text = _pages_text(path, *PASSAGE_PAGES)
    start = text.index(PASSAGE_OPENS)
    end = text.index(PASSAGE_CLOSES, start) + len(PASSAGE_CLOSES)
    passage = text[start:end]
    return {
        "pages": list(PASSAGE_PAGES),
        "page_text_sha256": _sha256(text.encode("utf-8")),
        "page_text_characters": len(text),
        "start": start,
        "end": end,
        "passage": passage,
        "passage_sha256": _sha256(passage.encode("utf-8")),
        "located_by": "the passage's own opening and closing words, never a typed offset",
        "crosses_a_page_boundary": "\f" in passage,
        "page_furniture_inside_the_passage": [
            {"text": item, "offset_in_passage": passage.index(item)}
            for item in FURNITURE
            if item in passage
        ],
        "the_arithmetic_is_an_image": "Solution\n2.2\n" in passage,
        "what_the_text_layer_carries_under_solution": (
            "the equation number 2.2 and nothing else; the computation is a figure with no "
            "text layer, so the derivation cannot be read and only the assertion can"
        ),
    }


def real_segment(passage: str) -> Segment:
    """One segment, derived from the passage and asserting what the passage asserts.

    `asserted` carries `110.4`, the exact value the Discussion states, and not the headline
    "about 110 m": the extraction rule is fixed for the campaign rather than chosen per
    passage, and it is the exact statement that a deterministic kernel can be held to.
    """
    return Segment(
        segment_id="physics-uniform-motion-layla",
        domain_id="engineering.mechanics",
        problem_type="mechanics.uniform-motion",
        subject="mechanics:uniform-motion",
        predicate_id="domain.worked_example",
        literal_kind=SemanticLiteralKind.STRING,
        value="a body at 2.4 m/s for 46 s is displaced 110.4 m",
        unit=None,
        prose=passage,
        formal_inputs={
            "speed": {"magnitude": "2.4", "unit": "m/s"},
            "time": {"magnitude": 46, "unit": "s"},
            "result_unit": "m",
        },
        asserted={"exact_value": "110.4", "units": "m"},
        expected_accepted=True,
        verbatim=passage,
    )


def real_manifest(rights: CampaignSourceRights, segment: Segment) -> CampaignManifestV1:
    """The physics campaign's manifest. One source, one domain, no provider, no spend."""
    return CampaignManifestV1(
        campaign_id="s22c-physics",
        revision=1,
        rights=rights,
        domain_ids=("engineering.mechanics",),
        goals=(
            "register the rights-cleared source and drive its first segment through all "
            "nine §9.1 stages",
            "walk the promoted artifact's citation back to the registered source bytes",
        ),
        budget=CampaignBudget(
            maximum_cycles=1,
            maximum_provider_calls_per_cycle=0,
            maximum_spend_usd=0.0,
            maximum_items_per_cycle=16,
        ),
        providers=(),
        curriculum=CampaignCurriculum(segment_hashes=(segment.content_hash,), segments_per_cycle=1),
        holdouts=(
            CampaignHoldout(
                holdout_id="s22c-w1-slice-holdout",
                case_hashes=(_sha256(b"s22c-w1-slice-holdout-placeholder"),),
                verifier_id="domains.checker",
                seeds=(22_031,),
                success_definition=(
                    "the case is accepted by domains.checker with every required capability "
                    "exercised"
                ),
                store_url_env="COGOS_HOLDOUT_DATABASE_URL",
            ),
        ),
        stop_conditions=(
            CampaignStopReason.STAGE_REFUSED,
            CampaignStopReason.CYCLE_TARGET_REACHED,
        ),
        # The clearance permits everything CC BY permits; the campaign still declares only
        # what it does. A manifest that declared its clearance's full breadth would make the
        # contract's use check vacuous.
        declared_uses=(CorpusUsageRight.INTERNAL_USE, CorpusUsageRight.DERIVATIVE_WORK),
        sealed_at=SLICE_TIME,
        sealed_by="sprint-22c-w1",
    )


async def slice_record() -> dict[str, Any]:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"the cleared source is not at {SOURCE_PATH}")
    rights, entry = _cleared_physics()

    # Fail closed, before a byte of content is read: the clearance names bytes, and these
    # must be them. A re-download that differs anywhere is a different source (S22C-020).
    file_hash = _sha256(SOURCE_PATH.read_bytes())
    if file_hash != rights.source_content_hash:
        raise SystemExit(
            f"the file at {SOURCE_PATH} hashes {file_hash[:16]}…, the clearance names "
            f"{rights.source_content_hash[:16]}… — this is a different source"
        )

    located = extract_passage(SOURCE_PATH)
    segment = real_segment(located["passage"])
    manifest = real_manifest(rights, segment)
    source = SourceSpec(
        identity=f"openstax:{entry['file_name']}",
        revision=entry["edition"],
        content_hash=rights.source_content_hash,
        media_type="text/plain",
        file_suffix=".txt",
    )
    clearance = operator_clearance(rights, rights.source_content_hash)
    state, composition = await run_cycle(manifest, segments=(segment,), source=source)
    citations = await walk_citations(composition, state)

    cross_check = state.cross_checks[segment.segment_id]
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W1",
        "items": ["S22C-033"],
        "recorded_at": _now(),
        "decides_an_exit_criterion": False,
        "why_no_exit": (
            "every 22C exit is a claim about three cycles over a campaign. This is one "
            "segment through one cycle, run before cycle 1 so the seams are found at the "
            "cost of one passage rather than at the cost of a campaign (§3.1)"
        ),
        "source": {
            "file_name": entry["file_name"],
            "source_content_hash": rights.source_content_hash,
            "verified_against_the_clearance": True,
            "license_identifier": entry["license_identifier"],
            "attribution_required": entry["attribution_required"],
            "domain_id": entry["domain_id"],
            "clearance_content_hash": rights.content_hash,
            "the_other_campaign_is_not_here": (
                "chemistry is CC BY-NC-SA and runs as its own campaign; no artifact in this "
                "record touches it, which is what keeping the two lineages apart means"
            ),
        },
        "passage": {key: value for key, value in located.items() if key not in {"passage"}},
        "what_the_real_source_had_that_the_fixture_did_not": [
            "the passage crosses a page boundary, so the folio numbers, a form feed and the "
            "running head sit inside the registered bytes. They are kept: a campaign that "
            "cleans its sources cannot afterwards prove what it read",
            "the worked example's arithmetic is an image with no text layer, so the source "
            "states a result and hides its derivation",
            "the passage asserts its answer at two precisions — 'about 110 m east' and "
            "'110.4 m' — and only the exact one can be held to a deterministic kernel",
            "the kernel answers in exact rationals (552/5) and the source writes decimals "
            "(110.4). W1-F3: the cross-check compared them as strings",
            "the released Corpus Factory does not recognise CC BY 4.0 and routed the passage "
            "to quarantine at stage 1, and the campaign promoted it anyway. W1-F5 in the "
            "driver, W1-F6 in the released licence policy — which W1-D2 then ruled a design "
            "error: a program may advise on a licence and may not decide it",
        ],
        "manifest": {
            "campaign_id": manifest.campaign_id,
            "revision": manifest.revision,
            "content_hash": manifest.content_hash,
            "rights_content_hash": manifest.rights.content_hash,
            "domain_ids": list(manifest.domain_ids),
            "providers": list(manifest.providers),
            "declared_uses": [use.value for use in manifest.declared_uses],
        },
        "stages": {
            "enumerated": [stage.value for stage in CAMPAIGN_STAGES],
            "completed": state.stages_completed,
            "count": len(state.stages_completed),
            "all_nine_in_order": state.stages_completed
            == [stage.value for stage in CAMPAIGN_STAGES],
            "same_functions_as_the_w0_slice": (
                "run_cycle is the only entry point, and the fixture chapter is its default "
                "argument rather than a separate path"
            ),
        },
        "register_source": state.corpus_items["_source_manifest"],
        "extract": {
            "proposals": len(state.proposals),
            "provider_calls": 0,
            "host_revalidated": sum(
                1 for item in state.proposals.values() if item["host_revalidated"]
            ),
        },
        "cross_check": {
            "derivation_accepted": cross_check["derivation_accepted"],
            "verifier_status": cross_check["verifier_status"],
            "assertion_agrees_with_kernel": cross_check["assertion_agrees_with_kernel"],
            "accepted": cross_check["accepted"],
            "asserted": cross_check["asserted"],
            "kernel_exact_value": "552/5",
            "the_two_are_one_number": (
                "Fraction('110.4') == Fraction('552/5'); the comparison is exact equality "
                "and not a tolerance, so the passage's rounded 'about 110 m' would still be "
                "refused"
            ),
        },
        "corpus_item": {
            "status": state.corpus_items[segment.segment_id]["status"],
            "routed_by": "the released CorpusFactory, at stage 1, before the campaign judged "
            "anything",
        },
        "quarantined": sorted(state.quarantined),
        "compiled": sorted(state.compiled),
        "promoted": sorted(state.promoted),
        "who_decided_this_material_may_be_used": {
            "authority": clearance.cleared_by,
            "decided_at": clearance.cleared_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "licence": clearance.identifier,
            "operator_status": clearance.status.value,
            "advisory_status": "unknown",
            "the_platform_did_not_recognise_this_licence": True,
            "and_that_is_not_a_refusal": (
                "W1-D2. The Corpus Factory recognises four software licences and offers that "
                "recognition as advice. It did not recognise CC BY 4.0 and said so, which is "
                "the correct thing for a program to say. What made the material usable is a "
                "person's determination, sealed in S22C-020, naming an authority and hashing "
                "the licence page — because the legal responsibility for using it is theirs "
                "and cannot be delegated to an allowlist"
            ),
            "clearance_evidence_hash": clearance.evidence_hash,
            "clearance_covers_bytes": clearance.source_content_hash,
        },
        "supersedes": {
            "record": "sprint-22c-w1-slice.json",
            "which_said": (
                "the same passage, quarantined with license-review-required. That record is "
                "true about the design it ran under and keeps its seal; this one is the same "
                "passage under the ruling in W1-D2"
            ),
            "what_changed_is_not_the_passage": (
                "byte-identical source, byte-identical extraction, the same nine stages and "
                "the same cross-check verdict. What changed is who was allowed to decide "
                "whether the material may be used"
            ),
        },
        "replay": state.replay,
        "citations": citations,
        "limitations": [
            "one passage, one domain, one source. The chapter is not acquired and no "
            "campaign number exists yet; W2's cycle 1 is where a corpus begins",
            "the extraction is host-side and deterministic. §3.3's provider path, with its "
            "receipts and sealed proposals, is W2's and is exercised by nothing here",
            "the passage was located by its own words, which is robust to offsets and not "
            "to a re-typeset edition. A new edition is a new source hash and a new clearance",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    if arguments.check:
        stored = _load(arguments.output)
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        rebuilt: dict[str, Any] | None = None
        if SOURCE_PATH.exists():
            rebuilt = asyncio.run(slice_record())
        moving = {"recorded_at", "integrity_content_hash"}
        same = rebuilt is not None and {
            key: value for key, value in stored.items() if key not in moving
        } == {key: value for key, value in rebuilt.items() if key not in moving}
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "stored_seal_intact": sealed,
                    # The cleared source is the gate owner's file and is not in the
                    # repository, so CI can verify the seal and not the run. Saying which
                    # was checked is the difference between a check and a claim.
                    "source_available": SOURCE_PATH.exists(),
                    "rebuilt_and_identical": same,
                    "reproduced": sealed and (same or not SOURCE_PATH.exists()),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if sealed and (same or not SOURCE_PATH.exists()) else 1

    record = asyncio.run(slice_record())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "stages": record["stages"]["count"],
                "all_nine_in_order": record["stages"]["all_nine_in_order"],
                "cross_check_accepted": record["cross_check"]["accepted"],
                "corpus_item_status": record["corpus_item"]["status"],
                "quarantined": record["quarantined"],
                "promoted": record["promoted"],
                "cleared_by": record["who_decided_this_material_may_be_used"]["authority"],
                "citations_resolve": record["citations"]["all_chains_resolve"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
