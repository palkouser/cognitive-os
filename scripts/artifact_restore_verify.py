"""Verify artifact metadata against restored content-addressed files from JSON lines."""

import hashlib
import json
import sys
from pathlib import Path, PurePosixPath


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: artifact_restore_verify.py ARTIFACT_ROOT")
    root = Path(sys.argv[1]).resolve()
    count = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        value = json.loads(line)
        storage_key = PurePosixPath(value["storage_key"])
        if storage_key.is_absolute() or ".." in storage_key.parts:
            raise ValueError("artifact storage key escapes the artifact root")
        path = root.joinpath(*storage_key.parts)
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError("artifact metadata references a missing regular file")
        data = path.read_bytes()
        if len(data) != value["size_bytes"]:
            raise ValueError("artifact size does not match restored metadata")
        if hashlib.sha256(data).hexdigest() != value["content_hash"]:
            raise ValueError("artifact content hash does not match restored metadata")
        count += 1
    print(f"Verified {count} artifact files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
