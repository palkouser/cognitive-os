import json
from hashlib import sha256
from pathlib import Path

from cognitive_os.schemas.export import check_schemas


def test_schema_manifest_hashes_match_files() -> None:
    root = Path("schemas")
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["schema_set_version"] == 1
    assert len(manifest["event_types"]) == 69
    for item in manifest["models"]:
        assert sha256((root / item["file"]).read_bytes()).hexdigest() == item["sha256"]


def test_schema_export_has_no_drift() -> None:
    assert check_schemas(Path("schemas"))
