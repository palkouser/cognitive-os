"""S21C3-032 and S21C3-042: what a provider is shown, and how its answer is classified.

Whether a real provider replies at all is a question for `scripts/reality_provider_campaign.py
preflight`, which calls one. What is asked here is everything that must hold before and after
that call: no control material in the prompt, and an answer sorted into the class it actually
belongs to rather than the one that flatters the denominator.
"""

from __future__ import annotations

import pytest

from cognitive_os.coding import reality_leakage, reality_provider
from cognitive_os.coding.reality_provider import (
    ProviderOutcomeClass,
    RepairPatch,
    build_prompt,
    classify,
    prompt_leaks,
)
from cognitive_os.coding.reality_tasks import available_templates, build_manifest, template

from .reality_fixtures import FIXTURE_TIME

TEMPLATE_ID = available_templates()[0]


def _task(template_id: str = TEMPLATE_ID):  # type: ignore[no-untyped-def]
    from uuid import uuid4

    return build_manifest(
        template_id,
        seed=1,
        hidden_bundle_artifact_id=uuid4(),
        hidden_bundle_hash="0" * 64,
        created_at=FIXTURE_TIME,
    )


def _answer(**overrides: object) -> RepairPatch:
    fields: dict[str, object] = {
        "refused": False,
        "refusal_reason": "",
        "unified_diff": "",
        "explanation": "",
    }
    fields.update(overrides)
    return RepairPatch(**fields)  # type: ignore[arg-type]


# ------------------------------------------------------------------ what is shown


def test_no_control_token_reaches_any_assembled_prompt() -> None:
    """W4-F1's regression: the prompt, not the projection, is what actually gets sent."""
    leaks = []
    for template_id in available_templates():
        task, item = _task(template_id), template(template_id)
        prompt = build_prompt(task.projection, item.visible_files)
        leaks.extend(prompt_leaks(prompt, reality_leakage.control_tokens(task, item)))

    assert leaks == []


def test_a_published_test_name_is_not_treated_as_a_secret() -> None:
    """W4-F1: a hidden suite reuses obvious names, and the published one is on screen.

    Before this, one leak per task was reported against prompts carrying nothing but
    material the provider is meant to see — and a scanner with thirty-two false positives
    is a scanner nobody reads.
    """
    task, item = _task(), template(TEMPLATE_ID)
    visible_names = {
        line.removeprefix("def ").split("(")[0]
        for text in item.visible_files.values()
        for line in text.splitlines()
        if line.startswith("def test_")
    }

    tokens = reality_leakage.control_tokens(task, item)

    assert visible_names, "the fixture must actually publish some test names"
    assert not (visible_names & tokens)


def test_the_scanner_still_finds_a_genuinely_hidden_name() -> None:
    """The relaxation must not turn the detector off."""
    task, item = _task(), template(TEMPLATE_ID)
    tokens = reality_leakage.control_tokens(task, item)
    hidden_only = sorted(token for token in tokens if token.startswith("test_"))

    assert hidden_only, "the control bundle must contribute at least one secret test name"
    assert prompt_leaks(f"hint: {hidden_only[0]}", tokens) == (hidden_only[0],)


def test_the_prompt_pins_every_file_it_inlines() -> None:
    """§4.13: inlined and hash-pinned, so a provider reads the bytes the sandbox will run."""
    task, item = _task(), template(TEMPLATE_ID)

    prompt = build_prompt(task.projection, item.visible_files)

    for entry in task.projection.files:
        assert entry.file_hash in prompt, entry.path


def test_the_prompt_names_no_repository_to_go_and_read() -> None:
    task, item = _task(), template(TEMPLATE_ID)

    prompt = build_prompt(task.projection, item.visible_files)

    assert "/verification" not in prompt
    assert "test_hidden_" not in prompt


# ------------------------------------------------------------------ what comes back


def test_a_refusal_is_an_outcome_not_an_error() -> None:
    candidate = classify(
        _answer(refused=True, refusal_reason="not comfortable"),
        task=_task(),
        provider_id="openrouter",
        sources=template(TEMPLATE_ID).visible_files,
    )

    assert candidate.outcome_class is ProviderOutcomeClass.REFUSED
    assert candidate.executable is False
    assert candidate.reason == "not comfortable"


