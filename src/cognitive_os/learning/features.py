"""The one situation encoding, used identically by every surface and every tier.

Gate L condition 3 asks for a single encoding serving several domains. Keeping it in one
module is how that stays true: the ladder, the kNN component, and the tests all import
this, so a feature added for one of them is added for all of them.

Prohibited features are declared rather than assumed. No problem text, no answer value,
no credential, no artifact body reaches a feature vector — only the structural facts a
decision could legitimately be made from before the run happens.
"""

from __future__ import annotations

from hashlib import sha256

from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.domain.learned import FeatureSchema, SituationVector
from cognitive_os.domains.fixtures import FIXTURE_TIME

from .selfplay import SURFACE, SkillCandidate

ENCODING_VERSION = "situation-v1"

#: Named so the schema's own validator can refuse them if anyone adds one later.
PROHIBITED_FEATURES = (
    "answer_value",
    "artifact_body",
    "credential",
    "problem_statement",
    "prompt_body",
)

CATEGORICAL_NAMES = (
    "candidate",
    "declared_capability",
    "problem_domain",
    "problem_type",
)


def feature_schema() -> FeatureSchema:
    return FeatureSchema(
        feature_schema_id="skill-selection-v1",
        version=1,
        surface=SURFACE,
        encoding_version=ENCODING_VERSION,
        categorical_names=CATEGORICAL_NAMES,
        prohibited_features=PROHIBITED_FEATURES,
        missing_value_policy="absent categorical features are encoded as the literal 'none'",
        created_at=FIXTURE_TIME,
    )


def _task_signature_hash(case: DomainBenchmarkCase, candidate: SkillCandidate) -> str:
    return sha256(
        f"{case.domain.value}:{case.problem_type}:{candidate.canonical_name}".encode()
    ).hexdigest()


def encode(case: DomainBenchmarkCase, candidate: SkillCandidate) -> SituationVector:
    """Encode one (case, candidate) decision situation.

    `declared_capability` is what the candidate package claims it will verify. It is a
    property of the candidate, not of the outcome, so it is available before the run and
    is not leakage — which is exactly why a deterministic rule can already use it.
    """
    return SituationVector(
        encoding_version=ENCODING_VERSION,
        surface=SURFACE,
        task_signature_hash=_task_signature_hash(case, candidate),
        problem_domain=case.domain.value,
        categorical_features=(
            ("candidate", candidate.canonical_name),
            ("declared_capability", "|".join(candidate.declared_capabilities) or "none"),
            ("problem_domain", case.domain.value),
            ("problem_type", case.problem_type),
        ),
        prohibited_feature_check=True,
    )


def categorical_pairs(vector: SituationVector) -> frozenset[tuple[str, str]]:
    return frozenset(vector.categorical_features)
