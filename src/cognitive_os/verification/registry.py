"""Explicit, deterministic, freezeable Verifier Registry."""

from __future__ import annotations

import json
from hashlib import sha256

import jsonschema

from cognitive_os.application.ports.verifier import VerifierPort
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verifiers import VerificationSubjectType, VerifierDescriptor, VerifierKind

from .errors import VerifierNotFoundError, VerifierRegistrationError, VerifierUnavailableError


class VerifierRegistry:
    def __init__(self) -> None:
        self._verifiers: dict[tuple[str, str], VerifierPort] = {}
        self._unavailable: dict[tuple[str, str], tuple[VerifierDescriptor, str]] = {}
        self._frozen = False

    def register(self, verifier: VerifierPort) -> None:
        if self._frozen:
            raise VerifierRegistrationError("verifier registry is frozen")
        descriptor = verifier.descriptor
        key = (descriptor.verifier_id, descriptor.version)
        if key in self._verifiers or key in self._unavailable:
            raise VerifierRegistrationError(
                f"duplicate verifier registration: {descriptor.verifier_id}@{descriptor.version}"
            )
        if descriptor.descriptor_hash != descriptor.computed_hash():
            raise VerifierRegistrationError("verifier descriptor hash is invalid")
        try:
            jsonschema.Draft202012Validator.check_schema(descriptor.configuration_schema)
        except jsonschema.SchemaError as error:
            raise VerifierRegistrationError("verifier configuration schema is invalid") from error
        self._verifiers[key] = verifier

    def register_unavailable(self, descriptor: VerifierDescriptor, reason: str) -> None:
        if self._frozen:
            raise VerifierRegistrationError("verifier registry is frozen")
        key = (descriptor.verifier_id, descriptor.version)
        if key in self._verifiers or key in self._unavailable:
            raise VerifierRegistrationError(
                f"duplicate verifier registration: {descriptor.verifier_id}@{descriptor.version}"
            )
        self._unavailable[key] = (descriptor, reason)

    def register_many(self, verifiers: tuple[VerifierPort, ...]) -> None:
        for verifier in verifiers:
            self.register(verifier)

    def get(self, verifier_id: str, version: str) -> VerifierPort | None:
        return self._verifiers.get((verifier_id, version))

    def require(self, verifier_id: str, version: str) -> VerifierPort:
        key = (verifier_id, version)
        if key in self._unavailable:
            raise VerifierUnavailableError(f"verifier is unavailable: {verifier_id}@{version}")
        verifier = self._verifiers.get(key)
        if verifier is None:
            raise VerifierNotFoundError(f"verifier is not registered: {verifier_id}@{version}")
        return verifier

    def list_all(self) -> tuple[VerifierDescriptor, ...]:
        descriptors = [item.descriptor for item in self._verifiers.values()]
        descriptors.extend(item[0] for item in self._unavailable.values())
        return tuple(sorted(descriptors, key=lambda item: (item.verifier_id, item.version)))

    def list_available(self) -> tuple[VerifierDescriptor, ...]:
        return tuple(
            sorted(
                (item.descriptor for item in self._verifiers.values()),
                key=lambda item: (item.verifier_id, item.version),
            )
        )

    def list_by_kind(self, kind: VerifierKind) -> tuple[VerifierDescriptor, ...]:
        return tuple(item for item in self.list_all() if item.kind is kind)

    def list_by_domain(self, domain: ProblemDomain) -> tuple[VerifierDescriptor, ...]:
        return tuple(
            item
            for item in self.list_all()
            if any(domain in capability.problem_domains for capability in item.capabilities)
        )

    def list_capable(
        self,
        subject_type: VerificationSubjectType,
        domain: ProblemDomain,
        criterion_type: CriterionType,
    ) -> tuple[VerifierDescriptor, ...]:
        return tuple(
            item
            for item in self.list_available()
            if any(
                capability.subject_type is subject_type
                and domain in capability.problem_domains
                and criterion_type in capability.criterion_types
                for capability in item.capabilities
            )
        )

    def freeze(self) -> None:
        self._frozen = True

    def snapshot(self) -> str:
        records = []
        for descriptor in self.list_all():
            key = (descriptor.verifier_id, descriptor.version)
            records.append(
                {
                    "verifier_id": descriptor.verifier_id,
                    "version": descriptor.version,
                    "descriptor_hash": descriptor.descriptor_hash,
                    "available": key in self._verifiers,
                    "capabilities": [
                        item.model_dump(mode="json") for item in descriptor.capabilities
                    ],
                    "determinism": descriptor.determinism.value,
                }
            )
        return sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
