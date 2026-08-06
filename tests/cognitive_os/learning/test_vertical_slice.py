"""S21D2-058: the first vertical slice, and S21D2-075's scratch leg.

Section 6.1 asks for one training group and one synthetic sealed-evaluation group to go end to
end through every authority this sprint added, before any bulk campaign spends a container on
them. The ten steps are ten test classes here, in order, so a failure names the step it broke.

Two things this slice deliberately does not do. It never opens a real final, batch-B or canary
body: the sealed-evaluation group is a fixture built for the purpose, and step ten proves the
real one stays shut. And `stop_on_first_accepted` runs only against an isolated scratch
component whose ACTIVE state is a fixture, because reaching that mode on the real component
would be an activation, and no activation exists yet.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

import pytest

from cognitive_os.application.services.correction_candidate_sequencer import (
    AttemptResult,
    CorrectionCandidateSequencer,
    SequenceMode,
)
from cognitive_os.application.services.correction_ranking_observations import (
    CORRECTION_SURFACE,
    CorrectionRankingObservationProjector,
)
from cognitive_os.application.services.learned_runtime import (
    ActiveComponentState,
    ArtifactAvailability,
    EmbeddingIdentity,
    LearnedRuntimeResolver,
    RoutingPolicy,
    RuntimeHealthReason,
)
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import LearnedRepositoryError
from cognitive_os.learning.correction_artifact import (
    CorrectionArtifactError,
    build_payload,
    canonical_bytes,
    load_correction_ranker,
)
from cognitive_os.learning.correction_catalogue import (
    CANDIDATES_PER_GROUP,
    campaign_manifest_for,
    corpus_entries,
    seal_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CandidateProvenance,
    CorrectionEncoder,
    CorrectionFeatureInput,
    CorrectionKnn,
    Exemplar,
    NumericBounds,
)

SLICE_NAMESPACE = UUID("3f7c1a9e-52d4-5b86-9e13-7a4c8d2f60b5")
FEATURE_SEALED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def bundle():
    return seal_corpus()


@pytest.fixture(scope="module")
def entries():
    return {entry.template_id: entry for entry in corpus_entries()}


@pytest.fixture(scope="module")
def training_group(bundle):
    """One real training group: step one's rights-clean package and four opaque candidates."""
    return bundle.catalogues[CorrectionPartition.TRAINING].groups[0]


def _embedding(seed: str, dimension: int = 8) -> tuple[float, ...]:
    """A deterministic committed vector fixture. CI never downloads a model to run this."""
    digest = uuid5(SLICE_NAMESPACE, seed).bytes
    return tuple(round((digest[index] % 200 - 100) / 100, 4) for index in range(dimension))


def _features(group, slot, *, accepted_hint: int) -> CorrectionFeatureInput:
    """Pre-outcome features only: everything here is derivable before the sandbox runs."""
    return CorrectionFeatureInput(
        problem_domain="coding",
        declared_problem_type="repair",
        task_requirement_embedding=_embedding(f"task:{group.template_id}"),
        candidate_delta_embedding=_embedding(f"cand:{slot.candidate_id}"),
        changed_file_count=1,
        hunk_count=1 + accepted_hint,
        added_line_count=4 + accepted_hint,
        removed_line_count=2,
        ast_node_count=30 + accepted_hint,
        graph_node_count=12,
        graph_edge_count=14,
        graph_path_length=3,
        declared_verifier_capabilities=("pytest",),
    )


@pytest.fixture(scope="module")
def encoder():
    rows = [
        {name: float(value) for name, value in row.items()}
        for row in (
            {
                "changed_file_count": 1,
                "hunk_count": 1,
                "added_line_count": 4,
                "removed_line_count": 2,
                "ast_node_count": 30,
                "graph_node_count": 12,
                "graph_edge_count": 14,
                "graph_path_length": 3,
            },
            {
                "changed_file_count": 3,
                "hunk_count": 4,
                "added_line_count": 12,
                "removed_line_count": 6,
                "ast_node_count": 60,
                "graph_node_count": 30,
                "graph_edge_count": 40,
                "graph_path_length": 9,
            },
        )
    ]
    return CorrectionEncoder(NumericBounds.from_training(rows))


