"""S22D-003 and S22D-004: the two gates W0 left open, and the two that would have let them shut.

W0 finished with `w2_may_proceed: false` and a named owner on each blocking dependency. Closing
them turned out to be less about acquiring things than about what the closing gates would
accept, so most of this file is about the second part.

*A clearance covers bytes, and three of four candidates had none.* The preflight requires the
licence text read out of the distribution rather than transcribed from a model card. Only one
candidate ships a `LICENSE` beside its weights; the rest carry a repository licence *tag*,
which is a publisher's assertion in metadata. The archived text is therefore asserted to be the
bytes the determination covers, and to be the canonical Apache-2.0 text apart from two named
deviations — because "it says Apache License at the top" and "it is the Apache License" are
different facts, and a vendor rider would satisfy the first.

*The licence gate concluded on a file existing.* It read `cleared_by` and `permitted_uses` off
whatever JSON sat at the path and reported `concluded: True`, so an empty object would have
unblocked W2 with `cleared_by: null`. `OperatorLicenseClearance` refuses `unknown` and
`conflicting` on its own — a decision or nothing — so the gate now asks the contract. Both
refusals are executed here rather than described: a gate nobody has watched refuse is a gate
nobody has tested (22A W4-F2).

*The runtime gate concluded on `PATH`.* A binary named `llama-server` on `PATH` is not a
serving runtime for the cleared weights, and after the symlink went in the gate would have said
yes while nothing had ever answered a request. It now wants the sealed serving proof, and the
proof's value is its last step: a real local server's bytes went through the **released**
`openai_compatible.map_response` with no provider-specific branch, which is the half of §1.2
that had only ever been read rather than run.

*Two records describe the same weights.* The clearance names the bytes it covers and the
runtime record names the bytes it served, and nothing would have compared them — which is
exactly where the released-primitive defects of this project live.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

import preflight_22d  # noqa: E402
from benchmark_22d import canonical  # noqa: E402
from model_runtime_22d import (  # noqa: E402
    CANONICAL_APACHE_SHA256,
    DETERMINATION,
    LICENCE_DEVIATIONS,
    LICENCE_TEXT,
    MODEL,
    PROOF_PROMPT,
    WEIGHTS,
    ClearanceRefused,
    advisory_status,
    build_clearance,
)
from tasks_22d import MICROBENCHMARK_TASKS  # noqa: E402

from cognitive_os.domain.corpus import (  # noqa: E402
    CorpusLicenseStatus,
    CorpusUsageRight,
    OperatorLicenseClearance,
)

RIGHTS = EVIDENCE / "sprint-22d-model-rights.json"
RUNTIME = EVIDENCE / "sprint-22d-runtime.json"
PREFLIGHT = EVIDENCE / "sprint-22d-preflight.json"

#: The weights are 6.7 GB and live outside the repository, so anything that reads them skips
#: where they are absent. Everything they produced is committed and asserted unconditionally.
_NEEDS_WEIGHTS = pytest.mark.skipif(
    not WEIGHTS.exists(), reason="the cleared weight file is not on this host"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [RIGHTS, RUNTIME, PREFLIGHT])
def test_every_gate_closure_seal_is_over_its_own_body(path: Path) -> None:
    record = _load(path)
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(canonical(body)).hexdigest() == record["integrity_content_hash"]


# ---------------------------------------------------------------------------
# S22D-003. The clearance, and the bytes it covers
# ---------------------------------------------------------------------------


def test_the_archived_licence_is_the_bytes_the_operator_cleared() -> None:
    """The one hash in this wave that CI can recompute, and therefore the one that binds."""
    record = _load(RIGHTS)
    recomputed = hashlib.sha256(LICENCE_TEXT.read_bytes()).hexdigest()
    assert recomputed == record["clearance"]["evidence_hash"]
    assert record["licence"]["bytes"] == LICENCE_TEXT.stat().st_size


def test_the_archived_licence_is_apache_2_0_and_not_merely_titled_apache_2_0() -> None:
    """A rider appended to a standard text leaves the heading intact.

    So the claim is a comparison rather than a reading: the archived text differs from
    apache.org's own copy only in the appendix copyright line — which is what the appendix is
    for — and a missing trailing newline. A third difference fails this, which is the point of
    naming the two.
    """
    text = LICENCE_TEXT.read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "Copyright 2025 Alibaba Cloud" in text
    record = _load(RIGHTS)
    assert record["licence"]["canonical_apache_2_0_sha256"] == CANONICAL_APACHE_SHA256
    assert tuple(record["licence"]["deviations_from_canonical"]) == LICENCE_DEVIATIONS
    assert record["licence"]["no_added_clause"] is True
    # No acceptable-use policy, no field-of-use restriction, no user-count threshold: the
    # three shapes a vendor rider usually takes on an otherwise permissive text.
    lowered = text.lower()
    assert "acceptable use" not in lowered
    assert "monthly active users" not in lowered


def test_the_program_advised_and_the_operator_decided_and_they_agreed() -> None:
    """Both halves are recorded because the difference between them is the whole design."""
    record = _load(RIGHTS)
    assert advisory_status(MODEL["licence_identifier"]) is CorpusLicenseStatus.APPROVED
    assert record["advisory"]["advisory_status"] == CorpusLicenseStatus.APPROVED.value
    assert record["clearance"]["cleared_by"] == DETERMINATION["cleared_by"]
    assert record["operator_departed_from_the_advice"] is False


def test_an_unrecognised_licence_advises_unknown_rather_than_permitting() -> None:
    """The advisory list's asymmetry, executed. It may quarantine; it may never permit."""
    assert advisory_status("llama3.1") is CorpusLicenseStatus.UNKNOWN
    assert advisory_status("CC-BY-NC-SA-4.0") is CorpusLicenseStatus.UNKNOWN


