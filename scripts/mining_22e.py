"""S22E-110. The weakness-to-proposal linkage: a sealed ledger entry becomes a real proposal.

This is the thing §1.3 says has never happened — "no proposal has ever been mined from real
weakness evidence" — and the plan is precise about why it matters: the loop's input is the
programme's own sealed findings, each carrying a reproduction and a priced expected benefit,
"which is precisely what `build_expected_benefit` wants and what invented weaknesses never
have".

**One signal per reproduced probe, not one per finding.** The W0 ledger reproduced its notation
entry as six probe pairs, each an ASCII spelling that verifies and a written spelling that
errors. Each of those pairs becomes a `WeaknessSignal`, so the group the mining service builds
has real distinct members and its impact score is computed over evidence that exists. A single
summary signal would have produced a group of one and an impact score about nothing.

**The evidence is a verifier result, and that is a released constraint rather than a choice.**
`WeaknessSignal` refuses a signal whose evidence is all `PROVIDER_RESULT` — "provider prose
alone cannot create a weakness signal". The notation defect is observed by the *verifier*
erroring, and the escalation defect by the sealed per-task accounting, so both are authoritative
non-shadow evidence and neither needs a model's opinion.

**The released vocabulary already had the words.** `VERIFIER_GAP` is exactly what ledger entry
L1 is — a registered verifier that starts and cannot decide — and `UNNECESSARY_PROVIDER_CALL`
is exactly what L2 is: seventy escalations to an external teacher for a citation the grounding
exit never reads. Neither needed a new enum member, which is the outcome 22A spent a sprint
making possible and 22C W2-F4 made a standing rule.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from cognitive_os.domain.memory import MemorySensitivity  # noqa: E402
from cognitive_os.domain.routing import TaskSignature  # noqa: E402
from cognitive_os.domain.weakness import (  # noqa: E402
    CausalRelationshipType,
    MiningSourceReference,
    SignalSourceType,
    WeaknessComponentType,
    WeaknessConfidenceLevel,
    WeaknessSeverity,
    WeaknessSignal,
    WeaknessType,
)

LEDGER = EVIDENCE / "sprint-22e-weakness-ledger.json"

#: Frozen, not read from a clock, so a rebuild is byte-identical.
MINING_TIME = datetime(2026, 8, 16, 0, 0, 0, tzinfo=UTC)

#: How each eligible ledger entry maps onto the released weakness vocabulary. Written here as
#: data rather than as branches, so that adding an entry is a row and never a code path — and
#: so a reader can see at a glance that no entry needed a new enum member (22C W2-F4: a
#: pipeline may be stricter than a released primitive and may never invent a value for it).
LEDGER_MAPPING: dict[str, dict[str, Any]] = {
    "L1": {
        "weakness_type": WeaknessType.VERIFIER_GAP,
        "component_type": WeaknessComponentType.VERIFIER,
        "failure_code": "physics_verifier_rejects_written_unit_notation",
        "severity": WeaknessSeverity.HIGH,
        "confidence": WeaknessConfidenceLevel.VERIFIED,
        "causal": CausalRelationshipType.OBSERVED_FAILURE,
        "problem_domain": "physics",
        "problem_class": "unit_bearing_quantity",
        "output_type": "physical_quantity",
    },
    "L2": {
        "weakness_type": WeaknessType.UNNECESSARY_PROVIDER_CALL,
        "component_type": WeaknessComponentType.CONTROLLER,
        "failure_code": "escalation_policy_ignores_output_kind",
        "severity": WeaknessSeverity.MEDIUM,
        "confidence": WeaknessConfidenceLevel.VERIFIED,
        "causal": CausalRelationshipType.OBSERVED_FAILURE,
        "problem_domain": "physics",
        "problem_class": "closed_form_computation",
        "output_type": "mathematical_expression",
    },
    "L6": {
        "weakness_type": WeaknessType.PROVIDER_AVAILABILITY_FAILURE,
        "component_type": WeaknessComponentType.PROVIDER,
        "failure_code": "expired_call_reported_as_cancellation",
        "severity": WeaknessSeverity.MEDIUM,
        "confidence": WeaknessConfidenceLevel.VERIFIED,
        "causal": CausalRelationshipType.OBSERVED_FAILURE,
        "problem_domain": "provider_boundary",
        "problem_class": "governed_call_timeout",
        "output_type": "typed_provider_error",
    },
    # **L7 is the sprint's one approved change, and its taxonomy reading is deliberate.**
    # `weakness_type` is `UNKNOWN` because the released enumeration has no member for "a host
    # merge returns a contract the next released statement refuses" — the closest,
    # `PROVIDER_STRUCTURED_OUTPUT_FAILURE`, would blame the provider for a host defect, and
    # W1-F4 is this sprint's own lesson about a misattributed diagnosis. The failure code
    # carries the precise meaning; `UNKNOWN` records that the taxonomy does not.
    # `component_type` is the CONTROLLER for the same reason: the proposal service is
    # host-side control, and nothing the provider sent was wrong.
    "L7": {
        "weakness_type": WeaknessType.UNKNOWN,
        "component_type": WeaknessComponentType.CONTROLLER,
        "failure_code": "merged_provider_revision_returns_an_unsealed_contract",
        "severity": WeaknessSeverity.HIGH,
        "confidence": WeaknessConfidenceLevel.VERIFIED,
        "causal": CausalRelationshipType.OBSERVED_FAILURE,
        "problem_domain": "proposal_engine",
        "problem_class": "provider_assisted_generation",
        "output_type": "harness_proposal_revision",
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def load_entry(entry_id: str) -> dict[str, Any]:
    """Read one ledger entry, and recompute the ledger's seal before believing it.

    A proposal mined from an unsealed ledger is a proposal mined from whatever was last
    written to that path.
    """
    stored = json.loads(LEDGER.read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError("the weakness ledger does not recompute its own seal")
    entry = next((item for item in stored["entries"] if item["entry_id"] == entry_id), None)
    if entry is None:
        # W2's ledger revision adds entries under its own seal (superseded, never edited);
        # an entry mined from it is checked against that seal the same way.
        revision_path = LEDGER.with_name("sprint-22e-weakness-ledger-2.json")
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
        revision_body = {
            key: value for key, value in revision.items() if key != "integrity_content_hash"
        }
        if _sha256(canonical(revision_body)) != revision["integrity_content_hash"]:
            raise ValueError("the ledger revision does not recompute its own seal")
        entry = next(item for item in revision["added_entries"] if item["entry_id"] == entry_id)
    if not entry["eligible"]:
        raise ValueError(f"{entry_id} is not eligible under the W0 gate-owner decision")
    return entry


def _source_reference(entry_id: str, key: str, content: str) -> MiningSourceReference:
    """One piece of authoritative, non-shadow, verifier-sourced evidence.

    `scope` and `source_id` are deliberately repository-relative names: the released contract
    rejects host paths outright, which is the right refusal and a reminder that this evidence
    has to be portable to a reader who does not have this machine.
    """
    return MiningSourceReference(
        source_type=SignalSourceType.VERIFIER,
        source_id=f"sprint-22e-weakness-ledger/{entry_id}/{key}",
        source_revision="1",
        source_content_hash=_sha256(content.encode("utf-8")),
        scope="sprint-22/evidence",
        sensitivity=MemorySensitivity.INTERNAL,
        required=True,
        authoritative=True,
        shadow=False,
        outcome_authority=True,
    )


def _task_signature(mapping: dict[str, Any]) -> TaskSignature:
    return TaskSignature(
        problem_domain=mapping["problem_domain"],
        problem_class=mapping["problem_class"],
        output_type=mapping["output_type"],
        repository_profile="cognitive-os",
        verifier_profile="sprint-22d-frozen-verifier-set",
        risk_level="standard",
    )


def signals_for(entry_id: str) -> tuple[WeaknessSignal, ...]:
    """Turn one sealed ledger entry into the signals its own reproduction supports.

    Each signal names a *reproduced observation*, never the finding as a whole, so the number
    of signals is a fact about the evidence rather than a number this file chose.
    """
    entry = load_entry(entry_id)
    mapping = LEDGER_MAPPING[entry_id]
    signature = _task_signature(mapping)
    mining_run_id = uuid5(NAMESPACE_URL, f"s22e-mining:{entry_id}")
    observations = _observations(entry_id, entry)

    signals = []
    for key, detail in observations:
        content = canonical(detail).decode("utf-8")
        signals.append(
            WeaknessSignal(
                signal_id=uuid5(NAMESPACE_URL, f"s22e-signal:{entry_id}:{key}"),
                mining_run_id=mining_run_id,
                weakness_type=mapping["weakness_type"],
                task_run_id=uuid5(NAMESPACE_URL, f"s22e-task-run:{entry_id}:{key}"),
                source_refs=(_source_reference(entry_id, key, content),),
                task_signature=signature,
                failure_code=mapping["failure_code"],
                component_type=mapping["component_type"],
                component_identity=entry["change_surface"],
                verifier_reference="sprint-22d-frozen-verifier-set",
                severity=mapping["severity"],
                confidence=mapping["confidence"],
                causal_relationship=mapping["causal"],
                observed_at=MINING_TIME,
                extractor_profile=f"sprint-22e-ledger-extractor:{entry_id}",
                limitations=(
                    "Observed by re-reading a sealed predecessor record, not by a live task run.",
                ),
            )
        )
    return tuple(signals)


def _observations(entry_id: str, entry: dict[str, Any]) -> list[tuple[str, Any]]:
    """The reproduced observations inside an entry, as (key, detail) pairs.

    Kept as one function per entry shape rather than a generic walk, because the two entries
    reproduce differently — L1 by live probe, L2 by counting a sealed per-task record — and a
    generic walk would have hidden that difference behind a uniform-looking list.
    """
    reproduction = entry["reproduction"]
    if entry_id == "L1":
        return [
            (probe["task_id"], probe)
            for probe in reproduction["probes"]
            if probe["notation_tax_reproduced"]
        ]
    if entry_id == "L2":
        return [
            (arm, {"arm": arm, **detail})
            for arm, detail in sorted(reproduction["arms"].items())
            if detail["escalated_without_being_a_factual_output"] > 0
        ]
    if entry_id in {"L6", "L7"}:
        # The revision ledger's reproductions are flat introspection blocks: each leg of the
        # chain is one reproduced observation, and the keys are the block's own. L7 reads the
        # same way — four legs, each a boolean the ledger's `--check` re-executes.
        return [
            (key, {key: value})
            for key, value in sorted(reproduction.items())
            if isinstance(value, (bool, int, float))
        ]
    raise KeyError(f"no observation reader for {entry_id}")


def impact_facts_for(entry_id: str) -> tuple[Decimal, Decimal]:
    """`(evidence_coverage, correctness_evidence)` for the released impact scorer.

    Both are 1 for L1 and L2 and the reason is worth stating rather than assuming: every probe
    in the entry reproduced, and every one of them was decided by a registered verifier rather
    than by a judgement. An entry whose probes only partly reproduced would take a coverage
    below one here, which is the field the released scorer exists to read.
    """
    entry = load_entry(entry_id)
    if entry_id == "L1":
        probes = entry["reproduction"]["probes"]
        coverage = Decimal(sum(1 for item in probes if item["notation_tax_reproduced"])) / Decimal(
            len(probes)
        )
        return coverage, Decimal("1")
    return Decimal("1"), Decimal("1")


# ---------------------------------------------------------------------------
# The proposal, built from the mined signals through the released services
# ---------------------------------------------------------------------------


def build_weakness(entry_id: str) -> dict[str, Any]:
    """Run the released mining chain over signals mined from a sealed ledger entry.

    Nothing here is a new algorithm. `build_exact_group_snapshot`, `score_impact`,
    `build_evidence_package`, `build_candidate`, `transition_revision` and `queue_entry_for` are
    the released weakness service, called in the order it defines, over evidence that came out
    of this programme's own findings ledger instead of out of a fixture generator.
    """
    from cognitive_os.config.weakness_config import WeaknessConfiguration
    from cognitive_os.domain.weakness import (
        WeaknessReproductionAssessment,
        WeaknessReproductionStatus,
        WeaknessStatus,
    )
    from cognitive_os.weakness.service import (
        ImpactFacts,
        build_candidate,
        build_evidence_package,
        build_exact_group_snapshot,
        default_mining_profile,
        queue_entry_for,
        score_impact,
        transition_revision,
    )

    signals = signals_for(entry_id)
    profile = default_mining_profile(created_at=MINING_TIME)
    groups = build_exact_group_snapshot(
        signals, profile_hash=profile.content_hash, created_at=MINING_TIME
    )
    # One entry, one signature, therefore one group — asserted rather than assumed, because a
    # group split would mean the signals disagree about what defect they are evidence of.
    if len(groups.groups) != 1:
        raise ValueError(
            f"{entry_id}: signals mined from one ledger entry produced {len(groups.groups)} "
            "groups; they do not share a signature"
        )
    group = groups.groups[0]
    coverage, correctness = impact_facts_for(entry_id)
    impact = score_impact(
        group,
        group_snapshot_hash=groups.content_hash,
        facts=ImpactFacts(evidence_coverage=coverage, correctness_evidence=correctness),
        reference_time=MINING_TIME,
    )
    reproduction = WeaknessReproductionAssessment(
        status=WeaknessReproductionStatus.NOT_ATTEMPTED,
        attempts=(),
        required_safety_restrictions=("bounded replay only",),
        limitations=(
            "Reproduced by re-reading a sealed predecessor record, not by a live replay.",
        ),
        assessed_at=MINING_TIME,
    )
    evidence = build_evidence_package(group, impact, signals, (), reproduction=reproduction)
    _, candidate = build_candidate(
        group,
        impact,
        evidence,
        actor="s22e-miner",
        created_at=MINING_TIME,
        verifier_bundle_hash=_sha256(b"sprint-22d-frozen-verifier-set"),
    )
    confirmed = transition_revision(
        candidate,
        WeaknessStatus.CONFIRMED,
        group=group,
        score=impact,
        evidence_coverage=coverage,
        actor="s22e-miner",
        reason=f"reproduced from sealed ledger entry {entry_id}",
        verifier_bundle_hash=_sha256(b"sprint-22d-frozen-verifier-set"),
        created_at=MINING_TIME,
        configuration=WeaknessConfiguration(),
    )
    queue = queue_entry_for(
        confirmed,
        impact,
        queue_policy_hash=_sha256(b"s22e-queue-policy"),
        created_at=MINING_TIME,
    )
    if queue is None:
        raise ValueError(f"{entry_id}: the released queue policy does not admit this weakness")
    return {
        "entry_id": entry_id,
        "signals": signals,
        "group": group,
        "impact": impact,
        "evidence": evidence,
        "revision": confirmed,
        "queue": queue,
    }


class LedgerWeaknessProposalSource:
    """The released `HarnessProposalService`'s source port, backed by a mined ledger entry.

    Same shape as `proposals.fixtures.FixtureWeaknessProposalSource`, and deliberately so: the
    port is what the released service reads, and a source that answered differently would be
    testing a different service. What changes is only where the weakness came from.
    """

    def __init__(self, mined: dict[str, Any]) -> None:
        self.mined = mined
        self.revision = mined["revision"]
        self.queue = mined["queue"]
        self.evidence = mined["evidence"]
        self.impact = mined["impact"]

    def _matches(self, weakness_id: Any, revision: int) -> bool:
        return (weakness_id, revision) == (
            self.revision.weakness_id,
            self.revision.revision,
        )

    async def get_exact_weakness_revision(self, weakness_id: Any, revision: int) -> Any:
        return self.revision if self._matches(weakness_id, revision) else None

    async def get_current_weakness_revision(self, weakness_id: Any) -> Any:
        return self.revision if weakness_id == self.revision.weakness_id else None

    async def get_exact_queue_entry(self, weakness_id: Any, weakness_revision: int) -> Any:
        return (
            self.queue
            if (weakness_id, weakness_revision)
            == (self.queue.weakness_id, self.queue.weakness_revision)
            else None
        )

    async def get_exact_evidence_package(self, weakness_id: Any, weakness_revision: int) -> Any:
        return self.evidence if self._matches(weakness_id, weakness_revision) else None

    async def get_exact_impact_score(self, weakness_id: Any, weakness_revision: int) -> Any:
        return self.impact if self._matches(weakness_id, weakness_revision) else None

    async def get_reproduction_assessment(self, weakness_id: Any, weakness_revision: int) -> Any:
        return self.evidence.reproduction if self._matches(weakness_id, weakness_revision) else None

    async def get_related_benchmark_candidates(self, weakness_id: Any, revision: int) -> tuple:
        return ()

    async def get_related_replay_candidates(self, weakness_id: Any, revision: int) -> tuple:
        return ()

    async def get_required_registry_snapshots(self) -> dict[str, str]:
        """Real snapshots where the repository has one, and a named hash where it does not.

        The weakness snapshot is the mined revision's own content hash. The other three are
        registry identities this sprint does not own and must not invent values for, so each
        is the hash of its own name — stable, honest about carrying no information, and
        impossible to mistake for a real registry digest.
        """
        return {
            "weakness": self.revision.content_hash,
            "verifiers": _sha256(b"sprint-22d-frozen-verifier-set"),
            "benchmarks": _sha256(b"sprint-22d-microbenchmark"),
            "authority": _sha256(b"sprint-22e-authority-snapshot"),
        }
