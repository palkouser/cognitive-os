"""Optional deterministic Inspect AI export adapter."""

from __future__ import annotations

import json
from importlib.util import find_spec
from pathlib import Path

from cognitive_os.domain.benchmarks import BenchmarkCase, BenchmarkCaseResult

from .errors import InspectAdapterUnavailableError


def ensure_inspect_available() -> None:
    if find_spec("inspect_ai") is None:
        raise InspectAdapterUnavailableError(
            "install the benchmark-inspect extra to export Inspect AI tasks"
        )


def case_to_sample(case: BenchmarkCase) -> dict[str, object]:
    return {
        "id": case.case_id,
        "input": dict(case.problem_request),
        "metadata": {
            "domain": case.domain.value,
            "source": case.source,
            "license": case.license,
            "case_hash": case.case_hash,
        },
    }


def result_to_score(result: BenchmarkCaseResult) -> dict[str, object]:
    return {"value": 1 if result.status.value == "passed" else 0, "answer": result.status.value}


def export_task(cases: tuple[BenchmarkCase, ...], output_directory: Path) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    samples = [case_to_sample(item) for item in sorted(cases, key=lambda item: item.case_id)]
    data_path = output_directory / "samples.json"
    data_path.write_text(json.dumps(samples, sort_keys=True, indent=2), encoding="utf-8")
    module_path = output_directory / "cognitive_os_task.py"
    module_path.write_text(
        '"""Generated Cognitive OS Inspect AI task data adapter."""\n\n'
        "from pathlib import Path\n\n"
        "SAMPLES_PATH = Path(__file__).with_name('samples.json')\n",
        encoding="utf-8",
    )
    return module_path