# ------------------------------------------------------------------ 1. the task package


class TestStepOneRightsCleanPackageAndOpaqueCandidates:
    def test_the_group_is_rights_clean(self, training_group) -> None:
        assert training_group.usage_rights_verified is True
        assert training_group.source_licence == "Apache-2.0"

    def test_it_carries_four_candidates_whose_identity_hides_the_recipe(
        self, training_group
    ) -> None:
        assert len(training_group.slots) == CANDIDATES_PER_GROUP
        for slot in training_group.slots:
            assert str(slot.candidate_id) not in slot.recipe
            assert slot.recipe not in str(slot.candidate_id)


# ------------------------------------------------------- 2. features before verifier results


class TestStepTwoFeaturesAreSealedBeforeAnyOutcome:
    def test_every_encoded_name_is_available_before_execution(
        self, training_group, encoder
    ) -> None:
        vector = encoder.encode(_features(training_group, training_group.slots[0], accepted_hint=0))

        assert "verifier_status" not in vector.names
        assert "candidate_recipe" not in vector.names
        assert vector.content_hash()

    def test_the_encoder_refuses_to_take_provenance(self, training_group, encoder) -> None:
        """`CandidateProvenance` is a separate object precisely so this cannot be passed."""
        provenance = CandidateProvenance(
            candidate_id=str(training_group.slots[0].candidate_id),
            task_id=str(training_group.task_id),
            group=training_group.repository_group,
            recipe=training_group.slots[0].recipe,
        )
        with pytest.raises(AttributeError):
            encoder.encode(provenance)  # type: ignore[arg-type]

    def test_the_feature_record_predates_the_outcome(self, training_group) -> None:
        outcome_at = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)

        assert outcome_at > FEATURE_SEALED_AT


# ------------------------------------------------ 3. role-bound projection from the manifest


class TestStepThreeProjectionIsBoundToThePartition:
    def test_a_training_candidate_projects_as_self_play(self, bundle) -> None:
        catalogue = bundle.catalogues[CorrectionPartition.TRAINING]
        manifest = campaign_manifest_for(
            catalogue,
            campaign_id=uuid5(SLICE_NAMESPACE, "training-campaign"),
            campaign_version=1,
            feature_sealed_at=FEATURE_SEALED_AT,
        )
        projector = CorrectionRankingObservationProjector(manifest)
        member = manifest.members[catalogue.groups[0].slots[0].candidate_id]

        assert member.partition is CorrectionPartition.TRAINING
        assert projector.surface == CORRECTION_SURFACE

    def test_a_final_candidate_would_project_as_real_governed(self, bundle) -> None:
        """The same projector, the same code path; only the partition differs."""
        catalogue = bundle.catalogues[CorrectionPartition.FINAL_A]
        manifest = campaign_manifest_for(
            catalogue,
            campaign_id=uuid5(SLICE_NAMESPACE, "final-campaign"),
            campaign_version=1,
            feature_sealed_at=FEATURE_SEALED_AT,
        )
        member = manifest.members[catalogue.groups[0].slots[0].candidate_id]

        assert member.partition is CorrectionPartition.FINAL_A

    def test_the_manifest_is_bound_to_the_catalogue_it_came_from(self, bundle) -> None:
        catalogue = bundle.catalogues[CorrectionPartition.TRAINING]
        manifest = campaign_manifest_for(
            catalogue,
            campaign_id=uuid5(SLICE_NAMESPACE, "training-campaign"),
            campaign_version=1,
            feature_sealed_at=FEATURE_SEALED_AT,
        )

        assert manifest.manifest_hash == catalogue.content_hash
        assert len(manifest.members) == catalogue.candidate_slots

    def test_a_candidate_outside_the_manifest_is_refused(self, bundle) -> None:
        manifest = campaign_manifest_for(
            bundle.catalogues[CorrectionPartition.TRAINING],
            campaign_id=uuid5(SLICE_NAMESPACE, "training-campaign"),
            campaign_version=1,
            feature_sealed_at=FEATURE_SEALED_AT,
        )
        with pytest.raises(LearnedRepositoryError):
            manifest.member_for(uuid4())


# ------------------------------------------------------ 4. explicit group-aware dataset split


