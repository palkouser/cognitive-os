"""The one local embedding model, frozen to an exact revision. §S21C3-050, §S21C3-051.

A floating reference — `main`, `latest`, or an unpinned download at runtime — would make
every retrieval measurement in this sprint unreproducible the first time upstream pushed a
commit, and it would do so silently. So the revision below is a commit SHA, the file list is
enumerated, and `health` refuses bytes that do not hash to what the manifest recorded.

The model is *not* committed. It is fetched once by an explicit operator command into an
absolute local directory and read from there with `local_files_only=True`; the runtime never
opens a socket. That split is the whole point: the network step is a decision somebody makes,
and the runtime step is one that cannot be made by accident.

`all-mpnet-base-v2` was the rejected alternative. It scores higher on general sentence
benchmarks and it is the wrong tool here: 768 dimensions and roughly five times the CPU cost,
corpus of a few hundred short technical records where §4.14 already concluded no approximate
index is needed. Paying five times the latency for accuracy this corpus cannot demonstrate is
not a trade, it is a habit.
"""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

#: Resolved 2026-07-30 from the Hugging Face model index. Never a branch name: a branch is a
#: pointer somebody else can move, and this identity has to survive them moving it.
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

DIMENSION = 384
LICENCE = "apache-2.0"
MAXIMUM_SEQUENCE_LENGTH = 256
NORMALIZATION = "l2"

#: Exactly what a CPU SentenceTransformer needs, and nothing else. The repository also ships
#: ONNX, OpenVINO, TensorFlow, Rust and a duplicate `pytorch_model.bin` — around 400 MB of
#: weights in formats this runtime cannot load. Fetching them would only add bytes to hash.
MODEL_FILES: tuple[str, ...] = (
    "1_Pooling/config.json",
    "README.md",
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)

#: Written beside the model, never into Git.
MANIFEST_NAME = "cognitive-os-model.json"


class ModelHealth(StrEnum):
    """Every way the local model can fail to be usable, named. §S21C3-051."""

    MISSING = "missing"
    DEPENDENCY_MISSING = "dependency_missing"
    DIGEST_MISMATCH = "digest_mismatch"
    DIMENSION_MISMATCH = "dimension_mismatch"
    HEALTHY = "healthy"


def file_digests(root: Path) -> dict[str, str]:
    """sha256 per declared file. A file that is absent is absent from the mapping."""
    digests = {}
    for name in MODEL_FILES:
        path = root / name
        if path.is_file():
            digests[name] = sha256(path.read_bytes()).hexdigest()
    return digests


def tree_digest(digests: dict[str, str]) -> str:
    """One hash over the whole tree, order-independent by construction."""
    joined = "".join(f"{name}:{digests[name]}\n" for name in sorted(digests))
    return sha256(joined.encode()).hexdigest()


def build_manifest(root: Path) -> dict[str, Any]:
    digests = file_digests(root)
    return {
        "model_id": MODEL_ID,
        "revision": REVISION,
        "dimension": DIMENSION,
        "normalization": NORMALIZATION,
        "maximum_sequence_length": MAXIMUM_SEQUENCE_LENGTH,
        "licence": LICENCE,
        "source_url": f"https://huggingface.co/{MODEL_ID}/tree/{REVISION}",
        "files": digests,
        "tree_digest": tree_digest(digests),
    }


def read_manifest(root: Path) -> dict[str, Any] | None:
    path = root / MANIFEST_NAME
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else None


def health(root: Path) -> tuple[ModelHealth, str]:
    """What the local directory is, before anything tries to embed with it.

    Ordered by what a wrong answer would cost: bytes are checked before the model is loaded,
    because loading tampered weights to discover they are tampered is the wrong way round.
    """
    manifest = read_manifest(root)
    if manifest is None:
        return ModelHealth.MISSING, f"no {MANIFEST_NAME} under {root}"
    if manifest.get("revision") != REVISION:
        return (
            ModelHealth.DIGEST_MISMATCH,
            f"manifest revision {manifest.get('revision')!r} is not the frozen {REVISION!r}",
        )
    missing = [name for name in MODEL_FILES if not (root / name).is_file()]
    if missing:
        return ModelHealth.MISSING, f"absent model files: {', '.join(missing)}"
    actual = file_digests(root)
    if actual != manifest.get("files"):
        changed = sorted(
            name for name in actual if actual[name] != (manifest.get("files") or {}).get(name)
        )
        return ModelHealth.DIGEST_MISMATCH, f"changed bytes: {', '.join(changed) or 'file set'}"
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return ModelHealth.DEPENDENCY_MISSING, "the local-embeddings extra is not installed"
    try:
        model = SentenceTransformer(str(root), device="cpu", local_files_only=True)
    except Exception as error:
        # Files that hash to a manifest we wrote, and still will not load. The manifest is
        # then the thing that is wrong, so this is a bytes problem however it presents.
        return ModelHealth.DIGEST_MISMATCH, f"the local model directory did not load: {error}"
    # Measured from an actual encode rather than read off the config, because the config is
    # what the model claims and this check exists for the case where the claim is wrong.
    reported = len(model.encode(["dimension probe"], normalize_embeddings=True)[0])
    if reported != DIMENSION:
        return (
            ModelHealth.DIMENSION_MISMATCH,
            f"the local model produces {reported} dimensions, not {DIMENSION}",
        )
    return ModelHealth.HEALTHY, f"{MODEL_ID}@{REVISION[:12]} verified at {root}"
