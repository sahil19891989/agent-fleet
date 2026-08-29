"""
Message bus abstraction for the enterprise agent fleet.
Every delegation from the orchestrator to a worker agent passes through here,
ensuring a unified point for telemetry, interception, and network isolation.

- LocalBus: Synchronous in-process bus, used for local development, tests, and web demo.
- PubSubBus: Asynchronous Google Cloud Pub/Sub bus for multi-container Cloud Run deployment.
"""

from __future__ import annotations
import os
import time
from typing import Callable, Dict, Any


class LocalBus:
    """Synchronous in-memory bus for local execution and immediate dashboard feedback."""

    def __init__(self):
        self._handlers: dict[str, Callable[[dict], dict]] = {}

    def register(self, agent_name: str, handler: Callable[[dict], dict]) -> None:
        self._handlers[agent_name] = handler

    def list_agents(self) -> list[str]:
        return list(self._handlers.keys())

    def send(self, agent_name: str, payload: dict) -> dict:
        if agent_name not in self._handlers:
            raise ValueError(f"No handler registered on LocalBus for agent '{agent_name}'")
        
        start_time = time.time()
        result = self._handlers[agent_name](payload)
        elapsed = round((time.time() - start_time) * 1000, 2)
        
        if isinstance(result, dict):
            result["_latency_ms"] = elapsed
        return result


class PubSubBus:
    """
    Production deployment bus. Publishes task payloads to Google Cloud Pub/Sub
    topic 'projects/{project}/topics/{agent_name}-tasks'.
    """

    def __init__(self, project_id: str | None = None):
        from google.cloud import pubsub_v1
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-project")
        self._publisher = pubsub_v1.PublisherClient()

    def register(self, agent_name: str, handler: Callable[[dict], dict]) -> None:
        # In cloud mode, agents run as independent Cloud Run services subscribed to Pub/Sub
        pass

    def list_agents(self) -> list[str]:
        return ["db_query_agent", "report_agent", "notifier_agent", "security_auditor_agent"]

    def send(self, agent_name: str, payload: dict) -> dict:
        import json
        topic_path = self._publisher.topic_path(self.project_id, f"{agent_name}-tasks")
        future = self._publisher.publish(topic_path, json.dumps(payload).encode("utf-8"))
        message_id = future.result()
        return {
            "status": "published",
            "topic": topic_path,
            "message_id": message_id,
            "agent": agent_name,
        }


class CloudRunHttpBus:
    """
    Production deployment bus. Each worker agent runs as its own independent,
    IAM-isolated Cloud Run service (see deploy.sh); this bus makes a genuine
    synchronous HTTPS call to that service's URL, authenticated with a
    Google-signed ID token minted for the orchestrator's own service account.
    Unlike PubSubBus (fire-and-forget, no result), this actually returns the
    worker's real output -- necessary because the whole point of per-agent
    Cloud Run isolation is that the worker, not the orchestrator, executes
    the task under its own least-privilege service account.

    Worker URLs are read from explicit env vars (set at orchestrator deploy
    time) rather than guessed from a URL pattern, so this doesn't silently
    break if Cloud Run's URL format changes.
    """

    _URL_ENV_VARS = {
        "db_query_agent": "DB_QUERY_AGENT_URL",
        "report_agent": "REPORT_AGENT_URL",
        "notifier_agent": "NOTIFIER_AGENT_URL",
        "security_auditor_agent": "SECURITY_AUDITOR_AGENT_URL",
    }

    def __init__(self):
        self._urls = {
            name: os.environ[env_var]
            for name, env_var in self._URL_ENV_VARS.items()
            if env_var in os.environ
        }

    def register(self, agent_name: str, handler: Callable[[dict], dict]) -> None:
        # Workers run as independent Cloud Run services, not in-process.
        pass

    def list_agents(self) -> list[str]:
        return list(self._urls.keys())

    def send(self, agent_name: str, payload: dict) -> dict:
        import requests
        import google.auth.transport.requests
        import google.oauth2.id_token

        if agent_name not in self._urls:
            raise ValueError(
                f"No Cloud Run URL configured for agent '{agent_name}'. "
                f"Set the {self._URL_ENV_VARS.get(agent_name, '<agent>_URL')} env var "
                f"at orchestrator deploy time."
            )
        url = self._urls[agent_name]

        start_time = time.time()
        id_token = google.oauth2.id_token.fetch_id_token(
            google.auth.transport.requests.Request(), url
        )
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {id_token}"},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        elapsed = round((time.time() - start_time) * 1000, 2)

        if isinstance(result, dict):
            result["_latency_ms"] = elapsed
        return result


def get_bus():
    backend = os.environ.get("BUS_BACKEND", "local")
    if backend == "cloudrun":
        return CloudRunHttpBus()
    if backend == "pubsub":
        return PubSubBus()
    return LocalBus()
