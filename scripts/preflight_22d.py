"""S22D-001 and S22D-002. The hardware preflight, the provider enumeration, and the gates.

Three things W0 must settle before a single arm is measured, and one it must refuse to settle.

**The host (§1.3).** The allocation permits local-model hardware benchmarks to begin after a
CPU/GPU preflight. The plan names a host; only a measurement may bind one, so every number
here is read from `/proc`, `nvidia-smi` and `statvfs` rather than transcribed from the
backlog. The split is 22B's S22B-002 and 22C's W1-F1: *invariants* are recomputed by
`--check` and *observations* are recorded and re-read, because a `--check` that re-derives a
world observation cannot survive the world changing.

**The enumeration (§2.2a).** "Large external LLM" is not a description in this sprint. It is
the complete list of adapters `providers/factory.py` can construct, derived from the
discriminated configuration union rather than typed out beside it, so the boundary cannot be
argued about after a number exists.

**The gates (§1.4).** Three rights questions, and this driver answers exactly one of them.
The microbenchmark's own content is ours and its provenance is frozen. The corpus for an
adapter is already cleared by 22C, with a constraint that decides what the option would be
worth. The model's licence is nobody's determination but the gate owner's — 22C W1-D2 is a
standing rule now — so the driver refuses to proceed on a model and reports a blocking
dependency with a named owner. It does not nominate a model, and it does not accept a
"temporary" one: a benchmark run on unclear weights is evidence that cannot be released.

    UV_CACHE_DIR=.cache/uv uv run python scripts/preflight_22d.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/preflight_22d.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import (  # noqa: E402
    EXTERNAL_PROVIDER_CONFIGS,
    EXTERNAL_PROVIDER_IDS,
    LOCAL_COMPONENTS_OUT_OF_SCOPE,
    REQUIRED_VERIFIER_EXTRAS,
    SLICE_TIME,
    BenchmarkVerifiersUnavailable,
    ExternalProviderRefused,
    canonical,
    refuse_external_providers,
    require_benchmark_verifiers,
)

from cognitive_os.config.provider_config import ProviderAdapterConfig  # noqa: E402
from cognitive_os.domain.corpus import CorpusUsageRight  # noqa: E402
from cognitive_os.domain.provider import ProviderKind  # noqa: E402

#: The named owner. Every blocking dependency in this record is addressed to this person, and
#: §3.2's rule is that W0's first act on an unconcluded gate is to surface it with an owner.
GATE_OWNER = "palkouser (Sprint 22 gate owner)"

#: The evidence file a concluded model-licence review must produce before W2 serves anything.
#: Its absence is the blocking dependency; its presence is what unblocks the local arm.
MODEL_CLEARANCE = EVIDENCE / "sprint-22d-model-rights.json"

#: 22C's sealed source-rights record, which already answers the adapter-corpus question.
SOURCE_RIGHTS = EVIDENCE / "sprint-22c-source-rights.json"

OUTPUT = EVIDENCE / "sprint-22d-preflight.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# §1.3. The host, measured
# ---------------------------------------------------------------------------


def _cpu() -> dict[str, Any]:
    text = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    models = {
        line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("model name")
    }
    cores = {
        line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("cpu cores")
    }
    return {
        "model": sorted(models)[0] if models else "unknown",
        "logical_cpus": os.cpu_count() or 0,
        "physical_cores": int(sorted(cores)[0]) if cores else 0,
    }


def _memory_total_kib() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1])
    return 0


def _gpu() -> dict[str, Any]:
    """Read the GPU if there is one. Absence is a recorded fact, never an error."""
    binary = shutil.which("nvidia-smi")
    if binary is None:
        return {"present": False, "reason": "nvidia-smi is not on PATH"}
    try:
        output = subprocess.run(
            [binary, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError) as error:
        return {"present": False, "reason": f"nvidia-smi failed: {error}"}
    name, _, memory = output.partition(",")
    return {"present": True, "name": name.strip(), "memory_mib": int(memory.strip())}


def _disk_free_gib(path: Path) -> int:
    stats = os.statvfs(path)
    return int(stats.f_bavail * stats.f_frsize / 1024**3)


def _invariants() -> dict[str, Any]:
    """What defines this host. `--check` recomputes every field here."""
    return {
        "cpu": _cpu(),
        "gpu": _gpu(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": sys.platform,
    }


#: Free memory and free disk move every minute of every day. Sealing them as invariants would
#: make `--check` fail for the reason 22C W1-F1 names — a validator that cannot survive the
#: world changing, which then tempts somebody to edit history so it passes.
OBSERVED_AT_W0 = ("observations", "model_licence_gate", "local_runtime")


def _observations() -> dict[str, Any]:
    return {
        "memory_total_kib": _memory_total_kib(),
        "free_disk_gib_repo": _disk_free_gib(REPO),
        "why_not_invariant": (
            "total memory and free disk are states of the world at W0, not properties of the "
            "declared host; `--check` re-reads them and compares them against nothing "
            "(22B S22B-002, 22C W1-F1)"
        ),
    }


def _cpu_viability() -> dict[str, Any]:
    """The exit asks for CPU viability — a claim about owned resources, not about speed."""
    invariants, observations = _invariants(), _observations()
    threads = invariants["cpu"]["logical_cpus"]
    memory_gib = observations["memory_total_kib"] / 1024**2
    return {
        "configuration_of_record": "cpu",
        "threads": threads,
        "memory_gib": round(memory_gib, 1),
        "supports_a_7_to_8b_quantized_model_on_cpu": threads >= 8 and memory_gib >= 16,
        "gpu_supports_parameter_efficient_finetuning": bool(
            invariants["gpu"]["present"] and invariants["gpu"].get("memory_mib", 0) >= 12_000
        ),
        "why_the_gpu_is_reported_beside_and_never_instead": (
            "the exit asks for CPU viability specifically, so the CPU configuration is the "
            "claim and GPU numbers are reported next to it; §3.2 names buying speed with the "
            "claim as a schedule risk, and the adapter stays outside every exit (§2.3)"
        ),
    }


# ---------------------------------------------------------------------------
# The local serving runtime, which does not exist here yet
# ---------------------------------------------------------------------------

_RUNTIME_CANDIDATES = ("ollama", "llama-server", "llama-cli", "vllm")


def _local_runtime() -> dict[str, Any]:
    """**W0-F3.** A cleared model still needs something to serve it, and nothing here does.

    `ProviderKind.LOCAL_API` is a released enum member with no configuration class and no
    adapter: the discriminated union in `config/provider_config.py` has four members and
    every one of them is `NETWORK_API` or `CLI_AGENT`. §1.2 reads the shared
    `openai_compatible` mapping as meaning a local model "plugs into the governed model path
    through an existing seam rather than a new adapter", and half of that is true — the wire
    mapping is reusable and is already shared by two adapters. The *config member and the
    adapter are not there*, so W2 adds released code rather than composing over it. That is
    the same shape as `ExtractionDecisionOutcome`: a released contract with nothing behind it.

    Surfaced rather than absorbed (§1.2), because a wave that quietly writes a new adapter
    has spent its budget on a gap the plan priced at zero.
    """
    found = {name: shutil.which(name) for name in _RUNTIME_CANDIDATES}
    kinds = {config.model_fields["kind"].default for config in EXTERNAL_PROVIDER_CONFIGS}
    return {
        "serving_runtime_installed": any(found.values()),
        "candidates_probed": list(_RUNTIME_CANDIDATES),
        "candidates_found": sorted(name for name, path in found.items() if path),
        "local_api_is_a_released_provider_kind": ProviderKind.LOCAL_API in set(ProviderKind),
        "local_api_configuration_classes": 0,
        "released_adapter_kinds": sorted(kind.value for kind in kinds),
        "openai_compatible_mapping_is_reusable": True,
        "w2_must_add": [
            "a LocalApiProviderConfig member of the discriminated provider union",
            "an adapter that maps it through providers/openai_compatible.py",
            "a serving runtime on this host for the cleared weights",
        ],
        "finding": "W0-F3",
    }


# ---------------------------------------------------------------------------
# §2.2(a). The enumeration, and the refusal executed rather than described
# ---------------------------------------------------------------------------


def _provider_enumeration() -> dict[str, Any]:
    members = ProviderAdapterConfig.__origin__.__args__  # type: ignore[attr-defined]
    derived = tuple(sorted(item.model_fields["provider_id"].default for item in members))
    probes = []
    for provider_id in (*EXTERNAL_PROVIDER_IDS, "local-model-under-measurement"):
        try:
            refuse_external_providers([provider_id])
        except ExternalProviderRefused:
            probes.append({"provider_id": provider_id, "refused": True})
        else:
            probes.append({"provider_id": provider_id, "refused": False})
    return {
        "derived_from": "config.provider_config.ProviderAdapterConfig discriminated union",
        "union_members": [item.__name__ for item in members],
        "external_provider_ids_derived": list(derived),
        "external_provider_ids_frozen": list(EXTERNAL_PROVIDER_IDS),
        "enumeration_matches_the_union": derived == EXTERNAL_PROVIDER_IDS,
        "out_of_scope_by_name": list(LOCAL_COMPONENTS_OUT_OF_SCOPE),
        "refusal_probes": probes,
        "every_external_probe_refused": all(
            item["refused"] for item in probes if item["provider_id"] in EXTERNAL_PROVIDER_IDS
        ),
        "the_local_model_is_not_refused": probes[-1]["refused"] is False,
    }


def _verifier_extras() -> dict[str, Any]:
    """W0-F1, recorded where the environment is recorded rather than in prose alone."""
    try:
        require_benchmark_verifiers()
    except BenchmarkVerifiersUnavailable as error:
        return {"frozen_verifiers_available": False, "refusal": str(error), "finding": "W0-F1"}
    return {
        "frozen_verifiers_available": True,
        "required_extras": list(REQUIRED_VERIFIER_EXTRAS),
        "finding": "W0-F1",
        "why_it_is_a_finding": (
            "build_builtin_registry registers the physics verifiers as *unavailable* when "
            "Pint is absent and list_all() returns them anyway, so a verifier set chosen by "
            "reading the registry looks complete while half of it errors; fifty of the "
            "hundred would have scored zero as 'undecidable' and the 70 % exit would have "
            "read as capability rather than as a missing extra"
        ),
    }


# ---------------------------------------------------------------------------
# §1.4. The three rights gates
# ---------------------------------------------------------------------------


def _model_licence_gate() -> dict[str, Any]:
    """The blocking one. This driver refuses to decide it, and says who must."""
    if MODEL_CLEARANCE.exists():
        clearance = json.loads(MODEL_CLEARANCE.read_text(encoding="utf-8"))
        return {
            "concluded": True,
            "clearance_file": MODEL_CLEARANCE.name,
            "clearance_hash": _sha256(MODEL_CLEARANCE.read_bytes()),
            "cleared_by": clearance.get("cleared_by"),
            "permitted_uses": clearance.get("permitted_uses"),
            "blocks": None,
        }
    return {
        "concluded": False,
        "owner": GATE_OWNER,
        "required_artefact": MODEL_CLEARANCE.name,
        "required_contract": "cognitive_os.domain.corpus.OperatorLicenseClearance",
        "what_the_owner_must_decide": [
            "which model, by name and by the SHA-256 of the weight file W2 will serve",
            "the SHA-256 of the licence text those weights ship with, read out of the "
            "distribution rather than transcribed from a model card (22C W1-D2: never "
            "transcribe a nominated licence; hash the bytes)",
            "which CorpusUsageRight values the operator permits — internal_use at minimum, "
            "and benchmark_use for the numbers in this sprint to be publishable",
        ],
        "what_this_program_may_do": (
            "read a licence if there is one, recognise it if it can, and advise. It may "
            "refuse on its own; it may never permit on its own"
        ),
        "blocks": ["W2 local model", "W3 local-model arm", "exits one, two, three and four"],
        "no_substitute_permitted": (
            "§3.2: never substitute a 'temporary' model — a benchmark run on unclear weights "
            "is evidence that cannot be released"
        ),
    }


def _adapter_corpus_gate() -> dict[str, Any]:
    """Already answered by 22C, and the answer decides what the adapter option is worth."""
    if not SOURCE_RIGHTS.exists():
        return {"concluded": False, "owner": GATE_OWNER, "reason": "22C rights record absent"}
    sealed = json.loads(SOURCE_RIGHTS.read_text(encoding="utf-8"))
    sources = [
        {
            "key": item["key"],
            "license_identifier": item["license_identifier"],
            "permitted_uses": item.get("permitted_uses"),
            "clearance_content_hash": item["clearance_content_hash"],
        }
        for item in sealed["sources"]
    ]
    noncommercial = [item for item in sources if "NC" in item["license_identifier"]]
    return {
        "concluded": True,
        "cleared_by": sealed["cleared_by"],
        "sources": sources,
        "model_training_is_cleared": False,
        "constraint_recorded_whether_or_not_the_adapter_is_attempted": (
            "one cleared source is CC BY-NC-SA 4.0, so every adaptation inherits "
            "noncommercial and ShareAlike; an adapter trained on it is internal-only by "
            "construction and could never ship in a released artifact. §1.4 records this "
            "now because it decides what the option would be worth, not after W4 has surplus"
        ),
        "noncommercial_sources": [item["key"] for item in noncommercial],
        "model_training_right_not_granted": (
            CorpusUsageRight.MODEL_TRAINING.value
            not in {
                right for item in sealed["sources"] for right in (item.get("permitted_uses") or ())
            }
        ),
        "blocks": None,
        "why_it_blocks_nothing": (
            "§2.3 puts adapter training outside every exit; this gate exists so the option "
            "is priced, not so the schedule waits on it"
        ),
    }


def _microbenchmark_provenance_gate() -> dict[str, Any]:
    """§1.4's third question: a hundred tasks lifted from a source are not ours."""
    from tasks_22d import MICROBENCHMARK_TASKS, manifest

    provenances = {str(task["provenance"]) for task in MICROBENCHMARK_TASKS}
    published = manifest()
    return {
        "concluded": True,
        "task_count": published["task_count"],
        "distinct_provenances": sorted(provenances),
        "every_task_authored_in_repository": provenances
        == {"authored in-repository for Sprint 22D"},
        "manifest_hash": published["manifest_hash"],
        "facts_are_grounded_in_cleared_sources": published["grounding_sources"],
        "why_asking_about_a_fact_is_authorship": (
            "the prompts and the expected answers are written here; the constants they ask "
            "about are stated by the two rights-cleared sources, both of which 22C cleared "
            "for benchmark_use. Nothing is copied out of a source into this repository"
        ),
        "blocks": None,
    }


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def _record() -> dict[str, Any]:
    invariants = _invariants()
    model_gate = _model_licence_gate()
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22D-001", "S22D-002"],
        "owner": GATE_OWNER,
        "predecessor_release_verified": {
            "tag": "sprint-22c-evidence-baseline",
            "tag_object": "22d88878251e6670cb365b76dce925eee6da1c13",
            "peels_to": "5ecb7c9ebd18c73ec78ac012103c9c77b61443f4",
            "is_ancestor_of_protected_main": True,
            "exact_head_ci_run": "31885260162",
            "exact_head_ci_conclusion": "success",
            "protection": {"required_checks": 27, "enforce_admins": True},
            "the_plan_said_otherwise": (
                "§0 of the backlog states 22C's release had not happened. It had, between "
                "the plan being written and W0 running: the tag, the ancestry and the "
                "exact-head run were read back from the remote rather than assumed, and W0's "
                "blocking dependency is therefore satisfied rather than waived"
            ),
        },
        "invariants": invariants,
        "observations": _observations(),
        "cpu_viability": _cpu_viability(),
        "local_runtime": _local_runtime(),
        "provider_enumeration": _provider_enumeration(),
        "verifier_extras": _verifier_extras(),
        "model_licence_gate": model_gate,
        "adapter_corpus_gate": _adapter_corpus_gate(),
        "microbenchmark_provenance_gate": _microbenchmark_provenance_gate(),
    }
    record["blocking_dependencies"] = [
        item
        for item in (
            None if model_gate["concluded"] else {"gate": "model_licence", **model_gate},
            None
            if record["local_runtime"]["serving_runtime_installed"]
            else {
                "gate": "local_serving_runtime",
                "owner": GATE_OWNER,
                "blocks": ["W2 local model"],
                "finding": "W0-F3",
            },
        )
        if item is not None
    ]
    record["w0_may_proceed"] = True
    record["w2_may_proceed"] = not record["blocking_dependencies"]
    record["why_w0_proceeds_anyway"] = (
        "§3.1 has the fixture-scale slice run before the real model is touched, so every W0 "
        "deliverable except the model itself is reachable while the clearance is outstanding "
        "— which is exactly how 22C finished a W0 whose source gate was still open"
    )
    record["invariants_hash"] = _sha256(canonical(invariants))
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    record = _record()
    if arguments.check:
        if not OUTPUT.exists():
            print(f"MISSING {OUTPUT}")
            return 1
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        moving = {"recorded_at", "integrity_content_hash", *OBSERVED_AT_W0}
        invariants_same = {k: v for k, v in stored.items() if k not in moving} == {
            k: v for k, v in record.items() if k not in moving
        }
        body = {k: v for k, v in stored.items() if k != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        print(
            json.dumps(
                {
                    "reproduced": invariants_same and sealed,
                    "invariants_recomputed": invariants_same,
                    "stored_seal_intact": sealed,
                    "recorded_not_recomputed": list(OBSERVED_AT_W0),
                    "model_gate_has_concluded_since_w0": (
                        stored["model_licence_gate"]["concluded"]
                        != record["model_licence_gate"]["concluded"]
                    ),
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if invariants_same and sealed else 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "cpu": record["invariants"]["cpu"]["model"],
                "threads": record["invariants"]["cpu"]["logical_cpus"],
                "gpu": record["invariants"]["gpu"].get("name"),
                "cpu_viable": record["cpu_viability"]["supports_a_7_to_8b_quantized_model_on_cpu"],
                "external_providers": record["provider_enumeration"][
                    "external_provider_ids_frozen"
                ],
                "enumeration_matches_the_union": record["provider_enumeration"][
                    "enumeration_matches_the_union"
                ],
                "blocking_dependencies": [item["gate"] for item in record["blocking_dependencies"]],
                "w2_may_proceed": record["w2_may_proceed"],
                "invariants_hash": record["invariants_hash"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
