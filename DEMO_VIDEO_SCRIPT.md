# 🎬 Fortified Enterprise Agent Fleet — 4-Minute Demo Video Script

**Target Duration**: ~3:45 to 4:00  
**Resolution**: 1080p 60fps  
**Video Requirement**: Must show backend running on Google Cloud / Control Plane UI.

---

### [0:00 - 0:45] The Problem & Value Proposition

**Visual**: Title slide with project branding $\rightarrow$ Architecture diagram showing compounding agent delegation risks.

**Speaker**:
> *"Welcome to the Fortified Enterprise Agent Fleet, built for the All Things Agentic Hackathon under the Fortified Enterprise Fleet track.*
>
> *As enterprises deploy autonomous multi-agent systems, agents delegate critical tasks to sub-agents. But standard frameworks have a fatal flaw: permissions get inherited implicitly, compounding risks go unmeasured, and there is no cryptographic guarantee against privilege escalation or log tampering.*
>
> *Our solution is the Fortified Fleet: an active zero-trust governance control plane that enforces mathematical Scope Attenuation, computes live Blast-Radius scores before any code runs, cryptographically signs every hop with HMAC-SHA256, and instantly quarantines unauthorized delegations."*

---

### [0:45 - 1:30] Google Cloud Architecture & System Overview

**Visual**: Google Cloud Console (Cloud Run dashboard showing 5 deployed services: `orchestrator`, `db-query-agent`, `report-agent`, `notifier-agent`, `security-auditor-agent`) $\rightarrow$ Switch to Web Dashboard at `http://localhost:8080`.

**Speaker**:
> *"Here is the architecture running on Google Cloud Run. Notice that each worker agent runs as an isolated microservice with its own dedicated Cloud IAM service account. The DB agent only has Cloud SQL viewer access, the report agent only has Firestore user access, and the notifier holds no ambient cloud permissions.*
>
> *Now, let's look at our live Web Control Plane. At the top, we see real-time metrics: 4 isolated agents, total delegations audited, quarantine interceptions, and average fleet blast radius. In the center is our interactive SVG Fleet Topology graph, where you can inspect each agent's IAM role, declared scope ceiling, and risk score."*

---

### [1:30 - 2:30] Live Execution: Standard Enterprise Task & Autonomous Gemini Planner

**Visual**:
1. Click **Enterprise Tasks** tab $\rightarrow$ Click **Execute Task** ("Q3 enterprise renewals analysis and retention alert").
2. Show animated green traffic flow on the topology graph.
3. Show execution telemetry in the console box.
4. Click **Autonomous Planner** tab $\rightarrow$ Enter "Investigate delinquent renewals and alert executive channel" $\rightarrow$ Click **Decompose & Run**.
5. Show Gemini decomposing the prompt into sub-tasks and successfully delegating through the firewall.

**Speaker**:
> *"Let's execute a standard enterprise workflow: analyzing Q3 renewals. As I click Execute Task, the orchestrator evaluates each step against the Blast-Radius Firewall. You see green traffic flow across DbQueryAgent, ReportAgent, and NotifierAgent, completing the pipeline safely.*
>
> *Next, let's test our Autonomous Gemini 2.5 Planner. I can enter an open-ended goal, and Gemini dynamically analyzes the request, selects the required agents, negotiates least-privilege scopes, and navigates the firewall to execute the mission autonomously."*

---

### [2:30 - 3:30] Attack Studio: Zero-Trust Quarantines & Tamper Detection

**Visual**:
1. Click **Attack Studio** tab.
2. Click **1. Privilege Escalation** $\rightarrow$ Show immediate red quarantine alert on topology graph and crimson `QUARANTINED` status in console.
3. Click **3. Audit Record Tampering** $\rightarrow$ Click **Verify Signatures** $\rightarrow$ Show alert banner flashing red: `HMAC Chain: Compromised (Tampering Detected)`.
4. Point to the **Cryptographic Provenance Table** showing HMAC-SHA256 signatures, blast-radius scores, and firewall rationales.

**Speaker**:
> *"Now for the most important test: security resilience in our Attack Studio.*
>
> *First, we simulate a Privilege Escalation attack where an agent requests write permissions on a read-only database. Instantly, the Blast-Radius Firewall catches the violation, the topology flashes red, and the chain is quarantined before any malicious action reaches the agent.*
>
> *Second, what if an adversary tampers with stored audit logs? When we inject a tampered record and click 'Verify Signatures', our cryptographic HMAC-SHA256 engine immediately detects the signature mismatch and flags the compromise.*
>
> *Every single delegation—allowed or blocked—is recorded in our immutable provenance audit trail with complete mathematical non-repudiation."*

---

### [3:30 - 4:00] Conclusion & Hackathon Wrap-Up

**Visual**: Full dashboard view showing green health restore $\rightarrow$ Summary slide with GitHub repo and track info.

**Speaker**:
> *"The Fortified Enterprise Agent Fleet brings true zero-trust security, transparent governance, and cryptographic auditability to multi-agent AI systems.*
>
> *All code is open-source, fully tested with 16/16 automated test suites, and ready for deployment on Google Cloud.*
>
> *Thank you, and we look forward to your feedback!"*
