"""S22D-003 and S22D-004. The two blocking dependencies W0 surfaced, closed.

W0 finished around two gates and named an owner for each: no model had been cleared, and
nothing on this host could serve one. `w2_may_proceed` was `false` and stayed false on
purpose — §3.2's rule is that a "temporary" model is worse than no model, because a benchmark
run on unclear weights is evidence that cannot be released.

**S22D-003, the clearance.** The division of labour is 22C's W1-D2 and it is not negotiable:
this program reads a licence, recognises it if it can, and *advises*; the operator decides.
So the search was run under a constraint that turned out to be decisive — the preflight
requires the licence text **read out of the distribution**, not transcribed from a model card,
and of the four candidates only one ships a `LICENSE` beside its weights. A repository licence
*tag* is a model-card assertion in a different font. Where there are no bytes there is nothing
to hash, and a clearance that cannot name the bytes it covers is exactly what
`OperatorLicenseClearance.source_content_hash` exists to prevent.

What this driver may refuse, and does: a licence whose archived bytes no longer hash to the
value the decision was made about, and a determination that does not permit the material to be
used at all. What it may not do, and does not: supply the determination. `DETERMINATION` below
is the operator's answer, recorded; if it were absent this driver would have nothing to seal.

**S22D-004, the runtime.** `llama-server` from a pinned llama.cpp release, CPU build, because
CPU is §1.3's configuration of record. The choice is evidential rather than aesthetic: the
clearance has to name **the SHA-256 of the weight file**, and a runtime that hides its weights
behind its own blob store and its own manifest digest cannot produce that number. A plain GGUF
on disk can.

The proof is not that a binary exists on `PATH`. It is that the server answered a request and
that the **released** `providers/openai_compatible.map_response` normalized the answer without
a provider-specific branch — which is the half of §1.2 that had never been executed. The
prompt is deliberately trivial and outside the frozen hundred: this is a serving proof, not a
measurement, and `measured_values` stays at zero until W3 says otherwise.

**Recomputable here, observed there.** 22B's S22B-002 split decides what `--check` may assert.
The licence bytes are archived in this repository, so their hash is an *invariant* and CI
recomputes it. The weight file is 6.7 GB and lives outside the repository, so its hash is an
*observation*: recomputed where the file exists, and compared against nothing where it does
not. A `--check` that demanded the weights would fail everywhere except this host, which is
how a green check stops meaning anything.

    UV_CACHE_DIR=.cache/uv uv run python scripts/model_runtime_22d.py --clear
    UV_CACHE_DIR=.cache/uv uv run python scripts/model_runtime_22d.py --serve
    UV_CACHE_DIR=.cache/uv uv run python scripts/model_runtime_22d.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid5

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import NAMESPACE, SLICE_TIME, canonical  # noqa: E402

from cognitive_os.corpus.factory import RECOGNISED_PERMISSIVE_LICENSES  # noqa: E402
from cognitive_os.domain.corpus import (  # noqa: E402
    CorpusLicenseStatus,
    CorpusUsageRight,
    OperatorLicenseClearance,
)
from cognitive_os.domain.model_requests import (  # noqa: E402
    ProviderMessage,
    ProviderMessageRole,
)
from cognitive_os.providers.openai_compatible import map_response  # noqa: E402

RIGHTS_RECORD = EVIDENCE / "sprint-22d-model-rights.json"
RUNTIME_RECORD = EVIDENCE / "sprint-22d-runtime.json"

#: The licence bytes the determination was made about, archived here so the decision can be
#: audited by someone who never had the weights. A clearance whose evidence is a dead URL is
#: a clearance nobody can check.
LICENCE_TEXT = EVIDENCE / "sprint-22d-model-licence.txt"

#: Everything large lives outside the repository. Neither path is committed, and neither is
#: allowed to be a `--check` invariant.
RUNTIME_HOME = Path("/home/palkouser/projekt/cognitive-os-data/s22d-runtime")
WEIGHTS = RUNTIME_HOME / "models/Qwen3-8B-Q6_K.gguf"
SERVER = RUNTIME_HOME / "llama-b10442/llama-server"


# ---------------------------------------------------------------------------
# The operator's determination — recorded, never derived
# ---------------------------------------------------------------------------

#: **The gate owner's answer, and the only part of this file a program did not decide.**
#:
#: The two rights are the ones the preflight named: `internal_use` is the minimum for the
#: weights to be served at all, and `benchmark_use` is what makes the sprint's measured
#: numbers publishable. The other six are *withheld*, which is a decision with consequences
#: and not an omission — see `_rights_not_granted`.
DETERMINATION: dict[str, Any] = {
    "cleared_by": "palkouser (Sprint 22 gate owner)",
    "status": CorpusLicenseStatus.APPROVED,
    "permitted_uses": (CorpusUsageRight.INTERNAL_USE, CorpusUsageRight.BENCHMARK_USE),
}

MODEL = {
    "repository": "Qwen/Qwen3-8B-GGUF",
    "revision": "7c41481f57cb95916b40956ab2f0b139b296d974",
    "weight_file": "Qwen3-8B-Q6_K.gguf",
    "quantization": "Q6_K",
    "parameter_class": "8B",
    "licence_identifier": "Apache-2.0",
    "licence_url": "https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/LICENSE",
    #: The publisher's own object id for this file, read from the distribution's tree rather
    #: than from the download. It is a SHA-256 over the same bytes, so it answers a question
    #: local hashing cannot: whether what was cleared is what was published, or an artifact
    #: of a transfer that nobody would have noticed truncating.
    "publisher_lfs_oid": "cb042ccd76795a8830d6be6bd4165245847cc68e41797b13bd61aed4c2cfbce6",
    "publisher_reported_bytes": 6725899040,
    "why_this_quantization": (
        "seventy of the hundred frozen tasks are closed-form computation and quantization "
        "damage lands hardest on arithmetic, so Q6_K buys the accuracy that matters; Q8_0 "
        "costs thirty per cent more for almost nothing and 46 GiB of RAM makes Q4_K_M's "
        "thrift pointless"
    ),
    "why_this_distribution": (
        "the only candidate of four that ships its licence text with its weights. The other "
        "three carry a repository licence tag and no LICENSE file, which is a model-card "
        "assertion — and 22C W1-D2 forbids transcribing a nominated licence"
    ),
}

#: What the platform's own short list says, on its own, before anyone decided anything. It is
#: kept beside the determination rather than instead of it, so a later reader can see whether
#: the operator agreed with the program or overruled it.
ADVISORY_SOURCE = "cognitive_os.corpus.factory.RECOGNISED_PERMISSIVE_LICENSES"

#: Fetched from apache.org and diffed against the archived text. Recorded because "it says
#: Apache 2.0 at the top" is not the same fact as "it is the Apache 2.0 text".
CANONICAL_APACHE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"

#: The two differences the diff found, both benign, both named so that a future run finding a
#: third one has something to fail against.
LICENCE_DEVIATIONS = (
    "the appendix copyright line is filled in as 'Copyright 2025 Alibaba Cloud', which is the "
    "appendix's documented purpose",
    "no trailing newline at end of file",
)

RUNTIME = {
    "name": "llama-server",
    "project": "ggml-org/llama.cpp",
    "release_tag": "b10442",
    "build_commit": "9b0a2ce85",
    "asset": "llama-b10442-bin-ubuntu-x64.tar.gz",
    "asset_sha256": "a447495bdf503af09a1874ebbb450927171da2c84c68cc4eae27c9789ca37b0e",
    "acceleration": "cpu",
    "why_not_a_model_manager": (
        "the clearance must name the SHA-256 of the weight file it covers. A runtime that "
        "stores weights in its own blob store under its own manifest digest cannot produce "
        "that number, so it cannot serve material this contract can describe"
    ),
}

#: Deliberately outside the frozen hundred, and deliberately dull. A serving proof that used a
#: benchmark task would be a measurement wearing a proof's clothes.
PROOF_PROMPT = "Reply with exactly the word: ready"

PROOF_PORT = 8127
PROOF_TIMEOUT_SECONDS = 240


class ClearanceRefused(RuntimeError):
    """Raised where this program is allowed to refuse — and it is only ever allowed to refuse."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    record["integrity_content_hash"] = _sha256(canonical(body))
    return record


