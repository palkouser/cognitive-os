"""S22D-100. The declarative-fact locators, and the coverage nobody priced in W0.

**Why this record exists at all, and it is a finding against W0.** 22C W3-F1 graduated into
this sprint's execution contract as a standing rule: *a verification floor decides what can be
acquired, and its coverage is priced before the campaign, not after — any wave that intends to
retain content states in advance which floor will verify it and samples the source against that
floor.* W0 froze a twelve-case declarative-fact holdout **without sampling the cleared sources
against it**. That is the rule the sprint's own §0 carries, broken by the wave that carries it.

The response is not to re-cut the holdout. Re-cutting an instrument after seeing which facts
the source happens to hold is choosing the questions to fit the answers, and nothing in
`measured_values: 0` makes that honest — the *selection* would be made against the data even
though no arm has run. So this module prices the coverage, publishes it **before** acquisition,
and leaves the holdout exactly as frozen. If the number that comes back is poor, it comes back
with its diagnosis attached, which is what §3.2 asks for.

**Three locators, fixed by the books' own layout rather than by the facts wanted.** Same
discipline as 22C's chapter reader: one rule applied uniformly, and the campaign takes whatever
it finds.

* `element_mass_table` — a table whose header names *Average Atomic Mass (amu)* and *Molar Mass
  (g/mol)*, read row by row. **The header is the whole safety argument.** Chapter 4 is full of
  lines that look identical to a table row — `C`, `1`, `H`, `4` — and they are stoichiometric
  subscripts. A locator keyed on the shape alone would retain "the atomic mass of C is 1" and
  every later verifier would agree with it, because nothing downstream knows what the number
  was supposed to mean.
* `stated_quantity` — the book saying it in a sentence: *the atomic mass of K is 39.10 amu*.
* `symbol_constant` — *g = 9.80 m/s2*, the physics chapters' way of stating a constant.

**And one refusal that is a locator's most useful output.** `pdftotext` renders
6.02214076 x 10^23 as `6.02214076 1023`: the multiplication sign and the superscript are gone,
and what is left reads as two numbers. This module **refuses** a numeral it cannot read
unambiguously, with a named reason, rather than repairing it. 22C W3-D1's rule — a component
that demands an input it does not use is a refusal with a name, never a value supplied to
satisfy it — applies exactly here, and the mangled exponent is the "maths is an image" wall in
its cheapest form.

    UV_CACHE_DIR=.cache/uv uv run python scripts/facts_22d.py --coverage
    UV_CACHE_DIR=.cache/uv uv run python scripts/facts_22d.py --coverage --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from chapter_22c import CHEMISTRY, PHYSICS, ChapterSpec, SourceProfile, page_text  # noqa: E402

COVERAGE_OUTPUT = EVIDENCE / "sprint-22d-w1-coverage.json"

#: Fixed, as everywhere in this sprint: a `--check` that re-derived "now" rebuilds a different
#: record every run (22C W1-F1).
W1_TIME = datetime(2026, 8, 15, 0, 0, 0, tzinfo=UTC)

#: The cleared sources, keyed as 22C's rights record keys them. This module never chooses a
#: chapter: it takes the ones S22C-020 cleared, which is what "needs no new rights decision"
#: means in the plan's W1 row.
PROFILES: tuple[SourceProfile, ...] = (CHEMISTRY, PHYSICS)


# ---------------------------------------------------------------------------
# The numeral reader, and the refusal that is its most useful output
# ---------------------------------------------------------------------------

#: A plain decimal. Anything else is refused rather than interpreted.
_PLAIN_NUMBER = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

#: What a lost `x 10^n` leaves behind: a decimal, whitespace, then a bare `10nn`. Recognised
#: **in order to refuse it**, so the refusal is specific rather than a shrug.
_MANGLED_EXPONENT = re.compile(r"^[0-9]+(?:\.[0-9]+)?\s+10[0-9]{1,2}$")

REFUSAL_MANGLED_EXPONENT = "numeral_lost_its_exponent_in_the_text_layer"
REFUSAL_NOT_A_PLAIN_NUMBER = "numeral_is_not_unambiguously_readable"
REFUSAL_SUBJECT_NOT_AN_ENTITY = "subject_is_a_sentence_fragment_not_an_entity"

#: A subject the pattern captured but no fact should carry. *"the molecular mass of chloroform,
#: which is 119.37 amu"* reads to `of X is N` as the subject `chloroform, which` — grammatically
#: the fact is about chloroform, and mechanically the locator has captured a relative clause.
#: Retaining it would put a sentence fragment where an entity belongs, and every verifier
#: downstream would accept it, because none of them knows what a subject is supposed to look
#: like. Narrowing the pattern until such sentences silently stop matching would hide the same
#: thing; refusing them by name counts it.
_SUBJECT_IS_A_FRAGMENT = re.compile(r"[,;]|\b(?:which|that|whose|and|or)\b", re.I)


class NumeralRefused(ValueError):
    """A numeral this module will not guess at. The reason travels with it."""

    def __init__(self, reason: str, raw: str) -> None:
        super().__init__(f"{reason}: {raw!r}")
        self.reason = reason
        self.raw = raw


def read_numeral(raw: str) -> str:
    """Return the numeral, or refuse by name. Never repairs, never guesses."""
    text = " ".join(raw.split())
    if _MANGLED_EXPONENT.match(text):
        raise NumeralRefused(REFUSAL_MANGLED_EXPONENT, text)
    if not _PLAIN_NUMBER.match(text):
        raise NumeralRefused(REFUSAL_NOT_A_PLAIN_NUMBER, text)
    return text


def read_subject(raw: str) -> str:
    """Return the entity a fact is about, or refuse by name."""
    text = " ".join(raw.split()).strip()
    if not text or _SUBJECT_IS_A_FRAGMENT.search(text):
        raise NumeralRefused(REFUSAL_SUBJECT_NOT_AN_ENTITY, text)
    return text


# ---------------------------------------------------------------------------
# The three locators
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactCandidate:
    """One located fact, addressed by a byte range in the chapter's extracted text.

    `start`/`end` are offsets into exactly the bytes `chapter_text()` returns, so a citation
    resolves by loading those bytes and cutting them — never by trusting an offset written
    down beside a quote.
    """

    candidate_id: str
    source_key: str
    chapter: int
    locator: str
    subject: str
    quantity: str
    value: str
    unit: str
    start: int
    end: int
    excerpt: str
    #: **What the kernel has to reproduce.** §1.5: a declarative fact cannot be recomputed, but
    #: a kernel-checkable consequence can corroborate it. The element-mass table prints the
    #: consequence in the next column — the molar mass in g/mol implied by the atomic mass in
    #: amu — so the kernel can be asked to derive it and the source's own printed value is the
    #: oracle. A candidate whose source prints no consequence carries `None`, and the ladder
    #: puts it on the weaker rung rather than pretending it was corroborated.
    consequence_value: str | None = None
    consequence_unit: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_key": self.source_key,
            "chapter": self.chapter,
            "locator": self.locator,
            "subject": self.subject,
            "quantity": self.quantity,
            "value": self.value,
            "unit": self.unit,
            "start": self.start,
            "end": self.end,
            "excerpt_hash": _sha256(self.excerpt.encode("utf-8")),
            "consequence_value": self.consequence_value,
            "consequence_unit": self.consequence_unit,
        }


@dataclass(frozen=True)
class FactRefusal:
    """A located shape this module declined to retain, and why. §1.2's 'surface, never absorb'."""

    source_key: str
    chapter: int
    locator: str
    reason: str
    raw: str

    def as_json(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "chapter": self.chapter,
            "locator": self.locator,
            "reason": self.reason,
            "raw": self.raw[:120],
        }


