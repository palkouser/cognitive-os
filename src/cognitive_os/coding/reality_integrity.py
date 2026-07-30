"""One integrity report over everything Gate C3 rests on. §S21C3-061.

The C3 evidence is spread over an Event Store, a content-addressed Artifact Store, the
Experience Compiler's tables, the Corpus Factory's, the learned-evidence plane's and the
Memory Plane's. Each has its own consistency rules and each is checked by its own tests. What
nobody was checking is whether they still agree with *each other* after a campaign — whether
an artifact a corpus item cites still has bytes, whether a group that must sit in one split
sits in one split, whether the counts add up to the numbers the sprint report published.

Two kinds of bad news, kept apart on purpose:

* a **failure** means recorded evidence is wrong — a broken authority link, missing bytes, a
  group crossing a split, a real governed run marked training-eligible;
* a **warning** means a capability is unavailable right now — the local embedding model is not
  fetched on this host, a provider is not configured.

Collapsing the two would be the expensive mistake in both directions. A missing model would
condemn a store that is perfectly intact, and — much worse — an operator who learned that this
report goes amber for ordinary reasons would stop reading it on the day it means something.

Every check is a read. This module writes nothing, anywhere.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reality_tasks import available_templates, build_manifest

FAILURE = "failure"
WARNING = "warning"


@dataclass(frozen=True, slots=True)
class IntegrityCheck:
    name: str
    ok: bool
    severity: str
    detail: str


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    checks: tuple[IntegrityCheck, ...]

    @property
    def healthy(self) -> bool:
        """Failures decide health. Warnings are reported and do not condemn the store."""
        return not any(not check.ok and check.severity == FAILURE for check in self.checks)

    @property
    def failures(self) -> tuple[IntegrityCheck, ...]:
        return tuple(c for c in self.checks if not c.ok and c.severity == FAILURE)

    @property
    def warnings(self) -> tuple[IntegrityCheck, ...]:
        return tuple(c for c in self.checks if not c.ok and c.severity == WARNING)

    def as_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "checks": [
                {
                    "name": check.name,
                    "ok": check.ok,
                    "severity": check.severity,
                    "detail": check.detail,
                }
                for check in self.checks
            ],
            "failures": [check.name for check in self.failures],
            "warnings": [check.name for check in self.warnings],
        }


def fingerprint(root: Path) -> tuple[str, int]:
    """The path-and-size fingerprint of an artifact root, and the number of files counted.

    SHA-256 of the newline-joined ``"<relative path> <size>"`` lines, sorted by path, no
    trailing newline. It deliberately reads no file content: this answers "was anything
    written here", and a store that must receive no writes is cheapest to check by its shape.
    `scripts/verify_artifact_store.sh` is the content check.
    """
    rows = sorted(
        (path.relative_to(root).as_posix(), path.stat().st_size)
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    body = "\n".join(f"{name} {size}" for name, size in rows)
    return hashlib.sha256(body.encode("utf-8")).hexdigest(), len(rows)


# ------------------------------------------------------------------ SQL checks
#
# Each entry is (name, statement, expectation). The statement returns one row of one value;
# `None` and `0` both mean "nothing wrong was found". Written as SQL rather than as Python
# over fetched rows because the question is always "does the store contain a contradiction",
# and the store is the only thing that can answer it without a second copy of the rules.

_ORPHAN_CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "every_artifact_row_has_bytes",
        """
        SELECT count(*) FROM cognitive_os.artifacts a
        LEFT JOIN cognitive_os.artifact_blobs b ON b.content_hash = a.content_hash
        WHERE b.content_hash IS NULL
        """,
        "artifact rows with no blob",
    ),
    (
        "every_artifact_names_the_event_that_produced_it",
        """
        SELECT count(*) FROM cognitive_os.artifacts a
        LEFT JOIN cognitive_os.events e ON e.event_id = a.source_event_id
        WHERE a.source_event_id IS NOT NULL AND e.event_id IS NULL
        """,
        "artifacts citing a missing event",
    ),
    (
        "every_corpus_item_source_resolves",
        """
        SELECT count(*) FROM cognitive_os.corpus_item_sources s
        LEFT JOIN cognitive_os.corpus_sources c
          ON c.source_manifest_id = s.source_manifest_id
        WHERE c.source_manifest_id IS NULL
        """,
        "corpus items citing a missing source",
    ),
    (
        "every_manifest_item_is_a_corpus_item",
        """
        SELECT count(*) FROM cognitive_os.corpus_manifest_items m
        LEFT JOIN cognitive_os.corpus_items i ON i.corpus_item_id = m.corpus_item_id
        WHERE i.corpus_item_id IS NULL
        """,
        "manifest entries with no item",
    ),
    (
        "every_experience_candidate_has_a_compilation",
        """
        SELECT count(*) FROM cognitive_os.experience_candidates c
        LEFT JOIN cognitive_os.experience_compilations p
          ON p.compilation_id = c.compilation_id
        WHERE p.compilation_id IS NULL
        """,
        "candidates with no compilation",
    ),
    (
        "every_learned_artifact_has_bytes",
        """
        SELECT count(*) FROM cognitive_os.learned_artifacts l
        LEFT JOIN cognitive_os.artifacts a ON a.artifact_id = l.artifact_id
        WHERE a.artifact_id IS NULL
        """,
        "learned lineage rows citing a missing artifact",
    ),
    (
        "every_memory_embedding_has_a_revision",
        """
        SELECT count(*) FROM cognitive_os.memory_embeddings e
        LEFT JOIN cognitive_os.memory_revisions r
          ON r.memory_id = e.memory_id AND r.revision = e.revision
             AND r.content_hash = e.content_hash
        WHERE r.memory_id IS NULL
        """,
        "embeddings whose revision or content hash moved under them",
    ),
    (
        "no_repository_group_crosses_a_split",
        """
        SELECT count(*) FROM (
          SELECT g.value AS group_hash
          FROM cognitive_os.corpus_manifests m,
               LATERAL jsonb_array_elements_text(
                 (m.payload_json::jsonb)->'split_manifest'->'lineage_group_hashes') g,
               LATERAL jsonb_array_elements(
                 (m.payload_json::jsonb)->'split_manifest'->'assignments') a
          GROUP BY g.value
          HAVING count(DISTINCT a->>'split') > 1
        ) crossing
        """,
        "repository groups appearing in more than one split",
    ),
    (
        # Accepted only. A quarantined observation is eligible for nothing, and requiring it
        # to be marked evaluation-eligible would turn correct refusals into reported damage.
        "every_accepted_real_run_is_evaluation_only",
        """
        SELECT count(*) FROM cognitive_os.learned_observations
        WHERE provenance_class = 'real_governed_run'
          AND status = 'accepted'
          AND evaluation_eligible IS NOT TRUE
        """,
        "accepted real governed runs that are not evaluation-only",
    ),
    (
        "no_quarantined_observation_is_eligible_for_anything",
        """
        SELECT count(*) FROM cognitive_os.learned_observations
        WHERE status <> 'accepted' AND evaluation_eligible IS TRUE
        """,
        "refused observations still marked eligible",
    ),
    (
        "every_observation_carries_a_content_hash",
        """
        SELECT count(*) FROM cognitive_os.learned_observations
        WHERE content_hash IS NULL OR length(content_hash) <> 64
        """,
        "observations with no usable content hash",
    ),
)

#: Read back for the report, not asserted against a hard-coded number: the campaign's own
#: evidence file carries the expected values, and a count baked in here would need editing
#: every time a legitimate run added rows.
COUNT_QUERY = """
SELECT json_build_object(
  'events', (SELECT count(*) FROM cognitive_os.events),
  'artifacts', (SELECT count(*) FROM cognitive_os.artifacts),
  'artifact_blobs', (SELECT count(*) FROM cognitive_os.artifact_blobs),
  'corpus_items', (SELECT count(*) FROM cognitive_os.corpus_items),
  'corpus_manifest_items', (SELECT count(*) FROM cognitive_os.corpus_manifest_items),
  'corpus_route_decisions', (SELECT count(*) FROM cognitive_os.corpus_route_decisions),
  'experience_compilations', (SELECT count(*) FROM cognitive_os.experience_compilations),
  'experience_candidates', (SELECT count(*) FROM cognitive_os.experience_candidates),
  'learned_observations', (SELECT count(*) FROM cognitive_os.learned_observations),
  'learned_datasets', (SELECT count(*) FROM cognitive_os.learned_datasets),
  'memory_items', (SELECT count(*) FROM cognitive_os.memory_items),
  'memory_embeddings', (SELECT count(*) FROM cognitive_os.memory_embeddings)
)::text
"""


def task_generation_is_deterministic() -> IntegrityCheck:
    """Regenerate every task twice. A corpus that cannot be regenerated cannot be audited."""
    from datetime import UTC, datetime
    from uuid import UUID

    epoch = datetime(2026, 7, 30, tzinfo=UTC)
    artifact = UUID("00000000-0000-0000-0000-0000000021c3")
    drifted = []
    for template_id in available_templates():
        hashes = {
            build_manifest(
                template_id,
                seed=1,
                hidden_bundle_artifact_id=artifact,
                hidden_bundle_hash="0" * 64,
                created_at=epoch,
            ).canonical_hash()
            for _ in range(2)
        }
        if len(hashes) != 1:
            drifted.append(template_id)
    return IntegrityCheck(
        name="task_generation_is_deterministic",
        ok=not drifted,
        severity=FAILURE,
        detail=(
            f"{len(available_templates())} templates regenerate identically"
            if not drifted
            else f"templates that did not regenerate identically: {', '.join(drifted)}"
        ),
    )


def development_pair_is_untouched(
    root: Path, *, expected_digest: str, expected_files: int
) -> IntegrityCheck:
    """The inconsistent development Artifact Store must receive nothing from C3. §S21C3-003."""
    if not root.is_dir():
        return IntegrityCheck(
            name="development_pair_is_untouched",
            ok=False,
            severity=FAILURE,
            detail=f"the development artifact root {root} is not present to compare",
        )
    digest, files = fingerprint(root)
    ok = digest == expected_digest and files == expected_files
    return IntegrityCheck(
        name="development_pair_is_untouched",
        ok=ok,
        severity=FAILURE,
        detail=(
            f"{digest} over {files} files"
            if ok
            else f"{digest} over {files} files, expected {expected_digest} over {expected_files}"
        ),
    )


def local_embedding_model_is_available(root: Path | None) -> IntegrityCheck:
    """A warning, never a failure. §S21C3-061: unavailability is a capability report."""
    from cognitive_os.infrastructure.embeddings import minilm

    if root is None:
        return IntegrityCheck(
            name="local_embedding_model_is_available",
            ok=False,
            severity=WARNING,
            detail="no local model directory was given; retrieval is a capability this host lacks",
        )
    status, reason = minilm.health(root)
    return IntegrityCheck(
        name="local_embedding_model_is_available",
        ok=status is minilm.ModelHealth.HEALTHY,
        severity=WARNING,
        detail=f"{status.value}: {reason}",
    )


async def inspect(
    connection: Any,
    *,
    development_root: Path,
    development_digest: str,
    development_files: int,
    model_root: Path | None,
) -> tuple[IntegrityReport, dict[str, int]]:
    """Every check, once, against one open connection. Returns the report and the counts."""
    from sqlalchemy import text as sql

    checks = [task_generation_is_deterministic()]
    for name, statement, subject in _ORPHAN_CHECKS:
        found = int(await connection.scalar(sql(statement)) or 0)
        checks.append(
            IntegrityCheck(
                name=name,
                ok=found == 0,
                severity=FAILURE,
                detail=f"{found} {subject}",
            )
        )
    checks.append(
        development_pair_is_untouched(
            development_root,
            expected_digest=development_digest,
            expected_files=development_files,
        )
    )
    checks.append(local_embedding_model_is_available(model_root))

    import json

    counts = json.loads(await connection.scalar(sql(COUNT_QUERY)))
    checks.append(
        IntegrityCheck(
            name="corpus_counts_reconcile",
            ok=counts["corpus_items"] == counts["corpus_route_decisions"],
            severity=FAILURE,
            detail=(
                f"{counts['corpus_items']} items, "
                f"{counts['corpus_route_decisions']} route decisions"
            ),
        )
    )
    return IntegrityReport(checks=tuple(checks)), counts
