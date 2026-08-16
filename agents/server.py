"""
Generic Cloud Run entrypoint for a worker agent. Each agent's Dockerfile
sets WORKER_AGENT_MODULE / WORKER_AGENT_CLASS to point at its own agent.py,
so this one file serves all three worker services.

POST / with JSON body {"task_id", "granted_scope": [...], "input"} runs the
agent and returns its result. Cloud Run's own IAM + service account per
service is what actually enforces network-level isolation between agents --
this HTTP layer is just the interface.
"""

import importlib
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

MODULE = os.environ["WORKER_AGENT_MODULE"]  # e.g. "agents.report_agent.agent"
CLASS = os.environ["WORKER_AGENT_CLASS"]    # e.g. "ReportAgent"

_agent_cls = getattr(importlib.import_module(MODULE), CLASS)
_agent = _agent_cls()


@app.route("/", methods=["POST"])
def handle():
    payload = request.get_json(force=True)
    result = _agent.handle(payload)
    return jsonify(result)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "agent": _agent.name})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