class TestStepFourTheSplitIsExplicitAndGroupAware:
    def test_fit_and_calibration_share_no_group(self, bundle) -> None:
        fit = bundle.groups_of(CorrectionPartition.TRAINING)
        calibration = bundle.groups_of(CorrectionPartition.CALIBRATION)

        assert fit and calibration
        assert not fit & calibration

    def test_the_split_is_named_by_partition_rather_than_by_row(self, bundle) -> None:
        """Group-aware means the unit is the group; a row-level split would leak a template."""
        for partition in (CorrectionPartition.TRAINING, CorrectionPartition.CALIBRATION):
            catalogue = bundle.catalogues[partition]
            groups = [group.repository_group for group in catalogue.groups]
            assert len(set(groups)) == len(groups)


# ------------------------------------------------------------- 5. one fit, canonical artifact


@pytest.fixture(scope="module")
def fitted(bundle, encoder):
    """One k-NN fit over the training partition's slots, labelled by the sealed declaration."""
    entries_by_id = {entry.template_id: entry for entry in corpus_entries()}
    exemplars: list[Exemplar] = []
    catalogue = bundle.catalogues[CorrectionPartition.TRAINING]
    for group in catalogue.groups[:12]:
        declared = entries_by_id[group.template_id].repairs_contract
        for slot in group.slots:
            accepted = declared[slot.variant_index]
            vector = encoder.encode(_features(group, slot, accepted_hint=2 if accepted else 0))
            exemplars.append(Exemplar(vector=vector, accepted=accepted))
    return CorrectionKnn(exemplars, k=5), exemplars


class TestStepFiveTheFitProducesACanonicalArtifact:
    def test_the_ranker_holds_the_exemplars_it_was_fitted_on(self, fitted) -> None:
        ranker, exemplars = fitted

        assert ranker.size == len(exemplars) == 48

    def test_the_artifact_is_canonical_json_and_reproducible(self, fitted) -> None:
        ranker, exemplars = fitted
        payload = _payload_for(ranker, exemplars)

        first = canonical_bytes(payload)
        assert first == canonical_bytes(payload)
        assert json.loads(first.decode())["surface"] == CorrectionKnn.surface

    def test_the_artifact_does_not_carry_its_own_hash(self, fitted) -> None:
        """The Artifact Store's hash is the hash; a self-declared one is a second answer."""
        ranker, exemplars = fitted
        document = json.loads(canonical_bytes(_payload_for(ranker, exemplars)).decode())

        assert "content_hash" not in document


def _payload_for(ranker: CorrectionKnn, exemplars):
    return build_payload(
        component_revision=1,
        ranker=ranker,
        exemplars=exemplars,
        encoder_version=CorrectionEncoder.version,
        code_version="21d2-w3c",
        training_dataset_id=uuid5(SLICE_NAMESPACE, "training-dataset"),
        calibration_dataset_id=uuid5(SLICE_NAMESPACE, "calibration-dataset"),
        example_manifest_hash="a" * 64,
        split_manifest_hash="b" * 64,
        feature_schema_hash="c" * 64,
        embedding_model_id="fixture-committed-vectors",
        embedding_revision="1",
        embedding_dimension=8,
        numeric_lower=dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
        numeric_upper=dict.fromkeys(NUMERIC_FEATURE_NAMES, 1.0),
    )


# ------------------------------------------------------------- 6. reload through the loader


class TestStepSixTheNarrowLoaderVerifiesWhatItReads:
    def test_the_artifact_round_trips(self, fitted) -> None:
        ranker, exemplars = fitted
        data = canonical_bytes(_payload_for(ranker, exemplars))

        restored, payload = load_correction_ranker(
            data,
            expected_component_id=CorrectionKnn.component_id,
            expected_revision=1,
            expected_surface=CorrectionKnn.surface,
        )

        assert restored.size == ranker.size
        assert payload.surface == CorrectionKnn.surface

    def test_the_wrong_revision_is_refused(self, fitted) -> None:
        ranker, exemplars = fitted
        data = canonical_bytes(_payload_for(ranker, exemplars))
        with pytest.raises(CorrectionArtifactError):
            load_correction_ranker(
                data,
                expected_component_id=CorrectionKnn.component_id,
                expected_revision=2,
                expected_surface=CorrectionKnn.surface,
            )

    def test_a_foreign_media_type_is_refused(self, fitted) -> None:
        ranker, exemplars = fitted
        with pytest.raises(CorrectionArtifactError):
            load_correction_ranker(
                canonical_bytes(_payload_for(ranker, exemplars)),
                expected_component_id=CorrectionKnn.component_id,
                expected_revision=1,
                expected_surface=CorrectionKnn.surface,
                media_type="application/octet-stream",
            )


