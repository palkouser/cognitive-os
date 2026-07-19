"""Explicit construction of built-in verifiers with safe optional availability."""

from __future__ import annotations

from importlib.util import find_spec

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.domain.enums import RiskLevel
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verifiers import (
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)
from cognitive_os.verification.coding import (
    DependencyPolicyVerifier,
    DiffPolicyVerifier,
    FilePolicyVerifier,
    ImportVerifier,
    MypyVerifier,
    PytestVerifier,
    RuffVerifier,
    WorkspaceIntegrityVerifier,
)
from cognitive_os.verification.generic import (
    ArtifactIntegrityVerifier,
    ExactValueVerifier,
    JsonSchemaVerifier,
    PlanConsistencyVerifier,
    StepCompletedVerifier,
    ToolSucceededVerifier,
)
from cognitive_os.verification.mathematics import NumericVerifier
from cognitive_os.verification.semantic import SEMANTIC_CAPABILITIES, SemanticInvariantVerifier
from cognitive_os.verification.skills import build_skill_verifiers
from cognitive_os.verification.strategies import build_strategy_verifiers

from .registry import VerifierRegistry


def _optional_descriptor(
    verifier_id: str,
    kind: VerifierKind,
    domain: ProblemDomain,
    subject_type: VerificationSubjectType,
) -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=verifier_id,
        version="1",
        display_name=verifier_id.replace(".", " ").title(),
        description="Optional deterministic domain verifier.",
        kind=kind,
        capabilities=(
            VerifierCapability(
                capability_id=f"{verifier_id}.v1",
                subject_type=subject_type,
                problem_domains=(domain,),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
            ),
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=10,
        maximum_input_bytes=262_144,
        configuration_schema={"type": "object"},
    )


def build_builtin_registry(
    *,
    artifacts: ArtifactStorePort | None = None,
    tool_execution: ToolExecutionService | None = None,
) -> VerifierRegistry:
    registry = VerifierRegistry()
    registry.register_many(
        (
            JsonSchemaVerifier(),
            ExactValueVerifier(),
            StepCompletedVerifier(),
            ToolSucceededVerifier(),
            PlanConsistencyVerifier(),
            NumericVerifier(),
            FilePolicyVerifier(),
            DiffPolicyVerifier(),
            DependencyPolicyVerifier(),
            WorkspaceIntegrityVerifier(),
            *(SemanticInvariantVerifier(item) for item in SEMANTIC_CAPABILITIES),
            *build_skill_verifiers(),
            *build_strategy_verifiers(),
        )
    )
    if artifacts is not None:
        registry.register(ArtifactIntegrityVerifier(artifacts))
    else:
        registry.register_unavailable(
            _optional_descriptor(
                "generic.artifact_integrity",
                VerifierKind.GENERIC,
                ProblemDomain.GENERIC,
                VerificationSubjectType.ARTIFACT,
            ),
            "artifact store is not configured",
        )
    if tool_execution is not None:
        registry.register_many(
            (
                PytestVerifier(tool_execution),
                RuffVerifier(tool_execution),
                MypyVerifier(tool_execution),
                ImportVerifier(tool_execution),
            )
        )
    else:
        for verifier_id in ("coding.pytest", "coding.ruff", "coding.mypy", "coding.import"):
            registry.register_unavailable(
                _optional_descriptor(
                    verifier_id,
                    VerifierKind.CODING,
                    ProblemDomain.CODING,
                    VerificationSubjectType.WORKSPACE,
                ),
                "Tool Execution Service and rootless sandbox are not configured",
            )
    if find_spec("sympy") is not None:
        from .mathematics import EquationSolutionVerifier, SymbolicEquivalenceVerifier

        registry.register_many((SymbolicEquivalenceVerifier(), EquationSolutionVerifier()))
    else:
        for verifier_id in ("mathematics.symbolic_equivalence", "mathematics.equation_solution"):
            registry.register_unavailable(
                _optional_descriptor(
                    verifier_id,
                    VerifierKind.MATHEMATICS,
                    ProblemDomain.MATHEMATICS,
                    VerificationSubjectType.MATHEMATICAL_EXPRESSION,
                ),
                "install the verification-math extra",
            )
    if find_spec("z3") is not None:
        from .logic import (
            ContradictionVerifier,
            EquivalenceVerifier,
            ImplicationVerifier,
            SatisfiabilityVerifier,
        )

        registry.register_many(
            (
                SatisfiabilityVerifier(),
                ContradictionVerifier(),
                ImplicationVerifier(),
                EquivalenceVerifier(),
            )
        )
    else:
        for verifier_id in (
            "logic.satisfiable",
            "logic.contradiction",
            "logic.implication",
            "logic.equivalence",
        ):
            registry.register_unavailable(
                _optional_descriptor(
                    verifier_id,
                    VerifierKind.LOGIC,
                    ProblemDomain.LOGIC,
                    VerificationSubjectType.LOGICAL_PROBLEM,
                ),
                "install the verification-logic extra",
            )
    if find_spec("pint") is not None:
        from .physics import DimensionVerifier, QuantityVerifier, UnitConversionVerifier

        registry.register_many((DimensionVerifier(), QuantityVerifier(), UnitConversionVerifier()))
    else:
        for verifier_id in ("physics.dimension", "physics.quantity", "physics.unit_conversion"):
            registry.register_unavailable(
                _optional_descriptor(
                    verifier_id,
                    VerifierKind.PHYSICS,
                    ProblemDomain.PHYSICS,
                    VerificationSubjectType.PHYSICAL_QUANTITY,
                ),
                "install the verification-physics extra",
            )
    return registry
