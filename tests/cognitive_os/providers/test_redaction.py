"""Redaction and secret scanning, against adversarially shaped payloads.

Two separate claims are tested separately on purpose. Redaction says "this value will not
appear in what we persist". Scanning says "we looked, and here is what we found". A test
suite that only exercised redaction would pass while a failed scan was being silently
converted into a pass — which is the specific failure the tri-state exists to prevent.
"""

from __future__ import annotations

import pytest

from cognitive_os.domain.provider_output import SecretScanStatus
from cognitive_os.providers.redaction import (
    REDACTED,
    REDACTION_RULESET_VERSION,
    environment_secret_values,
    is_secret_like_name,
    redact_for_diagnostics,
    redact_text,
    redact_value,
    scan_for_secrets,
)

SEEDED = {
    "openrouter": "sk-or-v1-" + "a" * 32,  # pragma: allowlist secret
    "openai": "sk-" + "b" * 32,  # pragma: allowlist secret
    "anthropic": "sk-ant-" + "c" * 32,  # pragma: allowlist secret
    "github": "ghp_" + "d" * 36,  # pragma: allowlist secret
    "google": "AIza" + "e" * 35,  # pragma: allowlist secret
    "aws": "AKIA" + "F" * 16,  # pragma: allowlist secret
    "slack": "xoxb-" + "1" * 24,  # pragma: allowlist secret
    "bearer": "Bearer " + "f" * 40,  # pragma: allowlist secret
    "url": "https://user:hunter2secret@provider.test/v1",  # pragma: allowlist secret
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N",
    "identity": "operator@example.test",
}


class TestValueShapedSecrets:
    @pytest.mark.parametrize("name", sorted(SEEDED))
    def test_every_seeded_secret_shape_is_masked(self, name: str) -> None:
        secret = SEEDED[name]
        redacted = redact_text(f"the provider said: {secret} and then stopped")
        assert secret not in redacted
        assert REDACTED in redacted

    def test_a_private_key_block_is_masked(self) -> None:
        block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow==\n"
        assert "BEGIN RSA PRIVATE KEY" not in redact_text(block)

    def test_ordinary_text_survives_unchanged(self) -> None:
        """A redactor that mangles normal prose gets turned off, and then nothing is safe."""
        prose = "The function returns a - b where it should return a + b."
        assert redact_text(prose) == prose


class TestNameShapedSecrets:
    @pytest.mark.parametrize(
        "name",
        [
            "api_key",
            "API-KEY",
            "authorization",
            "x-api-key",
            "session_key",
            "refresh_token",
            "OPENROUTER_API_KEY",
            "COGOS_MINIMAX_API_KEY",
            "aws_session_token",
            "my.password",
            "private_key",
        ],
    )
    def test_a_secret_like_name_is_recognised(self, name: str) -> None:
        assert is_secret_like_name(name)

    @pytest.mark.parametrize("name", ["PATH", "HOME", "model", "keyboard_layout", "tokenizer"])
    def test_an_ordinary_name_is_not(self, name: str) -> None:
        """`tokenizer` and `keyboard_layout` contain 'token' and 'key' as substrings."""
        assert not is_secret_like_name(name)

    def test_a_secret_named_field_is_masked_whatever_its_value_looks_like(self) -> None:
        payload = {"authorization": "plainvalue", "model": "vendor/model:free"}
        assert redact_value(payload) == {
            "authorization": REDACTED,
            "model": "vendor/model:free",
        }


