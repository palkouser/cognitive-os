"""S22C-040. The chapter cycle 1 acquires, located in the source's own words.

W1 registered **one** passage out of the cleared physics PDF, chosen by hand and addressed by
its opening and closing sentences. A campaign cannot be assembled that way: a chapter's worth
of passages picked one at a time is a curriculum the driver's author chose, and the yield —
how much of a real chapter a governed pipeline can actually acquire — would be a property of
that choosing rather than of the chapter.

So this module locates **every** worked example in the chapter by one rule applied uniformly,
and hands the campaign whatever that rule finds:

* the chapter's body pages are named, and the running heads on them are recorded, so the
  range can be checked rather than believed;
* a passage starts at the `WORKED EXAMPLE` marker and ends at the next structural marker of
  the book's own layout — never at a character offset typed into a driver;
* the located bytes are kept exactly as `pdftotext` produced them, page furniture and all,
  for the reason W1 found: a campaign that cleans its sources cannot afterwards prove what it
  read.

**What this module deliberately does not do** is decide whether a passage is usable. Whether
its arithmetic survived into the text layer, whether a kernel can recompute it, and whether
the value it asserts is exact are all judgements the cycle makes with evidence — the
provider proposes the formalisation, the domain's kernel recomputes it, and the cross-check
compares. A reader that pre-filtered its own inventory would be answering the sprint's
question before the pipeline ran.

    UV_CACHE_DIR=.cache/uv uv run python scripts/chapter_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/chapter_22c.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"
OUTPUT = EVIDENCE / "sprint-22c-w2-chapter.json"
CHEMISTRY_OUTPUT = EVIDENCE / "sprint-22c-w3-chapter.json"

#: The gate owner's files, named rather than searched for (W1).
SOURCE_PATH = Path.home() / "Letöltések" / "Physics_-_WEB.pdf"
CHEMISTRY_SOURCE_PATH = Path.home() / "Letöltések" / "chemistry-2e_-_WEB.pdf"


@dataclass(frozen=True, slots=True)
class ChapterSpec:
    """One chapter of the cleared source, and the problem type it was chosen for.

    Page numbers are the PDF's, not the folio numbers printed on the page — the two differ by
    twelve in this edition, which is exactly the sort of thing a record has to state rather
    than leave a reader to discover. The `body` range ends where the chapter's own review
    begins; the review pages are excluded because they are exercises with no worked
    solutions, so nothing in them can be recomputed, and counting them would inflate the
    denominator of a yield this sprint is about to publish.
    """

    number: int
    title: str
    body: tuple[int, int]
    review: tuple[int, int]
    #: The registered problem type S22C-020 named this chapter for. Recorded so the yield can
    #: be read per problem type rather than only in total — which is what turned out to
    #: matter (W2-F1).
    chosen_for: str


#: The three chapters the rights record names for `engineering.mechanics`, one per registered
#: problem type. Cycle 1 takes all three: a cycle that read only the kinematics chapter would
#: measure one problem type's coverage and report it as the source's yield.
CHAPTERS: tuple[ChapterSpec, ...] = (
    ChapterSpec(2, "Motion in One Dimension", (67, 95), (96, 105), "mechanics.uniform-motion"),
    ChapterSpec(
        4,
        "Forces and Newton’s Laws of Motion",  # noqa: RUF001 - the book's own title
        (133, 153),
        (154, 162),
        "mechanics.statics-equilibrium",
    ),
    ChapterSpec(
        6,
        "Circular and Rotational Motion",
        (217, 239),
        (240, 246),
        "mechanics.moment-balance",
    ),
)

MARKER = "WORKED EXAMPLE\n"

#: The book's own structural markers. A passage runs from `WORKED EXAMPLE` to whichever of
#: these comes first — the layout decides where a worked example ends, not this driver.
STOP_MARKERS: tuple[str, ...] = (
    "\nWORKED EXAMPLE",
    "\nPractice Problems",
    "\nCheck Your Understanding",
    "\nTIPS FOR SUCCESS",
    "\nSNAP LAB",
    "\nLINKS TO PHYSICS",
    "\nWATCH PHYSICS",
    "\nBOUNDLESS PHYSICS",
    "\nVirtual Physics",
    "\nFUN IN PHYSICS",
    "\nWORK IN PHYSICS",
    "\nFIGURE ",
    "\nSection Summary",
    "\nKEY TERMS",
)

#: **W3.** The second cleared source is a different book with a different layout, and
#: pretending otherwise would have cost a wave. *Chemistry 2e* opens a worked example with
#: `EXAMPLE 3.1` rather than `WORKED EXAMPLE`, and — unlike the physics text — it closes one
#: with a `Check Your Learning` question whose `Answer:` is printed in the text layer. That
#: answer is the only place in either book where a stated result reliably survives extraction,
#: so the passage must be cut *after* it, not before.
CHEMISTRY_MARKER = re.compile(r"^EXAMPLE \d+\.\d+\n", re.M)

CHEMISTRY_STOP_MARKERS: tuple[str, ...] = (
    "\nEXAMPLE ",
    "\nFIGURE ",
    "\nLINK TO LEARNING",
    "\nHOW SCIENCES INTERCONNECT",
    "\nCHEMISTRY IN EVERYDAY LIFE",
    "\nPORTRAIT OF A CHEMIST",
    "\nCHEMISTRY IN CONTEXT",
    "\nKey Terms",
    "\nKey Equations",
    "\nSummary",
    "\nExercises",
)

#: Where a chemistry example ends when it has a `Check Your Learning`: one line after the
#: answer, because that answer is the last thing the example asserts and everything after it
#: is the next piece of body prose.
CHEMISTRY_END = re.compile(r"\nAnswer:\n[^\n]+\n")


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """One cleared book, and how its own layout marks a worked example.

    Two books, two layouts, and the profile is what keeps that from becoming two readers.
    `id_prefix` is empty for physics and not for chemistry, deliberately: the physics passage
    identities are already sealed in W2's records and in eighteen sealed provider proposals,
    and a wave does not rewrite an identity that evidence already names.
    """

    key: str
    path: Path
    marker: re.Pattern[str]
    #: The marker as a reader sees it on the page. The compiled pattern is an implementation
    #: detail and does not belong in a record: W2's inventory named `WORKED EXAMPLE`, and a
    #: refactor that turned a literal into a regex must not rewrite what a sealed record says.
    marker_text: str
    stops: tuple[str, ...]
    end: re.Pattern[str] | None
    chapters: tuple[ChapterSpec, ...]
    why_these_chapters: str
    id_prefix: str = ""


#: The running-head shape, `2.2 • Speed and Velocity`. Read out of the pages rather than
#: transcribed, because a section number typed into a driver is a citation nobody checked.
#: Both OpenStax books use it, which is the one thing about their layouts that agrees.
SECTION_HEAD = re.compile(r"^(\d+\.\d+) • (.+)$", re.M)
CHAPTER_HEAD = re.compile(r"^(\d+) • (.+)$", re.M)

#: The two chemistry chapters S22C-020 names for `science.chemistry`, one per registered
#: problem type. Folio numbers run fourteen behind the PDF's in this edition.
CHEMISTRY_CHAPTERS: tuple[ChapterSpec, ...] = (
    ChapterSpec(
        3,
        "Composition of Substances and Solutions",
        (129, 159),
        (160, 168),
        "chemistry.molar-conversion",
    ),
    ChapterSpec(
        4,
        "Stoichiometry of Chemical Reactions",
        (169, 205),
        (206, 218),
        "chemistry.mass-balance",
    ),
)

PHYSICS = SourceProfile(
    key="physics",
    path=SOURCE_PATH,
    marker=re.compile(r"^WORKED EXAMPLE\n", re.M),
    marker_text="WORKED EXAMPLE",
    stops=STOP_MARKERS,
    end=None,
    chapters=CHAPTERS,
    why_these_chapters=(
        "S22C-020 names chapters 2, 4 and 6 of this source for engineering.mechanics, "
        "one per registered problem type. Cycle 1 takes all three: a cycle that read "
        "only the kinematics chapter would measure one problem type's coverage and "
        "report it as the source's yield"
    ),
)

CHEMISTRY = SourceProfile(
    key="chemistry",
    path=CHEMISTRY_SOURCE_PATH,
    marker=CHEMISTRY_MARKER,
    marker_text="EXAMPLE <chapter>.<number>",
    stops=CHEMISTRY_STOP_MARKERS,
    end=CHEMISTRY_END,
    chapters=CHEMISTRY_CHAPTERS,
    why_these_chapters=(
        "S22C-020 names chapters 3 and 4 of this source for science.chemistry, one per "
        "registered problem type: 3 for molar conversion and 4 for mass balance. Cycle 2 "
        "takes both, for the reason W2-F1 made concrete — a yield read from one chapter is "
        "a statement about one problem type"
    ),
    # Physics passage identities are already sealed in W2's records and in eighteen sealed
    # provider proposals. A wave does not rewrite an identity that evidence already names, so
    # the *new* source takes the prefix and the old one keeps its bare ids.
    id_prefix="chem-",
)

PROFILES: dict[str, SourceProfile] = {"physics": PHYSICS, "chemistry": CHEMISTRY}
OUTPUTS: dict[str, Path] = {"physics": OUTPUT, "chemistry": CHEMISTRY_OUTPUT}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def page_text(path: Path, first: int, last: int) -> str:
    """The document's own text layer for a page range, extracted and never edited."""
    result = subprocess.run(  # fixed argv, no shell
        ["pdftotext", "-f", str(first), "-l", str(last), str(path), "-"],
        capture_output=True,
        check=True,
    )
    return result.stdout.decode("utf-8")


