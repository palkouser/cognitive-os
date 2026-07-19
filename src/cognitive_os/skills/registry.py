"""Frozen exact-revision Skill Registry."""

import json
from hashlib import sha256
from uuid import UUID

from cognitive_os.domain.skills import SkillItem, SkillRevision, SkillStatus

from .errors import SkillError


class SkillRegistry:
    def __init__(self) -> None:
        self._revisions: dict[tuple[UUID, int], SkillRevision] = {}
        self._items: dict[UUID, SkillItem] = {}
        self._frozen = False

    def register(self, item: SkillItem, revision: SkillRevision) -> None:
        if self._frozen:
            raise SkillError("skill registry is frozen")
        key = revision.skill_id, revision.revision
        if key in self._revisions:
            raise SkillError("duplicate skill identity and revision")
        existing = self._items.get(item.identity.skill_id)
        if existing is not None and existing.identity != item.identity:
            raise SkillError("skill identity changed across registry revisions")
        if item.identity.skill_id != revision.skill_id:
            raise SkillError("skill item and revision identity mismatch")
        self._items[item.identity.skill_id] = item
        self._revisions[key] = revision

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, skill_id: UUID, revision: int) -> SkillRevision:
        try:
            return self._revisions[(skill_id, revision)]
        except KeyError as error:
            raise SkillError("skill revision is unavailable") from error

    def current(self, skill_id: UUID) -> SkillRevision:
        matches = [item for (identity, _), item in self._revisions.items() if identity == skill_id]
        if not matches:
            raise SkillError("skill identity is unavailable")
        return max(matches, key=lambda item: item.revision)

    def query(
        self,
        *,
        statuses: tuple[SkillStatus, ...] = (SkillStatus.VERIFIED,),
        domain: str | None = None,
    ) -> tuple[tuple[SkillItem, SkillRevision], ...]:
        current = {skill_id: self.current(skill_id) for skill_id, _ in self._revisions}
        return tuple(
            sorted(
                (
                    (self._items[skill_id], revision)
                    for skill_id, revision in current.items()
                    if revision.status in statuses
                    and (domain is None or domain in revision.domains)
                ),
                key=lambda item: (str(item[0].identity.skill_id), item[1].revision),
            )
        )

    def snapshot_hash(self) -> str:
        values = [
            {
                "identity": self._items[item.skill_id].identity.model_dump(mode="json"),
                "revision": item.model_dump(mode="json"),
            }
            for item in sorted(
                self._revisions.values(), key=lambda value: (str(value.skill_id), value.revision)
            )
        ]
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    def health(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "skill_id": str(revision.skill_id),
                "revision": revision.revision,
                "status": revision.status.value,
                "package_hash": revision.package_hash,
            }
            for _, revision in self.query(statuses=tuple(SkillStatus))
        )
