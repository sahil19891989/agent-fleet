"""
Scope model for the agent fleet.

A "scope" is a (resource, action) pair, e.g. ("firestore:reports", "write").
Every agent declares the scopes it needs. Every delegation grants a scope
set that must be a SUBSET of the parent's own granted scopes -- scope can
only narrow as it flows down a delegation chain, never widen.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Action(str, Enum):
    READ = "read"
    WRITE = "write"
    SEND = "send"
    ADMIN = "admin"
    AUDIT = "audit"


@dataclass(frozen=True)
class Scope:
    resource: str
    action: Action

    def __str__(self) -> str:
        return f"{self.resource}:{self.action.value}"

    @staticmethod
    def parse(s: str) -> "Scope":
        parts = s.rsplit(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid scope format: '{s}'. Expected 'resource:action'")
        resource, action_str = parts
        try:
            action = Action(action_str.lower())
        except ValueError:
            raise ValueError(f"Unknown action '{action_str}' in scope '{s}'")
        return Scope(resource, action)


@dataclass(frozen=True)
class ScopeSet:
    """An immutable set of scopes granted to an agent for one task."""
    scopes: frozenset[Scope] = field(default_factory=frozenset)

    @staticmethod
    def from_strings(items: list[str]) -> "ScopeSet":
        return ScopeSet(frozenset(Scope.parse(s) for s in items if s.strip()))

    def contains(self, scope: Scope) -> bool:
        return scope in self.scopes

    def is_subset_of(self, other: "ScopeSet") -> bool:
        return self.scopes.issubset(other.scopes)

    def intersect(self, other: "ScopeSet") -> "ScopeSet":
        """Used when delegating: child scope = requested ∩ parent's granted scope."""
        return ScopeSet(self.scopes & other.scopes)

    def to_list(self) -> list[str]:
        return sorted([str(s) for s in self.scopes])

    def __str__(self) -> str:
        if not self.scopes:
            return "{}"
        return "{" + ", ".join(sorted(str(s) for s in self.scopes)) + "}"

    def __iter__(self):
        return iter(self.scopes)

    def __len__(self):
        return len(self.scopes)


# Declared scope requirements per worker agent. This is the source of truth
# for what each agent is *allowed* to ever ask for -- the orchestrator uses
# this to compute the maximum scope it may grant on delegation.
AGENT_MAX_SCOPES: dict[str, ScopeSet] = {
    "report_agent": ScopeSet.from_strings([
        "firestore:reports:read",
        "firestore:reports:write",
    ]),
    "db_query_agent": ScopeSet.from_strings([
        "cloudsql:orders:read",
        "cloudsql:analytics:read",
    ]),
    "notifier_agent": ScopeSet.from_strings([
        "slack:general:send",
        "email:outbound:send",
        "pagerduty:alerts:send",
    ]),
    "security_auditor_agent": ScopeSet.from_strings([
        "provenance:chain:audit",
        "compliance:policies:read",
    ]),
}


def register_agent_scope(agent_name: str, scopes: list[str]) -> ScopeSet:
    """Dynamically register or update an agent's declared scope ceiling."""
    scope_set = ScopeSet.from_strings(scopes)
    AGENT_MAX_SCOPES[agent_name] = scope_set
    return scope_set