def passage_id(profile: SourceProfile, chapter: ChapterSpec, title: str) -> str:
    """A stable identity for a passage, derived from the book's own heading.

    Several worked examples differ only by the suffix `, Take Two`, which the slug keeps —
    the book distinguishes them that way and so does the campaign. The chapter number is a
    prefix because two chapters of one book may reuse a heading, and the profile's prefix
    keeps two *books* apart.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{profile.id_prefix}ch{chapter.number}-{slug}"[:96]


@dataclass(frozen=True, slots=True)
class Passage:
    """One worked example, exactly as the chapter's text layer carries it."""

    passage_id: str
    chapter: int
    title: str
    section: str
    first_page: int
    window: tuple[int, int]
    text: str

    @property
    def content_hash(self) -> str:
        return _sha256(self.text.encode("utf-8"))

    @property
    def crosses_a_page_boundary(self) -> bool:
        return "\f" in self.text

    @property
    def has_a_solution_heading(self) -> bool:
        return "\nSolution" in self.text


def body_pages(profile: SourceProfile, chapter: ChapterSpec) -> tuple[str, ...]:
    """The chapter body, one entry per page, from a single extraction.

    `pdftotext` ends every page with a form feed, so splitting on it recovers the exact page
    boundaries the citation has to be able to name. Extracting page by page would give the
    same characters and cost one subprocess per page; extracting the range and *not*
    splitting would lose which page a passage starts on.
    """
    first_page, last_page = chapter.body
    pages = page_text(profile.path, first_page, last_page).split("\f")
    if pages and not pages[-1]:
        pages.pop()
    expected = last_page - first_page + 1
    if len(pages) != expected:
        raise SystemExit(
            f"the chapter body extracted as {len(pages)} pages, not {expected}: the page "
            "range and the extraction disagree, and a citation cannot name a page nobody "
            "counted"
        )
    return tuple(pages)


