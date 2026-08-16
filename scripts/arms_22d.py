"""S22D-200..203. W2's three baseline arms on the frozen hundred.

W0 built the runner and proved it on ten fixture tasks with a simulated answerer. W2 replaces
the simulation with three real ones and changes nothing else: `run_arm` still owns verification,
accounting, escalation and the citation walk, and an arm still owns only what it answered. That
split is what keeps the four arms comparable, and it is why this wave is a set of answerers
rather than a second runner.

**S22D-200, priced before anything runs.** 22C W3-F1 is a standing rule in this sprint's §0 and
W1 has already been caught breaking it once: *a verification floor's coverage is priced before
the campaign, not after.* The `retrieval_only` arm is deliberately model-free — it returns what
the index found and nothing interprets it — so its ceiling is decided entirely by what Layer 1
holds, and Layer 1 holds eight facts. That ceiling is computed and sealed **before** the first
arm runs, so the number it produces is read rather than explained afterwards.

**Nothing here is tuned.** §2.3 forbids changing a pre-registered configuration after its first
measured number exists, and it equally forbids the quieter version: reshaping the arms until the
comparator looks respectable. The arms run as frozen and the coverage record says what that
means.

**The three answerers, and the one rule they share.** Each is asked for a strict answer form and
each **refuses to repair** what comes back. A reader that turns "about 3500 newtons" into
`{"magnitude": "3500"}` is scoring its own parser, and by W3 nobody would be able to tell the
model's competence from the leniency of a regular expression. A malformed answer is recorded as
malformed, and counted apart from an answer the verifier could not decide — those are different
facts, which is W0-F1 generalised.

**`external_teacher` goes through the governed boundary**, not around it: a registry, a
`ModelExecutionService`, and `GovernedTeacherService.execute_with_receipt`, so every call leaves
a receipt with a retention directive and a rights decision. The decision recorded is `unknown`
and the retention is `none`: nobody has cleared a model's output for reuse, and this wave does
not reuse it — it scores it and discards it. The per-call request and response hashes are
digested into the arm record, so a hundred calls leave one value a later reader can check.

**The free route drops about one call in four**, returning 404 when no capacity is spare. That
is a transport failure rather than an answer, so it is retried a bounded number of times — and
**every attempt is counted as an external call**, because counting only the successful one
would shrink the very baseline §2.2(c) measures the reduction against.

    UV_CACHE_DIR=.cache/uv uv run python scripts/arms_22d.py --coverage
    UV_CACHE_DIR=.cache/uv uv run python scripts/arms_22d.py --arm external_teacher
    UV_CACHE_DIR=.cache/uv uv run python scripts/arms_22d.py --arm no_memory
    UV_CACHE_DIR=.cache/uv uv run python scripts/arms_22d.py --arm retrieval_only
    UV_CACHE_DIR=.cache/uv uv run python scripts/arms_22d.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from benchmark_22d import (  # noqa: E402
    ABSTENTION_VALUE,
    SLICE_TIME,
    ArmOutcome,
    Citation,
    canonical,
    run_arm,
)
from chapter_22c import CHEMISTRY, PHYSICS, page_text  # noqa: E402
from facts_22d import CONSTANT_ALIASES, ELEMENT_ALIASES  # noqa: E402
from model_runtime_22d import (  # noqa: E402
    MODEL,
    REASONING_OF_RECORD,
    SAMPLING,
    SERVER,
    SERVER_ARGS,
    WEIGHTS,
)
from tasks_22d import MICROBENCHMARK_TASKS  # noqa: E402

ACQUISITION = EVIDENCE / "sprint-22d-w1-acquisition.json"
COVERAGE_OUTPUT = EVIDENCE / "sprint-22d-w2-retrieval-coverage.json"

#: One sealed record per arm, so a re-run of one arm cannot quietly restate another.
ARM_OUTPUTS = {
    "external_teacher": EVIDENCE / "sprint-22d-w2-external-teacher.json",
    "no_memory": EVIDENCE / "sprint-22d-w2-no-memory.json",
    "retrieval_only": EVIDENCE / "sprint-22d-w2-retrieval-only.json",
}

#: W2 runs three of the four. `local_model` is W3's, read once, on the acquired layer.
W2_ARMS = ("external_teacher", "no_memory", "retrieval_only")

PORT = 8128
LOCAL_TIMEOUT_SECONDS = 180
SERVER_START_SECONDS = 300

#: **The teacher of record, and it is not the first one tried.** OpenRouter's free tier allows
#: fifty free-model requests a day, so a hundred-task arm could never have completed there —
#: not a capacity problem to retry around, an arithmetic one. That run is kept sealed as
#: `sprint-22d-w2-external-teacher-abandoned.json`, because a route swapped *without* the
#: evidence for the swap is a route swapped until the number was liked.
EXTERNAL_PROVIDER_ID = "claude-code"
#: This sprint's own live configuration, untracked like every other. Kept apart from
#: `providers.live.local.yaml` because that file records Gate C2's operator decision that data
#: collection stays denied — true in its own scope, and not this sprint's to edit. Free
#: endpoints are free because providers may train on the prompts, so a request that denies data
#: collection matches no free endpoint and returns 404; the operator enabled publication on the
#: account and chose this arm, and this file is the request side of that same decision.
EXTERNAL_CONFIG = REPO / "config/providers.s22d.local.yaml"

#: **A teacher must be named.** `openrouter/free` is a router rather than a model, and a
#: baseline that may be served by a different model per task is not a baseline — §2.2(c) reads
#: the reduction against *this* arm. Where an adapter has no slug of its own the provider is
#: named instead, which is honest where an empty string would make two receipts look alike.
#:
#: The choice is deliberately unflattering to the sprint either way. This arm is the bar the
#: local model must come within three points of, so a weak teacher would make the
#: non-inferiority margin easy and the cost reduction cheap, and both exits would pass for a
#: reason that has nothing to do with the local model.
EXTERNAL_MODEL_BY_ADAPTER = {"openrouter": "nvidia/nemotron-3-ultra-550b-a55b:free"}

#: Filled when the service is built, so the record names the teacher it actually used rather
#: than the one this module was last edited to prefer.
TEACHER_OF_RECORD: dict[str, str] = {}


def requested_model(config: Any) -> str:
    """What the receipt calls the model that was asked for.

    A CLI agent carries no slug unless the operator pinned one, and naming the provider is
    honest where an empty string would make two different receipts look alike — the same
    reading `scripts/provider.py` takes.
    """
    pinned = EXTERNAL_MODEL_BY_ADAPTER.get(config.adapter.value)
    return pinned or getattr(config, "model", None) or f"{config.adapter.value}:default"


class ArmRefused(RuntimeError):
    """Raised where this module is allowed to refuse, which is the only way it may stop."""


class ExternalQuotaExhausted(ArmRefused):
    """**W2-F4.** The allowance ran out, and continuing would produce a record about it.

    Kept apart from every other provider failure because the response differs: a capacity 404
    is worth another attempt, and a spent daily allowance makes every further attempt spend
    allowance the run still needs. An arm that grinds on regardless does not fail — it
    finishes, with a number that reads as the teacher being weak.
    """


def _is_quota_exhausted(error: Exception) -> bool:
    """Whether this failure is the daily allowance rather than a transient one.

    Read off the status code and the provider's own words rather than guessed from the
    message, so a provider that starts phrasing it differently degrades to retrying rather
    than to silently mislabelling something else as a quota.
    """
    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if getattr(cause, "status_code", None) == 429:
            return True
        body = getattr(cause, "body", None)
        if isinstance(body, dict) and int(body.get("code") or 0) == 429:
            return True
        cause = cause.__cause__ or cause.__context__
    return False


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _seal(record: dict[str, Any]) -> dict[str, Any]:
    record["recorded_at"] = SLICE_TIME.isoformat().replace("+00:00", "Z")
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    record["integrity_content_hash"] = _sha256(canonical(body))
    return record


def _write(path: Path, record: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# The answer forms, asked for strictly and never repaired
# ---------------------------------------------------------------------------

#: What each verifier's subject type needs, expressed once. The instruction and the reader are
#: written next to each other on purpose: they are two halves of one contract, and a wave that
#: loosens the reader without loosening the instruction has started scoring its own parser.
ANSWER_FORMS: dict[str, dict[str, str]] = {
    "physical_quantity": {
        "instruction": "Reply with a magnitude and a unit on one line and nothing else, "
        "for example: 3500 N",
        "example": "3500 N",
    },
    "mathematical_expression": {
        "instruction": "Reply with a single number on one line and nothing else, for example: 3500",
        "example": "3500",
    },
    "structured_value": {
        "instruction": "Reply with a single word on one line and nothing else, for example: pascal",
        "example": "pascal",
    },
}

_NUMBER = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
_QUANTITY = re.compile(r"^([+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\s+(\S+)$")
_WORD = re.compile(r"^[A-Za-z][A-Za-z\- ]{0,40}$")


def build_prompt(task: Mapping[str, Any]) -> str:
    """One prompt, assembled from the task and its answer form. No retrieval, no examples.

    The abstention is offered explicitly because §2.2(d) requires a *typed* abstention the
    runtime produces and the verifier recognises. A model that cannot emit the value cannot
    express uncertainty in a way this exit can read, and the alternative — detecting hedging
    phrases in prose — would turn the exit into a string-matching exercise.
    """
    form = ANSWER_FORMS[str(task["subject_type"])]
    return (
        f"{task['prompt']}\n\n"
        f"{form['instruction']}. "
        f"If you do not know the answer, reply with exactly: {ABSTENTION_VALUE}"
    )


def read_answer(task: Mapping[str, Any], text: str) -> tuple[Any, bool, bool]:
    """Return `(answer, abstained, form_valid)`. Refuses; never repairs.

    The last line is taken rather than the whole body, because a model that reasons before it
    answers still ends on the answer — but nothing is extracted from *inside* a sentence. If
    the final line is not the requested form, the text is recorded as it arrived and marked
    malformed, which is a different fact from a verifier that could not decide.
    """
    stripped = (text or "").strip()
    if not stripped:
        return "", False, False
    if ABSTENTION_VALUE in stripped:
        return None, True, True
    line = stripped.splitlines()[-1].strip().rstrip(".")
    subject = str(task["subject_type"])
    if subject == "physical_quantity":
        match = _QUANTITY.match(line)
        if match is None:
            return line, False, False
        return {"magnitude": match.group(1), "unit": match.group(2)}, False, True
    if subject == "mathematical_expression":
        if _NUMBER.match(line) is None:
            return line, False, False
        return line, False, True
    if _WORD.match(line) is None:
        return line, False, False
    return line, False, True


# ---------------------------------------------------------------------------
# S22D-200. What the model-free arm could possibly answer, priced first
# ---------------------------------------------------------------------------


def retained_facts() -> list[dict[str, Any]]:
    if not ACQUISITION.exists():
        raise ArmRefused("W1's acquisition record is absent; there is no layer to retrieve from")
    return list(json.loads(ACQUISITION.read_text(encoding="utf-8"))["retained"])


def _alias_terms(subject: str) -> tuple[str, ...]:
    """Every way an asker might name what the source wrote. **W1-F3, carried and paid.**

    The layer is keyed as the source writes (`Cl`, `Na`, `g`) and asked as the asker speaks
    ("chlorine", "standard gravitational field strength"). Without this step every case misses
    for a plumbing reason and the record reads as a coverage failure, which is the wrong
    diagnosis entirely.
    """
    key = subject.strip()
    terms = {key.casefold()}
    for source in (ELEMENT_ALIASES, CONSTANT_ALIASES):
        for spoken, written in source.items():
            if written.casefold() == key.casefold():
                terms.add(spoken.casefold())
    return tuple(sorted(terms))


def _matches(task: Mapping[str, Any], fact: Mapping[str, Any]) -> bool:
    """Whether this task asks for the quantity this fact holds — both halves required.

    Naming the entity is not enough: a derivation mentions potassium and does not ask for its
    atomic mass. The quantity word has to be in the prompt too, which is what keeps the
    model-free arm from answering a question it was not asked.
    """
    prompt = str(task["prompt"]).casefold()
    if not any(
        re.search(rf"\b{re.escape(term)}\b", prompt) for term in _alias_terms(str(fact["subject"]))
    ):
        return False
    quantity = str(fact["quantity"]).casefold()
    if "atomic mass" in quantity or "average mass" in quantity:
        return "atomic mass" in prompt or "relative atomic mass" in prompt
    if "constant" in quantity:
        return "acceleration due to gravity" in prompt or "gravitational" in prompt
    return False


def coverage() -> dict[str, Any]:
    """**S22D-200.** The model-free arm's ceiling, computed before a single arm runs."""
    facts = retained_facts()
    servable: list[dict[str, Any]] = []
    for task in MICROBENCHMARK_TASKS:
        for fact in facts:
            if _matches(task, fact):
                servable.append(
                    {
                        "task_id": str(task["task_id"]),
                        "output_kind": str(task["output_kind"]),
                        "subject": fact["subject"],
                        "quantity": fact["quantity"],
                        "ladder_status": fact["ladder_status"],
                    }
                )
                break
    by_kind: dict[str, int] = {}
    for task in MICROBENCHMARK_TASKS:
        by_kind[str(task["output_kind"])] = by_kind.get(str(task["output_kind"])) or 0
    record = {
        "schema_version": 1,
        "items": ["S22D-200"],
        "published_before": "S22D-201, S22D-202 and S22D-203",
        "why_this_record_exists_at_all": (
            "22C W3-F1, carried into this sprint's §0 and already broken once by W0: a "
            "verification floor's coverage is priced before the campaign, not after. The "
            "retrieval_only arm is the ten-point margin's comparator and it is model-free by "
            "design, so its ceiling is decided entirely by what Layer 1 holds — and that "
            "ceiling is a fact about the instrument, not a result"
        ),
        "layer_facts": len(facts),
        "tasks": len(MICROBENCHMARK_TASKS),
        "tasks_the_layer_could_serve": len(servable),
        "servable": servable,
        "measured_values": 0,
        "one_alias_was_added_before_any_arm_ran": {
            "finding": "W1-F3",
            "alias": ["standard acceleration due to gravity", "acceleration due to gravity"],
            "resolves_to": "g",
            "moved_servable_from": 3,
            "moved_servable_to": 4,
            "why_this_is_a_debt_and_not_a_tuning": (
                "the layer already holds the quantity — the source states g = 9.80 m/s2 at "
                "ladder status 'grounded' — and the miss was a vocabulary gap between the "
                "source's notation and the microbenchmark's wording. W1-F3 named exactly this "
                "and said the alias belongs on the fact. A miss for a plumbing reason reported "
                "as a coverage failure is the wrong diagnosis, which is what that finding is "
                "for. Nothing in the frozen hundred, the eight facts or the arm's design "
                "changed, no measured number existed, and the movement is stated here rather "
                "than left to be noticed"
            ),
        },
        "what_this_does_not_license": (
            "re-cutting the hundred, widening the arm, or adding an interpreter to it. §2.3 "
            "forbids tuning a pre-registered configuration, and W1-F1's repair was to publish "
            "the pricing and read the instrument as frozen — not to reshape it once the shape "
            "of the answer was visible"
        ),
    }
    return _seal(record)