def test_the_six_withheld_rights_close_the_adapter_by_decision() -> None:
    """The licence would have permitted all eight; the operator granted two.

    That gap is not an omission to be tidied later. Without `modification`,
    `derivative_work` or `model_training` the optional §2.3 adapter is closed by the
    operator's decision as well as by the chemistry corpus being NC-SA — two independent
    reasons, so W4 surplus cannot reopen it by finding spare schedule.
    """
    record = _load(RIGHTS)
    granted = set(record["clearance"]["permitted_uses"])
    assert granted == {
        CorpusUsageRight.INTERNAL_USE.value,
        CorpusUsageRight.BENCHMARK_USE.value,
    }
    withheld = set(record["rights"]["withheld"])
    assert granted | withheld == {right.value for right in CorpusUsageRight}
    assert not granted & withheld
    for closed in ("modification", "derivative_work", "model_training"):
        assert closed in withheld
    assert record["rights"]["the_licence_would_have_permitted_all_eight"] is True


def test_benchmark_use_is_what_makes_the_sprint_numbers_publishable() -> None:
    record = _load(PREFLIGHT)
    assert record["model_licence_gate"]["numbers_are_publishable"] is True


def test_three_of_four_candidates_could_not_have_been_cleared_at_all() -> None:
    """Not because their licences are bad — because there were no bytes to hash."""
    record = _load(RIGHTS)
    rejected = record["candidates_rejected"]
    assert len(rejected) == 3
    assert all(entry["licence_text_in_distribution"] is False for entry in rejected)
    assert record["model"]["repository"] not in {entry["repository"] for entry in rejected}


@_NEEDS_WEIGHTS
def test_the_clearance_covers_the_weight_file_that_is_on_this_host() -> None:
    record = _load(RIGHTS)
    rebuilt = build_clearance()
    assert rebuilt.source_content_hash == record["clearance"]["source_content_hash"]
    assert rebuilt.evidence_hash == record["clearance"]["evidence_hash"]