def sections_by_page(pages: tuple[str, ...], chapter: ChapterSpec) -> tuple[str, ...]:
    """The section in force on each page, forward-filled from the running heads.

    The running head carries the section only on the pages the book chooses to put it on;
    the pages between inherit it. Filling forward is what the printed page means, and it is
    the difference between attributing a passage to its section and attributing it to
    whichever head happened to be nearby.
    """
    current = f"{chapter.number} {chapter.title}"
    resolved: list[str] = []
    for page in pages:
        match = SECTION_HEAD.search(page)
        if match:
            current = f"{match.group(1)} {match.group(2).strip()}"
        resolved.append(current)
    return tuple(resolved)


def locate_chapter(profile: SourceProfile, chapter: ChapterSpec) -> tuple[Passage, ...]:
    """Every worked example in one chapter body, by one rule applied to every page.

    The window is two pages wide because a worked example may run over a page break — W1's
    did — and only markers that begin on the window's *first* page are collected, so an
    overlapping window records each passage once.

    **W3.** The cut is the profile's, because the two books end an example differently. The
    physics text runs to the next structural marker. The chemistry text closes with a
    `Check Your Learning` whose `Answer:` is the last thing the example asserts and the only
    stated result that reliably survives extraction, so the cut falls one line after it.
    """
    first_page, _ = chapter.body
    pages = body_pages(profile, chapter)
    sections = sections_by_page(pages, chapter)
    found: dict[str, Passage] = {}
    for index, page in enumerate(pages):
        if not profile.marker.search(page):
            continue
        following = pages[index + 1] if index + 1 < len(pages) else ""
        window = page + "\f" + following
        for match in profile.marker.finditer(window):
            if match.start() >= len(page):
                break
            title = window[match.end() :].split("\n", 1)[0].strip()
            body = window[match.end() :]
            ends = [body.find(stop) for stop in profile.stops]
            cut = min([value for value in ends if value != -1], default=len(body))
            if profile.end is not None:
                closing = profile.end.search(body, 0, cut)
                if closing is not None:
                    cut = closing.end()
            text = window[match.start() : match.end() + cut]
            identity = passage_id(profile, chapter, title)
            if identity in found:
                continue
            found[identity] = Passage(
                passage_id=identity,
                chapter=chapter.number,
                title=title,
                section=sections[index],
                first_page=first_page + index,
                window=(
                    first_page + index,
                    first_page + min(index + 1, len(pages) - 1),
                ),
                text=text,
            )
    return tuple(found.values())