# ---------------------------------------------------------------------------
# The local runtime, started once per arm rather than once per task
# ---------------------------------------------------------------------------


@contextmanager
def local_server() -> Iterator[None]:
    """One server lifetime for a whole arm. A hundred model loads is not a measurement."""
    if not SERVER.exists() or not WEIGHTS.exists():
        raise ArmRefused("the cleared weights or the serving runtime are absent on this host")
    process = subprocess.Popen(
        [
            str(SERVER),
            "--model",
            str(WEIGHTS),
            "--port",
            str(PORT),
            "--host",
            "127.0.0.1",
            # **GC-F3, pinned.** Left unset this model spends the whole output budget inside a
            # think block and returns empty content that `map_response` normalizes happily.
            "--reasoning",
            REASONING_OF_RECORD,
            *SERVER_ARGS,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + SERVER_START_SECONDS
        healthy = False
        while time.monotonic() < deadline and not healthy:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as reply:
                    healthy = reply.status == 200
            except (urllib.error.URLError, OSError, TimeoutError):
                time.sleep(2)
        if not healthy:
            raise ArmRefused("the serving runtime did not become healthy")
        yield
    finally:
        process.terminate()
        process.wait(timeout=60)


def _ask_local(prompt: str) -> tuple[str, int, int, float]:
    payload = json.dumps(
        {
            "model": MODEL["weight_file"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": SAMPLING["temperature"],
            "seed": SAMPLING["seed"],
            "max_tokens": 128,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=LOCAL_TIMEOUT_SECONDS) as reply:
        raw = json.loads(reply.read().decode("utf-8"))
    seconds = time.monotonic() - started
    usage = raw.get("usage") or {}
    content = raw["choices"][0]["message"].get("content") or ""
    return (
        content,
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
        seconds,
    )


# ---------------------------------------------------------------------------
# The three answerers
# ---------------------------------------------------------------------------

#: Recorded per task so a malformed answer is never confused with a verifier that could not
#: decide — W0-F1's distinction, applied one layer further out.
MALFORMED: dict[str, list[str]] = {}

#: One entry per governed external call. Retention is `none`, so nothing durable is written —
#: these hashes are digested into the arm record instead, which is how a hundred calls leave a
#: single value a later reader can check rather than a hundred they must trust.
RECEIPTS: list[dict[str, Any]] = []

#: Every failed attempt, and every task that ran out of them. Recorded rather than smoothed:
#: a baseline whose provider dropped a quarter of its calls is a different baseline from one
#: that answered cleanly, and a reader who cannot see that cannot judge the comparison.
PROVIDER_FAILURES: list[dict[str, Any]] = []
EXHAUSTED: list[dict[str, Any]] = []

#: Three tries and a widening pause. The free route's 404 is capacity, not correctness, so a
#: bounded retry is ordinary robustness — but the bound is small on purpose, because a run
#: that retries indefinitely reports availability it does not have.
EXTERNAL_ATTEMPTS = 3
EXTERNAL_BACKOFF_SECONDS = 4.0


def no_memory_answerer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
    """The local model with nothing behind it: no retrieval, no layer, no citation.

    It therefore cannot ground anything. Every factual output it asserts lands as an
    ungrounded assertion unless it abstains, which is exactly the reading §2.2(d) wants from
    this arm and the reason the slice's `no_memory` row was the most useful one in W0.
    """
    text, input_tokens, output_tokens, seconds = _ask_local(build_prompt(task))
    answer, abstained, form_valid = read_answer(task, text)
    if not form_valid:
        MALFORMED.setdefault(arm, []).append(str(task["task_id"]))
    return ArmOutcome(
        task_id=str(task["task_id"]),
        arm=arm,
        answer=None if abstained else answer,
        abstained=abstained,
        answer_form_valid=form_valid,
        local_model_calls=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        local_compute_seconds=round(seconds, 3),
    )


def build_retrieval_index() -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    """The acquired layer, and the exact bytes its spans were measured against."""
    facts = retained_facts()
    sources: dict[str, bytes] = {}
    for fact in facts:
        key = f"{fact['source_key']}-ch{fact['chapter']}"
        if key in sources:
            continue
        profile = CHEMISTRY if fact["source_key"] == "chemistry" else PHYSICS
        chapter = next(item for item in profile.chapters if item.number == fact["chapter"])
        sources[key] = page_text(profile.path, *chapter.body).encode("utf-8")
    return facts, sources


def retrieval_only_answerer(facts: list[dict[str, Any]], sources: Mapping[str, bytes]) -> Any:
    """**Model-free by design.** It returns what the index found, and nothing interprets it.

    Where the index holds the quantity the task asks for, the answer is the value the layer
    holds, carrying the grounded span that put it there — a citation the released walk resolves
    by loading the cited bytes. Where it does not, the arm emits the typed abstention rather
    than reaching for something adjacent: a derivation mentions potassium and does not ask for
    its atomic mass, and answering it anyway would be interpretation by another name.
    """

    def answer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
        for fact in facts:
            if not _matches(task, fact):
                continue
            key = f"{fact['source_key']}-ch{fact['chapter']}"
            data = sources[key]
            start, end = int(fact["span"]["start"]), int(fact["span"]["end"])
            citation = Citation(
                source_id=key,
                content_hash=_sha256(data[start:end]),
                start=start,
                end=end,
            )
            value = str(fact["value"])
            shaped: Any = (
                {"magnitude": value, "unit": str(fact["unit"] or "")}
                if str(task["subject_type"]) == "physical_quantity"
                else value
            )
            return ArmOutcome(
                task_id=str(task["task_id"]),
                arm=arm,
                answer=shaped,
                abstained=False,
                citations=(citation,),
            )
        return ArmOutcome(task_id=str(task["task_id"]), arm=arm, answer=None, abstained=True)

    return answer


def external_teacher_answerer(service: Any, config: Any) -> Any:
    """The only arm in this sprint that reaches a network, and it goes through the boundary.

    Every call leaves a receipt carrying a retention directive and a rights decision. The
    decision is `unknown` and the retention is `hash_only` deliberately: nobody has cleared a
    model's output for reuse, and this wave does not reuse it — it scores it and discards it.
    Recording `verified` here would be this program making a determination that is not its to
    make (22C W1-D2).
    """
    from cognitive_os.application.services.governed_teacher import (
        RightsDecision,
        VerifierOutcome,
    )
    from cognitive_os.domain.model_requests import (
        ModelProviderRequest,
        ProviderMessage,
        ProviderMessageRole,
    )
    from cognitive_os.domain.provider_output import (
        ProviderAdapterKind,
        ProviderOutputIntendedUse,
        ProviderOutputRetentionMode,
        ProviderOutputVerifierStatus,
        ProviderRetentionDirective,
        UsageRightsDecision,
    )
    from cognitive_os.providers.errors import ProviderError

    async def answer(arm: str, task: Mapping[str, Any]) -> ArmOutcome:
        return await _answer_with_attempts(arm, task, service, config)

    async def _answer_with_attempts(
        arm: str, task: Mapping[str, Any], service: Any, config: Any
    ) -> ArmOutcome:
        """One task, up to `EXTERNAL_ATTEMPTS` calls, every attempt counted.

        The free 550 B route has finite capacity and returns 404 when none is spare — about
        one call in four during the diagnostic. That is a transport failure, not an answer,
        and the released retry policy does not classify it as transient, so the whole run died
        at the first one.

        **Every attempt is counted as an external call.** The alternative — counting only the
        successful one — would shrink the baseline that §2.2(c)'s twenty-five per cent
        reduction is measured against, which is the direction that flatters this sprint. When
        a number can be counted two ways, the honest one is the one that makes the exit harder.
        """
        attempts = 0
        last: Exception | None = None
        for index in range(EXTERNAL_ATTEMPTS):
            attempts += 1
            try:
                return await _one_call(arm, task, service, config, attempts)
            except ProviderError as error:
                last = error
                quota = _is_quota_exhausted(error)
                PROVIDER_FAILURES.append(
                    {
                        "task_id": str(task["task_id"]),
                        "attempt": attempts,
                        "error": type(error).__name__,
                        "quota_exhausted": quota,
                    }
                )
                # **W2-F4.** A retry policy that cannot tell "try again" from "you have no
                # budget left" turns a bounded failure into an exhausted quota. A 404 is
                # capacity and is worth another attempt; a 429 is the daily allowance, and
                # every further attempt spends allowance the run still needs. Stop the whole
                # arm rather than grinding the remaining tasks into the same wall.
                if quota:
                    raise ExternalQuotaExhausted(
                        "the provider's free-model daily allowance is exhausted; the run is "
                        "abandoned rather than continued into a record that would report "
                        "provider availability as teacher capability"
                    ) from error
                if index + 1 < EXTERNAL_ATTEMPTS:
                    await asyncio.sleep(EXTERNAL_BACKOFF_SECONDS * (index + 1))
        # Out of attempts. The teacher was called and produced nothing usable, which is a
        # result about this arm rather than a reason to abandon the run — and it is emphatically
        # not an abstention: the model never said it did not know.
        EXHAUSTED.append(
            {"task_id": str(task["task_id"]), "error": type(last).__name__ if last else None}
        )
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer="",
            abstained=False,
            answer_form_valid=False,
            external_provider_calls=attempts,
        )

    async def _one_call(
        arm: str, task: Mapping[str, Any], service: Any, config: Any, attempts: int
    ) -> ArmOutcome:
        request = ModelProviderRequest(
            model_call_id=uuid4(),
            task_run_id=uuid4(),
            correlation_id=uuid4(),
            requested_model=requested_model(config),
            messages=(ProviderMessage(role=ProviderMessageRole.USER, content=build_prompt(task)),),
            temperature=0.0,
            max_output_tokens=getattr(config, "maximum_output_tokens", None),
        )
        receipt = await service.execute_with_receipt(
            request,
            directive=ProviderRetentionDirective(
                intended_use=ProviderOutputIntendedUse.EVALUATION_EVIDENCE,
                # `none`, and it is the honest one rather than the weak one. Anything durable
                # requires an Event Store because the governance ledger names the exact
                # completed model-call envelope — and this wave has nothing to retain: it
                # scores an answer and discards it. The execution receipt still carries the
                # request hash and the normalized response hash, and those are digested into
                # the arm record, so a hundred calls leave one verifiable value behind.
                retention_mode=ProviderOutputRetentionMode.NONE,
            ),
            adapter_kind=ProviderAdapterKind(config.adapter.value),
            rights=RightsDecision(decision=UsageRightsDecision.UNKNOWN),
            verifier=VerifierOutcome(status=ProviderOutputVerifierStatus.NOT_RUN),
        )
        response = receipt.execution.response
        RECEIPTS.append(
            {
                "task_id": str(task["task_id"]),
                "request_hash": receipt.execution.request_hash,
                "normalized_response_hash": receipt.execution.normalized_response_hash,
                "resolved_model": receipt.execution.resolved_model,
                "retention_mode": receipt.execution.retention_mode.value,
            }
        )
        parsed, abstained, form_valid = read_answer(task, response.content or "")
        if not form_valid:
            MALFORMED.setdefault(arm, []).append(str(task["task_id"]))
        usage = response.usage
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer=None if abstained else parsed,
            abstained=abstained,
            answer_form_valid=form_valid,
            external_provider_calls=attempts,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )

    return answer


def _external_service() -> tuple[Any, Any]:
    from cognitive_os.application.services.model_execution import ModelExecutionService
    from cognitive_os.config.provider_config import load_provider_configuration
    from cognitive_os.providers.factory import build_provider
    from cognitive_os.providers.registry import ProviderRegistry

    if not EXTERNAL_CONFIG.exists():
        raise ArmRefused(f"no live provider configuration at {EXTERNAL_CONFIG}")
    configuration = load_provider_configuration(EXTERNAL_CONFIG)
    config = configuration.providers.get(EXTERNAL_PROVIDER_ID)
    if config is None:
        raise ArmRefused(f"{EXTERNAL_PROVIDER_ID} is not configured")
    # The same two keys `scripts/provider.py` requires. This module does not get a cheaper
    # door into a live provider than the operator entry point has.
    if not (config.enabled and config.live_smoke_enabled):
        raise ArmRefused(
            f"{EXTERNAL_PROVIDER_ID} is configured but live execution is not enabled for it"
        )
    from cognitive_os.application.services.governed_teacher import GovernedTeacherService

    TEACHER_OF_RECORD["provider_id"] = config.provider_id
    TEACHER_OF_RECORD["adapter"] = config.adapter.value
    TEACHER_OF_RECORD["requested_model"] = requested_model(config)
    registry = ProviderRegistry()
    registry.register(build_provider(config))
    service = GovernedTeacherService(
        ModelExecutionService(registry, default_provider_id=config.provider_id),
        repository=_memory_repository(),
    )
    return service, config


def _memory_repository() -> Any:
    from cognitive_os.infrastructure.learned.memory_provider_output import (
        InMemoryProviderOutputRepository,
    )

    return InMemoryProviderOutputRepository()


# ---------------------------------------------------------------------------
# Running one arm
# ---------------------------------------------------------------------------


async def run_one(arm: str) -> dict[str, Any]:
    if arm not in W2_ARMS:
        raise ArmRefused(f"W2 runs {W2_ARMS}; {arm!r} is not one of them")
    MALFORMED.pop(arm, None)
    facts, sources = build_retrieval_index()

    if arm == "retrieval_only":
        answerer = retrieval_only_answerer(facts, sources)
        accounting = await run_arm(arm, MICROBENCHMARK_TASKS, answerer, sources)
    elif arm == "no_memory":
        with local_server():
            accounting = await run_arm(arm, MICROBENCHMARK_TASKS, no_memory_answerer, sources)
    else:
        service, config = _external_service()
        answerer = external_teacher_answerer(service, config)
        accounting = await run_arm(arm, MICROBENCHMARK_TASKS, answerer, sources)

    malformed = sorted(MALFORMED.get(arm, ()))
    record = {
        "schema_version": 1,
        "items": [f"S22D-20{W2_ARMS.index(arm) + 1}"],
        "arm": arm,
        "tasks": len(MICROBENCHMARK_TASKS),
        "measured_values": len(MICROBENCHMARK_TASKS),
        "accounting": accounting.as_json(),
        "malformed_answers": len(malformed),
        "malformed_task_ids": malformed,
        "why_malformed_is_counted_apart": (
            "'the arm produced no readable answer', 'the verifier could not decide this "
            "answer' and 'the verifier could not start' are three different facts. W0-F1 was "
            "the third being reported as the second; this keeps the first from joining them"
        ),
        "answer_form_instructions": {
            key: value["instruction"] for key, value in sorted(ANSWER_FORMS.items())
        },
        "nothing_was_repaired": (
            "the readers refuse a malformed answer and record it as it arrived. A reader that "
            "extracted a number from a sentence would be scoring itself, and by W3 nobody "
            "could separate the model's competence from the leniency of a regular expression"
        ),
    }
    if arm == "no_memory":
        record["runtime"] = {
            "model": MODEL["weight_file"],
            "quantization": MODEL["quantization"],
            "reasoning": REASONING_OF_RECORD,
            "sampling": dict(SAMPLING),
            "server_arguments": list(SERVER_ARGS),
            "weights_sha256": MODEL["publisher_lfs_oid"],
        }
    if arm == "external_teacher":
        record["governance"] = {
            "boundary": "cognitive_os.application.services.governed_teacher",
            "intended_use": "evaluation_evidence",
            "retention_mode": "none",
            "rights_decision": "unknown",
            "teacher": dict(TEACHER_OF_RECORD),
            "why_the_teacher_is_named_and_strong": (
                "openrouter/free is a router, and a baseline served by a different model per "
                "task is not a baseline. The strongest free route was chosen on purpose: this "
                "arm is the bar the local model must come within the non-inferiority margin "
                "of, so a weak teacher would make two exits pass for a reason that has "
                "nothing to do with the local model"
            ),
            "receipts": len(RECEIPTS),
            "receipts_digest": _sha256(canonical(RECEIPTS)),
            "attempts_per_task_limit": EXTERNAL_ATTEMPTS,
            "failed_attempts": len(PROVIDER_FAILURES),
            "tasks_that_exhausted_their_attempts": len(EXHAUSTED),
            "exhausted_task_ids": sorted(item["task_id"] for item in EXHAUSTED),
            "why_every_attempt_counts_as_a_call": (
                "the free route returns 404 when no capacity is spare — about one call in "
                "four in the diagnostic — and counting only the successful attempt would "
                "shrink the baseline §2.2(c)'s twenty-five per cent reduction is measured "
                "against. When a number can be counted two ways, the honest one is the one "
                "that makes the exit harder to pass"
            ),
            "an_exhausted_task_is_not_an_abstention": (
                "the model never said it did not know; the provider never answered. Recording "
                "it as a typed abstention would credit this arm with the one thing §2.2(d) "
                "rewards, for a network failure"
            ),
            "what_the_digest_binds": (
                "every call's request hash and normalized response hash, in order. Retention "
                "is none because this wave scores an answer and discards it, so one verifiable "
                "value stands in for a hundred nobody would check"
            ),
            "why_unknown_and_hash_only": (
                "nobody has cleared a model's output for reuse and this wave does not reuse "
                "it. Recording 'verified' would be this program making a determination that "
                "belongs to the operator (22C W1-D2)"
            ),
        }
    return _seal(record)


def check() -> int:
    findings: list[str] = []
    report: dict[str, Any] = {}
    for path in (COVERAGE_OUTPUT, *ARM_OUTPUTS.values()):
        if not path.exists():
            report[path.name] = {"present": False}
            continue
        stored = json.loads(path.read_text(encoding="utf-8"))
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(canonical(body)) == stored["integrity_content_hash"]
        report[path.name] = {"present": True, "sealed": sealed}
        if not sealed:
            findings.append(f"{path.name} is not sealed")
    if COVERAGE_OUTPUT.exists() and ACQUISITION.exists():
        rebuilt = coverage()
        stored = json.loads(COVERAGE_OUTPUT.read_text(encoding="utf-8"))
        identical = rebuilt["integrity_content_hash"] == stored["integrity_content_hash"]
        report["coverage_rebuilds_identically"] = identical
        if not identical:
            findings.append("the retrieval coverage does not rebuild from the sealed layer")
    report["findings"] = findings
    print(json.dumps(report, indent=1, sort_keys=True))
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", action="store_true", help="seal S22D-200")
    parser.add_argument("--arm", choices=W2_ARMS)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        return check()
    if arguments.coverage:
        record = coverage()
        _write(COVERAGE_OUTPUT, record)
        print(
            json.dumps(
                {
                    "item": "S22D-200",
                    "layer_facts": record["layer_facts"],
                    "tasks_the_layer_could_serve": record["tasks_the_layer_could_serve"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0
    if arguments.arm:
        if not COVERAGE_OUTPUT.exists():
            raise ArmRefused(
                "S22D-200 has not been sealed. The comparator's coverage is priced before the "
                "campaign, not after (22C W3-F1, and W1-F1 is this sprint already paying for it)"
            )
        record = asyncio.run(run_one(arguments.arm))
        _write(ARM_OUTPUTS[arguments.arm], record)
        accounting = record["accounting"]
        print(
            json.dumps(
                {
                    "arm": arguments.arm,
                    "verified": accounting["verified"],
                    "abstained": accounting["abstained"],
                    "grounded": accounting["grounded"],
                    "ungrounded_assertions": accounting["ungrounded_assertions"],
                    "undecidable": accounting["undecidable"],
                    "malformed_answers": record["malformed_answers"],
                    "external_provider_calls": accounting["external_provider_calls"],
                    "integrity_content_hash": record["integrity_content_hash"],
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0
    parser.error("choose --coverage, --arm or --check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