#: The table header that makes an element-mass row safe to read. Both columns are required:
#: a header naming only "Element" would match a dozen tables that are not this one.
_TABLE_HEADER = re.compile(
    r"Element\s*\n\s*\n?\s*Average Atomic Mass \(amu\)\s*\n\s*\n?\s*Molar Mass \(g/mol\)", re.M
)

#: One row of that table, as `pdftotext` lays it out: the symbol, the average atomic mass, the
#: molar mass, and the *Atoms/Mole* column — which is where the lost exponent lives, because
#: `6.022 x 10^23` arrives as the two separate lines `6.022` and `1023`. The row pattern reads
#: that column deliberately, so the refusal fires on real content instead of the locator
#: quietly stopping one column short of the problem.
#: The trailing boundary is a **lookahead**, not a consumed newline. Consuming it eats the
#: newline the next row starts with, `finditer` cannot overlap, and the table reads as every
#: other row — three of five, with H and Na simply absent and nothing anywhere saying so.
_TABLE_ROW = re.compile(
    r"\n\s*([A-Z][a-z]?)\s*\n\s*\n?\s*([0-9]+\.[0-9]+)\s*\n\s*\n?\s*([0-9]+\.[0-9]+)\s*\n"
    r"\s*\n?\s*([0-9]+(?:\.[0-9]+)?\s*\n\s*\n?\s*10[0-9]{1,2})(?=\s*\n)"
)

_STATED_QUANTITY = re.compile(
    r"(?:the\s+)?(atomic mass|molar mass|formula mass|molecular mass|average mass)\s+of\s+"
    r"([A-Za-z0-9()·,\-' ]{1,60}?)\s+is\s+([0-9]+(?:\.[0-9]+)?)\s*(amu|g/mol)\b",
    re.I | re.S,
)

_SYMBOL_CONSTANT = re.compile(r"\b([a-z])\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*(m/s2|m/s²|N/kg)\b")

#: How far past the table header rows are still that table's. Bounded so the locator cannot
#: wander into the next section and read its numbers as element masses.
_TABLE_WINDOW = 900


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def chapter_text(profile: SourceProfile, chapter: ChapterSpec) -> str:
    """Exactly the bytes every span in this wave is measured against."""
    return page_text(profile.path, *chapter.body)


def _slug(value: str) -> str:
    """The canonical-identifier shape the released semantic layer requires.

    `canonical_identifier` admits `^[a-z0-9][a-z0-9._:/@+-]*$` and nothing else, so a subject
    read out of prose — "average atomic mass", "an aspirin molecule" — has to be slugged before
    it can key a claim. The human form survives on the claim's `display_label`.
    """
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:48]


def _entity_id(quantity: str, subject: str) -> str:
    return f"{_slug(quantity)}:{_slug(subject)}"


