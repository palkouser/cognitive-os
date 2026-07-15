"""Deterministic Markdown Wiki v3 rendering."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from cognitive_os.domain.semantic_memory import (
    BeliefStatus,
    Claim,
    ClaimRevision,
    ClaimRevisionReference,
    ContradictionRevision,
    ContradictionStatus,
    EvidenceLink,
    WikiClaimReference,
    WikiPage,
    WikiPageRevision,
    WikiSectionType,
    semantic_hash,
)

from .canonicalization import canonical_value

_ESCAPED = "\\`*_{}[]<>()#+-.!|"


def escape_markdown(value: str) -> str:
    return "".join("\\" + char if char in _ESCAPED else char for char in value)


def render_wiki_revision(
    *,
    page: WikiPage,
    claims: tuple[tuple[Claim, ClaimRevision], ...],
    evidence: tuple[EvidenceLink, ...] = (),
    contradictions: tuple[ContradictionRevision, ...] = (),
    revision: int,
    rendered_at: datetime,
    valid_at: datetime | None = None,
    known_at: datetime | None = None,
    maximum_bytes: int = 262_144,
) -> WikiPageRevision:
    claim_sections = (
        ("Current Supported Claims", WikiSectionType.CURRENT_SUPPORTED, BeliefStatus.SUPPORTED),
        ("Disputed Claims", WikiSectionType.DISPUTED, BeliefStatus.DISPUTED),
        ("Superseded History", WikiSectionType.SUPERSEDED_HISTORY, BeliefStatus.SUPERSEDED),
    )
    lines = [f"# {escape_markdown(page.canonical_subject_key)}", "", "Renderer: Wiki v3"]
    if valid_at is not None or known_at is not None:
        lines.extend(("", "Historical projection: yes"))
    references: list[WikiClaimReference] = []
    ordered = sorted(
        claims, key=lambda item: (item[0].identity.predicate_id, str(item[0].identity.claim_id))
    )
    evidence_by_claim: dict[ClaimRevisionReference, list[EvidenceLink]] = {}
    for link in evidence:
        evidence_by_claim.setdefault(link.claim, []).append(link)
    open_contradictions = tuple(
        sorted(
            (item for item in contradictions if item.status is ContradictionStatus.OPEN),
            key=lambda item: str(item.contradiction_id),
        )
    )
    contradiction_claims = {reference for item in open_contradictions for reference in item.claims}
    for title, section, status in claim_sections[:2]:
        lines.extend(("", f"## {title}", ""))
        matches = [(claim, item) for claim, item in ordered if item.belief_status is status]
        if not matches:
            lines.append("_None._")
            continue
        for order, (claim, item) in enumerate(matches):
            predicate = escape_markdown(claim.identity.predicate_id)
            value = escape_markdown(canonical_value(item.object))
            claim_reference = ClaimRevisionReference(claim_id=item.claim_id, revision=item.revision)
            interval = f"[{item.valid_interval.valid_from.isoformat()}, "
            interval += (
                item.valid_interval.valid_to.isoformat() if item.valid_interval.valid_to else "open"
            )
            interval += ")"
            lines.append(
                f"- **{predicate}**: `{value}` — {item.belief_status.value}; "
                f"valid {interval}; confidence {item.confidence.overall_confidence:.3f}; "
                f"claim `{item.claim_id}` revision {item.revision}; "
                f"evidence {len(evidence_by_claim.get(claim_reference, ()))}; "
                f"contradiction {'open' if claim_reference in contradiction_claims else 'none'}"
            )
            references.append(
                WikiClaimReference(
                    claim=claim_reference,
                    section=section,
                    display_order=order,
                )
            )
    lines.extend(("", "## Open Contradictions", ""))
    if not open_contradictions:
        lines.append("_None._")
    for contradiction_revision in open_contradictions:
        exact_claims = ", ".join(
            f"`{reference.claim_id}` revision {reference.revision}"
            for reference in sorted(
                contradiction_revision.claims, key=lambda value: str(value.claim_id)
            )
        )
        lines.append(
            f"- `{contradiction_revision.contradiction_id}` revision "
            f"{contradiction_revision.revision}; severity "
            f"{contradiction_revision.severity.value}; claims {exact_claims}"
        )
    title, section, status = claim_sections[2]
    lines.extend(("", f"## {title}", ""))
    matches = [(claim, item) for claim, item in ordered if item.belief_status is status]
    if not matches:
        lines.append("_None._")
    for order, (claim, item) in enumerate(matches):
        value = escape_markdown(canonical_value(item.object))
        lines.append(
            f"- **{escape_markdown(claim.identity.predicate_id)}**: `{value}`; "
            f"claim `{item.claim_id}` revision {item.revision}"
        )
        references.append(
            WikiClaimReference(
                claim=ClaimRevisionReference(claim_id=item.claim_id, revision=item.revision),
                section=section,
                display_order=order,
            )
        )
    lines.extend(("", "## Evidence Index", ""))
    displayed = {item.claim for item in references}
    displayed_evidence = sorted(
        (item for item in evidence if item.claim in displayed),
        key=lambda item: (str(item.claim.claim_id), item.claim.revision, str(item.evidence_id)),
    )
    if not displayed_evidence:
        lines.append("_None._")
    for link in displayed_evidence:
        lines.append(
            f"- `{link.evidence_id}` supports claim `{link.claim.claim_id}` revision "
            f"{link.claim.revision} from {link.source.source_type.value} "
            f"`{link.source.source_id}` hash `{link.source.content_hash}`"
        )
    lines.extend(
        (
            "",
            "## Revision Metadata",
            "",
            f"- Page ID: `{page.page_id}`",
            "- Renderer version: 3",
            "",
        )
    )
    markdown = "\n".join(lines).rstrip()
    if len(markdown.encode()) > maximum_bytes:
        raise ValueError("rendered Wiki page exceeds the host byte limit")
    content_hash = sha256(markdown.encode()).hexdigest()
    snapshot_hash = semantic_hash([item.model_dump(mode="json") for item in references])
    return WikiPageRevision(
        page_id=page.page_id,
        revision=revision,
        previous_revision=None if revision == 1 else revision - 1,
        markdown=markdown,
        claim_refs=tuple(references),
        valid_at=valid_at,
        known_at=known_at,
        rendered_at=rendered_at,
        content_hash=content_hash,
        snapshot_hash=snapshot_hash,
    )
