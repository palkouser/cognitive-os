from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_v2_seal_dataset_receipt_and_restart_end_to_end(tmp_path: Path) -> None:
    """Seeded W4-F3 regression: one authority chain must survive a service restart."""
    output = tmp_path / "seal-resume.json"
    completed = subprocess.run(  # nosec B603 - fixed interpreter, script, and test-owned path
        [
            sys.executable,
            "scripts/invariant_spine_fixture_d3.py",
            "--output",
            str(output),
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["chronology"]["strictly_pre_outcome"]
    assert evidence["chronology"]["stored_seal_time_preserved"]
    assert "strictly before" in evidence["chronology"]["post_outcome_seal_refusal"]
    assert evidence["restart"]["feature_seal_hash_reproduced"]
    assert evidence["restart"]["dataset_record_reproduced"]
    assert evidence["restart"]["receipt_effective_remainder"] == []
    assert evidence["artifact_lineage"]["all_bytes_verified"]
