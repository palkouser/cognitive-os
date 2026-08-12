#!/usr/bin/env python3
"""S22A groundwork: the measured starting state of the domain surface, sealed before W0.

Sprint 22A's exit is a negative claim about change — "both new domains register without
changing the core controller or storage schema" — and a negative claim about change needs a
sealed picture of what exists before anything moves. This record is that picture, taken the
way D7's groundwork took its transfer measurement: recomputed from the code and released
bytes rather than asserted, so the later waves diff against evidence instead of memory.

Three measurements:

*The enum coupling.* Every module importing `DomainKind`, every keyed table and member
reference, counted from the source tree. This is the surface the exit criterion is about;
the wave that dissolves it must show this number reaching the adapter boundary and stopping.

*The released registry, derived.* The four released domains expressed as
`DomainDescriptorV1` records through `released_domain_descriptors()` — capabilities, tools,
skills, strategies and problem types read out of the released problem-type registry.
Their content hashes are the backward-compatibility contract: a 22A wave that changes any
released domain's derived descriptor has changed released behaviour, and the diff names it.

*The package boundary, exercised.* The fail-closed loader is run against a valid pilot-shaped
package and against six refusal cases — oversize, non-JSON, non-object, unknown field, bad
id grammar, unresolvable shared concept — and the record stores each refusal's diagnostics.
A boundary that has never refused anything is a hope, which is the W3-F1 lesson one sprint
later: run the thing you intend to rely on, on the bytes you intend to feed it.

Read-only against the repository; writes only its own record.

    UV_CACHE_DIR=.cache/uv uv run python scripts/domain_survey_22a.py
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.domain.descriptors import (  # noqa: E402
    DOMAIN_PACKAGE_MAX_BYTES,
    DomainPackageError,
    released_domain_descriptors,
    validate_domain_package,
)
from cognitive_os.domains import registry  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-22" / "evidence"
OUTPUT = EVIDENCE / "sprint-22a-domain-survey.json"

SOURCE_ROOT = REPOSITORY / "src" / "cognitive_os"


def _digest(value: bytes | str) -> str:
    return sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _enum_coupling() -> dict[str, Any]:
    """Every `DomainKind` reference in the source tree, counted from the AST."""
    modules: dict[str, int] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "DomainKind" not in text:
            continue
        references = 0
        for node in ast.walk(ast.parse(text)):
            is_name = isinstance(node, ast.Name) and node.id == "DomainKind"
            is_attribute = isinstance(node, ast.Attribute) and node.attr == "DomainKind"
            if is_name or is_attribute:
                references += 1
        if references:
            modules[str(path.relative_to(REPOSITORY))] = references
    return {
        "modules": modules,
        "module_count": len(modules),
        "reference_count": sum(modules.values()),
        "definition": "src/cognitive_os/domain/domains.py",
    }


def _derived_descriptors() -> dict[str, Any]:
    descriptors = {}
    for descriptor in released_domain_descriptors():
        descriptors[descriptor.domain_id] = {
            "revision": descriptor.revision,
            "content_hash": descriptor.content_hash,
            "problem_types": list(descriptor.problem_types),
            "verifier_capabilities": list(descriptor.capabilities.verifier_capabilities),
            "tool_capabilities": list(descriptor.capabilities.tool_capabilities),
        }
    return {
        "descriptors": descriptors,
        # `released_snapshot_hash`, not `snapshot_hash`: this block is about the four
        # released domains, and S22A-030 split the two so that a process which admitted a
        # descriptor domain still reproduces this record exactly. The value is unchanged —
        # the two agree wherever nothing was registered — but only this one keeps agreeing.
        "registry_snapshot_hash": registry.released_snapshot_hash(),
        "reading": (
            "derived from the released problem-type registry at the snapshot hash above; "
            "a wave that changes any content hash here has changed released behaviour"
        ),
    }


def _valid_pilot_package() -> bytes:
    """A pilot-shaped package in the 22A grammar, used only to prove the loader accepts."""
    return json.dumps(
        {
            "domain_id": "engineering.mechanics",
            "revision": 1,
            "display_name": "mechanics (pilot shape)",
            "lifecycle": "pilot",
            "related_domain_ids": ["physics"],
            "problem_types": [],
            "concepts": [
                {
                    "concept_id": "rigid_body",
                    "description": "a body whose deformation is neglected",
                    "shared_with": ["physics"],
                }
            ],
            "capabilities": {
                "verifier_capabilities": ["physics.dimension"],
                "tool_capabilities": ["physics.kernel"],
                "units": ["newton", "pascal"],
            },
            "provenance": {
                "source": "sprint-22a groundwork fixture",
                "revision": "none",
                "licence": "internal",
                "redistributable": False,
            },
        }
    ).encode()


def _refusal_cases() -> dict[str, bytes]:
    valid = json.loads(_valid_pilot_package())
    unknown_field = dict(valid, controller_branch="mechanics")
    bad_grammar = dict(valid, domain_id="Mechanics!")
    unresolvable = json.loads(_valid_pilot_package())
    unresolvable["concepts"][0]["shared_with"] = ["chemistry"]
    return {
        "oversize": b" " * (DOMAIN_PACKAGE_MAX_BYTES + 1),
        "not_json": b"\xff\xfe not a descriptor",
        "not_an_object": b'["a", "list"]',
        "unknown_field": json.dumps(unknown_field).encode(),
        "bad_id_grammar": json.dumps(bad_grammar).encode(),
        "unresolvable_shared_concept": json.dumps(unresolvable).encode(),
    }


def _boundary_exercise() -> dict[str, Any]:
    accepted = validate_domain_package(_valid_pilot_package())
    refusals = {}
    for name, payload in _refusal_cases().items():
        try:
            validate_domain_package(payload)
        except DomainPackageError as error:
            refusals[name] = list(error.diagnostics)[:3]
        else:  # pragma: no cover - a refusal case that validates is the finding itself
            refusals[name] = ["ACCEPTED — the boundary did not refuse this case"]
    return {
        "valid_pilot_shape_accepted": accepted.domain_id == "engineering.mechanics",
        "accepted_content_hash": accepted.content_hash,
        "refusals": refusals,
        "every_refusal_refused": all(
            item and not item[0].startswith("ACCEPTED") for item in refusals.values()
        ),
    }


def _run(output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "22A",
            "stage": "groundwork",
            "recorded_at": datetime.now(UTC).isoformat(),
            "predecessor": {
                "tag": "sprint-21-learning-baseline",
                "commit": "3f5d7379caf85290da45885e22138506211bee2e",
            },
            "enum_coupling": _enum_coupling(),
            "released_domains_as_descriptors": _derived_descriptors(),
            "package_boundary": _boundary_exercise(),
            "what_this_record_is_not": (
                "a registration, a pilot package, or a change to any released domain. The "
                "fixture package proves the boundary's shape and is not the mechanics "
                "pilot; the pilots are authored under 22A's own plan"
            ),
        }
    )
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "output": output.name,
        "enum_modules": evidence["enum_coupling"]["module_count"],
        "enum_references": evidence["enum_coupling"]["reference_count"],
        "released_descriptors": len(evidence["released_domains_as_descriptors"]["descriptors"]),
        "boundary_refusals_all_refused": evidence["package_boundary"]["every_refusal_refused"],
        "integrity_content_hash": evidence["integrity_content_hash"],
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _run(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