def locate_passages(profile: SourceProfile) -> tuple[Passage, ...]:
    """Every worked example in every chapter the rights record names, in chapter order."""
    located: list[Passage] = []
    for chapter in profile.chapters:
        located.extend(locate_chapter(profile, chapter))
    return tuple(located)


def running_heads(profile: SourceProfile, chapter: ChapterSpec) -> dict[str, Any]:
    """What the chapter's own pages say they are, so the page range can be checked."""
    pages = body_pages(profile, chapter)
    review = page_text(profile.path, *chapter.review)
    chapters = {match.group(1) for match in CHAPTER_HEAD.finditer("\n".join(pages))}
    sections = sorted(set(sections_by_page(pages, chapter)) - {f"{chapter.number} {chapter.title}"})
    return {
        "number": chapter.number,
        "title": chapter.title,
        "chosen_for": chapter.chosen_for,
        "body_pages": list(chapter.body),
        "chapter_numbers_seen_in_the_body": sorted(chapters),
        "body_is_one_chapter": chapters == {str(chapter.number)},
        "sections_seen": sections,
        "review_pages_excluded": list(chapter.review),
        "review_declares_itself_review": any(
            marker in review for marker in ("Chapter Review", "Test Prep", "Exercises")
        ),
    }


def chapter_record(profile: SourceProfile = PHYSICS) -> dict[str, Any]:
    if not profile.path.exists():
        raise SystemExit(f"the cleared source is not at {profile.path}")
    rights = json.loads(SOURCE_RIGHTS.read_text(encoding="utf-8"))
    physics = next(item for item in rights["sources"] if item["key"] == profile.key)

    # Fail closed before a byte of content is read, exactly as W1 does: the clearance names
    # bytes, and these must be them.
    file_hash = _sha256(profile.path.read_bytes())
    if file_hash != physics["source_content_hash"]:
        raise SystemExit(
            f"the file at {profile.path} hashes {file_hash[:16]}…, the clearance names "
            f"{physics['source_content_hash'][:16]}… — this is a different source"
        )

    passages = locate_passages(profile)
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W2" if profile.key == "physics" else "W3",
        "items": ["S22C-040" if profile.key == "physics" else "S22C-050"],
        "recorded_at": _now(),
        "decides_an_exit_criterion": False,
        "why_no_exit": (
            "this is an inventory of what the chapter contains, not a measurement of what "
            "the pipeline did with it. Every 22C exit is read from the cycle records"
        ),
        "source": {
            "file_name": physics["file_name"],
            "source_content_hash": physics["source_content_hash"],
            "verified_against_the_clearance": True,
            "license_identifier": physics["license_identifier"],
            "attribution_required": physics["attribution_required"],
            "domain_id": physics["domain_id"],
        },
        "chapters": [running_heads(profile, chapter) for chapter in profile.chapters],
        "why_these_chapters": profile.why_these_chapters,
        "why_the_review_is_excluded": (
            "Chapter Review and Test Prep are exercises with no worked solutions, so nothing "
            "in them can be recomputed by a kernel. Counting them would inflate the "
            "denominator of the acquisition yield this campaign publishes"
        ),
        "location_rule": {
            "marker": profile.marker_text,
            "stops": [stop.strip() for stop in profile.stops],
            **({"ends_after": profile.end.pattern} if profile.end is not None else {}),
            "window_pages": 2,
            "attributed_to": "the page the marker is on, so an overlapping window collects "
            "each passage once",
            "never": "a character offset typed into a driver; offsets move with pdftotext",
            "bytes_are_kept": (
                "page furniture, form feeds and running heads inside a passage are left in "
                "the registered bytes. W1: a campaign that cleans its sources cannot "
                "afterwards prove what it read"
            ),
        },
        "passages": [
            {
                "passage_id": item.passage_id,
                "chapter": item.chapter,
                "title": item.title,
                "section": item.section,
                "first_page": item.first_page,
                "window": list(item.window),
                "characters": len(item.text),
                "content_hash": item.content_hash,
                "crosses_a_page_boundary": item.crosses_a_page_boundary,
                "has_a_solution_heading": item.has_a_solution_heading,
            }
            for item in passages
        ],
        "counts": {
            "chapters": len(profile.chapters),
            "worked_examples_in_the_bodies": len(passages),
            "per_chapter": {
                str(chapter.number): sum(1 for item in passages if item.chapter == chapter.number)
                for chapter in profile.chapters
            },
            "crossing_a_page_boundary": sum(1 for item in passages if item.crosses_a_page_boundary),
            "with_a_solution_heading": sum(1 for item in passages if item.has_a_solution_heading),
            "sections_contributing": len({item.section for item in passages}),
        },
        "what_this_record_does_not_decide": [
            "whether a passage can be formalised — the provider proposes that, and the "
            "record of what it proposed is the cycle's",
            "whether a passage's asserted answer survived into the text layer, which is the "
            "question the cross-check answers with the domain's own kernel",
            "which passages are acquired. A reader that pre-filtered its inventory would "
            "answer the yield question before the pipeline ran",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source", choices=sorted(PROFILES), default="physics")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    profile = PROFILES[arguments.source]
    output = arguments.output or OUTPUTS[arguments.source]

    if arguments.check:
        stored = json.loads(output.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        moving = {"recorded_at", "integrity_content_hash"}
        rebuilt = chapter_record(profile) if profile.path.exists() else None
        same = rebuilt is not None and {
            key: value for key, value in stored.items() if key not in moving
        } == {key: value for key, value in rebuilt.items() if key not in moving}
        print(
            json.dumps(
                {
                    "path": output.name,
                    "stored_seal_intact": sealed,
                    "source_available": profile.path.exists(),
                    "rebuilt_and_identical": same,
                    "reproduced": sealed and (same or not profile.path.exists()),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if sealed and (same or not profile.path.exists()) else 1

    record = chapter_record(profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "worked_examples": record["counts"]["worked_examples_in_the_bodies"],
                "per_chapter": record["counts"]["per_chapter"],
                "sections": record["counts"]["sections_contributing"],
                "crossing_a_page_boundary": record["counts"]["crossing_a_page_boundary"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