def test_an_unreadable_diff_is_malformed_not_incorrect() -> None:
    """The distinction is the denominator: output format is not repair ability."""
    candidate = classify(
        _answer(unified_diff="here you go, just change the function"),
        task=_task(),
        provider_id="openrouter",
        sources=template(TEMPLATE_ID).visible_files,
    )

    assert candidate.outcome_class is ProviderOutcomeClass.MALFORMED
    assert candidate.executable is False


def test_a_diff_that_does_not_apply_is_malformed() -> None:
    item = template(TEMPLATE_ID)
    path = next(name for name in item.visible_files if name.startswith("src/"))
    diff = (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n+++ b/{path}\n"
        "@@ -1,1 +1,1 @@\n-this line is not in the file\n+replacement\n"
    )

    candidate = classify(
        _answer(unified_diff=diff),
        task=_task(),
        provider_id="openrouter",
        sources=item.visible_files,
    )

    assert candidate.outcome_class is ProviderOutcomeClass.MALFORMED
    assert "does not apply" in (candidate.reason or "")


def test_a_patch_against_a_forbidden_path_is_refused() -> None:
    """A provider that edits the published tests has not repaired anything."""
    task = _task()
    forbidden = task.projection.forbidden_paths[0]
    target = f"{forbidden}/test_smuggled.py"
    diff = (
        f"diff --git a/{target} b/{target}\n"
        f"--- a/{target}\n+++ b/{target}\n@@ -0,0 +1 @@\n+assert True\n"
    )

    candidate = classify(
        _answer(unified_diff=diff),
        task=task,
        provider_id="openrouter",
        sources={target: ""},
    )

    assert candidate.outcome_class is ProviderOutcomeClass.MALFORMED
    assert "forbidden" in (candidate.reason or "")


def test_a_correct_shaped_patch_becomes_an_executable_candidate() -> None:
    """The only class that reaches a container. Correctness is still the verifier's call."""
    from cognitive_os.coding import reality_candidates
    from cognitive_os.domain.reality import RealityCandidateStrategy

    task, item = _task(), template(TEMPLATE_ID)
    generated = reality_candidates.build_candidate(task, RealityCandidateStrategy.CORRECT_NARROW)

    candidate = classify(
        _answer(unified_diff=generated.unified_diff),
        task=task,
        provider_id="openrouter",
        sources=item.visible_files,
    )

    assert candidate.outcome_class is ProviderOutcomeClass.PATCH_PROPOSED
    assert candidate.executable is True
    assert candidate.patched_source is not None
    assert candidate.patch_hash is not None


def test_candidate_identity_is_derived_not_allocated() -> None:
    from cognitive_os.coding import reality_candidates
    from cognitive_os.domain.reality import RealityCandidateStrategy

    task, item = _task(), template(TEMPLATE_ID)
    diff = reality_candidates.build_candidate(
        task, RealityCandidateStrategy.CORRECT_NARROW
    ).unified_diff
    kwargs = {"task": task, "provider_id": "openrouter", "sources": item.visible_files}

    first = classify(_answer(unified_diff=diff), **kwargs)  # type: ignore[arg-type]
    second = classify(_answer(unified_diff=diff), **kwargs)  # type: ignore[arg-type]

    assert first.candidate_id == second.candidate_id


# ------------------------------------------------------------------ who gets what


def test_the_assignment_is_frozen_and_evenly_split() -> None:
    """§4.13: decided before execution, so it cannot be chosen after seeing the scores."""
    providers = ("claude-code", "codex-cli", "openrouter")
    templates = tuple(available_templates())[:30]

    plan = reality_provider.assignment(templates, providers)
    counts = {name: sum(1 for value in plan.values() if value == name) for name in providers}

    assert set(plan) == set(templates)
    assert counts == {name: 10 for name in providers}
    assert plan == reality_provider.assignment(templates, providers)


@pytest.mark.parametrize("adapter", ("openrouter", "claude_code", "codex_cli"))
def test_every_adapter_maps_to_a_provider_candidate_source(adapter: str) -> None:
    """A network answer recorded as `curated` would be self-play contaminated with reality."""
    from cognitive_os.domain.reality import PROVIDER_CANDIDATE_SOURCES

    assert reality_provider.ADAPTER_SOURCES[adapter] in PROVIDER_CANDIDATE_SOURCES
