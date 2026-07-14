"""Export and verify deterministic JSON Schema snapshots."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from hashlib import sha256
from pathlib import Path

from .registry import SchemaEntry, build_schema_registry

SCHEMA_SET_VERSION = 1
GENERATED_BY = "cognitive_os.schemas.export"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "schemas"


def stable_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def schema_document(entry: SchemaEntry) -> dict[str, object]:
    schema = entry.model.model_json_schema(mode="serialization")
    schema["$id"] = f"https://cognitive-os.local/schemas/{entry.path}"
    schema["title"] = entry.model.__name__
    return schema


def export_schemas(output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    manifest_models: list[dict[str, object]] = []
    event_types: list[dict[str, object]] = []
    for entry in build_schema_registry():
        content = stable_json(schema_document(entry))
        destination = output / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        item: dict[str, object] = {
            "model": entry.model.__name__,
            "file": entry.path,
            "sha256": sha256(content).hexdigest(),
        }
        manifest_models.append(item)
        if entry.event_type is not None:
            event_types.append(
                {
                    "event_type": entry.event_type,
                    "schema_version": entry.schema_version,
                    "file": entry.path,
                }
            )
    manifest = {
        "schema_set_version": SCHEMA_SET_VERSION,
        "generated_by": GENERATED_BY,
        "models": manifest_models,
        "event_types": event_types,
    }
    (output / "manifest.json").write_bytes(stable_json(manifest))


def compare_schema_trees(expected: Path, actual: Path) -> tuple[list[str], list[str], list[str]]:
    expected_files = {
        path.relative_to(expected).as_posix() for path in expected.rglob("*") if path.is_file()
    }
    actual_files = {
        path.relative_to(actual).as_posix() for path in actual.rglob("*") if path.is_file()
    }
    added = sorted(actual_files - expected_files)
    removed = sorted(expected_files - actual_files)
    changed = sorted(
        path
        for path in expected_files & actual_files
        if (expected / path).read_bytes() != (actual / path).read_bytes()
    )
    return added, removed, changed


def check_schemas(output: Path) -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        generated = Path(temp_dir) / "schemas"
        export_schemas(generated)
        added, removed, changed = compare_schema_trees(output, generated)
    if added or removed or changed:
        print(f"Added schemas: {added}")
        print(f"Removed schemas: {removed}")
        print(f"Changed schemas: {changed}")
        return False
    print("Contract schema check passed.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when tracked schemas drift")
    args = parser.parse_args()
    if args.check:
        return 0 if check_schemas(DEFAULT_OUTPUT) else 1
    export_schemas(DEFAULT_OUTPUT)
    print(f"Exported contract schemas to {DEFAULT_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