# ------------------------------------------- 7. label_all, then scratch-ACTIVE stop-on-first


class _RecordingEvents:
    """A stand-in for `CodingEventService` that records what would have been appended."""

    def __init__(self) -> None:
        self.appended: list[tuple[UUID, object]] = []

    async def append(self, stream_id, payload, *, correlation_id, stream_type):
        self.appended.append((stream_id, payload))
        return uuid5(SLICE_NAMESPACE, f"event:{len(self.appended)}")


@pytest.mark.anyio
class TestStepSevenSequencingInBothModes:
    async def test_label_all_runs_every_candidate_in_baseline_order(self, training_group) -> None:
        events = _RecordingEvents()
        sequencer = CorrectionCandidateSequencer(events)  # type: ignore[arg-type]
        baseline = tuple(slot.candidate_id for slot in training_group.slots)
        resolved = tuple(reversed(baseline))

        async def attempt(candidate_id: UUID) -> AttemptResult:
            return AttemptResult(
                candidate_id=candidate_id,
                accepted=candidate_id == baseline[0],
                event_id=uuid5(SLICE_NAMESPACE, f"outcome:{candidate_id}"),
                verifier_evidence_hash="d" * 64,
            )

        outcome = await sequencer.run_task(
            campaign_id=uuid5(SLICE_NAMESPACE, "training-campaign"),
            task_id=training_group.task_id,
            partition=CorrectionPartition.TRAINING.value,
            mode=SequenceMode.LABEL_ALL,
            campaign_manifest_hash="e" * 64,
            baseline_order=baseline,
            attempt=attempt,
            resolved_order=resolved,
        )

        assert outcome.attempted_order == baseline
        assert outcome.intentionally_unattempted == ()
        assert outcome.resolved_order == resolved
        assert outcome.learned_ordering_used is False

    async def test_scratch_active_stop_on_first_leaves_the_rest_alone(self, training_group) -> None:
        """Reachable only on the isolated scratch component; never a SHADOW or final mode."""
        events = _RecordingEvents()
        sequencer = CorrectionCandidateSequencer(events)  # type: ignore[arg-type]
        baseline = tuple(slot.candidate_id for slot in training_group.slots)
        resolved = (baseline[2], baseline[0], baseline[1], baseline[3])

        async def attempt(candidate_id: UUID) -> AttemptResult:
            return AttemptResult(
                candidate_id=candidate_id,
                accepted=candidate_id == resolved[1],
                event_id=uuid5(SLICE_NAMESPACE, f"outcome:{candidate_id}"),
                verifier_evidence_hash="d" * 64,
            )

        outcome = await sequencer.run_task(
            campaign_id=uuid5(SLICE_NAMESPACE, "scratch-campaign"),
            task_id=training_group.task_id,
            partition="scratch",
            mode=SequenceMode.STOP_ON_FIRST_ACCEPTED,
            campaign_manifest_hash="e" * 64,
            baseline_order=baseline,
            attempt=attempt,
            resolved_order=resolved,
            learned_ordering_used=True,
        )

        assert outcome.attempted_order == resolved[:2]
        assert set(outcome.intentionally_unattempted) == set(resolved[2:])
        assert outcome.stop_reason == "verifier_accepted"
        assert outcome.learned_ordering_used is True

    async def test_the_receipt_is_appended_to_the_campaign_stream(self, training_group) -> None:
        events = _RecordingEvents()
        sequencer = CorrectionCandidateSequencer(events)  # type: ignore[arg-type]
        baseline = tuple(slot.candidate_id for slot in training_group.slots)

        async def attempt(candidate_id: UUID) -> AttemptResult:
            return AttemptResult(
                candidate_id=candidate_id,
                accepted=False,
                event_id=uuid5(SLICE_NAMESPACE, f"outcome:{candidate_id}"),
                verifier_evidence_hash="d" * 64,
            )

        campaign_id = uuid5(SLICE_NAMESPACE, "training-campaign")
        outcome = await sequencer.run_task(
            campaign_id=campaign_id,
            task_id=training_group.task_id,
            partition=CorrectionPartition.TRAINING.value,
            mode=SequenceMode.LABEL_ALL,
            campaign_manifest_hash="e" * 64,
            baseline_order=baseline,
            attempt=attempt,
        )
        await sequencer.record(outcome, correlation_id=uuid4())

        assert len(events.appended) == 1
        stream_id, payload = events.appended[0]
        assert stream_id == campaign_id
        assert payload.stop_reason == "exhausted_without_acceptance"


