# 🛡️ Fortified Enterprise Agent Fleet — Devpost Hackathon Submission

## 1. Submission Overview

- **Project Name**: Fortified Enterprise Agent Fleet: Zero-Trust Governance & Blast-Radius Firewall
- **Track**: **The Fortified Enterprise Fleet** ("An enterprise-grade, zero-trust network of agents that can be discovered, governed, and scaled safely inside a large organization")
- **Tagline**: A zero-trust scope attenuation firewall, dynamic blast-radius evaluator, and cryptographic HMAC provenance control plane for autonomous multi-agent systems.
- **Repository URL**: `https://github.com/sahil19891989/agent-fleet`
- **Hosted Demo URL**: `https://orchestrator-[project-hash]-uc.a.run.app` (or local `http://localhost:8080`)

---

## 2. Inspiration & The Problem

As enterprise organizations scale autonomous AI agents, multi-agent delegation becomes essential. However, existing multi-agent architectures suffer from three critical security and governance vulnerabilities:

1. **Implicit Privilege Inheritance**: When an orchestrator delegates a subtask, worker agents often inherit broad ambient permissions rather than least-privilege access.
2. **Untracked Compounding Blast-Radius**: As tasks flow through multiple sub-agents, compounding risks can allow low-privilege agents to escalate permissions across hops.
3. **Audit Trail Forgery**: Standard logging cannot prevent compromised agents from altering historical logs to conceal unauthorized operations.

We built the **Fortified Enterprise Agent Fleet** to make compounding risk transparent, enforceable, and tamper-evident across every delegation hop.

---

## 3. What It Does

The Fortified Enterprise Fleet acts as an active **Zero-Trust Control Plane** sitting between orchestrators and worker microservices:

1. **Zero-Trust Scope Attenuation**: Enforces the mathematical principle that permissions can only **narrow** down a delegation chain ($\text{Child Scope} = \text{Requested} \cap \text{Caller Scope} \cap \text{Ceiling}$), never widen.
2. **Blast-Radius Firewall**: Before any agent action executes, the firewall computes a live risk index ($\text{Read}=1, \text{Audit}=2, \text{Write}=4, \text{Send}=6, \text{Admin}=10$) and blocks unauthorized scope requests.
3. **Instant Quarantine**: Over-scoped or malicious delegation attempts are quarantined at the boundary with explanatory diagnostics logged to the audit trail.
4. **Cryptographic HMAC Provenance**: Every delegation attempt (allowed or blocked) is signed with HMAC-SHA256 and stored in an append-only log (Google Cloud Firestore / local JSONL) for verifiable non-repudiation.
5. **Autonomous Gemini 2.5 Planner**: Decomposes high-level natural language enterprise goals into multi-agent subtasks with negotiated least-privilege scopes.
6. **Interactive Visual Dashboard**: A real-time control plane featuring live SVG topology graphs, interactive attack simulators, blast-radius radars, and a cryptographic audit log explorer.

---

## 4. How We Built It

- **Gemini 2.5 Flash / Google ADK**: Powers dynamic task planning, text-to-SQL synthesis, executive reporting, and security evaluation.
- **Google Cloud Run**: Deploys the Orchestrator and 4 worker agents as independent, containerized microservices.
- **Google Cloud IAM**: Enforces true network-level and resource-level isolation using dedicated per-agent service accounts (`db-query-agent-sa`, `report-agent-sa`, `notifier-agent-sa`, `security-auditor-sa`).
- **Google Cloud Firestore & Pub/Sub**: Manages immutable cryptographic audit records and asynchronous event messaging.
- **HMAC-SHA256 Cryptographic Engine**: Signs and verifies all audit records against tampering.
- **Vanilla HTML5/CSS3/JavaScript Dashboard**: High-aesthetic, responsive control plane with zero-build-step overhead.

---

## 5. Challenges We Overcame

1. **Scope Attenuation Logic across Multi-Hop Chains**: Ensuring that scope calculations handle both direct orchestrator delegations and arbitrary nested sub-agent delegations while preventing privilege widening.
2. **Zero-Dependency Local to Multi-Service Cloud Parity**: Architecting the codebase so developers and judges can run 100% offline with zero setup via `python main.py --web` using mock mode and local stores, or deploy with one command to multi-service Google Cloud Run.
3. **Real-Time Visual Feedback of Attack Quarantines**: Designing an intuitive SVG topology visualizer that dynamically pulses traffic in green and flashes quarantined violations in crimson.

---

## 6. Accomplishments That We're Proud Of

- Built a production-grade governance firewall with **16/16 passing automated unit and integration tests**.
- Implemented an **Attack Studio** demonstrating live mitigation of Privilege Escalation, Cross-Hop Scope Widening, Audit Log Tampering, and Prompt Injection.
- Created a tamper-evident audit log with instant cryptographic verification.
- Designed a clean, responsive control plane interface that operates smoothly on both desktop and mobile viewports.

---

## 7. What We Learned

- How to structure true defense-in-depth across multiple layers: Firewall Interceptor $\rightarrow$ Worker Runtime Validation $\rightarrow$ Google Cloud IAM Service Account Boundaries.
- The power of combining Gemini's autonomous task planning with deterministic scope boundaries for safe enterprise deployment.

---

## 8. What's Next for Fortified Agent Fleet

- **Dynamic IAM Token Minting**: Integration with GCP Workload Identity to issue short-lived, ephemeral scoped tokens per subtask.
- **Asymmetric Ed25519 Public-Key Infrastructure**: Per-agent private keys for decentralized provenance verification.
- **Cross-Enterprise Agent Federation**: Extending the scope firewall to govern multi-organization agent collaborations.
