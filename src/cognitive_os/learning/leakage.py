"""The field allowlist and the leakage validator for the pre-registered D1 surface.

Sprint 21D1 pre-registers `experience.correction_context`: given a failing state,
retrieve a verified failed-to-success edit path as advisory repair context. Its inputs
are a query projection and a graph projection, so "feature" here means *any string or
identifier that reaches a query, a node attribute, or an embedding* — not a numeric
vector slot.

The allowlist is declared per field with the time its value becomes known. A field whose
timing nobody established is refused rather than allowed, because the leak that survives
review is the one nobody could describe.

`candidate_strategy` is forbidden on measured grounds, not stylistic ones: on the 150
enumerated C3 coding outcomes it determines the independent verifier label with no error
across all five strategies. See `docs/sprints/sprint-21/evidence/sprint-21d1-surface-audit.json`.

Control-token scanning is not reimplemented here. `coding.reality_leakage` already owns
it and is the authority C3 released against.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from cognitive_os.coding.reality_leakage import scan_for_control_leaks
from cognitive_os.domain.learned import FeatureTiming

SURFACE = "experience.correction_context"

#: Version the allowlist so a later revision invalidates results derived from this one.
ALLOWLIST_VERSION = "correction-context-fields-v1"

#: Every field D1 may project, with when its value becomes known. Anything absent from
#: this mapping is refused by `validate_record` as `unknown_field_timing`.
FIELD_TIMING: Mapping[str, FeatureTiming] = {
    # Identity and grouping. Known before the run starts.
    "task_id": FeatureTiming.PRE_OUTCOME,
    "task_manifest_hash": FeatureTiming.PRE_OUTCOME,
    "task_run_id": FeatureTiming.PRE_OUTCOME,
    "split_group_key": FeatureTiming.PRE_OUTCOME,
    "repository_group": FeatureTiming.PRE_OUTCOME,
    "problem_domain": FeatureTiming.PRE_OUTCOME,
    "problem_type": FeatureTiming.PRE_OUTCOME,
    "task_signature_hash": FeatureTiming.PRE_OUTCOME,
    # The failing state a repair request describes. Known at request time.
    "failure_classification": FeatureTiming.PRE_OUTCOME,
    "visible_test_command": FeatureTiming.PRE_OUTCOME,
    "action_type": FeatureTiming.PRE_OUTCOME,
    "node_kind": FeatureTiming.PRE_OUTCOME,
    "edge_kind": FeatureTiming.PRE_OUTCOME,
    # Terminal facts. Legitimate as provenance on a *stored* pair, never as query input.
    "final_status": FeatureTiming.POST_OUTCOME,
    "hidden_verification_passed": FeatureTiming.POST_OUTCOME,
    "outcome_hash": FeatureTiming.POST_OUTCOME,
    "outcome_artifact_hash": FeatureTiming.POST_OUTCOME,
    "hidden_evidence_hash": FeatureTiming.POST_OUTCOME,
    "verifier_status": FeatureTiming.POST_OUTCOME,
    "recorded_at": FeatureTiming.POST_OUTCOME,
    # Measured oracle. Nominally pre-outcome, refused anyway.
    "candidate_strategy": FeatureTiming.UNKNOWN,
}

#: Fields that may never appear in a query projection, whatever their declared timing.
FORBIDDEN_IN_QUERY = frozenset(
    name for name, timing in FIELD_TIMING.items() if timing is not FeatureTiming.PRE_OUTCOME
)

#: Substrings that mark host paths and credential material in a projected value.
_HOST_PATH_MARKERS = ("/home/", "/root/", "/var/tmp/", "C:\\")
_CREDENTIAL_MARKERS = ("authorization", "api_key", "apikey", "password", "secret", "token=")


@dataclass(frozen=True, slots=True)
class LeakageFinding:
    """One refusal, with a stable reason code a test can assert on."""

    reason: str
    field: str
    detail: str


def allowlisted_query_fields() -> tuple[str, ...]:
    """The only fields a query projection may carry, sorted for determinism."""
    return tuple(
        sorted(name for name, timing in FIELD_TIMING.items() if timing is FeatureTiming.PRE_OUTCOME)
    )


def validate_query_projection(
    projection: Mapping[str, str],
    *,
    query_group: str,
    candidate_group: str,
    control_tokens: Iterable[str] = (),
) -> tuple[LeakageFinding, ...]:
    """Refuse a query projection that could see its own answer.

    Five independent ways that happens, each with its own reason code:
    an unknown field, a post-outcome field, a measured oracle field, a control token or
    credential in a value, and a candidate drawn from the query's own group.
    """
    findings: list[LeakageFinding] = []

    for field, value in sorted(projection.items()):
        timing = FIELD_TIMING.get(field)
        if timing is None:
            findings.append(
                LeakageFinding("unknown_field_timing", field, "field is not on the allowlist")
            )
            continue
        if timing is FeatureTiming.POST_OUTCOME:
            findings.append(
                LeakageFinding("post_outcome_field", field, "value is only known after the outcome")
            )
            continue
        if timing is FeatureTiming.UNKNOWN:
            findings.append(
                LeakageFinding(
                    "answer_revealing_field",
                    field,
                    "measured to determine the verifier label; see the D1 surface audit",
                )
            )
            continue
        lowered = value.lower()
        for marker in _HOST_PATH_MARKERS:
            if marker.lower() in lowered:
                findings.append(LeakageFinding("host_path_present", field, marker))
        for marker in _CREDENTIAL_MARKERS:
            if marker in lowered:
                findings.append(LeakageFinding("credential_marker_present", field, marker))

    for leak in scan_for_control_leaks(dict(projection), control_tokens):
        findings.append(LeakageFinding("control_token_present", leak.surface, leak.kind))

    if query_group == candidate_group:
        findings.append(
            LeakageFinding(
                "same_group_crossing",
                "split_group_key",
                f"the candidate pool must exclude the query group {query_group!r}",
            )
        )

    return tuple(findings)


def duplicate_identities(identities: Iterable[str]) -> tuple[str, ...]:
    """Identities appearing more than once, so a denominator cannot be inflated.

    The C3 evidence store holds four replay waves of the same 64 benchmark cases and
    641 outcome rows against a released 214. Deduplication is not hygiene here, it is
    the difference between a real sample size and a fabricated one.
    """
    seen: set[str] = set()
    repeated: set[str] = set()
    for identity in identities:
        if identity in seen:
            repeated.add(identity)
        seen.add(identity)
    return tuple(sorted(repeated))


if __name__ == "__main__":  # pragma: no cover - the smallest runnable check
    clean = {
        "task_id": "cc11c841-5a71-4cfb-97f3-db241f780836",
        "problem_domain": "logic",
        "failure_classification": "wrong_answer",
    }
    assert validate_query_projection(clean, query_group="g1", candidate_group="g2") == ()

    reasons = {
        finding.reason
        for finding in validate_query_projection(
            {
                "task_id": "/home/palkouser/projekt/x",
                "candidate_strategy": "correct_narrow",
                "final_status": "accepted",
                "invented_field": "whatever",
                "problem_domain": "authorization: Bearer abc",
            },
            query_group="g1",
            candidate_group="g1",
            control_tokens=("deadbeef",),
        )
    }
    assert reasons == {
        "host_path_present",
        "answer_revealing_field",
        "post_outcome_field",
        "unknown_field_timing",
        "credential_marker_present",
        "same_group_crossing",
    }, reasons

    assert "candidate_strategy" in FORBIDDEN_IN_QUERY
    assert duplicate_identities(("a", "b", "a", "c", "b")) == ("a", "b")
    assert len(allowlisted_query_fields()) == 13
    print("leakage validator self-check passed;", len(FIELD_TIMING), "fields declared")