def _candidate_id(source_key: str, chapter: int, locator: str, subject: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", subject.casefold()).strip("-")[:40]
    return f"{source_key}-ch{chapter}-{locator}-{slug}"


def locate_element_mass_table(
    profile: SourceProfile, chapter: ChapterSpec, text: str
) -> tuple[list[FactCandidate], list[FactRefusal]]:
    """Rows of a table the header has identified. **The header is the safety argument.**"""
    found: list[FactCandidate] = []
    refused: list[FactRefusal] = []
    for header in _TABLE_HEADER.finditer(text):
        window_end = min(len(text), header.end() + _TABLE_WINDOW)
        window = text[header.end() : window_end]
        for row in _TABLE_ROW.finditer(window):
            symbol, average, molar, atoms_per_mole = row.groups()
            start = header.end() + row.start(2)
            end = header.end() + row.end(2)
            # The Atoms/Mole cell is read and refused, every row. It is the same table, the
            # same rights clearance and the same locator as the mass cell beside it; the only
            # difference is that its numeral did not survive the text layer. Counting that is
            # the point — an unread column is indistinguishable from a column that is not
            # there, and only one of those is a source problem worth reporting.
            try:
                read_numeral(atoms_per_mole)
            except NumeralRefused as error:
                refused.append(
                    FactRefusal(
                        profile.key, chapter.number, "element_mass_table", error.reason, error.raw
                    )
                )
            try:
                value = read_numeral(average)
            except NumeralRefused as error:
                refused.append(
                    FactRefusal(
                        profile.key, chapter.number, "element_mass_table", error.reason, error.raw
                    )
                )
                continue
            found.append(
                FactCandidate(
                    candidate_id=_candidate_id(profile.key, chapter.number, "table", symbol),
                    source_key=profile.key,
                    chapter=chapter.number,
                    locator="element_mass_table",
                    subject=symbol,
                    quantity="average atomic mass",
                    value=value,
                    unit="amu",
                    start=start,
                    end=end,
                    excerpt=text[start:end],
                    consequence_value=molar,
                    consequence_unit="g/mol",
                )
            )
    return found, refused


def locate_stated_quantity(
    profile: SourceProfile, chapter: ChapterSpec, text: str
) -> tuple[list[FactCandidate], list[FactRefusal]]:
    found: list[FactCandidate] = []
    refused: list[FactRefusal] = []
    for match in _STATED_QUANTITY.finditer(text):
        quantity, raw_subject, raw, unit = match.groups()
        try:
            subject = read_subject(raw_subject)
            value = read_numeral(raw)
        except NumeralRefused as error:
            refused.append(
                FactRefusal(profile.key, chapter.number, "stated_quantity", error.reason, error.raw)
            )
            continue
        found.append(
            FactCandidate(
                candidate_id=_candidate_id(
                    profile.key, chapter.number, "stated", f"{quantity}-{subject}"
                ),
                source_key=profile.key,
                chapter=chapter.number,
                locator="stated_quantity",
                subject=subject,
                quantity=quantity.casefold(),
                value=value,
                unit=unit,
                start=match.start(),
                end=match.end(),
                excerpt=match.group(0),
            )
        )
    return found, refused


def locate_symbol_constant(
    profile: SourceProfile, chapter: ChapterSpec, text: str
) -> tuple[list[FactCandidate], list[FactRefusal]]:
    found: list[FactCandidate] = []
    refused: list[FactRefusal] = []
    for match in _SYMBOL_CONSTANT.finditer(text):
        symbol, raw, unit = match.groups()
        try:
            value = read_numeral(raw)
        except NumeralRefused as error:
            refused.append(
                FactRefusal(profile.key, chapter.number, "symbol_constant", error.reason, error.raw)
            )
            continue
        found.append(
            FactCandidate(
                candidate_id=_candidate_id(profile.key, chapter.number, "symbol", symbol),
                source_key=profile.key,
                chapter=chapter.number,
                locator="symbol_constant",
                subject=symbol,
                quantity="stated constant",
                value=value,
                unit=unit.replace("²", "2"),
                start=match.start(),
                end=match.end(),
                excerpt=match.group(0),
            )
        )
    return found, refused


LOCATORS = (locate_element_mass_table, locate_stated_quantity, locate_symbol_constant)


def locate_all() -> tuple[tuple[FactCandidate, ...], tuple[FactRefusal, ...]]:
    """Every cleared chapter, every locator, whatever they find. No chapter is chosen here."""
    candidates: list[FactCandidate] = []
    refusals: list[FactRefusal] = []
    for profile in PROFILES:
        for chapter in profile.chapters:
            text = chapter_text(profile, chapter)
            for locator in LOCATORS:
                found, refused = locator(profile, chapter, text)
                candidates.extend(found)
                refusals.extend(refused)
    # A candidate located twice — the same fact stated in prose and printed in the table — is
    # one fact, and the first sighting wins so the record is stable across runs.
    unique: dict[tuple[str, str, str], FactCandidate] = {}
    duplicates = 0
    for candidate in candidates:
        key = (candidate.source_key, candidate.subject.casefold(), candidate.value)
        if key in unique:
            duplicates += 1
            continue
        unique[key] = candidate
    return tuple(unique.values()), tuple(refusals)


# ---------------------------------------------------------------------------
# The coverage record — the W3-F1 pricing W0 owed and did not pay
# ---------------------------------------------------------------------------


def coverage() -> dict[str, Any]:
    candidates, refusals = locate_all()
    by_chapter: dict[str, int] = {}
    by_locator: dict[str, int] = {}
    for candidate in candidates:
        chapter_key = f"{candidate.source_key}-ch{candidate.chapter}"
        by_chapter[chapter_key] = by_chapter.get(chapter_key, 0) + 1
        by_locator[candidate.locator] = by_locator.get(candidate.locator, 0) + 1
    reasons: dict[str, int] = {}
    for refusal in refusals:
        reasons[refusal.reason] = reasons.get(refusal.reason, 0) + 1
    return {
        "schema_version": 1,
        "items": ["S22D-100"],
        "why_this_record_exists": (
            "22C W3-F1 is a standing rule in this sprint's §0: a verification floor's coverage "
            "is priced before the campaign, not after. W0 froze the twelve-case holdout "
            "without sampling the cleared sources against it, which is that rule broken by the "
            "wave that carries it. This is the pricing, published before acquisition runs"
        ),
        "the_holdout_is_not_re_cut": (
            "re-cutting an instrument after seeing which facts a source happens to hold is "
            "choosing the questions to fit the answers, and measured_values: 0 does not make "
            "that honest — the selection would still be made against the data. The holdout "
            "stays exactly as frozen and is read once at the end of W1"
        ),
        "sources_sampled": [profile.key for profile in PROFILES],
        "chapters_sampled": [
            f"{profile.key}-ch{chapter.number}"
            for profile in PROFILES
            for chapter in profile.chapters
        ],
        "chapters_chosen_by": "S22C-020, unchanged — W1 needs no new rights decision",
        "locators": [locator.__name__ for locator in LOCATORS],
        "candidates_located": len(candidates),
        "candidates_by_chapter": by_chapter,
        "candidates_by_locator": by_locator,
        "candidates": [candidate.as_json() for candidate in candidates],
        "subjects_located": sorted({candidate.subject for candidate in candidates}),
        "refusals": len(refusals),
        "refusals_by_reason": reasons,
        "refusal_examples": [refusal.as_json() for refusal in refusals[:10]],
        "what_a_refusal_means_here": (
            "pdftotext renders 6.02214076 x 10^23 as '6.02214076 1023' — the multiplication "
            "sign and the superscript are gone and what is left reads as two numbers. This "
            "module refuses a numeral it cannot read unambiguously rather than repairing it "
            "(22C W3-D1), so the 'maths is an image' wall arrives as a counted refusal instead "
            "of a wrong retained fact"
        ),
        "why_the_table_header_is_load_bearing": (
            "chemistry chapter 4 is full of lines shaped exactly like an element-mass row — "
            "'C' then '1', 'H' then '4' — and they are stoichiometric subscripts. A locator "
            "keyed on the row shape alone retains 'the atomic mass of C is 1', and every "
            "verifier downstream agrees, because nothing after the locator knows what the "
            "number was supposed to mean"
        ),
    }


# ---------------------------------------------------------------------------
# S22D-101. The declarative-fact acquisition path
# ---------------------------------------------------------------------------

#: The one predicate a declarative fact needs, alongside 22C's `domain.worked_example`. Same
#: composed-registry move as 22C W0-F2: the released registry is host-owned and frozen, and
#: `PredicateRegistry` is publicly constructible, so acquired facts and released claims live
#: under one vocabulary rather than two. `registry_snapshot_hash` on a fact extraction is
#: therefore not the released snapshot hash, and it cannot be.
DECLARATIVE_PREDICATE_ID = "domain.declarative_fact"
DECLARATIVE_SUBJECT_TYPE = "domain_entity"

#: §1.5's ladder, as this driver decides it. The statuses are W0's, frozen before any fact was
#: admitted; nothing here may add a rung or move a boundary.
LADDER_CORROBORATED = "corroborated"
LADDER_GROUNDED = "grounded"
LADDER_REFUSED = "refused"

REFUSAL_EXCERPT_NOT_IN_REGISTERED_BYTES = "excerpt_absent_from_the_normalized_artifact"
REFUSAL_PROMOTION_GATE = "released_promotion_gate_refused"


def corroborate(candidate: FactCandidate) -> dict[str, Any]:
    """**The kernel as consistency oracle, not as a recomputation.** §1.5.

    A declarative fact cannot be recomputed — there is nothing to derive an atomic mass
    *from*. What can be done is to ask the registered kernel to derive a *consequence* of the
    fact and compare that against the consequence the source prints beside it. For an element
    mass the consequence is the molar mass of one mole of that element, which is exactly what
    `chemistry.molar-conversion` computes, and the table's own g/mol column is the oracle.

    The comparison is exact, over `Fraction`, and never within a tolerance — 22C W1-F3, and
    22C W3-F2 is the reason it matters: the books round, so a fact that fails to corroborate
    has usually met a rounded printed value rather than a wrong retained one. The ladder says
    `grounded` in that case, which is a weaker status and not a rejection.
    """
    if candidate.consequence_value is None:
        return {
            "attempted": False,
            "reason": "the source prints no kernel-checkable consequence beside this fact",
        }
    from fractions import Fraction

    from cognitive_os.domain.domains import ResourceBudget
    from cognitive_os.domains.chemistry import solve_molar_conversion

    try:
        solution = solve_molar_conversion(
            {
                "formula": candidate.subject,
                "atomic_masses": {candidate.subject: candidate.value},
                "mass": {"magnitude": candidate.consequence_value, "unit": "g"},
                "molar_mass_unit": candidate.consequence_unit,
            },
            ResourceBudget(),
        )
    except Exception as error:  # a kernel refusal is an outcome, not a crash
        return {
            "attempted": True,
            "corroborated": False,
            "kernel": "chemistry.molar-conversion",
            "kernel_refused": str(error)[:200],
        }
    # **One mole, exactly.** The printed molar mass in grams is by definition one mole of the
    # element whose atomic mass was retained, so the kernel fed the retained mass must answer
    # exactly 1 mol. Anything else means the source's two columns and the retained fact do not
    # agree, and the ladder puts the fact on the weaker rung.
    derived = solution.candidate.exact_value
    try:
        exact = Fraction(str(derived)) == Fraction(1)
    except (ValueError, ZeroDivisionError, TypeError):
        exact = False
    return {
        "attempted": True,
        "corroborated": exact,
        "kernel": "chemistry.molar-conversion",
        "printed_consequence": f"{candidate.consequence_value} {candidate.consequence_unit}",
        "kernel_answer": f"{derived} {solution.candidate.units}",
        "expected_answer": "1 mol",
        "compared": "exactly, over Fraction, never within a tolerance (22C W1-F3)",
    }


def _cleared_rights(source_key: str) -> Any:
    """22C's clearance, rebuilt through the released contract from the sealed record.

    W1 needs no new rights decision — the plan says so and this is what that means
    mechanically: the operator's determination is read back out of S22C-020 and carried into
    the factory, never re-made here.
    """
    from cognitive_os.domain.campaigns import CampaignSourceRights, RightsClearanceStatus
    from cognitive_os.domain.corpus import CorpusUsageRight

    record = json.loads((EVIDENCE / "sprint-22c-source-rights.json").read_text(encoding="utf-8"))
    entry = next(item for item in record["sources"] if item["key"] == source_key)
    return CampaignSourceRights(
        status=RightsClearanceStatus.CLEARED,
        source_content_hash=entry["source_content_hash"],
        edition=entry["edition"],
        author=entry["author"],
        location=entry["location"],
        license_identifier=entry["license_identifier"],
        permitted_uses=tuple(CorpusUsageRight(value) for value in sorted(entry["permitted_uses"])),
        cleared_by=record["cleared_by"],
        cleared_at=W1_TIME,
        evidence_hash=entry["evidence_hash"],
        notes=entry["notes"],
    )


def build_fact_predicate_registry() -> Any:
    """The released vocabulary, plus 22C's worked example and this wave's declarative fact."""
    from campaign_22c import CAMPAIGN_PREDICATE_ID, CAMPAIGN_SUBJECT_TYPE

    from cognitive_os.domain.memory import MemorySensitivity
    from cognitive_os.domain.semantic_memory import SemanticLiteralKind
    from cognitive_os.semantic_memory.predicates import (
        Cardinality,
        PredicateDescriptor,
        PredicateRegistry,
        build_default_predicate_registry,
    )

    registry = PredicateRegistry()
    for descriptor in build_default_predicate_registry().list_all():
        registry.register(descriptor)
    registry.register(
        PredicateDescriptor(
            predicate_id=CAMPAIGN_PREDICATE_ID,
            version="1",
            display_name="Domain worked example",
            description=(
                "A worked example a domain's deterministic kernel can recompute, acquired "
                "from a rights-cleared source."
            ),
            allowed_subject_types=(CAMPAIGN_SUBJECT_TYPE,),
            allowed_object_types=(SemanticLiteralKind.STRING,),
            cardinality=Cardinality.FUNCTIONAL,
            temporal_behavior="bitemporal",
            default_sensitivity=MemorySensitivity.INTERNAL,
            rendering_label=CAMPAIGN_PREDICATE_ID,
            contradiction_rule="functional_overlap",
        )
    )
    registry.register(
        PredicateDescriptor(
            predicate_id=DECLARATIVE_PREDICATE_ID,
            version="1",
            display_name="Declarative fact",
            description=(
                "A value a rights-cleared source states about a named entity, which no "
                "kernel can recompute and which a kernel-checkable consequence may "
                "corroborate."
            ),
            allowed_subject_types=(DECLARATIVE_SUBJECT_TYPE,),
            # A value with a unit is a QUANTITY, not a DECIMAL: the released contract admits
            # a unit on quantity literals alone, which is the vocabulary saying that '12.01'
            # and '12.01 amu' are different facts.
            allowed_object_types=(SemanticLiteralKind.QUANTITY,),
            # Functional, and this is the whole reason a fact store is not a search index:
            # two different atomic masses for one element over overlapping validity is a
            # contradiction, and the released functional detector is what says so.
            cardinality=Cardinality.FUNCTIONAL,
            temporal_behavior="bitemporal",
            default_sensitivity=MemorySensitivity.INTERNAL,
            rendering_label=DECLARATIVE_PREDICATE_ID,
            contradiction_rule="functional_overlap",
        )
    )
    registry.freeze()
    return registry


def _extraction_decision(
    candidate_id: str, outcome: Any, proposal_hash: str, reasons: tuple[str, ...]
) -> dict[str, Any]:
    """**The missing seam, recorded.** `ExtractionDecisionOutcome` had no implementation.

    §1.2 named it as the one genuinely missing step, and this is what it is for: every
    located candidate leaves a decision behind, with reason codes, whether it was retained or
    not. Without it the 53-of-59 wall 22C measured is an *absence* — a fact that is not in the
    store looks exactly like a fact nobody looked for.
    """
    from uuid import NAMESPACE_URL, uuid5

    from cognitive_os.domain.semantic_memory import (
        ExtractionDecision,
        SemanticActor,
        SemanticActorType,
    )

    decision = ExtractionDecision(
        extraction_id=uuid5(NAMESPACE_URL, f"cognitive-os:sprint-22d:{candidate_id}"),
        outcome=outcome,
        proposal_hash=proposal_hash,
        reason_codes=reasons,
        decided_at=W1_TIME,
        decided_by=SemanticActor(
            actor_type=SemanticActorType.APPROVED_INTERNAL_SERVICE,
            actor_id="sprint-22d-declarative-facts",
        ),
    )
    return decision.model_dump(mode="json")


def build_fact_composition() -> Any:
    """22C's composition, with the declarative-fact predicate in its registry.

    Everything else is the released service graph 22C already drove: the same Corpus Factory,
    the same `SemanticMemoryService`, the same `TrustedSourceResolver`. W1 adds a predicate and
    a decision record, not a pipeline.
    """
    from campaign_22c import Composition

    from cognitive_os.application.services.memory_service import MemoryService
    from cognitive_os.config.corpus_config import CorpusConfiguration
    from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
    from cognitive_os.corpus.factory import CorpusFactory
    from cognitive_os.corpus.fixtures import FixtureArtifactStore
    from cognitive_os.corpus.repository import InMemoryCorpusRepository
    from cognitive_os.domain.memory import (
        MemoryScopeType,
        MemorySensitivity,
        MemoryType,
        MemoryWritePolicy,
    )
    from cognitive_os.events.memory_event_service import MemoryEventService
    from cognitive_os.events.memory_store import MemoryEventStore
    from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
    from cognitive_os.memory.repository import InMemoryMemoryRepository
    from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
    from cognitive_os.semantic_memory.repository import InMemorySemanticMemoryRepository
    from cognitive_os.semantic_memory.service import SemanticMemoryService

    events = MemoryEventStore()
    artifacts = FixtureArtifactStore()
    memory_repository = InMemoryMemoryRepository()
    semantic_repository = InMemorySemanticMemoryRepository()
    predicates = build_fact_predicate_registry()
    semantic_events = SemanticMemoryEventService(events)
    source_resolver = TrustedSourceResolver(memory_repository, artifacts=artifacts)
    return Composition(
        events=events,
        tool_events=events,
        corpus=CorpusFactory(InMemoryCorpusRepository(), artifacts, CorpusConfiguration()),
        artifacts=artifacts,
        memory=MemoryService(
            memory_repository,
            MemoryWritePolicy(
                allowed_types=frozenset(MemoryType),
                allowed_scopes=frozenset(MemoryScopeType),
                maximum_sensitivity=MemorySensitivity.INTERNAL,
            ),
            event_service=MemoryEventService(events),
        ),
        memory_repository=memory_repository,
        semantic=SemanticMemoryService(
            semantic_repository,
            predicates,
            SemanticMemoryConfiguration(),
            event_service=semantic_events,
            source_resolver=source_resolver,
        ),
        semantic_repository=semantic_repository,
        source_resolver=source_resolver,
        semantic_events=semantic_events,
        predicates=predicates,
    )


async def _register_chapters(composition: Any) -> dict[str, dict[str, Any]]:
    """Every cleared chapter through the released Corpus Factory, rights first."""
    from uuid import NAMESPACE_URL, uuid5

    from campaign_22c import operator_clearance, rights_gate

    from cognitive_os.config.corpus_config import CorpusConfiguration
    from cognitive_os.corpus.sources import SourceMaterial, _build_source
    from cognitive_os.domain.corpus import CorpusFactoryRequest, CorpusSourceType
    from cognitive_os.domain.memory import MemorySensitivity

    registered: dict[str, dict[str, Any]] = {}
    for profile in PROFILES:
        rights = _cleared_rights(profile.key)
        # Nothing reads a byte before the gate, and the gate is the operator's decision.
        rights_gate(rights, rights.source_content_hash)
        materials = [
            SourceMaterial(
                f"{profile.key}-ch{chapter.number}.txt",
                chapter_text(profile, chapter).encode("utf-8"),
                "text/plain",
                "utf-8",
            )
            for chapter in profile.chapters
        ]
        source = _build_source(
            CorpusSourceType.DOCUMENT,
            f"openstax:{profile.key}",
            "w1",
            materials,
            CorpusConfiguration(),
        )
        request = CorpusFactoryRequest(
            request_id=uuid5(NAMESPACE_URL, f"cognitive-os:sprint-22d:corpus:{profile.key}"),
            source_type=CorpusSourceType.DOCUMENT,
            source_identity=source.source_identity,
            source_revision=source.source_revision,
            scope="project:cognitive-os",
            sensitivity=MemorySensitivity.INTERNAL,
            license_identifiers=(rights.license_identifier,),
            license_clearances=(operator_clearance(rights, rights.source_content_hash),),
            usage_rights={right: True for right in rights.permitted_uses},
            created_at=W1_TIME,
            created_by="sprint-22d-declarative-facts",
        )
        result = await composition.corpus.ingest(request, source)
        by_hash = {item.canonical_content_hash: item for item in result.items}
        for chapter in profile.chapters:
            name = f"{profile.key}-ch{chapter.number}.txt"
            normalized = next(
                content
                for content in result.normalized
                if any(entry.relative_path == name for entry in content.source_file_refs)
            )
            item = by_hash[normalized.canonical_content_hash]
            registered[f"{profile.key}-ch{chapter.number}"] = {
                "corpus_item_id": str(item.corpus_item_id),
                "status": item.current_status.value,
                "artifact_id": str(item.normalized_content_artifact.artifact_id),
                "artifact_hash": item.normalized_content_artifact.content_hash,
                "license_identifier": rights.license_identifier,
            }
    return registered


async def acquire(composition: Any) -> dict[str, Any]:
    """The declarative-fact path, end to end, over the already-cleared chapters.

    One candidate at a time: the located excerpt is found in the *registered* bytes, a
    grounding span is built over that range, an observation and a claim are proposed, the
    released extraction service commits them, the released promotion gate runs the twelve
    verifiers, and the kernel is asked to corroborate. Every candidate leaves an
    `ExtractionDecision` behind whether it was retained or not.
    """
    from uuid import NAMESPACE_URL, uuid5

    from campaign_22c import ACTOR

    from cognitive_os.application.services.verification_service import VerificationService
    from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity
    from cognitive_os.domain.semantic_memory import (
        BeliefStatus,
        ClaimPromotionOutcome,
        ClaimProposal,
        ClaimRevision,
        ClaimRevisionReference,
        ClaimTemporalInterval,
        ExtractionBudget,
        ExtractionDecisionOutcome,
        GroundedSourceSpan,
        GroundingMode,
        ObservationProposal,
        SemanticEntityRef,
        SemanticExtractionProposal,
        SemanticLiteral,
        SemanticLiteralKind,
        SemanticSourceRef,
        SemanticSourceType,
        claim_revision_hash,
        semantic_hash,
    )
    from cognitive_os.events.verifier_event_service import VerifierEventService
    from cognitive_os.semantic_memory.beliefs import aggregate_confidence
    from cognitive_os.semantic_memory.compilation import SemanticExtractionService
    from cognitive_os.semantic_memory.promotion import SemanticPromotionGate
    from cognitive_os.verification.factory import build_builtin_registry

    def identifier(label: str) -> Any:
        return uuid5(NAMESPACE_URL, f"cognitive-os:sprint-22d:{label}")

    candidates, refusals = locate_all()
    registered = await _register_chapters(composition)
    extraction = SemanticExtractionService(
        composition.semantic, composition.predicates, events=composition.semantic_events
    )
    verifier_registry = build_builtin_registry()
    gate_ids = iter(identifier(f"promotion-gate:{index}") for index in range(1000))
    gate = SemanticPromotionGate(
        composition.semantic,
        VerificationService(verifier_registry, VerifierEventService(composition.events)),
        verifier_registry,
        composition.semantic_events,
        clock=lambda: W1_TIME,
        id_factory=lambda: next(gate_ids),
    )

    decisions: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []

    # Every locator refusal is a decision too. A fact that is not in the store has to be
    # distinguishable from a fact nobody looked for, and this is the difference.
    for index, refusal in enumerate(refusals):
        decisions.append(
            {
                "candidate_id": f"refused-{refusal.source_key}-ch{refusal.chapter}-{index}",
                "decision": _extraction_decision(
                    f"refused-{refusal.source_key}-ch{refusal.chapter}-{index}",
                    ExtractionDecisionOutcome.REJECTED,
                    _sha256(canonical(refusal.as_json())),
                    (refusal.reason,),
                ),
                "ladder_status": LADDER_REFUSED,
                "locator": refusal.locator,
            }
        )

    for candidate in candidates:
        chapter_key = f"{candidate.source_key}-ch{candidate.chapter}"
        entry = registered[chapter_key]
        data = await composition.artifacts.get_bytes(__import__("uuid").UUID(entry["artifact_id"]))
        needle = candidate.excerpt.encode("utf-8")
        start = data.find(needle)
        proposal_hash = _sha256(canonical(candidate.as_json()))
        if start < 0:
            # **Normalization moved the bytes the citation names.** Refused by name rather
            # than re-grounded onto the whole artifact, because a span that silently widens
            # to the entire chapter is a citation that stopped meaning anything.
            decisions.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "decision": _extraction_decision(
                        candidate.candidate_id,
                        ExtractionDecisionOutcome.REJECTED,
                        proposal_hash,
                        (REFUSAL_EXCERPT_NOT_IN_REGISTERED_BYTES,),
                    ),
                    "ladder_status": LADDER_REFUSED,
                    "locator": candidate.locator,
                }
            )
            continue
        end = start + len(needle)
        span = GroundedSourceSpan(
            source=SemanticSourceRef(
                source_type=SemanticSourceType.ARTIFACT,
                source_id=__import__("uuid").UUID(entry["artifact_id"]),
                content_hash=entry["artifact_hash"],
            ),
            mode=GroundingMode.ARTIFACT_BYTES,
            start=start,
            end=end,
            excerpt_hash=_sha256(data[start:end]),
        )
        root = f"fact:{candidate.candidate_id}"
        observation_id = identifier(f"{root}:observation")
        proposal = SemanticExtractionProposal(
            extraction_id=identifier(root),
            registry_snapshot_hash=composition.predicates.snapshot_hash(),
            observations=(
                ObservationProposal(
                    proposal_id=observation_id,
                    content=(
                        f"{candidate.source_key} chapter {candidate.chapter} states that the "
                        f"{candidate.quantity} of {candidate.subject} is "
                        f"{candidate.value} {candidate.unit}."
                    ),
                    source_spans=(span,),
                ),
            ),
            claims=(
                ClaimProposal(
                    proposal_id=identifier(f"{root}:claim"),
                    subject=SemanticEntityRef(
                        entity_id=_entity_id(candidate.quantity, candidate.subject),
                        entity_type=DECLARATIVE_SUBJECT_TYPE,
                        display_label=candidate.subject,
                    ),
                    predicate_id=DECLARATIVE_PREDICATE_ID,
                    object=SemanticLiteral(
                        literal_kind=SemanticLiteralKind.QUANTITY,
                        value=candidate.value,
                        unit=candidate.unit,
                    ),
                    valid_interval=ClaimTemporalInterval(valid_from=W1_TIME),
                    observation_proposal_ids=(observation_id,),
                ),
            ),
            budget=ExtractionBudget(
                maximum_observations=1,
                maximum_claims=1,
                maximum_evidence_links=1,
                maximum_relations=0,
            ),
        )
        committed = await extraction.commit(
            proposal,
            scope=MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id="science.chemistry"),
            sensitivity=MemorySensitivity.INTERNAL,
            actor=ACTOR,
            recorded_at=W1_TIME,
        )
        claim_id = committed.claims[0].claim_id
        proposed = await composition.semantic_repository.get_claim_revision(claim_id, 1)
        first_evidence = await composition.semantic_repository.list_evidence(claim_id, revision=1)
        evidence = tuple(
            link.model_copy(
                update={
                    "evidence_id": identifier(f"evidence:{claim_id}:2"),
                    "claim": ClaimRevisionReference(claim_id=claim_id, revision=2),
                    "created_by": ACTOR,
                }
            )
            for link in first_evidence
        )
        confidence = aggregate_confidence(
            extraction=1, source=1, grounding=1, evidence=1, verification=1, consistency=1
        )
        reason = "registered semantic verifier bundle passed on an acquired declarative fact"
        successor = ClaimRevision(
            claim_id=claim_id,
            revision=2,
            previous_revision=1,
            object=proposed.object,
            statement=proposed.statement,
            belief_status=BeliefStatus.SUPPORTED,
            confidence=confidence,
            valid_interval=proposed.valid_interval,
            reason=reason,
            recorded_at=W1_TIME,
            created_by=ACTOR,
            evidence_snapshot_hash=semantic_hash(
                [link.model_dump(mode="json") for link in evidence]
            ),
            content_hash=claim_revision_hash(
                claim_id=claim_id,
                revision=2,
                object_value=proposed.object,
                statement=proposed.statement,
                belief_status=BeliefStatus.SUPPORTED,
                confidence=confidence,
                valid_interval=proposed.valid_interval,
                reason=reason,
                evidence_snapshot_hash=semantic_hash(
                    [link.model_dump(mode="json") for link in evidence]
                ),
            ),
        )
        decision = await gate.decide(
            successor, evidence, task_run_id=identifier(f"{root}:task-run"), actor=ACTOR
        )
        # `ClaimPromotionOutcome.SUPPORTED` is what a passed gate says — there is no
        # "promoted" member, and comparing against one refuses every fact the gate accepted
        # while the record cheerfully reports the gate's own verdict beside the rejection.
        promoted = decision.outcome is ClaimPromotionOutcome.SUPPORTED
        if not promoted:
            decisions.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "decision": _extraction_decision(
                        candidate.candidate_id,
                        ExtractionDecisionOutcome.REQUIRES_REVIEW,
                        proposal_hash,
                        (REFUSAL_PROMOTION_GATE, decision.outcome.value),
                    ),
                    "ladder_status": LADDER_REFUSED,
                    "locator": candidate.locator,
                }
            )
            continue
        oracle = corroborate(candidate)
        status = LADDER_CORROBORATED if oracle.get("corroborated") else LADDER_GROUNDED
        decisions.append(
            {
                "candidate_id": candidate.candidate_id,
                "decision": _extraction_decision(
                    candidate.candidate_id,
                    ExtractionDecisionOutcome.ACCEPTED,
                    proposal_hash,
                    (f"promoted_to_{status}",),
                ),
                "ladder_status": status,
                "locator": candidate.locator,
            }
        )
        retained.append(
            {
                "candidate_id": candidate.candidate_id,
                "claim_id": str(claim_id),
                "subject": candidate.subject,
                "quantity": candidate.quantity,
                "value": candidate.value,
                "unit": candidate.unit,
                "ladder_status": status,
                "corroboration": oracle,
                "span": {"artifact_id": entry["artifact_id"], "start": start, "end": end},
                "source_key": candidate.source_key,
                "chapter": candidate.chapter,
                "license_identifier": entry["license_identifier"],
            }
        )

    by_status: dict[str, int] = {}
    for item in decisions:
        by_status[item["ladder_status"]] = by_status.get(item["ladder_status"], 0) + 1
    return {
        "candidates_located": len(candidates),
        "locator_refusals": len(refusals),
        "decisions_recorded": len(decisions),
        "every_candidate_left_a_decision": len(decisions) == len(candidates) + len(refusals),
        "retained": retained,
        "retained_count": len(retained),
        "by_ladder_status": by_status,
        "chapters_registered": registered,
        "decisions": decisions,
    }


