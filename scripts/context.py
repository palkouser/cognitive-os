"""Build, inspect, verify, regenerate, and health-check Context Bundles."""

from __future__ import annotations

import argparse
import asyncio
import json
from hashlib import sha256
from pathlib import Path

from cognitive_os.config.context_config import ContextConfiguration, load_context_configuration
from cognitive_os.context.fixtures import sprint11_fixture_builder
from cognitive_os.domain.context import ContextBundleRevision, ContextRequest, ContextRetrievalTrace
from cognitive_os.verification.context import build_context_verification_snapshot


def _json(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


async def _build(output: Path) -> int:
    service, request = sprint11_fixture_builder()
    result = await service.build_context(request)
    if result.bundle is None or result.trace is None or result.rendered_context is None:
        raise RuntimeError("Context Builder fixture did not return persisted output")
    output.mkdir(parents=True, exist_ok=True)
    (output / "context-request.json").write_text(_json(request) + "\n", encoding="utf-8")
    (output / "retrieval-trace.json").write_text(_json(result.trace) + "\n", encoding="utf-8")
    (output / "context-bundle.json").write_text(_json(result.bundle) + "\n", encoding="utf-8")
    (output / "rendered-context.txt").write_text(result.rendered_context, encoding="utf-8")
    print(
        _json(
            {
                "bundle_id": str(result.bundle.context_bundle_id),
                "revision": result.bundle.revision,
                "bundle_hash": result.bundle.content_hash,
                "trace_hash": result.trace.trace_hash,
            }
        )
    )
    return 0


def _load_bundle(path: Path) -> ContextBundleRevision:
    return ContextBundleRevision.model_validate_json(path.read_bytes())


def _inspect(command: str, bundle_path: Path, trace_path: Path | None) -> int:
    bundle = _load_bundle(bundle_path)
    if command == "get":
        value = {
            "bundle_id": str(bundle.context_bundle_id),
            "revision": bundle.revision,
            "content_hash": bundle.content_hash,
            "total_token_estimate": bundle.total_token_estimate,
            "section_count": len(bundle.sections),
        }
    elif command == "sources":
        value = [
            source.model_dump(mode="json")
            for section in bundle.sections
            for source in section.source_references
        ]
    elif command == "warnings":
        value = [item.model_dump(mode="json") for item in bundle.warnings]
    else:
        if trace_path is None:
            raise ValueError(f"{command} requires --trace")
        trace = ContextRetrievalTrace.model_validate_json(trace_path.read_bytes())
        value = (
            trace.model_dump(mode="json")
            if command == "trace"
            else [item.model_dump(mode="json") for item in trace.exclusions]
        )
    print(_json(value))
    return 0


def _verify(directory: Path) -> int:
    request = ContextRequest.model_validate_json((directory / "context-request.json").read_bytes())
    trace = ContextRetrievalTrace.model_validate_json(
        (directory / "retrieval-trace.json").read_bytes()
    )
    bundle = _load_bundle(directory / "context-bundle.json")
    rendered = (directory / "rendered-context.txt").read_text(encoding="utf-8")
    results = build_context_verification_snapshot(bundle, trace, request, rendered)
    print(_json(results))
    return 0 if all(results.values()) else 1


async def _regenerate(expected_hash: str) -> int:
    service, request = sprint11_fixture_builder()
    result = await service.build_context(request)
    if result.bundle is None:
        raise RuntimeError("Context Builder fixture did not return a bundle")
    matches = result.bundle.content_hash == expected_hash
    print(_json({"matches": matches, "content_hash": result.bundle.content_hash}))
    return 0 if matches else 1


def _health(configuration_path: Path) -> int:
    configuration = (
        load_context_configuration(configuration_path)
        if configuration_path.exists()
        else ContextConfiguration()
    )
    service, _ = sprint11_fixture_builder()
    value = {
        "status": "available",
        "configuration_hash": sha256(configuration.model_dump_json().encode()).hexdigest(),
        "artifact_store": "fixture_available",
        "network_retrieval": configuration.allow_network_retrieval,
        "approximate_vector_search": configuration.allow_approximate_vector_search,
        "learned_ranking": configuration.allow_learned_ranking,
        "provider_retriever_selection": configuration.allow_provider_retriever_selection,
        "context_builder": type(service).__name__,
    }
    print(_json(value))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    for command in ("get", "trace", "sources", "exclusions", "warnings"):
        inspect = subparsers.add_parser(command)
        inspect.add_argument("--bundle", type=Path, required=True)
        inspect.add_argument("--trace", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--directory", type=Path, required=True)
    regenerate = subparsers.add_parser("regenerate")
    regenerate.add_argument("--expected-hash", required=True)
    health = subparsers.add_parser("health")
    health.add_argument("--config", type=Path, default=Path("config/context.example.yaml"))
    args = parser.parse_args()
    if args.command == "build":
        return asyncio.run(_build(args.output))
    if args.command in {"get", "trace", "sources", "exclusions", "warnings"}:
        return _inspect(args.command, args.bundle, args.trace)
    if args.command == "verify":
        return _verify(args.directory)
    if args.command == "regenerate":
        return asyncio.run(_regenerate(args.expected_hash))
    return _health(args.config)


if __name__ == "__main__":
    raise SystemExit(main())
