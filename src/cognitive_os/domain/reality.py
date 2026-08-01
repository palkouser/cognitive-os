"""Contracts for the Sprint 21C3 reality-grade input corpus.

Everything here is a *reference* contract. Task repositories, patch bytes, hidden control
bundles and coding outcomes live in the Artifact Store; lifecycle and outcome identity live
in the Event Store; corpus items live in the Corpus Factory's own tables. These models carry
identities and hashes so those authorities stay single, and so a manifest cannot drift away
from the bytes it describes.

The one structural rule worth stating twice: a task manifest knows the answer and a provider
must not. `RealityTaskManifest` holds the hidden bundle hash, the control-material hash and
the declared baseline reason. `RealityTaskProjection` — the only thing a provider, feature
builder, embedding input or selector ever sees — is a *separate model* with no field capable
of holding any of them. Filtering a dict is a rule someone can forget to apply; a type that
has no such field is a rule the compiler applies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .coding import CodingOutcomeStatus, RelativeRepositoryPath
from .common import NonEmptyStr, Sha256Hex, UtcDatetime
from .corpus import CorpusSplit
from .experience import HashedExperienceContract
from .memory import MemorySensitivity


class RealityTaskFamily(StrEnum):
    """The six families of §3.1.

    Fixed for C3: the split policy assigns whole families, so adding a seventh silently
    would move a split.
    """

    BOUNDARY_COLLECTIONS = "boundary_collections"
    PARSING_VALIDATION = "parsing_validation"
    STATE_IDEMPOTENCY = "state_idempotency"
    NUMERIC_LOGIC = "numeric_logic"
    ERROR_HANDLING = "error_handling"
    DATA_TRANSFORMATION = "data_transformation"


class RealityTaskDifficulty(StrEnum):
    SINGLE_EDIT = "single_edit"
    MULTI_EDIT = "multi_edit"
    CROSS_MODULE = "cross_module"


class RealityCandidateStrategy(StrEnum):
    """The four offline strategies of §4.6, plus what a provider returns.

    `PROVIDER_PROPOSED` deliberately has no declared correctness. A provider candidate's
    result is whatever the hidden verifier says it is, and a strategy value that predicted
    it would be a label the corpus had assigned to itself.

    The four `RECIPE_*` values are Sprint 21D2's, and they exist because the C3 four are a
    measured perfect oracle: on all 120 D1 correction-ranking examples `correct_*` passed and
    `incomplete_*` failed, without exception. A ranking surface fitted on a corpus whose
    recipe name determines the label learns the name. So D2 generates its candidates under
    outcome-neutral recipes whose family is `UNDECLARED`, which means the corpus makes no
    claim about them and a hidden-verifier result that contradicts the generator's intent is
    a valid label rather than a corpus defect.
    """

    INCOMPLETE_A = "incomplete_a"
    CORRECT_NARROW = "correct_narrow"
    INCOMPLETE_B = "incomplete_b"
    CORRECT_ROBUST = "correct_robust"
    PROVIDER_PROPOSED = "provider_proposed"
    RECIPE_ALPHA = "recipe_alpha"
    RECIPE_BETA = "recipe_beta"
    RECIPE_GAMMA = "recipe_gamma"
    RECIPE_DELTA = "recipe_delta"

    @property
    def family(self) -> RealityStrategyFamily:
        if self in _INCORRECT_STRATEGIES:
            return RealityStrategyFamily.INCORRECT
        if self in _CORRECT_STRATEGIES:
            return RealityStrategyFamily.CORRECT
        return RealityStrategyFamily.UNDECLARED


class RealityStrategyFamily(StrEnum):
    INCORRECT = "incorrect"
    CORRECT = "correct"
    UNDECLARED = "undeclared"


_INCORRECT_STRATEGIES = frozenset(
    {RealityCandidateStrategy.INCOMPLETE_A, RealityCandidateStrategy.INCOMPLETE_B}
)
_CORRECT_STRATEGIES = frozenset(
    {RealityCandidateStrategy.CORRECT_NARROW, RealityCandidateStrategy.CORRECT_ROBUST}
)

#: The recipes a Sprint 21D2 campaign may generate under. Membership is what the D2 campaign
#: protocol checks; the enum stays open so C3 evidence keeps validating under its own rules.
D2_NEUTRAL_RECIPES: frozenset[RealityCandidateStrategy] = frozenset(
    {
        RealityCandidateStrategy.RECIPE_ALPHA,
        RealityCandidateStrategy.RECIPE_BETA,
        RealityCandidateStrategy.RECIPE_GAMMA,
        RealityCandidateStrategy.RECIPE_DELTA,
    }
)

#: The label-predicting family. A D2 campaign that names one of these is refused: the point
#: of the neutral recipes is lost the moment the corpus can answer its own question.
LABEL_PREDICTING_STRATEGIES: frozenset[RealityCandidateStrategy] = (
    _INCORRECT_STRATEGIES | _CORRECT_STRATEGIES
)


class RealityCandidateSource(StrEnum):
    """Who produced the patch. Not who decided whether it works — that is the verifier."""

    BASELINE = "baseline"
    CURATED = "curated"
    CODEX_CLI = "codex_cli"
    CLAUDE_CODE = "claude_code"
    OPENROUTER = "openrouter"


#: Sources that reached a network or an external CLI. Everything here must be executed with
#: an inlined, hash-pinned projection and must never receive a control-bundle reference.
PROVIDER_CANDIDATE_SOURCES: frozenset[RealityCandidateSource] = frozenset(
    {
        RealityCandidateSource.CODEX_CLI,
        RealityCandidateSource.CLAUDE_CODE,
        RealityCandidateSource.OPENROUTER,
    }
)


class RealityBaselineExpectation(StrEnum):
    """What the untouched repository must do before any candidate runs.

    Only one value is valid for a C3 task. It is an enum rather than a boolean because
    `expected_baseline_status=False` reads as "we expect no baseline status", and the field
    exists precisely so that a task whose baseline unexpectedly passes is rejected.
    """

    HIDDEN_VERIFICATION_FAILS = "hidden_verification_fails"


class RealityRunKind(StrEnum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"


class RealityOutcomeCountReason(StrEnum):
    """Why a recorded execution did or did not add to the denominator."""

    COUNTED = "counted"
    DUPLICATE_EVENT_ID = "duplicate_event_id"
    DUPLICATE_TASK_RUN_ID = "duplicate_task_run_id"
    DUPLICATE_OUTCOME_HASH = "duplicate_outcome_hash"
    IDEMPOTENT_REPLAY = "idempotent_replay"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class RealitySourceRights(HashedExperienceContract):
    """Redistribution evidence for one task's source material.

    `rights_verified` stays an operator input with an evidence hash. ADR 0088 classifies
    open-development data as `public`; it explicitly does not let that classification answer
    the redistribution question, so this contract refuses to derive one from the other.
    """

    source_identity: NonEmptyStr
    licence_identifier: NonEmptyStr
    rights_verified: bool
    rights_evidence_hash: Sha256Hex
    attribution: NonEmptyStr
    sensitivity: MemorySensitivity


class RealityContentEntry(HashedExperienceContract):
    """One file a provider is allowed to see, pinned by hash.

    The file's own digest is `file_hash`; `content_hash` is the sealed hash of this contract,
    inherited from `HashedExperienceContract`. Naming the file digest `content_hash` would
    silently override the seal, which is how the corpus `SourceFileEntry` arrived at the same
    two names.
    """

    path: RelativeRepositoryPath
    size_bytes: int = Field(ge=0)
    file_hash: Sha256Hex


class RealityTaskProjection(HashedExperienceContract):
    """The provider-visible face of a task. Structurally incapable of leaking the answer.

    There is no hidden path, hidden test name, golden patch, solution hash, expected
    candidate ID or control rationale field on this model, and `extra="forbid"` means one
    cannot be added at runtime. This is the only task shape that may reach a provider
    request, a candidate feature row, an embedding input or a selection input before scoring.
    """

    task_id: UUID
    task_family: RealityTaskFamily
    difficulty: RealityTaskDifficulty
    issue_description: NonEmptyStr
    expected_behavior: NonEmptyStr
    visible_test_command: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1, max_length=16)]
    allowed_paths: tuple[RelativeRepositoryPath, ...] = ()
    forbidden_paths: tuple[RelativeRepositoryPath, ...] = ()
    files: Annotated[tuple[RealityContentEntry, ...], Field(min_length=1, max_length=256)]

    @model_validator(mode="after")
    def files_are_sorted_and_unique(self) -> RealityTaskProjection:
        paths = [item.path for item in self.files]
        if paths != sorted(paths):
            raise ValueError("provider-visible files must be sorted")
        if len(paths) != len(set(paths)):
            raise ValueError("provider-visible files must be unique")
        return self


class RealityTaskManifest(HashedExperienceContract):
    """The full task package, including everything a provider may not see.

    Held by the generator, the verifier and the campaign. Never serialized into a provider
    request: `projection` is what goes out.
    """

    task_id: UUID
    manifest_version: int = Field(default=1, ge=1)
    domain: NonEmptyStr = "coding"
    task_family: RealityTaskFamily
    repository_group: NonEmptyStr
    difficulty: RealityTaskDifficulty
    generator_profile_id: NonEmptyStr
    generator_profile_version: int = Field(ge=1)
    generation_seed: int = Field(ge=0)
    projection: RealityTaskProjection
    base_repository_manifest_hash: Sha256Hex
    hidden_verifier_bundle_artifact_id: UUID
    hidden_verifier_bundle_hash: Sha256Hex
    control_material_manifest_hash: Sha256Hex
    expected_baseline: RealityBaselineExpectation = (
        RealityBaselineExpectation.HIDDEN_VERIFICATION_FAILS
    )
    baseline_failure_reason: NonEmptyStr
    required_verifier_ids: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1, max_length=32)]
    rights: RealitySourceRights
    created_at: UtcDatetime

    @field_validator("required_verifier_ids")
    @classmethod
    def verifier_ids_are_sorted_and_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if list(value) != sorted(set(value)):
            raise ValueError("required verifier IDs must be sorted and unique")
        return value

    @model_validator(mode="after")
    def projection_belongs_to_this_task(self) -> RealityTaskManifest:
        if self.projection.task_id != self.task_id:
            raise ValueError("provider-visible projection belongs to a different task")
        if self.projection.task_family is not self.task_family:
            raise ValueError("provider-visible projection declares a different task family")
        return self

    @model_validator(mode="after")
    def control_material_is_distinct_from_visible_content(self) -> RealityTaskManifest:
        """A control bundle equal to a visible file is not a hidden test.

        Cheap, but it catches the generator bug that matters: writing the hidden bundle into
        the workspace instead of beside it.
        """
        visible = {item.file_hash for item in self.projection.files}
        if self.hidden_verifier_bundle_hash in visible:
            raise ValueError("the hidden verifier bundle is present in provider-visible content")
        if self.control_material_manifest_hash in visible:
            raise ValueError("control material is present in provider-visible content")
        return self


class RealityCandidateManifest(HashedExperienceContract):
    """One proposed repair, bound to its task and its patch bytes.

    Carries no expected result. `strategy` says what the generator was *trying* to produce;
    whether it succeeded is the hidden verifier's answer and lives in the outcome, so a
    selector reading candidates cannot read the label off them.
    """

    candidate_id: UUID
    task_id: UUID
    task_manifest_hash: Sha256Hex
    strategy: RealityCandidateStrategy
    source: RealityCandidateSource
    patch_artifact_id: UUID
    patch_hash: Sha256Hex
    generator_profile_id: NonEmptyStr
    generator_profile_version: int = Field(ge=1)
    provider_id: NonEmptyStr | None = None
    resolved_model: NonEmptyStr | None = None
    provider_output_id: UUID | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def provider_identity_matches_source(self) -> RealityCandidateManifest:
        is_provider = self.source in PROVIDER_CANDIDATE_SOURCES
        if is_provider and self.provider_id is None:
            raise ValueError("a provider candidate must name the provider that produced it")
        if not is_provider and (self.provider_id or self.resolved_model or self.provider_output_id):
            raise ValueError("an offline candidate cannot carry provider identity")
        if is_provider and self.strategy is not RealityCandidateStrategy.PROVIDER_PROPOSED:
            raise ValueError("a provider candidate cannot declare an offline strategy")
        if not is_provider and self.strategy is RealityCandidateStrategy.PROVIDER_PROPOSED:
            raise ValueError("an offline candidate must declare one of the four strategies")
        return self


def validate_recorded_run_invariants(
    *,
    run_kind: RealityRunKind,
    candidate_id: UUID | None,
    strategy: RealityCandidateStrategy | None,
    hidden_verification_passed: bool,
) -> None:
    """The invariants `CodingOutcomeRecorded` and `RealityOutcomeReference` both depend on.

    S21D2-021. `CodingOutcomeRecorder.record()` used to append the authoritative event and
    only then build the reference, so a reference validator that refused left the event
    durably appended with nothing able to resolve it — a partial authority, which is the one
    outcome the recording order exists to prevent. The rules are the same rules; they simply
    have to be checkable before the append rather than after it.

    Raises `ValueError`, so the model validators below can delegate and keep their behaviour.
    """
    if run_kind is RealityRunKind.BASELINE:
        if candidate_id is not None or strategy is not None:
            raise ValueError("a baseline run has no candidate")
        if hidden_verification_passed:
            raise ValueError(
                "a baseline whose hidden verification passed is not a repair task; "
                "reject or revise the task instead of recording it"
            )
    elif candidate_id is None or strategy is None:
        raise ValueError("a candidate run must name its candidate and strategy")

    if strategy is None:
        return
    #: §4.6, enforced where the result is known. A `correct_*` candidate that failed, or an
    #: `incomplete_*` one that passed, means the generator and the verifier disagree about the
    #: task: a corpus defect rather than an outcome to count. The D2 `RECIPE_*` values are
    #: `UNDECLARED` and fall through untouched, which is exactly the point of them — a D2
    #: outcome that contradicts its generator's intent is a label, not a defect.
    family = strategy.family
    if family is RealityStrategyFamily.CORRECT and not hidden_verification_passed:
        raise ValueError(
            f"candidate strategy {strategy.value!r} is declared correct but failed "
            "hidden verification"
        )
    if family is RealityStrategyFamily.INCORRECT and hidden_verification_passed:
        raise ValueError(
            f"candidate strategy {strategy.value!r} is declared incomplete but passed "
            "hidden verification"
        )


class RealityOutcomeReference(HashedExperienceContract):
    """One executed run, resolvable to bytes and to an event.

    This is the unit the 200-outcome threshold counts. Every field that identifies it is
    required, because a reference that cannot be resolved is a label, and the whole point of
    C3 is that labels are not outcomes.
    """

    task_run_id: UUID
    run_kind: RealityRunKind
    task_id: UUID
    task_manifest_hash: Sha256Hex
    candidate_id: UUID | None = None
    strategy: RealityCandidateStrategy | None = None
    outcome_hash: Sha256Hex
    outcome_artifact_id: UUID
    outcome_artifact_hash: Sha256Hex
    hidden_evidence_artifact_id: UUID
    hidden_evidence_hash: Sha256Hex
    final_status: CodingOutcomeStatus
    hidden_verification_passed: bool
    provider_output_id: UUID | None = None
    source_event_id: UUID
    occurred_at: UtcDatetime

    @model_validator(mode="after")
    def run_invariants_hold(self) -> RealityOutcomeReference:
        """Delegated, so the recorder can check the same rules before it appends anything."""
        validate_recorded_run_invariants(
            run_kind=self.run_kind,
            candidate_id=self.candidate_id,
            strategy=self.strategy,
            hidden_verification_passed=self.hidden_verification_passed,
        )
        return self

    @property
    def count_identity(self) -> str:
        """What makes this outcome one outcome. Used by the campaign's denominator."""
        return f"{self.source_event_id}|{self.task_run_id}|{self.outcome_hash}"