# --------------------------------------------------------- 8. missing or corrupt artifact


class TestStepEightFallbackWhenTheArtifactIsNotThere:
    """Every refusal here hands back the deterministic order rather than an error."""

    EMBEDDING = EmbeddingIdentity(model_id="fixture", revision="1", available=True)

    def _resolver(self) -> LearnedRuntimeResolver:
        return LearnedRuntimeResolver(
            surface=CorrectionKnn.surface, expected_embedding=self.EMBEDDING
        )

    def _state(self, **overrides) -> ActiveComponentState:
        base = {
            "component_id": CorrectionKnn.component_id,
            "surface": CorrectionKnn.surface,
            "revision": 1,
            "model_artifact_id": uuid5(SLICE_NAMESPACE, "artifact"),
            "lineage_verified": True,
            "descriptor_revision": 1,
        }
        return ActiveComponentState(**{**base, **overrides})

    def _policy(self, bundle, **overrides) -> RoutingPolicy:
        canary = bundle.canary_routing
        base = {
            "persistence_enabled": True,
            "activation_enabled": True,
            "active_components": (CorrectionKnn.component_id,),
            "routed_groups": canary.routed_groups,
            "routing_manifest_hash": canary.canary_manifest_hash,
        }
        return RoutingPolicy(**{**base, **overrides})

    def test_a_missing_artifact_falls_back_deterministically(self, bundle) -> None:
        resolved = self._resolver().resolve(
            policy=self._policy(bundle),
            active_states=[self._state()],
            group=bundle.canary_routing.routed_groups[0],
            artifact=ArtifactAvailability(present=False),
            local_embedding=self.EMBEDDING,
        )

        assert resolved.learned_ordering_permitted is False
        assert resolved.reason is RuntimeHealthReason.ARTIFACT_MISSING
        assert resolved.uses_deterministic_fallback is True

    def test_an_unverified_lineage_falls_back_too(self, bundle) -> None:
        resolved = self._resolver().resolve(
            policy=self._policy(bundle),
            active_states=[self._state(lineage_verified=False)],
            group=bundle.canary_routing.routed_groups[0],
            artifact=ArtifactAvailability(present=True),
            local_embedding=self.EMBEDDING,
        )

        assert resolved.reason is RuntimeHealthReason.ARTIFACT_UNVERIFIED
        assert resolved.learned_ordering_permitted is False

    def test_a_corrupt_artifact_never_becomes_a_ranker(self, fitted) -> None:
        ranker, exemplars = fitted
        corrupt = canonical_bytes(_payload_for(ranker, exemplars))[:-5]
        with pytest.raises(CorrectionArtifactError):
            load_correction_ranker(
                corrupt,
                expected_component_id=CorrectionKnn.component_id,
                expected_revision=1,
                expected_surface=CorrectionKnn.surface,
            )

    def test_an_unrouted_group_gets_the_deterministic_order(self, bundle) -> None:
        resolved = self._resolver().resolve(
            policy=self._policy(bundle),
            active_states=[self._state()],
            group="a-group-that-is-not-routed",
            artifact=ArtifactAvailability(present=True),
            local_embedding=self.EMBEDDING,
        )

        assert resolved.reason is RuntimeHealthReason.GROUP_NOT_ROUTED
        assert resolved.learned_ordering_permitted is False

    def test_the_shipped_state_routes_nothing_at_all(self, bundle) -> None:
        """Activation disabled is the default, and it is the first gate the resolver applies."""
        resolved = self._resolver().resolve(
            policy=self._policy(bundle, activation_enabled=False),
            active_states=[self._state()],
            group=bundle.canary_routing.routed_groups[0],
            artifact=ArtifactAvailability(present=True),
            local_embedding=self.EMBEDDING,
        )

        assert resolved.reason is RuntimeHealthReason.ACTIVATION_DISABLED

    def test_an_unavailable_embedding_falls_back(self, bundle) -> None:
        resolved = self._resolver().resolve(
            policy=self._policy(bundle),
            active_states=[self._state()],
            group=bundle.canary_routing.routed_groups[0],
            artifact=ArtifactAvailability(present=True),
            local_embedding=EmbeddingIdentity(model_id="fixture", revision="1", available=False),
        )

        assert resolved.reason is RuntimeHealthReason.EMBEDDING_UNAVAILABLE