class TestAdversarialShapes:
    def test_a_secret_nested_several_levels_deep_is_masked(self) -> None:
        payload = {
            "response": {
                "choices": [
                    {"message": {"content": f"key is {SEEDED['openrouter']}"}},
                ],
                "meta": {"headers": {"Authorization": SEEDED["bearer"]}},
            }
        }
        rendered = str(redact_value(payload))
        assert SEEDED["openrouter"] not in rendered
        assert "f" * 40 not in rendered

    def test_a_secret_in_a_list_of_strings_is_masked(self) -> None:
        payload = ["fine", SEEDED["github"], "also fine"]
        assert SEEDED["github"] not in str(redact_value(payload))

    def test_an_environment_secret_value_is_masked_by_literal_substitution(self) -> None:
        """The value has no recognisable shape; only knowing the variable name finds it."""
        environment = {"COGOS_PROVIDER_TOKEN": "a-perfectly-ordinary-looking-value"}
        secrets = environment_secret_values(environment)
        text = "the CLI printed a-perfectly-ordinary-looking-value to stderr"
        assert "a-perfectly-ordinary-looking-value" not in redact_text(text, extra_secrets=secrets)

    def test_a_short_environment_value_is_not_used_for_substitution(self) -> None:
        """Masking every occurrence of a three-character token would corrupt normal text."""
        assert environment_secret_values({"API_KEY": "abc"}) == ()

    def test_a_diagnostic_excerpt_is_redacted_and_bounded(self) -> None:
        text = f"{SEEDED['bearer']} " + "x" * 2000
        excerpt = redact_for_diagnostics(text, limit=100)
        assert SEEDED["bearer"] not in excerpt
        assert len(excerpt) <= 101


class TestScanningIsSeparateFromRedaction:
    def test_a_clean_payload_passes(self) -> None:
        result = scan_for_secrets(
            {"summary": "the function subtracts where it should add"}, extra_secrets=()
        )
        assert result.status is SecretScanStatus.PASSED
        assert result.matched_rules == {}
        assert result.passed

    def test_a_seeded_payload_fails_and_names_the_rule(self) -> None:
        result = scan_for_secrets({"summary": SEEDED["openrouter"]}, extra_secrets=())
        assert result.status is SecretScanStatus.FAILED
        assert "openrouter_key" in result.matched_rules
        assert not result.passed

    def test_a_failed_scan_records_no_matched_text(self) -> None:
        """An evidence record that copied the secret would widen the exposure it records."""
        result = scan_for_secrets({"summary": SEEDED["openrouter"]}, extra_secrets=())
        rendered = repr(result) + str(result.matched_rules) + str(result.scanned_fields)
        assert SEEDED["openrouter"] not in rendered
        assert result.evidence_hash != ""

    def test_redaction_does_not_turn_a_failed_scan_into_a_pass(self) -> None:
        """Scanning the redacted value would always pass. That is the trap, so it is tested."""
        payload = {"summary": f"key {SEEDED['anthropic']}"}
        assert scan_for_secrets(payload, extra_secrets=()).status is SecretScanStatus.FAILED
        redacted = redact_value(payload)
        assert scan_for_secrets(redacted, extra_secrets=()).status is SecretScanStatus.PASSED

    def test_a_login_identity_is_a_scan_failure_not_merely_a_masked_value(self) -> None:
        result = scan_for_secrets({"account": SEEDED["identity"]}, extra_secrets=())
        assert result.status is SecretScanStatus.FAILED
        assert "email_identity" in result.matched_rules

    def test_a_secret_named_field_fails_the_scan_even_with_a_harmless_value(self) -> None:
        result = scan_for_secrets({"api_key": "placeholder"}, extra_secrets=())
        assert result.status is SecretScanStatus.FAILED
        assert result.matched_rules["secret_named_field"] == 1


class TestScanEvidence:
    def test_the_evidence_hash_is_deterministic_for_the_same_finding(self) -> None:
        first = scan_for_secrets({"summary": SEEDED["github"]}, extra_secrets=())
        second = scan_for_secrets({"summary": SEEDED["github"]}, extra_secrets=())
        assert first.evidence_hash == second.evidence_hash

    def test_a_different_finding_hashes_differently(self) -> None:
        clean = scan_for_secrets({"summary": "nothing here"}, extra_secrets=())
        dirty = scan_for_secrets({"summary": SEEDED["github"]}, extra_secrets=())
        assert clean.evidence_hash != dirty.evidence_hash

    def test_the_ruleset_version_is_part_of_the_evidence(self) -> None:
        """A record scanned by an older rule set must be identifiable, not assumed current."""
        current = scan_for_secrets({"summary": "clean"}, extra_secrets=())
        older = scan_for_secrets(
            {"summary": "clean"}, extra_secrets=(), ruleset_version="2020.01-old"
        )
        assert current.ruleset_version == REDACTION_RULESET_VERSION
        assert current.evidence_hash != older.evidence_hash

    def test_a_scan_that_never_ran_is_representable_and_distinct_from_passing(self) -> None:
        assert SecretScanStatus.NOT_RUN is not SecretScanStatus.PASSED
