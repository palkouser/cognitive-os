"""Credential-free Sprint 14 smoke path."""

from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import build_fixture
from cognitive_os.experience.governance import export_candidate
from cognitive_os.verification.experience import verify_compilation


def main() -> int:
    request, sources, profiles = build_fixture("repaired-bug-fix")
    compiler = ExperienceCompiler(sources, profiles)
    first = compiler.compile(request)
    second = compiler.compile(request)
    assert first.manifest == second.manifest
    assert first.verifier_bundle.passed
    assert not verify_compilation(first)
    assert first.analysis.failed_branches
    assert first.analysis.recovery_paths
    assert first.candidates
    package = export_candidate(first.candidates[0])
    assert "manifest.json" in package
    print(
        first.manifest.model_dump_json(),
        sources.snapshot_hash(),
        profiles.snapshot_hash(),
        sep="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
