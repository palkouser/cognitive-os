"""Governed proposal-only harness improvement services."""

from .repository import InMemoryProposalRepository
from .service import HarnessProposalService, ProposalTypeRegistry

__all__ = ["HarnessProposalService", "InMemoryProposalRepository", "ProposalTypeRegistry"]
