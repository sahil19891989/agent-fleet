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


def get_bus():
    backend = os.environ.get("BUS_BACKEND", "local")
    if backend == "pubsub":
        return PubSubBus()
    return LocalBus()
