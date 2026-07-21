import pytest
from pydantic import ValidationError

from cognitive_os.config.corpus_config import CorpusConfiguration
from cognitive_os.corpus.factory import build_destination_registry, build_normalizer_registry
from cognitive_os.corpus.fixtures import FIXTURE_TIME, fixture_id
from cognitive_os.domain.corpus import CorpusExportRequest


@pytest.mark.parametrize(
    "field",
    [
        "allow_network_sources",
        "allow_remote_download",
        "allow_source_execution",
        "allow_automatic_destination_write",
        "allow_automatic_promotion",
        "allow_automatic_duplicate_merge",
        "allow_provider_license_authority",
        "allow_provider_route_authority",
        "allow_model_training",
    ],
)
def test_prohibited_authority_configuration_fails_closed(field: str) -> None:
    with pytest.raises(ValidationError):
        CorpusConfiguration.model_validate({field: True})


def test_registries_are_frozen() -> None:
    with pytest.raises(RuntimeError):
        build_normalizer_registry().register("extra", lambda data, path: (data, ()))
    with pytest.raises(RuntimeError):
        build_destination_registry().register("extra", object())


def test_export_cannot_upload_or_train() -> None:
    with pytest.raises(ValidationError):
        CorpusExportRequest(
            export_id=fixture_id("export", "unsafe"),
            corpus_id=fixture_id("corpus", "unsafe"),
            corpus_revision=1,
            export_type="jsonl",
            requested_at=FIXTURE_TIME,
            requested_by="test",
            upload=True,
            train=True,
        )