class CorrectionTrajectoryManifest(HashedExperienceContract):
    """An ordered baseline-failure to corrected path, §4.10.

    Distinctness is the ordered source identity, not the manifest ID, so two manifests built
    from the same three runs cannot both be counted.
    """

    trajectory_id: UUID
    task_id: UUID
    incorrect_strategy: RealityCandidateStrategy
    correct_strategy: RealityCandidateStrategy
    ordered_outcome_event_ids: Annotated[tuple[UUID, ...], Field(min_length=3, max_length=8)]
    ordered_outcome_hashes: Annotated[tuple[Sha256Hex, ...], Field(min_length=3, max_length=8)]
    compilation_id: UUID | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def strategies_are_a_failure_then_a_correction(self) -> CorrectionTrajectoryManifest:
        if self.incorrect_strategy.family is not RealityStrategyFamily.INCORRECT:
            raise ValueError("a correction trajectory must start from a declared failure")
        if self.correct_strategy.family is not RealityStrategyFamily.CORRECT:
            raise ValueError("a correction trajectory must end at a declared correction")
        return self

    @model_validator(mode="after")
    def sources_line_up_and_do_not_repeat(self) -> CorrectionTrajectoryManifest:
        if len(self.ordered_outcome_event_ids) != len(self.ordered_outcome_hashes):
            raise ValueError("each trajectory step needs one event ID and one outcome hash")
        if len(set(self.ordered_outcome_event_ids)) != len(self.ordered_outcome_event_ids):
            raise ValueError("a trajectory step cannot reuse an outcome event")
        return self

    @property
    def distinct_identity(self) -> str:
        return "|".join(
            (
                str(self.task_id),
                self.incorrect_strategy.value,
                self.correct_strategy.value,
                *(str(item) for item in self.ordered_outcome_event_ids),
            )
        )