# ---------------------------------------------------------------------------
# S22D-102. The holdout, read once
# ---------------------------------------------------------------------------

#: **W1-F3, and it is a property of acquisition rather than of this driver.** The acquired
#: layer is keyed by the notation the *source* uses — `Cl`, `Na`, `g` — and a question is
#: phrased in the notation the *asker* uses: "chlorine", "sodium", "standard gravitational
#: field strength". Without a resolution step every case misses for a plumbing reason and the
#: record reads as a coverage failure, which would be the wrong diagnosis entirely.
#:
#: The table is the first thirty elements plus the two named constants — general, written once,
#: and deliberately not the set of names this holdout happens to ask for. An alias table cut to
#: the questions would be the questions answering themselves.
ELEMENT_ALIASES = {
    "hydrogen": "H",
    "helium": "He",
    "lithium": "Li",
    "beryllium": "Be",
    "boron": "B",
    "carbon": "C",
    "nitrogen": "N",
    "oxygen": "O",
    "fluorine": "F",
    "neon": "Ne",
    "sodium": "Na",
    "magnesium": "Mg",
    "aluminium": "Al",
    "aluminum": "Al",
    "silicon": "Si",
    "phosphorus": "P",
    "sulfur": "S",
    "sulphur": "S",
    "chlorine": "Cl",
    "argon": "Ar",
    "potassium": "K",
    "calcium": "Ca",
    "scandium": "Sc",
    "titanium": "Ti",
    "vanadium": "V",
    "chromium": "Cr",
    "manganese": "Mn",
    "iron": "Fe",
    "cobalt": "Co",
    "nickel": "Ni",
    "copper": "Cu",
    "zinc": "Zn",
}

