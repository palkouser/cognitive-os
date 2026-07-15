"""Verify restored Wiki Markdown and exact-lineage hashes from JSON lines on stdin."""

import base64
import json
import sys
from hashlib import sha256

from cognitive_os.domain.semantic_memory import semantic_hash


def main() -> int:
    count = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        value = json.loads(line)
        markdown = base64.b64decode(value["markdown_base64"])
        if sha256(markdown).hexdigest() != value["content_hash"]:
            raise ValueError("restored Wiki content hash mismatch")
        if semantic_hash(value["claim_refs"]) != value["snapshot_hash"]:
            raise ValueError("restored Wiki lineage snapshot mismatch")
        count += 1
    print(f"Verified {count} restored Wiki revision hashes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
