"""Inspect a Python 3.12 repository without executing repository code."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from cognitive_os.coding.indexing import RepositoryIndexer
from cognitive_os.coding.repository_profile import detect_repository_profile
from cognitive_os.domain.coding import CodingLimits
from cognitive_os.infrastructure.repository.git_repository import GitRepositoryService


async def inspect(
    repository: Path, base_commit: str, *, rootless_docker: bool
) -> dict[str, object]:
    resolved = repository.resolve(strict=True)
    service = GitRepositoryService((resolved.parent,))
    reference = await service.validate(resolved, base_commit)
    profile = detect_repository_profile(resolved, rootless_docker=rootless_docker)
    index = RepositoryIndexer(CodingLimits()).build(resolved, reference.base_commit, 0)
    return {
        "repository_identity": reference.repository_identity,
        "base_commit": reference.base_commit,
        "profile": profile.model_dump(mode="json"),
        "index_hash": index.canonical_hash(),
        "files": len(index.files),
        "modules": len(index.modules),
        "truncated": index.truncated,
        "warnings": index.warnings,
        "executed_repository_code": False,
        "supported": profile.status.value == "supported",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--rootless-docker", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        inspect(args.repository, args.base_commit, rootless_docker=args.rootless_docker)
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["supported"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
