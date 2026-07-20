"""Independent checks for Experience Compiler outputs."""

from cognitive_os.domain.experience import ExperienceCandidateStatus, TrajectoryCompleteness
from cognitive_os.experience.compiler import MANDATORY_CAPABILITIES, ExperienceCompilationResult


def verify_compilation(result: ExperienceCompilationResult) -> tuple[str, ...]:
    failures: list[str] = []
    capabilities = tuple(item.capability for item in result.verifier_bundle.results)
    if capabilities != MANDATORY_CAPABILITIES:
        failures.append("mandatory verifier registry mismatch")
    if (
        result.trajectory.completeness
        in {
            TrajectoryCompleteness.INCOMPLETE,
            TrajectoryCompleteness.CONFLICTED,
            TrajectoryCompleteness.INVALID,
        }
        and result.verifier_bundle.passed
    ):
        failures.append("incomplete trajectory passed compiler verification")
    if any(item.status is not ExperienceCandidateStatus.PROPOSED for item in result.candidates):
        failures.append("compiler assigned destination authority to a candidate")
    if result.manifest.candidate_hashes != tuple(item.content_hash for item in result.candidates):
        failures.append("manifest candidate hashes differ")
    origin = result.analysis.first_incorrect_step.causal_origin
    if origin.causal_claim_supported and not origin.evidence_refs:
        failures.append("unsupported causal claim")
    return tuple(failures)
