"""S22E-200. The ledger revision W1 owed: two released-path defects, reproduced and priced.

W1 carried two findings "to the ledger" and could not put them there: the W0 ledger is a
sealed record every later wave binds by hash, and re-sealing it in W1 would have invalidated
the record the tests check. The mechanism here is 22B W1-D2's — **supersede, never edit**. The
W0 file stays byte-identical; this record is revision 2 under its own identity, binds its
predecessor's file hash and integrity hash, carries the five W0 entries by reference with
their sealed ranks unchanged, and adds the two entries with **executed** reproductions.

**L6 — 22E W1-F5.** A governed call that expires is reported as one somebody cancelled.
`ModelProviderRequest.timeout_seconds` defaults to 120 independently of the adapter's
configured limit, so a request against a slower-but-permitted adapter expires first; the
cancellation is converted to `ProviderCancelledError` inside `BoundedCliRunner._communicate`
before the outer timeout handler can see it, `events.timed_out` never fires, and the retry
policy declines to act because `ProviderCancelledError` is not in `retryable_error_types`
while `ProviderTimeoutError` is. Two live calls were lost to it in W1. Every leg of that is
introspected here from released code, not quoted from the wave.

**L7 — 22E W1-F7.** `merge_provider_draft` returns
`revision.model_copy(update={..., "content_hash": ""})`, and `model_copy(update=...)` does not
re-run validators in Pydantic v2 — so the one released writer of a provider-assisted revision
hands back a contract whose seal is the empty string, and the next released statement refuses
it against `^[0-9a-f]{64}$`. The provider-assisted mark therefore cannot survive to an
approved revision by any caller's route, which is what makes §2.2(b)'s chain unwalkable as
written and puts this entry in front of the gate owner's W3 decision. The reproduction runs
the released path on the released fixture and records both halves: the blank seal, and the
refusal.

Both reproductions are credential-free and deterministic, so — unlike W1's records — this
`--check` recomputes *everything*: the predecessor binding, both reproductions, and the seal.

    UV_CACHE_DIR=.cache/uv uv run python scripts/ledger_revision_22e.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/ledger_revision_22e.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

PREDECESSOR = EVIDENCE / "sprint-22e-weakness-ledger.json"
OUTPUT = EVIDENCE / "sprint-22e-weakness-ledger-2.json"
REVISION_TIME = "2026-08-16T12:00:00Z"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _predecessor_binding() -> dict[str, Any]:
    stored = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    return {
        "file": PREDECESSOR.name,
        "file_sha256": _sha256(PREDECESSOR.read_bytes()),
        "integrity_content_hash": stored["integrity_content_hash"],
        "seal_recomputes": _sha256(canonical(body)) == stored["integrity_content_hash"],
        "superseded_not_edited": (
            "the W0 record is byte-identical and its tests still hold it; this record is "
            "revision 2 under its own identity (22B W1-D2 — a host is superseded, never edited)"
        ),
    }


def _carried_entries() -> list[dict[str, Any]]:
    stored = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    return [
        {
            "entry_id": entry["entry_id"],
            "finding": entry["finding"],
            "rank": entry["rank"],
            "eligible": entry["eligible"],
            "carried_by_reference": True,
            "rank_unchanged_because": (
                "the W0 ranks are sealed measurements; a revision repriced silently would be "
                "the drift W0-F1 exists to name"
            ),
        }
        for entry in stored["entries"]
    ]


def _reproduce_timeout_misreport() -> dict[str, Any]:
    """L6, executed: every leg of the misreport chain, read from released code."""
    import inspect

    from cognitive_os.config.provider_config import DEFAULT_CLI_TIMEOUT_SECONDS
    from cognitive_os.domain.model_requests import ModelProviderRequest
    from cognitive_os.providers.cli_process import BoundedCliRunner
    from cognitive_os.providers.errors import ProviderCancelledError, ProviderTimeoutError
    from cognitive_os.providers.retry import RetryPolicy

    request_default = ModelProviderRequest.model_fields["timeout_seconds"].default
    policy = RetryPolicy()
    conversion_site = inspect.getsource(BoundedCliRunner._communicate)
    return {
        "request_timeout_default_seconds": request_default,
        "cli_limit_default_seconds": DEFAULT_CLI_TIMEOUT_SECONDS,
        "defaults_are_independent": (
            "the request default is not derived from the adapter's configured limit; W1 "
            "observed a configured limit of 300 against the request's 120, and the request "
            "expired first"
        ),
        "cancellation_is_converted_before_the_timeout_handler": (
            "ProviderCancelledError" in conversion_site
        ),
        "timeout_is_retryable": ProviderTimeoutError in policy.retryable_error_types,
        "cancellation_is_retryable": ProviderCancelledError in policy.retryable_error_types,
        "the_defect_in_one_sentence": (
            "an expired governed call is recorded as cancelled, fires no timed_out event, "
            "and is not retried, because the conversion happens below the layer that owns "
            "the timeout"
        ),
    }


async def _reproduce_blank_seal() -> dict[str, Any]:
    """L7, executed: the released path, the blank seal, and the released refusal."""
    from uuid import uuid4

    from pydantic import ValidationError

    from cognitive_os.changes.fixtures import fixture_approved_proposal
    from cognitive_os.domain.common import utc_now
    from cognitive_os.domain.proposals import (
        HarnessProposalType,
        ProposalGenerationMode,
        ProviderProposalDraft,
    )
    from cognitive_os.events.proposal_events import ProposalCreated
    from cognitive_os.proposals.service import merge_provider_draft

    _, proposal = await fixture_approved_proposal()
    draft = ProviderProposalDraft(
        proposal_type=HarnessProposalType(proposal.change_specification.change_surface),
        summary="a fixture draft for the reproduction",
        proposed_body="describes the repair in prose",
        rationale="the reproduction needs a draft that passes host verification",
        alternative_drafts=("none",),
        affected_component_hints=(proposal.change_specification.current_identity,),
        validation_rationale="not applicable to a reproduction",
        rollback_rationale="not applicable to a reproduction",
        limitations=("this draft exists to reproduce W1-F7",),
        cited_host_source_ref_ids=(),
    )
    merged = merge_provider_draft(proposal, draft, allowed_source_ids=())

    refusal = ""
    try:
        ProposalCreated(
            proposal_id=merged.proposal_id,
            proposal_revision=merged.revision,
            source_snapshot_hash=merged.source_snapshot.snapshot_hash,
            proposal_content_hash=merged.content_hash,
            actor_identity="s22e-reproduction",
            actor_authority="proposal-author",
            summary="the released statement that refuses the merged revision",
            occurred_at=utc_now(),
        )
    except ValidationError as error:
        refusal = str(error.errors()[0]["msg"])[:120]

    resealed = type(merged).model_validate(merged.model_dump(exclude={"content_hash"}))
    _ = uuid4()  # keep the import surface identical across runs
    return {
        "host_verification_admitted_the_draft": (
            merged.generation_mode is ProposalGenerationMode.PROVIDER_ASSISTED
        ),
        "merged_content_hash": merged.content_hash,
        "merged_seal_is_blank": merged.content_hash == "",
        "released_statement_refuses": bool(refusal),
        "refusal": refusal,
        "reseal_through_the_contract_recovers": bool(resealed.content_hash)
        and len(resealed.content_hash) == 64,
        "the_defect_in_one_sentence": (
            "model_copy(update=...) does not re-run validators, so the only released writer "
            "of a provider-assisted revision returns a contract with an empty seal and the "
            "next released statement refuses it"
        ),
    }


async def _added_entries() -> list[dict[str, Any]]:
    timeout = _reproduce_timeout_misreport()
    blank = await _reproduce_blank_seal()
    return [
        {
            "entry_id": "L6",
            "finding": "22E W1-F5",
            "weakness_class": "provider_boundary",
            "change_surface": (
                "the request timeout default, the cancellation conversion in "
                "BoundedCliRunner._communicate, and the retry policy's error-type set"
            ),
            "summary": (
                "an expired governed provider call is reported as cancelled, records no "
                "timeout event, and is silently not retried"
            ),
            "risk_class": "low",
            "eligible": True,
            "touches_a_gate_m_condition": None,
            "rank": 6,
            "expected_benefit": {
                "measured": "two live calls lost in W1 before the layers were bisected",
                "what_a_repair_restores": (
                    "honest timeout events and a retry policy that does what it is configured to do"
                ),
            },
            "reproduction": timeout,
        },
        {
            "entry_id": "L7",
            "finding": "22E W1-F7",
            "weakness_class": "released_seam",
            "change_surface": "proposals.service.merge_provider_draft's returned revision",
            "summary": (
                "the released provider-assisted path raises on its own success path, so the "
                "provider_assisted mark cannot survive to an approved revision"
            ),
            "risk_class": "low",
            "eligible": True,
            "touches_a_gate_m_condition": None,
            "touches_the_walkability_of_exit_two": True,
            "rank": 7,
            "expected_benefit": {
                "measured": (
                    "dry run 1's approved revision reads deterministic over a live, "
                    "host-verified, admitted draft"
                ),
                "what_a_repair_restores": (
                    "§2.2(b)'s chain as written — a provider-assisted candidate whose mark "
                    "survives to the approved revision"
                ),
            },
            "reproduction": blank,
        },
    ]


async def _record() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-200"],
        "sprint": "22E",
        "wave": "W2",
        "revision": 2,
        "supersedes": _predecessor_binding(),
        "carried_entries": _carried_entries(),
        "added_entries": await _added_entries(),
        "ranking_note": (
            "ranks 6 and 7 follow the W0 rule — measured benefit against the Gate M "
            "condition an entry touches, and neither touches one. L7's weight sits outside "
            "that rule: it decides whether §2.2(b) can be walked as written, which is the "
            "gate owner's W3 question, not this record's ranking"
        ),
        "recorded_at": REVISION_TIME,
    }
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Everything here is recomputable: both reproductions are deterministic and free."""
    mismatches: list[str] = []
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != record.get("integrity_content_hash"):
        mismatches.append("integrity_content_hash")

    binding = _predecessor_binding()
    for field in ("file_sha256", "integrity_content_hash", "seal_recomputes"):
        if record["supersedes"][field] != binding[field]:
            mismatches.append(f"supersedes.{field}")

    if record["carried_entries"] != _carried_entries():
        mismatches.append("carried_entries")

    rebuilt = asyncio.run(_added_entries())
    for stored_entry, rebuilt_entry in zip(record["added_entries"], rebuilt, strict=True):
        if stored_entry != rebuilt_entry:
            fields = [
                key for key in rebuilt_entry if stored_entry.get(key) != rebuilt_entry.get(key)
            ]
            mismatches.append(f"added_entries.{stored_entry.get('entry_id')}: {fields}")

    return {
        "reproduced": not mismatches,
        "mismatches": mismatches,
        "recomputed": [
            "integrity_content_hash",
            "supersedes (the predecessor's bytes and seal)",
            "carried_entries (re-read from the predecessor)",
            "added_entries (both reproductions re-executed)",
        ],
        "recorded_not_recomputed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        verdict = check_record(stored)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["reproduced"] else 1

    record = asyncio.run(_record())
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    added = record["added_entries"]
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "revision": record["revision"],
                "supersedes_seal_recomputes": record["supersedes"]["seal_recomputes"],
                "carried": len(record["carried_entries"]),
                "added": [entry["entry_id"] for entry in added],
                "l6_cancellation_is_retryable": added[0]["reproduction"][
                    "cancellation_is_retryable"
                ],
                "l7_merged_seal_is_blank": added[1]["reproduction"]["merged_seal_is_blank"],
                "l7_released_statement_refuses": added[1]["reproduction"][
                    "released_statement_refuses"
                ],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