def _write(path: Path, record: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# S22D-003. The clearance
# ---------------------------------------------------------------------------


def advisory_status(identifier: str) -> CorpusLicenseStatus:
    """What the platform thinks on its own. Advice, and the ceiling of what it may do."""
    if identifier in RECOGNISED_PERMISSIVE_LICENSES:
        return CorpusLicenseStatus.APPROVED
    return CorpusLicenseStatus.UNKNOWN


def _rights_not_granted() -> dict[str, Any]:
    """The six rights the operator withheld, and what withholding them actually closes.

    Apache-2.0 would permit all eight. The operator granted two. That gap is the whole point
    of the contract — the licence sets a ceiling and the operator sets the grant — so it is
    recorded as a consequence rather than left to be inferred from a short list.
    """
    granted = set(DETERMINATION["permitted_uses"])
    withheld = tuple(sorted(right.value for right in CorpusUsageRight if right not in granted))
    return {
        "withheld": withheld,
        "the_licence_would_have_permitted_all_eight": True,
        "what_the_withheld_rights_close": (
            "without modification, derivative_work or model_training the optional adapter of "
            "§2.3 is closed by the operator's own decision, independently of the chemistry "
            "corpus being NC-SA. Two separate reasons now point the same way, and W4 surplus "
            "cannot reopen either of them by finding spare schedule"
        ),
        "what_the_granted_rights_open": (
            "internal_use lets the weights be served at all; benchmark_use lets the numbers "
            "W3 measures be published. Every exit criterion in this sprint is reachable"
        ),
    }


def build_clearance() -> OperatorLicenseClearance:
    """Construct the operator's decision as the released contract, or refuse to.

    Two refusals live here and both are the program refusing, which is the only direction it
    is permitted to move in. Neither can be turned into a permission by editing this file:
    the first compares bytes, and the second asks whether the determination permits the
    material to be used at all.
    """
    if not LICENCE_TEXT.exists():
        raise ClearanceRefused(
            "the licence bytes the determination was made about are not archived; a clearance "
            "that cannot show its evidence is not auditable"
        )
    evidence_hash = _sha256_file(LICENCE_TEXT)
    if not WEIGHTS.exists():
        raise ClearanceRefused(
            f"the weight file named by the determination is absent at {WEIGHTS}; a clearance "
            "covers bytes and there are none to cover"
        )
    if CorpusUsageRight.INTERNAL_USE not in DETERMINATION["permitted_uses"]:
        raise ClearanceRefused(
            "the determination does not permit internal use, so the weights may not be served "
            "and there is nothing for W2 to do with them"
        )
    weights_hash = _sha256_file(WEIGHTS)
    if weights_hash != MODEL["publisher_lfs_oid"]:
        raise ClearanceRefused(
            "the weight file on this host is not the file the publisher published: its "
            f"SHA-256 is {weights_hash} and the distribution's object id is "
            f"{MODEL['publisher_lfs_oid']}. Clearing it would attach a person's name to bytes "
            "nobody can trace back to a source"
        )
    return OperatorLicenseClearance(
        identifier=MODEL["licence_identifier"],
        status=DETERMINATION["status"],
        permitted_uses=DETERMINATION["permitted_uses"],
        cleared_by=DETERMINATION["cleared_by"],
        cleared_at=SLICE_TIME,
        evidence_hash=evidence_hash,
        source_content_hash=weights_hash,
        notes=(
            f"{MODEL['repository']}@{MODEL['revision']}, {MODEL['weight_file']}. The licence "
            "text was read out of the distribution beside the weights and archived as "
            f"{LICENCE_TEXT.name}, not transcribed from the model card."
        ),
    )


def rights_record() -> dict[str, Any]:
    clearance = build_clearance()
    advice = advisory_status(MODEL["licence_identifier"])
    licence_bytes = LICENCE_TEXT.read_bytes()
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22D-003"],
        "closes": "the model_licence blocking dependency W0 surfaced with a named owner",
        "model": dict(MODEL),
        "licence": {
            "read_from_the_distribution": True,
            "archived_as": LICENCE_TEXT.name,
            "sha256": clearance.evidence_hash,
            "bytes": len(licence_bytes),
            "identified_as": MODEL["licence_identifier"],
            "canonical_apache_2_0_sha256": CANONICAL_APACHE_SHA256,
            "deviations_from_canonical": list(LICENCE_DEVIATIONS),
            "no_added_clause": True,
            "why_the_diff_and_not_the_title": (
                "a vendor may append an acceptable-use rider to an otherwise standard text "
                "and the heading will still read Apache License. The text was diffed against "
                "apache.org's own copy, so 'permissive' is a comparison rather than a guess"
            ),
        },
        "advisory": {
            "advisory_status": advice.value,
            "recognised_by": ADVISORY_SOURCE,
            "the_program_may_not_permit": (
                "this status is advice. It became a permission only because a named person "
                "decided it did, and the two are kept in the same record so the difference "
                "stays visible"
            ),
        },
        "clearance": json.loads(clearance.model_dump_json()),
        "operator_departed_from_the_advice": advice is not clearance.status,
        "rights": _rights_not_granted(),
        "weights_are_an_observation": {
            "path": str(WEIGHTS),
            "sha256": clearance.source_content_hash,
            "bytes": WEIGHTS.stat().st_size,
            "matches_the_publisher_object_id": (
                clearance.source_content_hash == MODEL["publisher_lfs_oid"]
            ),
            "why_that_comparison_and_not_just_a_local_hash": (
                "a local hash proves the file did not change after it landed. The publisher's "
                "own object id is what says the file that landed is the file that was "
                "published — the two questions look alike and only one of them is about "
                "provenance"
            ),
            "why_not_an_invariant": (
                "6.7 GB cannot live in this repository, so `--check` recomputes this hash "
                "where the file exists and compares it against nothing where it does not. "
                "The licence bytes are archived and therefore *are* recomputed everywhere"
            ),
        },
        "candidates_rejected": [
            {
                "repository": "bartowski/Mistral-7B-Instruct-v0.3-GGUF",
                "licence_tag": "apache-2.0",
                "licence_text_in_distribution": False,
                "upstream": "mistralai/Mistral-7B-Instruct-v0.3 ships no licence file either",
            },
            {
                "repository": "unsloth/Phi-4-mini-instruct-GGUF",
                "licence_tag": "mit",
                "licence_text_in_distribution": False,
                "upstream": (
                    "microsoft/Phi-4-mini-instruct ships a LICENSE, but it covers a different "
                    "repository's bytes and source_content_hash exists to catch exactly that "
                    "drift"
                ),
            },
            {
                "repository": "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
                "licence_tag": "llama3.1",
                "licence_text_in_distribution": False,
                "upstream": (
                    "meta-llama/Llama-3.1-8B-Instruct is gated:manual and its identifier is "
                    "not one the platform recognises, so the advice would have been 'unknown'"
                ),
            },
        ],
        "what_the_search_found": (
            "three of four candidates could not satisfy the preflight's own requirement, and "
            "not for a reason about their licences being bad. A licence tag is metadata a "
            "publisher types; a LICENSE file beside the weights is bytes that shipped with "
            "them. The requirement to hash the second is what made the difference visible"
        ),
    }
    return _seal(record)


