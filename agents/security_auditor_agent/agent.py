"""
Security Auditor Agent.
Specialized in continuous compliance verification, HMAC cryptographic chain auditing,
and fleet-wide blast-radius exposure analysis.
"""

from agents.base import WorkerAgent, call_gemini
from provenance.chain import get_chain_store


class SecurityAuditorAgent(WorkerAgent):
    name = "security_auditor_agent"
    system_prompt = (
        "You are an enterprise Security & Compliance Auditor Agent. You analyze provenance records, "
        "audit cryptographic chain integrity, and evaluate fleet blast-radius risk. "
        "Provide clear security verdicts and actionable governance recommendations."
    )

    def handle(self, payload: dict) -> dict:
        granted = set(payload.get("granted_scope", []))
        
        if "provenance:chain:audit" not in granted and "compliance:policies:read" not in granted:
            return {
                "error": "Access Denied",
                "reason": f"Agent '{self.name}' requires 'provenance:chain:audit' scope. Held: {list(granted)}",
                "status": "quarantined_by_agent",
            }

        # Perform live audit of provenance chain
        chain_store = get_chain_store()
        audit_result = chain_store.verify_all()
        stats = chain_store.stats()

        user_input = payload.get("input", "")
        summary_prompt = (
            f"Context: Chain integrity is {'100% VALID' if audit_result['is_integral'] else 'COMPROMISED'}. "
            f"Total records audited: {audit_result['total']}. "
            f"Quarantined violations caught: {stats['quarantined_count']}. "
            f"Average blast radius: {stats['average_blast_radius']}. "
            f"User query: {user_input}"
        )
        
        narrative = call_gemini(self.system_prompt, summary_prompt)

        return {
            "agent": self.name,
            "status": "success",
            "audit_summary": narrative,
            "chain_integrity": audit_result,
            "fleet_stats": stats,
            "scope_used": "provenance:chain:audit",
        }
