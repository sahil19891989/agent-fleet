"""
Fortified Enterprise Agent Fleet - Zero-Trust Scope Firewall & Governance Runner.

Usage:
  python main.py          # Run the full end-to-end CLI demo with attacks and audits
  python main.py --web    # Launch the real-time web dashboard control plane
"""

import argparse
import json
import os
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from orchestrator.orchestrator import Orchestrator


def run_cli_demo():
    orch = Orchestrator()
    print("=" * 70)
    print("[*] FORTIFIED ENTERPRISE AGENT FLEET: ZERO-TRUST CONTROL PLANE DEMO")
    print("=" * 70)

    print("\n[1/4] Running standard enterprise task (Query -> Report -> Notify)...")
    res1 = orch.run_task("Q3 enterprise renewals and revenue retention")
    print(f"Status: {res1['status']} (Task ID: {res1['task_id'][:8]}...)")
    for step in res1.get("steps", []):
        print(f"  + {step['agent']}: SUCCESS")

    print("\n[2/4] Simulating Privilege Escalation Attack (Write attempt on Read-only Agent)...")
    res2 = orch.run_attack("privilege_escalation")
    print(f"Status: {res2['status']} | Quarantined: {res2.get('quarantined')}")
    print(f"Reason: {res2.get('reason')}")

    print("\n[3/4] Simulating Scope Widening Attack Across Delegation Hops...")
    res3 = orch.run_attack("scope_widening")
    print(f"Status: {res3['status']} | Quarantined: {res3.get('quarantined')}")
    print(f"Reason: {res3.get('reason')}")

    print("\n[4/4] Cryptographic HMAC-SHA256 Provenance Audit...")
    audit = orch.chain.verify_all()
    stats = orch.chain.stats()
    print(f"Total Delegations Audited: {audit['total']}")
    print(f"Valid Signatures: {audit['valid']} | Tampered: {audit['tampered_count']}")
    print(f"Chain Integrity: {'100% VERIFIED' if audit['is_integral'] else 'COMPROMISED'}")
    print(f"Quarantined Violations Blocked: {stats['quarantined_count']}")
    print(f"Average Fleet Blast Radius: {stats['average_blast_radius']}")

    print("\n" + "=" * 70)
    print("Demo complete! Launch interactive dashboard with: python main.py --web")
    print("=" * 70)


def run_web_server(port: int = 8080):
    from orchestrator.server import app
    print(f"Starting Fortified Fleet Control Plane at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    parser = argparse.ArgumentParser(description="Fortified Agent Fleet Control Plane")
    parser.add_argument("--web", action="store_true", help="Launch the web dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port for web server (default: 8080)")
    args = parser.parse_args()

    if args.web:
        run_web_server(args.port)
    else:
        run_cli_demo()


if __name__ == "__main__":
    main()
