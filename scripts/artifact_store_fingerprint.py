"""Compute the path-and-size fingerprint of an artifact root, optionally asserting it.

Sprints 21C1, 21C2 and 21C3 all carry the claim that the inconsistent development Artifact
Store pair is untouched, evidenced by a fingerprint. Until Sprint 21C3 the algorithm behind
that value existed only in an operator's shell history, so the claim was not independently
checkable. This is that algorithm, tracked.

The fingerprint is the SHA-256 of the newline-joined ``"<relative path> <size>"`` lines for
every regular file under the root, sorted by relative path, with no trailing newline. It
deliberately reads no file content: the point is to detect writes to a store that must
receive none, and hashing content would make an integrity check out of what is meant to be a
cheap read-only one. ``scripts/verify_artifact_store.sh`` is the content check.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.coding.reality_integrity import fingerprint


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="artifact root to fingerprint")
    parser.add_argument("--expect", help="fail unless the fingerprint equals this value")
    parser.add_argument(
        "--expect-files", type=int, help="fail unless exactly this many files are counted"
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON object")
    arguments = parser.parse_args()

    root = arguments.root.resolve()
    if not root.is_dir():
        print(f"Artifact root does not exist: {root}", file=sys.stderr)
        return 1

    digest, files = fingerprint(root)
    matched = arguments.expect is None or digest == arguments.expect
    counted = arguments.expect_files is None or files == arguments.expect_files

    if arguments.json:
        print(
            json.dumps(
                {
                    "artifact_root": str(root),
                    "files": files,
                    "path_and_size_fingerprint_sha256": digest,
                    "expected": arguments.expect,
                    "matches_expected": matched and counted,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(f"{digest}  {files} files  {root}")

    if not matched:
        print(f"Fingerprint changed: expected {arguments.expect}", file=sys.stderr)
    if not counted:
        print(f"File count changed: expected {arguments.expect_files}", file=sys.stderr)
    return 0 if matched and counted else 1


if __name__ == "__main__":
    raise SystemExit(main())