def test_a_clearance_without_its_evidence_bytes_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The program refusing on its own — the only direction it is allowed to move in."""
    monkeypatch.setattr("model_runtime_22d.LICENCE_TEXT", tmp_path / "absent.txt")
    with pytest.raises(ClearanceRefused, match="auditable"):
        build_clearance()


@_NEEDS_WEIGHTS
def test_a_determination_that_permits_nothing_usable_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Needs the weights, because the refusal it is about comes after the one for their absence.

    The same rule is asserted host-independently against the preflight gate below, so nothing
    goes unchecked where the 6.7 GB file is not on disk — only this driver-level ordering does.
    """
    monkeypatch.setitem(DETERMINATION, "permitted_uses", (CorpusUsageRight.BENCHMARK_USE,))
    with pytest.raises(ClearanceRefused, match="internal use"):
        build_clearance()


# ---------------------------------------------------------------------------
# The licence gate, and what it used to accept
# ---------------------------------------------------------------------------


def test_the_licence_gate_no_longer_concludes_on_a_file_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The defect, replayed. An empty object at this path unblocked W2 with `cleared_by: null`."""
    empty = tmp_path / "sprint-22d-model-rights.json"
    empty.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(preflight_22d, "MODEL_CLEARANCE", empty)
    gate = preflight_22d._model_licence_gate()
    assert gate["concluded"] is False
    assert "why_the_artefact_does_not_conclude_the_gate" in gate


def test_widening_the_grant_after_the_fact_is_caught_by_the_contract_hash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A stronger refusal than the gate's own, and it arrives first.

    `OperatorLicenseClearance` is a hashed experience contract, so the permitted uses are
    covered by the clearance's own digest. Editing the sealed record to grant a right the
    operator did not grant fails on the hash before any rule in this repository looks at the
    value — which is the property that makes the decision belong to the person who made it
    rather than to whoever last had write access to the file.
    """
    record = _load(RIGHTS)
    record["clearance"]["permitted_uses"] = [right.value for right in CorpusUsageRight]
    widened = tmp_path / "sprint-22d-model-rights.json"
    widened.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(preflight_22d, "MODEL_CLEARANCE", widened)
    gate = preflight_22d._model_licence_gate()
    assert gate["concluded"] is False
    assert "hash mismatch" in gate["why_the_artefact_does_not_conclude_the_gate"]


def test_the_gate_refuses_a_coherent_clearance_that_permits_no_internal_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A cleared model that may not be served is not a cleared model.

    Built through the contract rather than edited into the record, so the clearance's own
    digest is correct and the only thing wrong with it is the decision it carries. Otherwise
    this would re-test the hash and never reach the rule it is about.
    """
    stored = _load(RIGHTS)["clearance"]
    coherent = OperatorLicenseClearance(
        identifier=stored["identifier"],
        status=CorpusLicenseStatus.APPROVED,
        permitted_uses=(CorpusUsageRight.BENCHMARK_USE,),
        cleared_by=stored["cleared_by"],
        cleared_at=stored["cleared_at"],
        evidence_hash=stored["evidence_hash"],
        source_content_hash=stored["source_content_hash"],
    )
    narrowed = tmp_path / "sprint-22d-model-rights.json"
    narrowed.write_text(
        json.dumps({"clearance": json.loads(coherent.model_dump_json())}), encoding="utf-8"
    )
    monkeypatch.setattr(preflight_22d, "MODEL_CLEARANCE", narrowed)
    gate = preflight_22d._model_licence_gate()
    assert gate["concluded"] is False
    assert "internal use" in gate["why_the_artefact_does_not_conclude_the_gate"]


def test_an_undecided_determination_cannot_be_constructed_at_all() -> None:
    """`unknown` is an operator declining to decide while looking like one who had.

    The refusal is in the released contract, not in this sprint's driver, so there is no
    version of this record that carries it — which is why the gate never needed a rule of
    its own for the case.
    """
    stored = _load(RIGHTS)["clearance"]
    with pytest.raises(ValidationError, match="absence of one"):
        OperatorLicenseClearance(
            identifier=stored["identifier"],
            status=CorpusLicenseStatus.UNKNOWN,
            permitted_uses=(CorpusUsageRight.INTERNAL_USE,),
            cleared_by=stored["cleared_by"],
            cleared_at=stored["cleared_at"],
            evidence_hash=stored["evidence_hash"],
            source_content_hash=stored["source_content_hash"],
        )


# ---------------------------------------------------------------------------
# S22D-004. The runtime, proved by serving
# ---------------------------------------------------------------------------


def test_the_runtime_gate_is_not_satisfied_by_a_binary_on_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The other defect, replayed — and the reason the symlink alone was not the answer.

    `PATH` is *simulated* rather than read. Asserting that `llama-server` is genuinely
    installed would make this pass only on the host that has it, and everywhere else the
    gate would refuse for the wrong reason and the replay would prove nothing — a test that
    is green in one place and vacuous in every other is the shape 22A W4-F2 warns about.
    """
    monkeypatch.setattr(preflight_22d.shutil, "which", lambda name: f"/simulated/bin/{name}")
    monkeypatch.setattr(preflight_22d, "RUNTIME_PROOF", tmp_path / "absent.json")
    runtime = preflight_22d._local_runtime()
    assert runtime["serving_runtime_installed"] is True
    assert runtime["serving_runtime_available"] is False
    assert runtime["serving_runtime_proved"]["serve_proof_mapped"] is False


