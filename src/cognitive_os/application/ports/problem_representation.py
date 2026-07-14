"""Problem Representation Engine boundary."""

from typing import Protocol

from cognitive_os.domain.clarifications import ClarificationResponse
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.problem.normalization import NormalizedProblemSeed


class ProblemRepresentationPort(Protocol):
    async def represent(self, request: NormalizedProblemSeed) -> ProblemRepresentation: ...
    async def revise(
        self, current: ProblemRepresentation, clarification: ClarificationResponse
    ) -> ProblemRepresentation: ...