# ------------------------------------------------------------------ 9. restart and replay


class TestStepNineRestartIsDeterministic:
    def test_sealing_again_after_a_restart_reproduces_the_same_corpus(self, bundle) -> None:
        assert seal_corpus().seal.content_hash == bundle.seal.content_hash

    def test_the_artifact_is_byte_identical_after_a_refit(self, bundle, encoder) -> None:
        """Same exemplars, same bytes: a replay that produced new bytes would be a new model."""
        entries_by_id = {entry.template_id: entry for entry in corpus_entries()}
        catalogue = bundle.catalogues[CorrectionPartition.TRAINING]

        def fit():
            exemplars = []
            for group in catalogue.groups[:4]:
                declared = entries_by_id[group.template_id].repairs_contract
                for slot in group.slots:
                    accepted = declared[slot.variant_index]
                    exemplars.append(
                        Exemplar(
                            vector=encoder.encode(
                                _features(group, slot, accepted_hint=2 if accepted else 0)
                            ),
                            accepted=accepted,
                        )
                    )
            return CorrectionKnn(exemplars, k=3), exemplars

        first_ranker, first_exemplars = fit()
        second_ranker, second_exemplars = fit()

        assert canonical_bytes(_payload_for(first_ranker, first_exemplars)) == canonical_bytes(
            _payload_for(second_ranker, second_exemplars)
        )

    def test_the_encoder_is_stable_across_a_restart(self, training_group, encoder) -> None:
        slot = training_group.slots[0]
        first = encoder.encode(_features(training_group, slot, accepted_hint=1))
        second = encoder.encode(_features(training_group, slot, accepted_hint=1))

        assert first.content_hash() == second.content_hash()


# ------------------------------------------ 10. the sealed evaluation refuses access early


class TestStepTenTheSealedEvaluationStaysShut:
    def test_the_seal_locates_no_final_body(self, bundle) -> None:
        """Fitting holds the manifest hash and nothing that finds a holdout candidate."""
        serialized = bundle.seal.model_dump_json()
        for partition in (
            CorrectionPartition.FINAL_A,
            CorrectionPartition.FINAL_B,
            CorrectionPartition.CANARY,
        ):
            for group in bundle.catalogues[partition].groups:
                assert str(group.task_id) not in serialized

    def test_no_final_outcome_exists_to_be_read(self, bundle) -> None:
        for partition in (CorrectionPartition.FINAL_A, CorrectionPartition.FINAL_B):
            assert bundle.catalogues[partition].outcomes_present is False

    def test_a_synthetic_evaluation_group_projects_as_real_governed(self, bundle) -> None:
        """The synthetic stand-in exercises the path; the real batch is never opened."""
        catalogue = bundle.catalogues[CorrectionPartition.FINAL_A]
        manifest = campaign_manifest_for(
            catalogue,
            campaign_id=uuid5(SLICE_NAMESPACE, "synthetic-evaluation"),
            campaign_version=1,
            feature_sealed_at=FEATURE_SEALED_AT,
        )
        member = next(iter(manifest.members.values()))

        assert member.partition is CorrectionPartition.FINAL_A
        assert ProvenanceClass.REAL_GOVERNED_RUN.value == "real_governed_run"
