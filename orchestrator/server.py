"""
Flask HTTP Control Plane Server for the Fortified Enterprise Fleet.
Serves the real-time web dashboard and exposes REST APIs for task orchestration,
attack simulations, cryptographic chain verification, and telemetry.
"""

from __future__ import annotations
import os
import sys

# Ensure root directory is on python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory, Response
from orchestrator.orchestrator import Orchestrator
from provenance.chain import get_chain_store

app = Flask(__name__, static_folder="../dashboard", static_url_path="")
orch = Orchestrator()
chain_store = get_chain_store()


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


# --- REST API Endpoints ---

@app.route("/api/fleet", methods=["GET"])
def get_fleet():
    """Returns all registered agents, their declared ceilings, and status."""
    return jsonify(orch.get_fleet_status())


@app.route("/api/run-task", methods=["POST"])
def run_task():
    """Executes a standard 3-step enterprise workflow (Query -> Report -> Notify)."""
    body = request.get_json(silent=True) or {}
    description = body.get("description", "Q3 enterprise renewals analysis")
    result = orch.run_task(description)
    return jsonify(result)


@app.route("/api/run-autonomous", methods=["POST"])
def run_autonomous():
    """Dynamically decomposes an open-ended goal with Gemini and delegates with least privilege."""
    body = request.get_json(silent=True) or {}
    goal = body.get("goal", "Audit top customer churn risks and notify stakeholders")
    result = orch.run_autonomous_plan(goal)
    return jsonify(result)


@app.route("/api/run-attack", methods=["POST"])
def run_attack():
    """Simulates enterprise attack vectors (Privilege Escalation, Scope Widening, Tampering)."""
    body = request.get_json(silent=True) or {}
    attack_type = body.get("attack_type", "privilege_escalation")
    custom_input = body.get("input", "")
    result = orch.run_attack(attack_type, custom_input)
    return jsonify(result)


@app.route("/api/provenance", methods=["GET"])
def get_provenance():
    """Returns all HMAC-signed audit logs and aggregate blast-radius statistics."""
    records = chain_store.read_all()
    stats = chain_store.stats()
    return jsonify({
        "stats": stats,
        "records": list(reversed(records)),  # Newest first
    })


@app.route("/api/verify-chain", methods=["GET", "POST"])
def verify_chain():
    """Verifies HMAC-SHA256 signatures for every record in the provenance log."""
    audit_report = chain_store.verify_all()
    return jsonify(audit_report)


@app.route("/api/simulate-tamper", methods=["POST"])
def simulate_tamper():
    """Adversarial simulation: intentionally corrupts a log record to prove HMAC detection."""
    body = request.get_json(silent=True) or {}
    record_id = body.get("record_id")
    
    if not record_id:
        records = chain_store.read_all()
        if not records:
            orch.run_task("Baseline task before tampering")
            records = chain_store.read_all()
        record_id = records[-1]["record_id"]

    if hasattr(chain_store, "simulate_tamper"):
        success = chain_store.simulate_tamper(record_id)
        audit = chain_store.verify_all()
        return jsonify({
            "tampered_record_id": record_id,
            "success": success,
            "audit": audit,
        })
    return jsonify({"error": "Backend does not support direct tampering simulation"}), 400


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "healthy", "service": "orchestrator-control-plane"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Fortified Agent Fleet Control Plane on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
