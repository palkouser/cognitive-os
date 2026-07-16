"""Source-snapshot comparison immediately before provider execution."""

from cognitive_os.domain.context import ContextSourceSnapshot


def stale_source_codes(
    expected: ContextSourceSnapshot, current: ContextSourceSnapshot
) -> tuple[str, ...]:
    codes: list[str] = []
    if expected.event_streams != current.event_streams:
        codes.append("event_stream_version_changed")
    if expected.artifacts != current.artifacts:
        codes.append("artifact_digest_changed")
    if expected.memory_revisions != current.memory_revisions:
        codes.append("memory_revision_changed")
    if expected.semantic_revisions != current.semantic_revisions:
        codes.append("semantic_revision_changed")
    if expected.repository != current.repository:
        codes.append("repository_revision_changed")
    if expected.workspace != current.workspace:
        codes.append("workspace_revision_changed")
    return tuple(codes)


def source_snapshot_matches(
    expected: ContextSourceSnapshot, current: ContextSourceSnapshot
) -> bool:
    return not stale_source_codes(expected, current)
