"""
Notification & Dispatch Agent.
Specialized in formatting and routing notifications to team channels (Slack, Email, PagerDuty)
under granular channel-level permission boundaries.
"""

from agents.base import WorkerAgent, call_gemini


class NotifierAgent(WorkerAgent):
    name = "notifier_agent"
    system_prompt = (
        "You are an enterprise Notification Agent. You draft concise, high-signal alerts "
        "and executive broadcasts for Slack and Email channels. Format with clear callouts "
        "and actionable links."
    )

    def handle(self, payload: dict) -> dict:
        granted = set(payload.get("granted_scope", []))
        
        # Defense-in-depth check
        allowed_channels = granted & {
            "slack:general:send",
            "email:outbound:send",
            "pagerduty:alerts:send",
        }
        if not allowed_channels:
            return {
                "error": "Access Denied",
                "reason": f"Agent '{self.name}' has no active dispatch scope granted. Held: {list(granted)}",
                "status": "quarantined_by_agent",
            }

        # Select primary delivery channel based on granted scope
        if "pagerduty:alerts:send" in granted:
            channel = "pagerduty:alerts"
        elif "slack:general:send" in granted:
            channel = "slack:#general-announcements"
        else:
            channel = "email:executive-outbound@company.com"

        user_input = payload.get("input", "")
        message_text = call_gemini(self.system_prompt, user_input)

        return {
            "agent": self.name,
            "status": "success",
            "output": message_text,
            "channel": channel,
            "sent_via": channel,
            "scope_used": list(allowed_channels)[0],
        }
