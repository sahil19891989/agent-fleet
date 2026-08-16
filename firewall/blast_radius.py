"""
The blast-radius firewall.

Sits between the orchestrator and every worker agent. Before a delegation
is allowed to proceed, it checks that the requested scope is fully covered
by what the target agent is permitted to ever hold (AGENT_MAX_SCOPES), and
that it does not exceed the scope the *caller* itself was granted.

If a delegation would widen scope or exceed policy, the chain is quarantined:
it is not executed, and a human-readable reason is logged to the provenance store
so the dashboard and auditors can show exactly what was blocked and why.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from firewall.scopes import ScopeSet, AGENT_MAX_SCOPES


class QuarantineError(Exception):
    """Raised when a delegation is blocked for exceeding granted scope."""
    def __init__(self, reason: str, violation_type: str = "SCOPE_EXCEEDED"):
        self.reason = reason
        self.violation_type = violation_type
        super().__init__(reason)


@dataclass
class FirewallDecision:
    allowed: bool
    granted_scope: ScopeSet
    reason: str
    violation_type: Optional[str] = None
    risk_level: str = "LOW"
    blast_radius: int = 0


ACTION_WEIGHTS = {
    "read": 1,
    "audit": 2,
    "write": 4,
    "send": 6,
    "admin": 10,
}


def blast_radius_score(scope: ScopeSet) -> int:
    """
    A transparent, explainable severity score for a granted scope set,
    used to color-code nodes and assess aggregate fleet exposure.
    """
    if not scope or len(scope) == 0:
        return 0
    return sum(ACTION_WEIGHTS.get(s.action.value, 2) for s in scope)


def get_risk_level(score: int) -> str:
    if score == 0:
        return "NONE"
    elif score <= 2:
        return "LOW"
    elif score <= 5:
        return "MEDIUM"
    elif score <= 9:
        return "HIGH"
    return "CRITICAL"


def evaluate_delegation(
    caller_agent: str,
    caller_granted_scope: ScopeSet | None,
    target_agent: str,
    requested_scope: ScopeSet,
) -> FirewallDecision:
    """
    Decide whether caller_agent may delegate to target_agent with the
    requested scope. Scope may only ever narrow, never widen, across a hop.
    """
    # 1. Target Agent Must Exist in Registry
    if target_agent not in AGENT_MAX_SCOPES:
        reason = f"Unknown agent '{target_agent}'. Agent is not registered in the fleet policy."
        return FirewallDecision(
            allowed=False,
            granted_scope=ScopeSet(),
            reason=reason,
            violation_type="UNREGISTERED_AGENT",
            risk_level="CRITICAL",
            blast_radius=0,
        )

    # 2. The target agent can never be granted more than it's declared ceiling.
    target_ceiling = AGENT_MAX_SCOPES.get(target_agent, ScopeSet())
    if not requested_scope.is_subset_of(target_ceiling):
        excess = requested_scope.scopes - target_ceiling.scopes
        reason = (
            f"Privilege Escalation Blocked: {caller_agent} requested {ScopeSet(frozenset(excess))} "
            f"for {target_agent}, exceeding declared ceiling {target_ceiling}."
        )
        return FirewallDecision(
            allowed=False,
            granted_scope=ScopeSet(),
            reason=reason,
            violation_type="CEILING_EXCEEDED",
            risk_level="HIGH",
            blast_radius=blast_radius_score(requested_scope),
        )

    # 3. The caller can never hand down more than it was itself granted.
    #    (Root orchestrator passes caller_granted_scope=None to represent root authority)
    if caller_granted_scope is not None:
        if not requested_scope.is_subset_of(caller_granted_scope):
            excess = requested_scope.scopes - caller_granted_scope.scopes
            reason = (
                f"Scope Widening Blocked: {caller_agent} attempted to delegate {ScopeSet(frozenset(excess))} "
                f"to {target_agent}, but {caller_agent} only holds {caller_granted_scope}. "
                f"Scope cannot widen down a delegation chain."
            )
            return FirewallDecision(
                allowed=False,
                granted_scope=ScopeSet(),
                reason=reason,
                violation_type="SCOPE_WIDENING",
                risk_level="HIGH",
                blast_radius=blast_radius_score(requested_scope),
            )

    # Attenuated scope granted for this hop.
    granted = requested_scope.intersect(target_ceiling)
    score = blast_radius_score(granted)
    risk = get_risk_level(score)

    return FirewallDecision(
        allowed=True,
        granted_scope=granted,
        reason=f"Delegation Approved: Granted {granted} to {target_agent} (within ceiling {target_ceiling}).",
        risk_level=risk,
        blast_radius=score,
    )
