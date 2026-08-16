"""
Shared base for worker agents in the fortified enterprise fleet.
Each worker wraps a Gemini model call behind a narrow, declared job.
Each agent has a distinct identity, declared scope ceiling, and runtime
defense-in-depth boundary.

Supports:
- Gemini 3.5 Flash / Pro via google-generativeai / google-genai
- MOCK_MODE: Generates realistic mock responses when GEMINI_API_KEY is not set
"""

from __future__ import annotations
import os
import json
from typing import Optional


# Auto-load .env file if present
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip("'").strip('"')
                    os.environ[key.strip()] = val

_load_env()

def is_mock_mode() -> bool:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return not key or key == "your-key" or key == ""


def call_gemini(system_prompt: str, user_input: str, response_format: str = "text") -> str:
    """Invokes Gemini API or returns a contextual mock response if in mock mode."""
    if is_mock_mode():
        return _mock_gemini_response(system_prompt, user_input)

    try:
        import google.generativeai as genai

        api_key = os.environ["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(user_input)
        return response.text
    except Exception as e:
        # Fallback to intelligent mock with error note if API call fails
        return f"[Live Gemini Fallback: {str(e)[:60]}] Summary for: {user_input[:80]}..."


def _mock_gemini_response(system_prompt: str, user_input: str) -> str:
    """Provides realistic domain responses for zero-dependency local demos."""
    prompt_lower = system_prompt.lower()
    
    if "sql" in prompt_lower or "orders" in prompt_lower:
        return (
            f"SELECT order_id, customer_id, renewal_date, contract_value_usd, status\n"
            f"FROM orders\n"
            f"WHERE renewal_date >= CURRENT_DATE AND status = 'active'\n"
            f"ORDER BY contract_value_usd DESC LIMIT 10;\n\n"
            f"-- Summary: Found 6 high-priority enterprise renewals totaling $1,420,000 ARR relevant to '{user_input[:40]}'."
        )
    elif "status report" in prompt_lower or "reports" in prompt_lower:
        return (
            f"### Executive Renewal & Health Briefing\n"
            f"- **Target Scope**: {user_input[:50]}\n"
            f"- **Key Metrics**: 6 Enterprise Accounts | Total ARR: $1.42M | Retention Target: 98%\n"
            f"- **Top Accounts**: Acme Corp ($450k), Wayne Enterprises ($380k), Cyberdyne ($290k)\n"
            f"- **Action Required**: Schedule executive sponsor check-ins for Q3 contracts expiring < 45 days.\n"
            f"- **Status**: Document filed to `firestore:reports/q3_enterprise_renewals`."
        )
    elif "notification" in prompt_lower or "slack" in prompt_lower or "email" in prompt_lower:
        return (
            f"📢 *Fleet Alert: Executive Report Ready*\n"
            f"> *Task Context*: {user_input[:60]}\n"
            f"> *Action*: Q3 Renewal summary has been generated and validated by ReportAgent.\n"
            f"> *Link*: `https://console.cloud.google.com/firestore/reports`\n"
            f"_Sent via Fortified Fleet Dispatcher_"
        )
    elif "security" in prompt_lower or "audit" in prompt_lower:
        return (
            f"🛡️ **Fleet Security & Provenance Assessment**\n"
            f"- **Chain Integrity**: 100% Valid (All HMAC-SHA256 signatures match)\n"
            f"- **Access Violation Rate**: 0% detected on active channels\n"
            f"- **Fleet Blast Radius Index**: 2.4 (LOW RISK)\n"
            f"- **Recommendation**: Fleet operational under Zero-Trust Scope Attenuation."
        )
    
    return f"[Autonomous Gemini Output] Processed input: '{user_input}' with zero-trust validation."


class WorkerAgent:
    name: str = "base_agent"
    system_prompt: str = "You are a secure, scoped agent in an enterprise fleet."

    def handle(self, payload: dict) -> dict:
        """
        payload: {"task_id": str, "granted_scope": [str], "input": str}
        Enforces defense-in-depth: independently verifies granted_scope before acting.
        """
        raise NotImplementedError
