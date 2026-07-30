#!/usr/bin/env python3
"""Prefetch and check the frozen local embedding model. §S21C3-051.

    scripts/embedding_model.py prefetch --destination /abs/path --allow-network
    scripts/embedding_model.py health --destination /abs/path

`prefetch` is the only code path in this repository that downloads a model, and it refuses to
run without `--allow-network`. Everything else — the provider, the benchmark, the memory plane
— reads the destination with `local_files_only=True`.

It is idempotent and resumable because `snapshot_download` is: a second run re-verifies what is
already on disk rather than re-fetching it, and an interrupted run resumes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.infrastructure.embeddings.minilm import (
    LICENCE,
    MANIFEST_NAME,
    MODEL_FILES,
    MODEL_ID,
    REVISION,
    ModelHealth,
    build_manifest,
    health,
)


def _prefetch(destination: Path, *, model_id: str, revision: str, allow_network: bool) -> int:
    if not allow_network:
        print("refused: prefetch downloads a model and needs --allow-network")
        return 2
    if not destination.is_absolute():
        print("refused: destination must be an absolute path")
        return 2
    if model_id != MODEL_ID or revision != REVISION:
        print(f"refused: only the frozen {MODEL_ID}@{REVISION} may be fetched")
        return 2
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("refused: the local-embeddings extra is not installed")
        return 2

    snapshot_download(
        repo_id=model_id,
        revision=revision,
        local_dir=str(destination),
        allow_patterns=list(MODEL_FILES),
    )
    licence = (destination / "README.md").read_text(encoding="utf-8")
    if f"license: {LICENCE}" not in licence:
        # The card is the licence evidence S21C3-050 asks for. A repository that stopped
        # declaring Apache-2.0 is a different rights question, not a download to keep going.
        print(f"refused: the model card does not declare {LICENCE}")
        return 1
    manifest = build_manifest(destination)
    (destination / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{model_id}@{revision} -> {destination}")
    print(f"tree_digest {manifest['tree_digest']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("prefetch", help="download the frozen model (network)")
    fetch.add_argument("--destination", type=Path, required=True)
    fetch.add_argument("--model-id", default=MODEL_ID)
    fetch.add_argument("--revision", default=REVISION)
    fetch.add_argument("--allow-network", action="store_true")

    check = commands.add_parser("health", help="verify a local model directory (no network)")
    check.add_argument("--destination", type=Path, required=True)

    arguments = parser.parse_args()
    if arguments.command == "prefetch":
        return _prefetch(
            arguments.destination.resolve(),
            model_id=arguments.model_id,
            revision=arguments.revision,
            allow_network=arguments.allow_network,
        )
    status, reason = health(arguments.destination.resolve())
    print(f"{status.value}: {reason}")
    return 0 if status is ModelHealth.HEALTHY else 1


if __name__ == "__main__":
    raise SystemExit(main())
