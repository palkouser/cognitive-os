"""Read persisted Experience Graph evidence and name exactly what failed to resolve.

Two readers need this: the operator CLI and the unified integrity report. Neither should
carry its own copy of "which file holds this pair", and neither should collapse the ways
evidence can be wrong into a single boolean, because the remedies differ entirely.

Four distinct outcomes, kept apart on purpose:

* **missing bytes** — the root names an artifact the store does not hold. The store lost it.
* **corrupt bytes** — the store holds bytes that do not hash to the name they are filed
  under, or that the pair contract refuses. The bytes changed under us.
* **broken authority links** — the pair loads and is internally sound, but a hash the root
  declared about it disagrees. The root and the store describe different evidence.
* **legacy non-recompilation** — a historical pair whose original run cannot be recompiled
  byte for byte. Recorded on the pair at construction; not damage, and never reported as it.

Every function here reads. This module writes nothing, anywhere.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from cognitive_os.domain.experience_graph import FailedSuccessGraphPair

from .graph_projection import round_trips


def blob_path(artifact_root: Path, content_hash: str) -> Path:
    """Where the content-addressed store files a blob. Two-character shard, then the hash."""
    return artifact_root / "sha256" / content_hash[:2] / content_hash


@dataclass(frozen=True, slots=True)
class GraphEvidence:
    """What resolved, and what did not, with the pair identity that names each problem."""

    graph_set_id: str
    declared_pairs: int
    pairs: tuple[FailedSuccessGraphPair, ...]
    missing_bytes: tuple[str, ...]
    corrupt_bytes: tuple[str, ...]
    broken_links: tuple[str, ...]
    failed_round_trips: tuple[str, ...]
    legacy_recompilation: tuple[str, ...]

    @property
    def intact(self) -> bool:
        """Damage only. A legacy pair is not damage and does not condemn the set."""
        return not (
            self.missing_bytes
            or self.corrupt_bytes
            or self.broken_links
            or self.failed_round_trips
            or len(self.pairs) != self.declared_pairs
        )


def load_evidence(root_manifest: Path, artifact_root: Path) -> GraphEvidence:
    """Load every pair the root names, classifying each failure rather than raising on it.

    Raising on the first bad pair would answer a different question. An operator asking
    whether the store is intact needs the whole list, not the first entry of it.
    """
    root = json.loads(root_manifest.read_text())
    pairs, missing, corrupt, broken, no_round_trip, legacy = [], [], [], [], [], []

    for child in root.get("children", ()):
        pair_id = child["pair_id"]
        path = blob_path(artifact_root, child["content_hash"])
        if not path.is_file():
            missing.append(pair_id)
            continue
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != child["content_hash"]:
            corrupt.append(pair_id)
            continue
        try:
            pair = FailedSuccessGraphPair.model_validate(json.loads(raw))
        except Exception:  # every refusal is the same verdict here: the bytes are unusable
            corrupt.append(pair_id)
            continue
        declared = (
            child["pair_hash"],
            child["failed_structural"],
            child["successful_structural"],
            child["edit_path_hash"],
        )
        actual = (
            pair.content_hash,
            pair.failed.structural_hash,
            pair.successful.structural_hash,
            pair.edit_path.content_hash,
        )
        if declared != actual:
            broken.append(pair_id)
            continue
        if not round_trips(pair.failed, pair.successful, pair.edit_path):
            no_round_trip.append(pair_id)
            continue
        if pair.legacy_recompilation_unavailable:
            legacy.append(pair_id)
        pairs.append(pair)

    return GraphEvidence(
        graph_set_id=root.get("graph_set_id", root_manifest.stem),
        declared_pairs=int(root.get("pair_count", len(root.get("children", ())))),
        pairs=tuple(pairs),
        missing_bytes=tuple(sorted(missing)),
        corrupt_bytes=tuple(sorted(corrupt)),
        broken_links=tuple(sorted(broken)),
        failed_round_trips=tuple(sorted(no_round_trip)),
        legacy_recompilation=tuple(sorted(legacy)),
    )