def test_the_runtime_gate_is_satisfied_when_the_proof_is_there(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half, so the gate is known to say yes as well as no."""
    monkeypatch.setattr(preflight_22d.shutil, "which", lambda name: f"/simulated/bin/{name}")
    runtime = preflight_22d._local_runtime()
    assert runtime["serving_runtime_available"] is True
    assert runtime["serving_runtime_proved"]["sealed"] is True


def test_an_unsealed_serving_proof_does_not_conclude_the_runtime_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    record = _load(RUNTIME)
    record["serve_proof"]["content"] = "tampered"
    tampered = tmp_path / "sprint-22d-runtime.json"
    tampered.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(preflight_22d, "RUNTIME_PROOF", tampered)
    proved = preflight_22d._serving_proved()
    assert proved["sealed"] is False
    assert proved["serve_proof_mapped"] is False


def test_the_local_server_answered_through_the_released_mapping() -> None:
    """§1.2's claim about the existing seam, executed rather than read off the source."""
    proof = _load(RUNTIME)["serve_proof"]
    assert proof["mapping"] == "cognitive_os.providers.openai_compatible.map_response"
    assert proof["mapped_by_the_released_adapter_seam"] is True
    assert proof["provider_specific_branch_required"] is False
    assert proof["content"], "the server returned content the released mapping normalized"
    # Token accounting arrived through the same mapping. W3's cost exit is built on these
    # two numbers, so a local server that answered without them would be a different
    # problem discovered much later.
    assert proof["output_tokens"] and proof["output_tokens"] > 0
    assert proof["input_tokens"] and proof["input_tokens"] > 0


def test_the_failing_reasoning_configuration_was_run_and_not_merely_avoided() -> None:
    """**GC-F3.** The finding exists because the failing setting was executed.

    A cleared model that happens to be a hybrid reasoner spends its output budget thinking
    unless something says otherwise, and nothing does by default. Recording only the working
    configuration would have left the sprint a pinned flag with no reason attached — and the
    first person to change it would have had nothing to read.
    """
    proof = _load(RUNTIME)["serve_proof"]
    attempts = proof["attempts"]
    assert set(attempts) == {"on", "off"}
    assert attempts["on"]["content_is_empty"] is True
    assert attempts["on"]["finish_reason"] == "length"
    assert attempts["off"]["content_is_empty"] is False
    assert proof["reasoning_of_record"] == "off"
    assert proof["finding"] == "GC-F3"


def test_the_released_mapping_normalized_the_empty_answer_without_complaint() -> None:
    """Why the finding needed running rather than reading.

    `map_response` reads `message.content`. When the whole budget went to thinking it found
    an empty string and returned a valid `ModelProviderResponse` — so an answer nobody wrote
    and an answer the model declined to give arrive downstream in the same shape, and the
    only thing separating them is a token count nobody was comparing.
    """
    attempts = _load(RUNTIME)["serve_proof"]["attempts"]
    assert attempts["on"]["mapped_without_error"] is True
    assert attempts["on"]["output_tokens"] and attempts["on"]["output_tokens"] > 0


def test_the_runtime_harness_is_pinned_rather_than_defaulted() -> None:
    """§1.2 asks for model, quantization, context and sampling pinned and hashed."""
    proof = _load(RUNTIME)["serve_proof"]
    assert proof["sampling"]["temperature"] == 0.0
    assert proof["sampling"]["seed"] == 22
    arguments = proof["server_arguments"]
    assert "--ctx-size" in arguments and "--n-gpu-layers" in arguments
    assert arguments[arguments.index("--n-gpu-layers") + 1] == "0"


def test_the_serving_proof_is_not_a_measurement() -> None:
    """A proof that used one of the frozen hundred would be a measurement in disguise."""
    record = _load(RUNTIME)
    assert record["measured_values"] == 0
    prompts = {str(task["prompt"]) for task in MICROBENCHMARK_TASKS}
    assert PROOF_PROMPT not in prompts
    assert record["serve_proof"]["prompt"] == PROOF_PROMPT


def test_cpu_is_the_configuration_of_record_and_no_layers_were_offloaded() -> None:
    record = _load(RUNTIME)
    assert record["configuration_of_record"] == "cpu"
    assert record["gpu_reported_beside_never_instead"]["gpu_layers_offloaded"] == 0


def test_the_runtime_served_the_weights_the_clearance_covers() -> None:
    """The seam between two records that each judge the same bytes.

    Nothing else compares them: the clearance names what the operator decided about and the
    runtime record names what the server actually loaded, and a mismatch would mean the
    measured model is not the cleared model while both records read clean on their own.
    """
    clearance = _load(RIGHTS)["clearance"]
    proof = _load(RUNTIME)["serve_proof"]
    assert proof["weights_sha256"] == clearance["source_content_hash"]
    assert proof["weight_file"] == MODEL["weight_file"]


def test_what_the_gate_closure_deliberately_did_not_build() -> None:
    """W0-F3 had three lines and this closes one. The other two are released code."""
    outstanding = _load(RUNTIME)["what_this_does_not_yet_provide"]
    assert any("LocalApiProviderConfig" in line for line in outstanding)
    assert any("adapter" in line for line in outstanding)


# ---------------------------------------------------------------------------
# The preflight, re-read
# ---------------------------------------------------------------------------


def test_both_blocking_dependencies_are_closed_and_w2_may_proceed() -> None:
    record = _load(PREFLIGHT)
    assert record["blocking_dependencies"] == []
    assert record["w2_may_proceed"] is True
    assert record["model_licence_gate"]["concluded"] is True
    assert record["model_licence_gate"]["revalidated_against_the_released_contract"] is True
    assert record["local_runtime"]["serving_runtime_available"] is True


#: What W0 sealed for this host, before either gate closed. Pinned so the claim below is a
#: comparison of two *recorded* values rather than a recomputation: `invariants_hash` binds the
#: declared host, and a CI runner is not that host — recomputing it there compares the machine
#: reading the record against the machine that wrote it, which is a different question and one
#: that always answers no.
W0_INVARIANTS_HASH = "122bcd4066feb3c3c4a4b444548afccbeac5d1b5add77336a1dd318cd83c24cd"


def test_the_host_invariants_did_not_move_when_the_gates_closed() -> None:
    """Closing a gate is a change in the world, not in the declared host.

    22B's S22B-002 split is what makes the reseal honest: `invariants_hash` is over the CPU,
    the GPU, the platform and the Python version, and none of them had any business changing
    because a person made a decision. The preflight record's own hash moved and this one did
    not, which is the pair of facts that says the reseal recorded a decision and not a host.
    """
    record = _load(PREFLIGHT)
    assert record["invariants_hash"] == W0_INVARIANTS_HASH
