#!/usr/bin/env python3
"""S22A-030. The one decision W1 handed to W2, taken deliberately rather than discovered.

The W1 handoff named it: *whether registering a pilot may change `registry.snapshot_hash()`,
or whether the snapshot becomes per-domain scoped* — and said to take it deliberately, not to
find it in a failing test. This record takes it, and corrects the premise it arrived with.

Both branches are priced from the live code rather than described, because the cheap answer
("scope the hash so nothing moves") and the honest answer ("a registry that gained a domain
says so") differ in exactly one place: whether a fingerprint is allowed to cover less than
the thing it fingerprints.

    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22a_w2.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22a_w2.py --check
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from cognitive_os.domain.descriptors import validate_domain_package  # noqa: E402
from cognitive_os.domains import registry  # noqa: E402
from cognitive_os.domains.mechanics import MECHANICS_KERNELS  # noqa: E402

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22a-w2-decisions.json"
CONTRACTS = EVIDENCE / "sprint-22a-contracts.json"
PACKAGE = REPO / "docs/sprints/sprint-22/packages/engineering.mechanics.v1.json"

SEALED_RELEASED_SNAPSHOT = "00187f2bc6e0015529de8388ea33a1e6287939ca4d393875400bc68320997119"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _call_sites(name: str) -> dict[str, list[str]]:
    """Every first-party `<something>.<name>` call site, with the receiver kept.

    Counted from the AST rather than grepped, and the receiver expression is carried
    through because that is the only thing separating four registries that all publish a
    method called `snapshot_hash`. `receiver` is what a reader needs to judge the finding
    below, and dropping it would reproduce the very confusion the finding is about.
    """
    found: dict[str, list[str]] = {}
    for path in sorted((REPO / "src").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the tree is first-party and parses
            continue
        hits = sorted(
            {
                f"{ast.unparse(node.value)}.{name} (line {node.lineno})"
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute) and node.attr == name
            }
        )
        if hits:
            found[str(path.relative_to(REPO))] = hits
    return found


def _imports_domains_registry() -> set[str]:
    """First-party modules that import the *domain* problem-type registry.

    A bare `from .registry import ...` is only this registry when the importing module sits
    inside `cognitive_os/domains/`; the same line inside `verification/` or `tools/` names a
    different registry entirely, which is exactly how the premise below went wrong.
    """
    package = "src/cognitive_os/domains/"
    importers: set[str] = set()
    for path in sorted((REPO / "src").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the tree is first-party and parses
            continue
        relative = str(path.relative_to(REPO))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = {alias.name for alias in node.names}
                absolute = module == "cognitive_os.domains.registry"
                sibling = node.level > 0 and module == "registry" and relative.startswith(package)
                through_package = (
                    module == "cognitive_os.domains" or (node.level > 0 and module is None)
                ) and "registry" in names
                if absolute or sibling or through_package:
                    importers.add(relative)
            elif isinstance(node, ast.Import):
                if any(alias.name == "cognitive_os.domains.registry" for alias in node.names):
                    importers.add(relative)
    return importers


def _measure() -> dict[str, Any]:
    """Register the pilot in this process and watch both hashes, rather than assert them."""
    before_released = registry.released_snapshot_hash()
    before_all = registry.snapshot_hash()
    descriptor = validate_domain_package(PACKAGE.read_bytes())
    registry.register_descriptor_domain(descriptor, MECHANICS_KERNELS)
    return {
        "released_before": before_released,
        "released_after": registry.released_snapshot_hash(),
        "whole_before": before_all,
        "whole_after": registry.snapshot_hash(),
        "entries_after": len(registry.entries()),
        "domain_ids_after": list(registry.domain_ids()),
    }


def _decision(measured: dict[str, Any]) -> dict[str, Any]:
    call_sites = _call_sites("snapshot_hash")
    importers = _imports_domains_registry()
    # A module can only be calling *this* registry's snapshot if it imported it, and only
    # through a receiver that is that registry. Both conditions are computed rather than
    # asserted, because the finding below is precisely that the obvious answer was wrong.
    with_module_receiver = {
        path: [site for site in sites if site.startswith("registry.")]
        for path, sites in call_sites.items()
        if path in importers and not path.endswith("domains/registry.py")
    }
    domain_registry_callers = {path: sites for path, sites in with_module_receiver.items() if sites}
    body = {
        "item": "S22A-030",
        "question": (
            "may registering a descriptor domain change registry.snapshot_hash(), or does "
            "the snapshot become per-domain scoped?"
        ),
        "decision": (
            "both, and they are two different questions wearing one name. snapshot_hash() "
            "covers the whole resolution surface and therefore changes when the registry "
            "gains a domain; released_snapshot_hash() covers exactly the four released "
            "domains and no registration can move it. The sealed compat value re-binds to "
            "the second, which is the claim it always made"
        ),
        "reasoning": (
            "a fingerprint that omits part of the table it fingerprints lets two different "
            "resolution surfaces share one hash. That is the failure the hash exists to "
            "prevent, so scoping the released claim is right and scoping the general hash "
            "is not"
        ),
        "re_binding": {
            "rule": (
                "W4-F1: an authorised change re-binds rather than edits. The W0 contract's "
                "`registry_snapshot_hash` value is unchanged here; what changed is the "
                "function that reproduces it, from snapshot_hash() to released_snapshot_hash()"
            ),
            "sealed_value": SEALED_RELEASED_SNAPSHOT,
            "sealed_in": CONTRACTS.name,
            "sealed_in_sha256": _sha256(CONTRACTS.read_bytes()),
            "reproduced_by": "cognitive_os.domains.registry.released_snapshot_hash",
            "reproduces": measured["released_after"] == SEALED_RELEASED_SNAPSHOT,
        },
        "measured": measured,
        "branches_priced": {
            "scope_the_hash_so_nothing_moves": {
                "cost": (
                    "one hash for two surfaces. A process holding a pilot and a process "
                    "holding none would report the same fingerprint, and any later record "
                    "binding that hash would be unfalsifiable"
                ),
                "taken": False,
            },
            "let_the_registry_say_it_gained_a_domain": {
                "cost": (
                    "the sealed compat claim needs a function that means exactly it, which "
                    "is `released_snapshot_hash`. Twelve lines, one re-binding, no released "
                    "value moved"
                ),
                "taken": True,
            },
        },
        "premise_corrected": {
            "finding": "W2-F1",
            "the_handoff_said": (
                "registering a pilot would change a hash 'bound into released "
                "semantic-memory records'"
            ),
            "what_is_true": (
                "the snapshot_hash() in semantic-memory records is the PredicateRegistry's, "
                "a different registry with a method of the same name. "
                "domains.registry.snapshot_hash() has no production caller at all"
            ),
            "domains_registry_snapshot_hash_callers_in_src": domain_registry_callers,
            "modules_importing_the_domain_registry": sorted(importers),
            "every_snapshot_hash_call_site_in_src": call_sites,
            "how_this_was_counted": (
                "AST attribute access named `snapshot_hash` with the receiver expression "
                "kept, restricted to modules that import the domain registry, and then to "
                "the receiver `registry` — the module alias this registry is used through. "
                "Several registries publish a method of this name and only the receiver "
                "tells them apart: `skill_registry.snapshot_hash` in domains/skill_runner.py "
                "is the Skill Engine's, not this one"
            ),
            "why_the_decision_still_matters": (
                "the constraint is the sprint's own sealed compat contract and the CI check "
                "that enforces it, not a released runtime binding. A pilot registered in a "
                "test session would have failed that check by test ordering alone"
            ),
        },
        "what_this_decision_does_not_change": [
            "no released domain, problem type, verifier capability or stored record",
            "no threshold, no gate condition, no migration",
            "the four sealed compat hashes, which are re-derived unchanged",
        ],
    }
    body["content_hash"] = _sha256(_canonical(body))
    return body


def _write() -> None:
    measured = _measure()
    decision = _decision(measured)
    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22A",
        "wave": "W2",
        "items": ["S22A-030"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measured_values": 0,
        "thresholds_changed": 0,
        "authority": "sprint-22a pre-registration revision 1, backward_compatibility contract",
        "decisions": {"registry_snapshot_scope": decision},
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "decision": "scoped: released_snapshot_hash is the compat claim",
                "released_snapshot_unchanged": decision["re_binding"]["reproduces"],
                "whole_snapshot_changed": measured["whole_after"] != measured["whole_before"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    record = json.loads(OUTPUT.read_text(encoding="utf-8"))
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != record["integrity_content_hash"]:
        raise SystemExit(f"{OUTPUT.name} integrity hash does not match its content")
    decision = record["decisions"]["registry_snapshot_scope"]
    stated = {key: value for key, value in decision.items() if key != "content_hash"}
    if _sha256(_canonical(stated)) != decision["content_hash"]:
        raise SystemExit("the S22A-030 decision body no longer hashes to its recorded value")
    if decision["re_binding"]["sealed_in_sha256"] != _sha256(CONTRACTS.read_bytes()):
        raise SystemExit("the contract this decision re-binds against has changed")
    # The decision's whole point, re-measured: admitting the pilot moves one hash and not
    # the other. Asserting it from the record would only prove the record was not edited.
    measured = _measure()
    if measured["released_after"] != SEALED_RELEASED_SNAPSHOT:
        raise SystemExit("registering the pilot moved the released snapshot hash")
    if measured["whole_after"] == measured["whole_before"]:
        raise SystemExit("the whole-registry snapshot did not notice a domain being added")
    print(
        json.dumps(
            {
                "checked": OUTPUT.name,
                "released_snapshot_unchanged_after_registration": True,
                "whole_snapshot_changed_after_registration": True,
                "entries_after": measured["entries_after"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    _check() if arguments.check else _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