class RealityRunIdentity(HashedExperienceContract):
    """What makes a planned campaign run the same run on resume, §4.14.

    Every field that changes the executed work is in here. Resume skips an identity that has
    already produced a counted outcome; the same identity presenting different content is a
    new campaign revision, not an update.
    """

    task_id: UUID
    task_manifest_hash: Sha256Hex
    run_kind: RealityRunKind
    candidate_id: UUID | None = None
    strategy: RealityCandidateStrategy | None = None
    source: RealityCandidateSource
    generator_profile_id: NonEmptyStr
    verifier_profile_hash: Sha256Hex
    campaign_version: int = Field(ge=1)

    @model_validator(mode="after")
    def baseline_runs_have_no_candidate(self) -> RealityRunIdentity:
        if self.run_kind is RealityRunKind.BASELINE:
            if self.candidate_id is not None or self.strategy is not None:
                raise ValueError("a baseline run identity has no candidate")
            if self.source is not RealityCandidateSource.BASELINE:
                raise ValueError("a baseline run identity must declare the baseline source")
        elif self.candidate_id is None or self.strategy is None:
            raise ValueError("a candidate run identity must name its candidate and strategy")
        return self

    @property
    def key(self) -> str:
        return self.content_hash


class RealityCampaignManifest(HashedExperienceContract):
    """The frozen plan for one campaign revision.

    Provider assignment is frozen here, before execution, so that "which tasks went to
    OpenRouter" cannot be decided after seeing which ones it got right.
    """

    campaign_id: UUID
    campaign_version: int = Field(ge=1)
    planned_runs: Annotated[tuple[RealityRunIdentity, ...], Field(min_length=1, max_length=4096)]
    verifier_profile_hash: Sha256Hex
    live_providers_enabled: bool = False
    created_at: UtcDatetime

    @model_validator(mode="after")
    def planned_runs_are_unique_and_current(self) -> RealityCampaignManifest:
        keys = [item.key for item in self.planned_runs]
        if len(keys) != len(set(keys)):
            raise ValueError("a campaign cannot plan the same run identity twice")
        for item in self.planned_runs:
            if item.campaign_version != self.campaign_version:
                raise ValueError("planned run belongs to a different campaign revision")
            if item.verifier_profile_hash != self.verifier_profile_hash:
                raise ValueError("planned run declares a different verifier profile")
        return self

    @model_validator(mode="after")
    def provider_runs_require_the_live_opt_in(self) -> RealityCampaignManifest:
        if not self.live_providers_enabled and any(
            item.source in PROVIDER_CANDIDATE_SOURCES for item in self.planned_runs
        ):
            raise ValueError("a campaign with provider runs must declare the live opt-in")
        return self


