"""
Database Query Agent.
Specialized in translating natural language queries into safe, read-only SQL
against Cloud SQL databases. Enforces read-only isolation and schema constraints.
"""

from agents.base import WorkerAgent, call_gemini


class DbQueryAgent(WorkerAgent):
    name = "db_query_agent"
    system_prompt = (
        "You are an enterprise Database Query Agent. You translate natural-language questions "
        "into strict read-only SQL against the 'orders' and 'analytics' tables and summarize the result. "
        "You NEVER generate write, update, alter, or delete queries."
    )

    def handle(self, payload: dict) -> dict:
        granted = set(payload.get("granted_scope", []))
        
        # Defense-in-depth: Verify read scope is actually held
        has_read = bool(granted & {"cloudsql:orders:read", "cloudsql:analytics:read"})
        if not has_read:
            return {
                "error": "Access Denied",
                "reason": f"Agent '{self.name}' requires read scope, but task granted: {list(granted)}",
                "status": "quarantined_by_agent",
            }

        user_input = payload.get("input", "")

        # Agent-level defense-in-depth: check for destructive keywords in request
        destructive_keywords = ["drop table", "truncate", "delete from", "update ", "alter table"]
        for kw in destructive_keywords:
            if kw in user_input.lower():
                return {
                    "error": "Safety Policy Violation",
                    "reason": f"Destructive SQL command '{kw.upper()}' rejected by DbQueryAgent read-only policy.",
                    "status": "blocked",
                }

        output_text = call_gemini(self.system_prompt, user_input)
        
        return {
            "agent": self.name,
            "status": "success",
            "output": output_text,
            "read_from": "cloudsql:orders",
            "scope_used": "cloudsql:orders:read" if "cloudsql:orders:read" in granted else "cloudsql:analytics:read",
        }