CONSTANT_ALIASES = {
    "standard gravitational field strength": "g",
    # **W1-F3, paid rather than re-observed.** W1 named this debt and W2 is where it comes
    # due: the layer is keyed as the source writes (`g`), was aliased as the holdout asks
    # ("field strength"), and the microbenchmark asks a third way. The quantity is the same
    # one — the source states `g = 9.80 m/s2` and the task wants m/s² — so a miss here would
    # be a plumbing failure reported as a coverage failure, which is the wrong diagnosis and
    # the exact sentence W1-F3 was written to prevent. Added before any arm ran, and the
    # movement it causes (three servable tasks to four) is stated in S22D-200 rather than
    # left for a reader to notice.
    "standard acceleration due to gravity": "g",
    "acceleration due to gravity": "g",
    "faraday constant": "F",
}

REFUSAL_FACT_NOT_IN_LAYER = "fact_not_in_acquired_layer"


def _layer_index(retained: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The acquired layer as a lookup, keyed by the subject the source wrote."""
    return {str(item["subject"]).casefold(): item for item in retained}


def _resolve(name: str, index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = name.casefold().strip()
    for candidate in (key, ELEMENT_ALIASES.get(key, ""), CONSTANT_ALIASES.get(key, "")):
        if candidate and candidate.casefold() in index:
            return index[candidate.casefold()]
    return None


async def read_holdout(retained: list[dict[str, Any]]) -> dict[str, Any]:
    """The twelve cases, both arms, read exactly once. §2.1's `measured_values` becomes 12.

    Arm A is the acquired layer as 22C left it: worked examples only, no declarative facts at
    all, so every case is refused by name. Arm B is the layer after this wave. Neither arm is a
    different model or a different prompt — the *only* difference is what the store holds, which
    is the one thing this holdout was frozen to measure.

    A case succeeds under the frozen definition: the layer supplies every fact the derivation
    needs at a retrievable ladder status, the answer is derived from the value the layer
    actually holds, and the case's own registered verifier decides it. Deriving from the layer
    rather than comparing against the value the case withheld is what keeps this from being
    circular — the expected answer was computed *from* that withheld value.
    """
    from benchmark_22d import ArmOutcome, verify_answer
    from holdout_22d import DERIVATIONS, HOLDOUT_CASES, LADDER_RETRIEVABLE

    index_b = _layer_index(retained)
    arms: dict[str, Any] = {}
    for arm, index in (("arm_a", {}), ("arm_b", index_b)):
        cases: list[dict[str, Any]] = []
        for case in HOLDOUT_CASES:
            case_id = str(case["case_id"])
            kind, operand, required = DERIVATIONS[case_id]
            resolved: list[tuple[str, dict[str, Any], int]] = []
            missing: list[str] = []
            for name, count in required:
                fact = _resolve(name, index)
                if fact is None or fact["ladder_status"] not in LADDER_RETRIEVABLE:
                    missing.append(name)
                else:
                    resolved.append((name, fact, count))
            if missing:
                cases.append(
                    {
                        "case_id": case_id,
                        "answered": False,
                        "verified": False,
                        "refusal_reason": REFUSAL_FACT_NOT_IN_LAYER,
                        "facts_missing": missing,
                    }
                )
                continue
            values = {name: float(fact["value"]) for name, fact, _ in resolved}
            counts = {name: count for name, _, count in resolved}
            match kind:
                case "moles":
                    answer = operand / next(iter(values.values()))
                case "mass_of":
                    answer = operand * next(iter(values.values()))
                case "molar_mass":
                    answer = sum(values[name] * counts[name] for name in values)
                case "weight":
                    answer = operand * next(iter(values.values()))
                case _:
                    answer = next(iter(values.values()))
            verified, undecidable = await verify_answer(
                case,
                ArmOutcome(
                    task_id=case_id, arm="local_model", answer=f"{answer:.6g}", abstained=False
                ),
            )
            cases.append(
                {
                    "case_id": case_id,
                    "answered": True,
                    "verified": verified,
                    "undecidable": undecidable,
                    "answer": f"{answer:.6g}",
                    "facts_used": [
                        {
                            "asked_as": name,
                            "found_as": fact["subject"],
                            "value": fact["value"],
                            "ladder_status": fact["ladder_status"],
                        }
                        for name, fact, _ in resolved
                    ],
                }
            )
        arms[arm] = {
            "cases": cases,
            "answered": sum(1 for item in cases if item["answered"]),
            "verified": sum(1 for item in cases if item["verified"]),
        }
    return {
        "holdout_id": "sprint-22d-declarative-fact-holdout",
        "case_count": len(HOLDOUT_CASES),
        "read_once": True,
        "measured_values": len(HOLDOUT_CASES),
        "arms": arms,
        "arm_a_verified": arms["arm_a"]["verified"],
        "arm_b_verified": arms["arm_b"]["verified"],
        "improvement": arms["arm_b"]["verified"] - arms["arm_a"]["verified"],
        "arms_differ": arms["arm_a"]["verified"] != arms["arm_b"]["verified"],
        "entity_alias_step_was_required": True,
        "why_an_alias_step": (
            "the acquired layer is keyed by the notation the source writes — Cl, Na, g — and a "
            "question is phrased in the asker's — chlorine, sodium, standard gravitational "
            "field strength. Without resolution every case misses for a plumbing reason and "
            "the record reads as a coverage failure, which is the wrong diagnosis (W1-F3)"
        ),
    }


def build_postgres_composition(engine: Any, root: Path) -> Any:
    """The same path, over a provisioned store. **22C W2-F2 is why this exists.**

    The standing rule: *two implementations of one contract are tested against each other, not
    each against itself.* 22C's most dangerous find was a PostgreSQL active view that returned
    superseded and retracted claims wearing their old belief — a defect only PostgreSQL had,
    invisible to a whole suite that ran in memory. So this wave acquires twice and compares the
    two layers, rather than acquiring once and trusting whichever store it happened to use.
    """
    from campaign_22c import Composition

    from cognitive_os.application.services.memory_service import MemoryService
    from cognitive_os.config.corpus_config import CorpusConfiguration
    from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
    from cognitive_os.corpus.factory import CorpusFactory
    from cognitive_os.domain.memory import (
        MemoryScopeType,
        MemorySensitivity,
        MemoryType,
        MemoryWritePolicy,
    )
    from cognitive_os.events.catalog import build_default_event_catalog
    from cognitive_os.events.memory_event_service import MemoryEventService
    from cognitive_os.events.memory_store import MemoryEventStore
    from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
    from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
    from cognitive_os.infrastructure.artifacts.service import ArtifactService
    from cognitive_os.infrastructure.corpus.postgres.repository import PostgresCorpusRepository
    from cognitive_os.infrastructure.memory.postgres.repository import PostgresMemoryRepository
    from cognitive_os.infrastructure.postgres.artifact_repository import (
        PostgresArtifactRepository,
    )
    from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore
    from cognitive_os.infrastructure.semantic_memory.postgres.repository import (
        PostgresSemanticMemoryRepository,
    )
    from cognitive_os.semantic_memory.grounding import TrustedSourceResolver
    from cognitive_os.semantic_memory.service import SemanticMemoryService

    artifacts = ArtifactService(
        ContentAddressedFilesystem(root), PostgresArtifactRepository(engine)
    )
    events = PostgresEventStore(engine, build_default_event_catalog())
    memory_repository = PostgresMemoryRepository(engine)
    semantic_repository = PostgresSemanticMemoryRepository(engine)
    predicates = build_fact_predicate_registry()
    semantic_events = SemanticMemoryEventService(events)
    source_resolver = TrustedSourceResolver(memory_repository, artifacts=artifacts)
    return Composition(
        events=events,
        # 22C W2-F3, carried by name: the Tool Plane's events can only reach an in-memory
        # store. Nothing in W1 depends on them, and the accounting exit that will is W2's.
        tool_events=MemoryEventStore(),
        corpus=CorpusFactory(PostgresCorpusRepository(engine), artifacts, CorpusConfiguration()),
        artifacts=artifacts,
        memory=MemoryService(
            memory_repository,
            MemoryWritePolicy(
                allowed_types=frozenset(MemoryType),
                allowed_scopes=frozenset(MemoryScopeType),
                maximum_sensitivity=MemorySensitivity.INTERNAL,
            ),
            event_service=MemoryEventService(events),
        ),
        memory_repository=memory_repository,
        semantic=SemanticMemoryService(
            semantic_repository,
            predicates,
            SemanticMemoryConfiguration(),
            event_service=semantic_events,
            source_resolver=source_resolver,
        ),
        semantic_repository=semantic_repository,
        source_resolver=source_resolver,
        semantic_events=semantic_events,
        predicates=predicates,
    )


def _layer_fingerprint(result: dict[str, Any]) -> list[dict[str, Any]]:
    """What the two stores must agree on. Claim ids differ; the acquired knowledge does not."""
    return sorted(
        (
            {
                "candidate_id": item["candidate_id"],
                "subject": item["subject"],
                "quantity": item["quantity"],
                "value": item["value"],
                "unit": item["unit"],
                "ladder_status": item["ladder_status"],
                "span": item["span"]["start"],
            }
            for item in result["retained"]
        ),
        key=lambda item: str(item["candidate_id"]),
    )


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    record["recorded_at"] = W1_TIME.isoformat().replace("+00:00", "Z")
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


ACQUISITION_OUTPUT = EVIDENCE / "sprint-22d-w1-acquisition.json"
HOLDOUT_READ_OUTPUT = EVIDENCE / "sprint-22d-w1-holdout-read.json"

#: What 22C's acquired-knowledge store held when this wave started, from its sealed record.
#: The plan's W1 row asks for the measurement "against the 1 artifact it holds now", so the
#: number is carried rather than recomputed — 22C's store is closed evidence and W1 does not
#: reopen it.
LAYER_1_BEFORE = 1


async def _acquire_both() -> dict[str, Any]:
    """In memory and on the provisioned store, then compared. 22C W2-F2's standing rule."""
    import os

    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    memory_result = await acquire(build_fact_composition())
    url = os.environ.get("COGOS_DATABASE_URL")
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not url or not root:
        raise SystemExit(
            "COGOS_DATABASE_URL and COGOS_ARTIFACT_ROOT are required: source "
            ".env.s22d.local explicitly rather than exporting (22C W0-F1)"
        )
    engine = create_postgres_engine(url, pool_size=4, max_overflow=0)
    try:
        postgres_result = await acquire(build_postgres_composition(engine, Path(root)))
    finally:
        await engine.dispose()

    memory_layer = _layer_fingerprint(memory_result)
    postgres_layer = _layer_fingerprint(postgres_result)
    return {
        "memory": memory_result,
        "postgres": postgres_result,
        "parity": {
            "compared": "the acquired layer, not the claim identifiers a store assigns",
            "in_memory_retained": len(memory_layer),
            "postgres_retained": len(postgres_layer),
            "layers_identical": memory_layer == postgres_layer,
            "why": (
                "22C W2-F2 is a standing rule — two implementations of one contract are "
                "tested against each other, not each against itself. Its own worst find was "
                "a PostgreSQL active view returning superseded claims wearing their old "
                "belief, invisible to a suite that ran entirely in memory"
            ),
        },
        "store": {
            "kind": "postgresql",
            # The database name, never the URL: a credential does not belong in evidence.
            "database": url.rsplit("/", 1)[-1],
            "migration_head": "0015",
        },
    }


def _acquisition_record(both: dict[str, Any], holdout: dict[str, Any]) -> dict[str, Any]:
    result = both["postgres"]
    return {
        "schema_version": 1,
        "items": ["S22D-101", "S22D-102"],
        "layer_1_before": LAYER_1_BEFORE,
        "layer_1_after": result["retained_count"],
        "layer_1_change": result["retained_count"] - LAYER_1_BEFORE,
        "materially_filled": result["retained_count"] > LAYER_1_BEFORE,
        "candidates_located": result["candidates_located"],
        "locator_refusals": result["locator_refusals"],
        "decisions_recorded": result["decisions_recorded"],
        "every_candidate_left_a_decision": result["every_candidate_left_a_decision"],
        "by_ladder_status": result["by_ladder_status"],
        "retained": result["retained"],
        "decisions": result["decisions"],
        "parity": both["parity"],
        "store": both["store"],
        "promotion_path": (
            "every retained fact passed the twelve released semantic promotion verifiers "
            "through SemanticPromotionGate; this wave added a predicate and a decision "
            "record, not a promotion rule"
        ),
        "holdout_read": {
            "arm_a_verified": holdout["arm_a_verified"],
            "arm_b_verified": holdout["arm_b_verified"],
            "improvement": holdout["improvement"],
            "read_once": True,
        },
    }


def main() -> int:
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", action="store_true", help="price the source coverage")
    parser.add_argument("--acquire", action="store_true", help="run the declarative-fact path")
    parser.add_argument("--check", action="store_true", help="rebuild and compare")
    arguments = parser.parse_args()
    if not (arguments.coverage or arguments.acquire):
        parser.error("pass --coverage or --acquire")

    if arguments.coverage:
        record = _seal(coverage())
        if arguments.check:
            if not COVERAGE_OUTPUT.exists():
                print(f"MISSING {COVERAGE_OUTPUT}")
                return 1
            stored = json.loads(COVERAGE_OUTPUT.read_text(encoding="utf-8"))
            body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
            sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
            identical = stored == record
            print(f"seal_recomputes={sealed} rebuild_identical={identical}")
            return 0 if sealed and identical else 1

        COVERAGE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        COVERAGE_OUTPUT.write_text(
            json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "output": COVERAGE_OUTPUT.name,
                    "candidates_located": record["candidates_located"],
                    "by_locator": record["candidates_by_locator"],
                    "by_chapter": record["candidates_by_chapter"],
                    "subjects": record["subjects_located"],
                    "refusals_by_reason": record["refusals_by_reason"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 0

    # --acquire. `--check` re-runs the in-memory half only: the provisioned store holds rows
    # this wave observed and re-ingesting them is refused by the Corpus Factory by design
    # (22C's `--cycle` is not idempotent either), so the persistent half is an *observation*
    # and the in-memory half is the invariant (22C W1-F1's split).
    if arguments.check:
        memory_result = asyncio.run(acquire(build_fact_composition()))
        holdout = asyncio.run(read_holdout(memory_result["retained"]))
        for path in (ACQUISITION_OUTPUT, HOLDOUT_READ_OUTPUT):
            if not path.exists():
                print(f"MISSING {path}")
                return 1
        stored = json.loads(ACQUISITION_OUTPUT.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        layer_same = _layer_fingerprint({"retained": stored["retained"]}) == _layer_fingerprint(
            memory_result
        )
        stored_holdout = json.loads(HOLDOUT_READ_OUTPUT.read_text(encoding="utf-8"))
        holdout_same = stored_holdout["improvement"] == holdout["improvement"]
        print(
            f"seal_recomputes={sealed} layer_reproduces={layer_same} "
            f"holdout_reproduces={holdout_same}"
        )
        return 0 if sealed and layer_same and holdout_same else 1

    both = asyncio.run(_acquire_both())
    holdout = asyncio.run(read_holdout(both["postgres"]["retained"]))
    acquisition = _seal(_acquisition_record(both, holdout))
    ACQUISITION_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ACQUISITION_OUTPUT.write_text(
        json.dumps(acquisition, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    HOLDOUT_READ_OUTPUT.write_text(
        json.dumps(
            _seal({"schema_version": 1, "items": ["S22D-102"], **holdout}),
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "outputs": [ACQUISITION_OUTPUT.name, HOLDOUT_READ_OUTPUT.name],
                "layer_1_before": acquisition["layer_1_before"],
                "layer_1_after": acquisition["layer_1_after"],
                "by_ladder_status": acquisition["by_ladder_status"],
                "decisions_recorded": acquisition["decisions_recorded"],
                "layers_identical": acquisition["parity"]["layers_identical"],
                "arm_a_verified": holdout["arm_a_verified"],
                "arm_b_verified": holdout["arm_b_verified"],
                "improvement": holdout["improvement"],
                "integrity_content_hash": acquisition["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
