"""Read-only Context Builder adapter for verified procedural skills."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.skill_repository import SkillRepositoryPort
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.context.query import candidate_id, reseal_candidate
from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextComponentStatus,
    ContextRequest,
    ContextRetrieverDescriptor,
    ContextScoreBreakdown,
    ContextSourceReference,
    ContextSourceType,
    ContextTrustClass,
    HydrationLevel,
    RetrievalMode,
    RetrievalSubquery,
    RetrieverRank,
)
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType
from cognitive_os.domain.skills import (
    SkillAccessRecord,
    SkillAccessType,
    SkillRevision,
    SkillScope,
    SkillScopeType,
    SkillStatus,
)
from cognitive_os.memory.governance import sensitivity_allows

from .packaging import LoadedSkillPackage, load_artifact_package
from .registry import SkillRegistry


def _context_scope(scope: SkillScope) -> MemoryScope:
    scope_type = {
        SkillScopeType.GLOBAL: MemoryScopeType.GLOBAL,
        SkillScopeType.PROJECT: MemoryScopeType.PROJECT,
        SkillScopeType.REPOSITORY: MemoryScopeType.REPOSITORY,
        SkillScopeType.DOMAIN: MemoryScopeType.DOMAIN,
        SkillScopeType.PROVIDER: MemoryScopeType.DOMAIN,
    }[scope.scope_type]
    scope_id = (
        f"provider:{scope.scope_id}"
        if scope.scope_type is SkillScopeType.PROVIDER
        else scope.scope_id
    )
    return MemoryScope(scope_type=scope_type, scope_id=scope_id)


class SkillContextRetriever:
    """Expose verified skill metadata and bounded instructions as retrieved data."""

    def __init__(
        self,
        registry: SkillRegistry,
        repository: SkillRepositoryPort,
        artifacts: ArtifactStorePort,
        configuration: SkillConfiguration,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._artifacts = artifacts
        self._configuration = configuration
        self._revisions: dict[UUID, SkillRevision] = {}
        self._packages: dict[UUID, LoadedSkillPackage] = {}
        self._requests: dict[UUID, ContextRequest] = {}
        self._descriptor = ContextRetrieverDescriptor(
            retriever_id="context.procedural-skill",
            version="1",
            source_types=(ContextSourceType.PROCEDURAL_SKILL,),
            supported_modes=(
                RetrievalMode.METADATA,
                RetrievalMode.LEXICAL,
                RetrievalMode.SOURCE_LOOKUP,
            ),
            deterministic=True,
            requires_artifact_store=True,
            default_trust_class=ContextTrustClass.VERIFIED,
            maximum_candidates=200,
        )

    @property
    def descriptor(self) -> ContextRetrieverDescriptor:
        return self._descriptor

    async def health_check(self) -> ContextComponentHealth:
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)

    async def retrieve(
        self,
        subquery: RetrievalSubquery,
        request: ContextRequest,
        cancellation: asyncio.Event | None = None,
    ) -> tuple[ContextCandidate, ...]:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        if subquery.source_type is not ContextSourceType.PROCEDURAL_SKILL:
            raise ValueError("skill retriever accepts only procedural skill subqueries")
        terms = {term.normalized for term in subquery.terms}
        matches: list[tuple[int, ContextCandidate, SkillAccessRecord]] = []
        for item, revision in self._registry.query(statuses=(SkillStatus.VERIFIED,)):
            scope = _context_scope(item.identity.scope)
            if scope not in request.required_scopes or not sensitivity_allows(
                revision.sensitivity, request.sensitivity_limit
            ):
                continue
            searchable = " ".join(
                (
                    item.identity.canonical_name,
                    revision.display_name,
                    revision.description,
                    revision.purpose,
                    *revision.domains,
                )
            ).casefold()
            hits = sum(term in searchable for term in terms)
            exact = request.query.casefold() in {
                str(revision.skill_id).casefold(),
                item.identity.canonical_name,
                f"{revision.skill_id}@{revision.revision}".casefold(),
            }
            if subquery.mode is RetrievalMode.LEXICAL and terms and hits == 0:
                continue
            if subquery.mode is RetrievalMode.SOURCE_LOOKUP and not exact:
                continue
            summary = f"{revision.display_name}: {revision.description}"
            identity = str(revision.skill_id)
            digest = sha256(revision.purpose.encode()).hexdigest()
            context_id = candidate_id(
                ContextSourceType.PROCEDURAL_SKILL,
                identity,
                str(revision.revision),
                (scope,),
                revision.package_hash,
            )
            access_id = uuid5(
                NAMESPACE_URL,
                f"skill-context:{subquery.subquery_id}:{revision.skill_id}:{revision.revision}",
            )
            score = max(hits, 1)
            candidate = ContextCandidate(
                candidate_id=context_id,
                source_type=ContextSourceType.PROCEDURAL_SKILL,
                source_identity=identity,
                source_revision=str(revision.revision),
                content_hash=digest,
                summary=summary,
                artifact_references=(revision.package_artifact,),
                scopes=(scope,),
                sensitivity=revision.sensitivity,
                trust_class=ContextTrustClass.VERIFIED,
                retrieval_routes=(
                    RetrieverRank(
                        retriever_id=self.descriptor.retriever_id,
                        mode=subquery.mode,
                        rank=1,
                        raw_score=Decimal(score),
                    ),
                ),
                score_breakdown=ContextScoreBreakdown(
                    verification=Decimal("1"), salience=Decimal("0.5")
                ),
                provenance=(
                    ContextSourceReference(
                        source_type=ContextSourceType.PROCEDURAL_SKILL,
                        source_identity=identity,
                        source_revision=str(revision.revision),
                        content_hash=revision.package_hash,
                        artifact_id=revision.package_artifact.artifact_id,
                    ),
                ),
                known_at=revision.created_at,
                available_hydration_levels=(
                    HydrationLevel.METADATA,
                    HydrationLevel.SUMMARY,
                    HydrationLevel.FULL,
                ),
                evidence=True,
                access_audit_ids=(access_id,),
            )
            self._revisions[context_id] = revision
            self._requests[context_id] = request
            access = SkillAccessRecord(
                access_id=access_id,
                skill_id=revision.skill_id,
                revision=revision.revision,
                access_type=SkillAccessType.CONTEXT_RETRIEVAL,
                task_run_id=request.task_run_id,
                context_request_id=request.context_request_id,
                query_hash=sha256(request.query.encode()).hexdigest(),
                scope=item.identity.scope,
                sensitivity=request.sensitivity_limit,
                accessed_at=request.created_at,
            )
            matches.append((score, candidate, access))
        matches.sort(key=lambda value: (-value[0], str(value[1].candidate_id)))
        limited = matches[: min(subquery.maximum_results, self.descriptor.maximum_candidates)]
        await self._repository.record_access(tuple(value[2] for value in limited))
        return tuple(
            reseal_candidate(
                value[1],
                retrieval_routes=(value[1].retrieval_routes[0].model_copy(update={"rank": rank}),),
            )
            for rank, value in enumerate(limited, start=1)
        )

    async def hydrate(
        self,
        candidate: ContextCandidate,
        level: HydrationLevel,
        cancellation: asyncio.Event | None = None,
    ) -> ContextCandidate:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        revision = self._revisions.get(candidate.candidate_id)
        request = self._requests.get(candidate.candidate_id)
        if revision is None or request is None:
            raise ValueError("skill candidate was not returned by this retriever")
        package = self._packages.get(candidate.candidate_id)
        if package is None:
            raw = await self._artifacts.get_bytes(revision.package_artifact.artifact_id)
            package = load_artifact_package(raw, self._configuration)
            if package.manifest.package_hash != revision.package_hash:
                raise ValueError("skill package revision changed after retrieval")
            self._packages[candidate.candidate_id] = package
        if level is HydrationLevel.METADATA:
            content = None
            access_type = SkillAccessType.CONTEXT_RETRIEVAL
        elif level is HydrationLevel.SUMMARY:
            content = candidate.summary
            access_type = SkillAccessType.SUMMARY_HYDRATION
        elif level is HydrationLevel.FULL:
            referenced_resources = [
                (path, value)
                for path, value in sorted(package.files.items())
                if path.startswith("resources/") and path in package.instructions
            ]
            resource_bytes = sum(len(value) for _, value in referenced_resources)
            if resource_bytes > self._configuration.maximum_resource_bytes:
                raise ValueError("referenced skill resources exceed the hydration budget")
            sections = [package.instructions]
            sections.extend(
                f"\n[Referenced resource: {path}]\n{value.decode('utf-8', errors='replace')}"
                for path, value in referenced_resources
            )
            content = "\n".join(sections).strip()
            access_type = (
                SkillAccessType.RESOURCE_HYDRATION
                if referenced_resources
                else SkillAccessType.FULL_HYDRATION
            )
        else:
            raise ValueError("excerpt hydration is not defined for skill packages")
        access_id = uuid5(
            NAMESPACE_URL,
            f"skill-hydration:{request.context_request_id}:{candidate.candidate_id}:{level.value}",
        )
        item = next(
            value[0]
            for value in self._registry.query(statuses=(SkillStatus.VERIFIED,))
            if value[1].skill_id == revision.skill_id
        )
        await self._repository.record_access(
            (
                SkillAccessRecord(
                    access_id=access_id,
                    skill_id=revision.skill_id,
                    revision=revision.revision,
                    access_type=access_type,
                    task_run_id=request.task_run_id,
                    context_request_id=request.context_request_id,
                    query_hash=sha256(request.query.encode()).hexdigest(),
                    scope=item.identity.scope,
                    sensitivity=request.sensitivity_limit,
                    accessed_at=request.created_at,
                ),
            )
        )
        return reseal_candidate(
            candidate,
            content=content,
            content_hash=(
                sha256(content.encode()).hexdigest()
                if content is not None
                else candidate.content_hash
            ),
            selected_hydration_level=level,
            access_audit_ids=tuple(sorted({*candidate.access_audit_ids, access_id})),
        )
