"""Frozen host-owned predicate registry."""

import json
from hashlib import sha256

from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.semantic_memory import (
    Cardinality,
    PredicateDescriptor,
    SemanticLiteralKind,
)


class PredicateRegistry:
    def __init__(self) -> None:
        self._descriptors: dict[tuple[str, str], PredicateDescriptor] = {}
        self._frozen = False

    def register(self, descriptor: PredicateDescriptor) -> None:
        if self._frozen:
            raise ValueError("predicate registry is frozen")
        key = (descriptor.predicate_id, descriptor.version)
        if key in self._descriptors:
            raise ValueError("duplicate predicate ID and version")
        self._descriptors[key] = descriptor

    def freeze(self) -> None:
        self._frozen = True

    def require(self, predicate_id: str, version: str = "1") -> PredicateDescriptor:
        try:
            return self._descriptors[(predicate_id, version)]
        except KeyError as error:
            raise ValueError(f"unknown predicate: {predicate_id}@{version}") from error

    def list_all(self) -> tuple[PredicateDescriptor, ...]:
        return tuple(self._descriptors[key] for key in sorted(self._descriptors))

    def snapshot_hash(self) -> str:
        payload = [item.model_dump(mode="json") for item in self.list_all()]
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def build_default_predicate_registry() -> PredicateRegistry:
    registry = PredicateRegistry()
    definitions = (
        ("project.uses_language", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("project.python_version", SemanticLiteralKind.VERSION, Cardinality.FUNCTIONAL),
        ("project.test_framework", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("project.linter", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("project.type_checker", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("repository.base_commit", SemanticLiteralKind.STRING, Cardinality.FUNCTIONAL),
        ("repository.supported_profile", SemanticLiteralKind.STRING, Cardinality.FUNCTIONAL),
        ("task.outcome", SemanticLiteralKind.STRING, Cardinality.FUNCTIONAL),
        ("task.acceptance_status", SemanticLiteralKind.STRING, Cardinality.FUNCTIONAL),
        ("task.changed_file", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("verification.result", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("user.instruction", SemanticLiteralKind.STRING, Cardinality.MULTI),
        ("memory.correction", SemanticLiteralKind.STRING, Cardinality.MULTI),
    )
    for predicate_id, object_type, cardinality in definitions:
        registry.register(
            PredicateDescriptor(
                predicate_id=predicate_id,
                version="1",
                display_name=predicate_id.replace(".", " ").replace("_", " ").title(),
                description=f"Host-defined predicate for {predicate_id}.",
                allowed_subject_types=(predicate_id.split(".", 1)[0],),
                allowed_object_types=(object_type,),
                cardinality=cardinality,
                temporal_behavior="bitemporal",
                default_sensitivity=MemorySensitivity.INTERNAL,
                rendering_label=predicate_id,
                contradiction_rule="functional_overlap"
                if cardinality is Cardinality.FUNCTIONAL
                else None,
            )
        )
    registry.freeze()
    return registry