# ---------------------------------------------------------------------------
# S22D-004. The runtime, proved by serving rather than by existing
# ---------------------------------------------------------------------------


def _wait_for_health(port: int, deadline: float) -> bool:
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as reply:
                if reply.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(2)
    return False


def _post_completion(port: int, prompt: str) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": MODEL["weight_file"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "seed": 22,
            "max_tokens": 64,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=PROOF_TIMEOUT_SECONDS) as reply:
        return json.loads(reply.read().decode("utf-8"))


def _proof_request() -> Any:
    from cognitive_os.domain.model_requests import ModelProviderRequest

    return ModelProviderRequest(
        model_call_id=uuid5(NAMESPACE, "s22d-serving-proof-call"),
        task_run_id=uuid5(NAMESPACE, "s22d-serving-proof-run"),
        correlation_id=uuid5(NAMESPACE, "s22d-serving-proof-correlation"),
        requested_model=MODEL["weight_file"],
        messages=(ProviderMessage(role=ProviderMessageRole.USER, content=PROOF_PROMPT),),
        temperature=0.0,
        max_output_tokens=64,
    )


#: **GC-F3.** The cleared model is a hybrid reasoning model, so how much of its output budget
#: goes to thinking is a *runtime configuration* rather than a property of the weights — and
#: it is left unpinned by every mainstream default. Both settings are executed and both are
#: recorded: the finding is only a finding because the failing configuration was run.
REASONING_MODES = ("on", "off")