class RealityCountBreakdown(HashedExperienceContract):
    """A count that carries its own denominator. §8 asks for no bare percentages."""

    dimension: NonEmptyStr
    value: NonEmptyStr
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)

    @model_validator(mode="after")
    def numerator_fits_denominator(self) -> RealityCountBreakdown:
        if self.numerator > self.denominator:
            raise ValueError("a numerator cannot exceed its denominator")
        return self


class RealityCorpusStatistics(HashedExperienceContract):
    """Machine-readable corpus and provider counts, reproducible from persisted evidence."""

    campaign_id: UUID
    campaign_version: int = Field(ge=1)
    unique_outcomes: int = Field(ge=0)
    duplicate_outcomes_excluded: int = Field(ge=0)
    distinct_trajectories: int = Field(ge=0)
    unique_tasks_with_trajectories: int = Field(ge=0)
    breakdowns: tuple[RealityCountBreakdown, ...] = ()
    split_assignments: dict[str, CorpusSplit] = Field(default_factory=dict)
    created_at: UtcDatetime

    @model_validator(mode="after")
    def breakdowns_are_unique(self) -> RealityCorpusStatistics:
        keys = [(item.dimension, item.value) for item in self.breakdowns]
        if len(keys) != len(set(keys)):
            raise ValueError("a statistics breakdown cannot report the same value twice")
        return self


PUBLIC_REALITY_CONTRACTS: tuple[type[HashedExperienceContract], ...] = (
    RealitySourceRights,
    RealityContentEntry,
    RealityTaskProjection,
    RealityTaskManifest,
    RealityCandidateManifest,
    RealityOutcomeReference,
    CorrectionTrajectoryManifest,
    RealityRunIdentity,
    RealityCampaignManifest,
    RealityCountBreakdown,
    RealityCorpusStatistics,
)
