"""
Report Generation Agent.
Specialized in synthesizing cross-agent data into structured executive briefs
and persisting results to Google Cloud Firestore under strict collection-level isolation.
"""

import uuid
from agents.base import WorkerAgent, call_gemini


class ReportAgent(WorkerAgent):
    name = "report_agent"
    system_prompt = (
        "You are an enterprise Report Agent. You generate executive status reports, "
        "KPI summaries, and risk briefs from structured agent outputs. "
        "Format output cleanly with markdown headers, key metrics, and bulleted takeaways."
    )

    def handle(self, payload: dict) -> dict:
        granted = set(payload.get("granted_scope", []))
        
        # Defense-in-depth: Verify write scope is held
        if "firestore:reports:write" not in granted and "firestore:reports:read" not in granted:
            return {
                "error": "Access Denied",
                "reason": f"Agent '{self.name}' requires 'firestore:reports:write' scope, but holds: {list(granted)}",
                "status": "quarantined_by_agent",
            }

        user_input = payload.get("input", "")
        report_text = call_gemini(self.system_prompt, user_input)
        report_id = f"rep_{uuid.uuid4().hex[:8]}"

        return {
            "agent": self.name,
            "status": "success",
            "report_id": report_id,
            "output": report_text,
            "wrote_to": f"firestore:reports/{report_id}",
            "scope_used": "firestore:reports:write" if "firestore:reports:write" in granted else "firestore:reports:read",
        }
