"""The advisory schema as it goes on the wire, and the failure diagnosis around it.

Every test here exists because the Sprint 21C2 live smoke found the defect it covers. None
of them could have failed in CI before, because CI never sends the schema anywhere and never
starts a CLI that can exit non-zero for an interesting reason. They are written against the
*shape* the providers demand rather than against a captured response, so they keep holding
without a credential.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from cognitive_os.providers.advisory_schema import (
    ADVISORY_JSON_SCHEMA,
    STRICT_ADVISORY_JSON_SCHEMA,
    AdvisoryResult,
    advisory_schema_json,
)
from cognitive_os.providers.claude_code.advisory import FAILURE_DIAGNOSTIC_KEYS, failure_details


def _object_nodes(node: Any) -> list[dict[str, Any]]:
    """Every schema node that declares properties, including those under `$defs`."""
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if isinstance(node.get("properties"), dict):
            found.append(node)
        for value in node.values():
            found.extend(_object_nodes(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_object_nodes(item))
    return found


class TestTheStrictSchemaSatisfiesStructuredOutput:
    """`codex exec --output-schema` forwards the schema to a backend that enforces
    OpenAI's strict subset and rejects the turn with a 400 otherwise."""

    def test_every_object_requires_all_of_its_properties(self) -> None:
        nodes = _object_nodes(STRICT_ADVISORY_JSON_SCHEMA)
        assert nodes, "the schema declares no object nodes"
        for node in nodes:
            assert sorted(node["properties"]) == node["required"], node.get("title")

    def test_every_object_forbids_additional_properties(self) -> None:
        for node in _object_nodes(STRICT_ADVISORY_JSON_SCHEMA):
            assert node["additionalProperties"] is False, node.get("title")

    def test_the_defaulted_fields_are_the_ones_that_were_missing(self) -> None:
        """Pydantic omits defaulted fields from `required`; those five were the 400."""
        pydantic_required = set(ADVISORY_JSON_SCHEMA.get("required", ()))
        assert {"findings", "recommendations", "risks", "verification_steps"} - pydantic_required
        finding = STRICT_ADVISORY_JSON_SCHEMA["$defs"]["AdvisoryFinding"]
        assert "evidence" in finding["required"]

    def test_what_goes_on_the_wire_is_the_strict_schema(self) -> None:
        assert json.loads(advisory_schema_json()) == STRICT_ADVISORY_JSON_SCHEMA

    def test_it_is_canonical_so_two_runs_write_the_same_bytes(self) -> None:
        rendered = advisory_schema_json()
        assert rendered == advisory_schema_json()
        # Compact separators, so the file a CLI flag points at is byte-stable. Property
        # titles legitimately contain spaces, so only the separators are checked.
        assert ", " not in rendered
        assert ": " not in rendered

    def test_the_contract_still_accepts_an_answer_shaped_by_the_strict_schema(self) -> None:
        """Requiring every field costs nothing on the way back: empty arrays validate."""
        result = AdvisoryResult.model_validate(
            {
                "summary": "ok",
                "findings": [],
                "recommendations": [],
                "risks": [],
                "verification_steps": [],
            }
        )
        assert result.findings == ()

    def test_the_pydantic_schema_is_the_one_that_was_incomplete(self) -> None:
        """`extra="forbid"` already gave us `additionalProperties: false`. The 400 was
        `required`, and the contract's own schema still declares only `summary`."""
        assert ADVISORY_JSON_SCHEMA["additionalProperties"] is False
        assert ADVISORY_JSON_SCHEMA["required"] == ["summary"]
        assert STRICT_ADVISORY_JSON_SCHEMA["required"] == sorted(ADVISORY_JSON_SCHEMA["properties"])


class TestClaudeFailureDiagnosis:
    """Claude Code reports why it stopped on stdout, so a bare non-zero exit said nothing."""

    def test_an_exhausted_turn_budget_is_named(self) -> None:
        envelope = json.dumps(
            {
                "is_error": True,
                "subtype": "error_max_turns",
                "stop_reason": "tool_use",
                "num_turns": 2,
                "duration_api_ms": 6275,
                "result": "a partial answer nobody should retain",
            }
        )
        details = failure_details(envelope)
        assert details["likely_cause"] == "the run reached its configured maximum turns"
        assert details["envelope_subtype"] == "error_max_turns"
        assert details["envelope_num_turns"] == 2

    def test_no_message_body_is_ever_copied_into_the_diagnosis(self) -> None:
        """A failing run can still hold model prose, which this boundary never retains."""
        prose = "a partial answer nobody should retain"
        details = failure_details(
            json.dumps({"is_error": True, "subtype": "error_during_execution", "result": prose})
        )
        rendered = json.dumps(details)
        assert prose not in rendered
        assert all(key.startswith("envelope_") or key == "likely_cause" for key in details)

    @pytest.mark.parametrize("stdout", ["", "not json", "[1,2,3]", "null"])
    def test_unparsable_output_yields_no_keys_rather_than_a_guess(self, stdout: str) -> None:
        assert failure_details(stdout) == {}

    def test_only_scalar_metadata_keys_are_reported(self) -> None:
        details = failure_details(
            json.dumps({"subtype": {"nested": "object"}, "num_turns": 3, "usage": {"tokens": 1}})
        )
        assert details == {"envelope_num_turns": 3}

    def test_the_allowlist_names_no_content_field(self) -> None:
        assert "result" not in FAILURE_DIAGNOSTIC_KEYS
        assert "message" not in FAILURE_DIAGNOSTIC_KEYS