#: The proof of record. W3 measures bounded answers and accounts for their tokens, and a
#: reasoning budget nobody set is a budget the model sets.
REASONING_OF_RECORD = "off"

#: Pinned here rather than left to the server's defaults, because §1.2 asks for the runtime
#: harness — model, quantization, context, sampling — pinned and hashed.
SAMPLING = {"temperature": 0.0, "seed": 22, "max_tokens": 64}
SERVER_ARGS = ("--threads", "16", "--ctx-size", "2048", "--n-gpu-layers", "0")


def _serve_once(reasoning: str) -> dict[str, Any]:
    """One server lifetime, one request, one normalization through the released mapping."""
    process = subprocess.Popen(
        [
            str(SERVER),
            "--model",
            str(WEIGHTS),
            "--port",
            str(PROOF_PORT),
            "--host",
            "127.0.0.1",
            "--reasoning",
            reasoning,
            *SERVER_ARGS,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + PROOF_TIMEOUT_SECONDS
        if not _wait_for_health(PROOF_PORT, deadline):
            raise ClearanceRefused("the serving runtime did not become healthy")
        started = time.monotonic()
        raw = _post_completion(PROOF_PORT, PROOF_PROMPT)
        latency_ms = (time.monotonic() - started) * 1000
        normalized = map_response(
            raw,
            _proof_request(),
            provider_id="local-model-under-measurement",
            latency_ms=latency_ms,
        )
    finally:
        process.terminate()
        process.wait(timeout=30)
    return {
        "reasoning": reasoning,
        "content": normalized.content,
        "content_is_empty": not (normalized.content or "").strip(),
        "resolved_model": normalized.resolved_model,
        "finish_reason": normalized.finish_reason.value,
        "input_tokens": normalized.usage.input_tokens if normalized.usage else None,
        "output_tokens": normalized.usage.output_tokens if normalized.usage else None,
        "total_tokens": normalized.usage.total_tokens if normalized.usage else None,
        "mapped_without_error": True,
    }


def serve_proof() -> dict[str, Any]:
    """Start the server on the cleared weights, ask it one thing, and normalize the answer.

    §1.2 claims a local model reaches the governed path through the existing
    `openai_compatible` seam. Until a real local server's bytes went through `map_response`
    that was a reading of the source rather than a fact about the wire, and running it turned
    up something the reading could not have: with thinking left on, this model spends the
    whole output budget inside a `<think>` block, `map_response` reads `message.content`,
    finds it empty, and **normalizes it without complaint**. An answer nobody wrote and an
    answer the model declined to give arrive in the same shape.
    """
    if not SERVER.exists():
        raise ClearanceRefused(f"no serving runtime at {SERVER}")
    if not WEIGHTS.exists():
        raise ClearanceRefused(f"no cleared weights at {WEIGHTS}")
    attempts = {mode: _serve_once(mode) for mode in REASONING_MODES}
    proof = attempts[REASONING_OF_RECORD]
    if proof["content_is_empty"]:
        raise ClearanceRefused(
            "the configuration of record returned no assistant content, so nothing here "
            "demonstrates that the runtime can answer"
        )
    return {
        "prompt": PROOF_PROMPT,
        # The bytes that were served, so this record and the clearance can be checked against
        # each other. Two records describing the same weights and neither reading the other's
        # verdict is where the defects live.
        "weights_sha256": _sha256_file(WEIGHTS),
        "weight_file": MODEL["weight_file"],
        "sampling": dict(SAMPLING),
        "server_arguments": list(SERVER_ARGS),
        "reasoning_of_record": REASONING_OF_RECORD,
        "attempts": attempts,
        "content": proof["content"],
        "resolved_model": proof["resolved_model"],
        "finish_reason": proof["finish_reason"],
        "input_tokens": proof["input_tokens"],
        "output_tokens": proof["output_tokens"],
        "total_tokens": proof["total_tokens"],
        "mapped_by_the_released_adapter_seam": True,
        "mapping": "cognitive_os.providers.openai_compatible.map_response",
        "provider_specific_branch_required": False,
        "finding": "GC-F3",
        "what_the_failing_configuration_costs_later": (
            "the frozen escalation policy escalates when the answer form is invalid, and the "
            "accounting exit divides cost by answers produced. A model thinking past its "
            "budget returns empty content with finish_reason 'length' — so W3 would have "
            "escalated every task and charged for output nobody could read, and the record "
            "would have called it a capability result"
        ),
        "why_the_prompt_is_dull": (
            "a serving proof that used one of the frozen hundred would be a measurement, and "
            "the manifest still reports measured_values: 0"
        ),
    }


def runtime_record(proof: dict[str, Any]) -> dict[str, Any]:
    on_path = shutil.which("llama-server")
    version = subprocess.run(
        [str(SERVER), "--version"], capture_output=True, text=True, check=False
    )
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22D-004"],
        "closes": "the local_serving_runtime blocking dependency, W0-F3",
        "runtime": dict(RUNTIME),
        "binary": {
            "path": str(SERVER),
            "sha256": _sha256_file(SERVER),
            "version_output": (version.stderr or version.stdout).strip().splitlines()[:2],
            "discoverable_on_path": on_path is not None,
            "path_entry": on_path,
            "why_on_path": (
                "the preflight probes PATH, and a runtime that is not on PATH is not installed "
                "in any sense the harness can act on. The binary itself stays outside the "
                "repository with the weights"
            ),
        },
        "configuration_of_record": "cpu",
        "gpu_reported_beside_never_instead": {
            "gpu_layers_offloaded": 0,
            "why": (
                "§1.3 makes CPU the measured configuration because the exit asks about owned "
                "resources rather than speed. The prebuilt Linux assets carry no CUDA build, "
                "and this host's GPU is newer than the toolkit installed, so a GPU number "
                "would need its own preflight before it meant anything"
            ),
        },
        "serve_proof": proof,
        "measured_values": 0,
        "what_this_does_not_yet_provide": [
            "a LocalApiProviderConfig member of the discriminated provider union",
            "an adapter that constructs it through providers/openai_compatible.py",
        ],
        "why_that_is_still_W2": (
            "the blocking dependency was a runtime on this host for the cleared weights, and "
            "that is what this record closes. The union member and the adapter are W0-F3's "
            "other two lines and they are released code, which belongs in a wave rather than "
            "in a gate closure"
        ),
    }
    return _seal(record)


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------


def check() -> int:
    findings: list[str] = []
    report: dict[str, Any] = {}
    for path in (RIGHTS_RECORD, RUNTIME_RECORD):
        if not path.exists():
            findings.append(f"{path.name} is absent")
            continue
        stored = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        report[path.name] = {"sealed": sealed}
        if not sealed:
            findings.append(f"{path.name} is not sealed")

    if RIGHTS_RECORD.exists() and LICENCE_TEXT.exists():
        stored = json.loads(RIGHTS_RECORD.read_text(encoding="utf-8"))
        recomputed = _sha256_file(LICENCE_TEXT)
        matches = recomputed == stored["clearance"]["evidence_hash"]
        report["licence_evidence_recomputed"] = {
            "sha256": recomputed,
            "matches_the_clearance": matches,
        }
        if not matches:
            findings.append("the archived licence bytes are not the bytes that were cleared")
        # The contract's own validators are the check that matters: `unknown` and
        # `conflicting` are refused here rather than in a rule this file could relax.
        OperatorLicenseClearance.model_validate(stored["clearance"])
        report["clearance_revalidates_against_the_released_contract"] = True

    if RIGHTS_RECORD.exists():
        stored = json.loads(RIGHTS_RECORD.read_text(encoding="utf-8"))
        observed = WEIGHTS.exists()
        report["weights_observation"] = {
            "present_on_this_host": observed,
            "sha256_matches": (_sha256_file(WEIGHTS) == stored["clearance"]["source_content_hash"])
            if observed
            else None,
            "why_none_is_not_a_failure": (
                "an observation compared against nothing where the world does not hold it"
            ),
        }
        if observed and not report["weights_observation"]["sha256_matches"]:
            findings.append("the weight file on this host is not the file that was cleared")

    report["findings"] = findings
    print(json.dumps(report, indent=1, sort_keys=True))
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear", action="store_true", help="seal S22D-003")
    parser.add_argument("--serve", action="store_true", help="seal S22D-004")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        return check()

    if arguments.clear:
        record = rights_record()
        _write(RIGHTS_RECORD, record)
        print(
            json.dumps(
                {
                    "item": "S22D-003",
                    "cleared_by": record["clearance"]["cleared_by"],
                    "permitted_uses": record["clearance"]["permitted_uses"],
                    "weights_sha256": record["clearance"]["source_content_hash"],
                    "licence_sha256": record["clearance"]["evidence_hash"],
                    "departed_from_the_advice": record["operator_departed_from_the_advice"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
            )
        )

    if arguments.serve:
        record = runtime_record(serve_proof())
        _write(RUNTIME_RECORD, record)
        print(
            json.dumps(
                {
                    "item": "S22D-004",
                    "content": record["serve_proof"]["content"],
                    "finish_reason": record["serve_proof"]["finish_reason"],
                    "output_tokens": record["serve_proof"]["output_tokens"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
            )
        )

    if not (arguments.clear or arguments.serve):
        parser.error("choose --clear, --serve or --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
