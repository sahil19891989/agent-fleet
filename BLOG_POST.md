# Fortifying Multi-Agent Systems: Zero-Trust Scope Attenuation & Cryptographic HMAC Provenance

*Published for the **All Things Agentic Hackathon** (Track: Fortified Enterprise Fleet)*

---

## The Silent Threat in Multi-Agent AI Architectures

Autonomous AI agents are rapidly evolving from simple conversational interfaces into distributed, multi-tier agent fleets. In these architectures, an **Orchestrator Agent** decomposes complex enterprise tasks and delegates subtasks to specialized worker agents—such as database query bots, reporting engines, and alert dispatchers.

However, as permissions flow through delegation chains, standard multi-agent systems suffer from a severe architectural vulnerability: **Implicit Privilege Escalation & Compounding Ambient Risk**.

When an agent delegates a task, how do we guarantee that a sub-agent only receives the minimum necessary permissions? What prevents a compromised analytics agent from requesting destructive `WRITE` or `ADMIN` access? And if an adversary alters the delegation logs, how can compliance auditors mathematically prove non-repudiation?

To solve this, we built the **Fortified Enterprise Agent Fleet**—a zero-trust governance control plane powered by **Gemini 2.5 Flash**, **Google ADK**, and **Google Cloud Run**.

---

## 1. Zero-Trust Scope Attenuation

In traditional RBAC, roles are static. In our zero-trust agent fleet, permissions are dynamic and strictly **attenuated** across hops.

A scope is defined as a granular `(resource, action)` pair (e.g., `cloudsql:orders:read` or `firestore:reports:write`). We enforce the mathematical law of Scope Attenuation:

$$\text{Granted Scope} = \text{Requested Scope} \cap \text{Caller Scope} \cap \text{Target Ceiling}$$

Scope can **only narrow** as it travels down a delegation chain—it can **never widen**.

```python
# firewall/scopes.py
@dataclass(frozen=True)
class ScopeSet:
    scopes: frozenset[Scope] = field(default_factory=frozenset)

    def is_subset_of(self, other: "ScopeSet") -> bool:
        return self.scopes.issubset(other.scopes)

    def intersect(self, other: "ScopeSet") -> "ScopeSet":
        """Child scope = requested ∩ caller's granted scope."""
        return ScopeSet(self.scopes & other.scopes)
```

---

## 2. The Blast-Radius Firewall

Before any delegated task executes, it is intercepted by the **Blast-Radius Firewall**. The firewall calculates an explainable risk metric based on operation severity:

$$\text{Score}(\text{Scope}) = \sum \text{Weight}(\text{Action})$$
*(where $\text{Read}=1, \text{Audit}=2, \text{Write}=4, \text{Send}=6, \text{Admin}=10$)*

If an agent attempts an unauthorized action (e.g., a read-only query agent attempting `cloudsql:orders:write`), the firewall instantly halts execution, raises a `QuarantineError`, and logs the full diagnostic rationale.

---

## 3. Cryptographic HMAC-SHA256 Provenance Audit Trail

Standard database logs can be manipulated if a storage layer is compromised. To ensure verifiable non-repudiation, every single delegation hop (whether **ALLOWED** or **QUARANTINED**) is cryptographically signed using `HMAC-SHA256`:

```python
# provenance/chain.py
@dataclass
class ProvenanceRecord:
    task_id: str
    parent_agent: str
    child_agent: str
    requested_scope: str
    granted_scope: str
    allowed: bool
    reason: str
    blast_radius_score: int
    timestamp: float
    signature: str = ""

    def sign(self) -> "ProvenanceRecord":
        sig = hmac.new(
            SECRET.encode(), self.signed_payload().encode(), hashlib.sha256
        ).hexdigest()
        self.signature = sig
        return self

    def verify(self) -> bool:
        expected = hmac.new(
            SECRET.encode(), self.signed_payload().encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, self.signature)
```

If any log record is mutated after the fact, the cryptographic audit engine immediately detects the signature mismatch.

---

## 4. Multi-Service Cloud Run Isolation

Rather than running all agents in a single monolith, the Fortified Fleet deploys each worker as an independent **Google Cloud Run** service backed by a dedicated **Google Cloud IAM Service Account**:

- `db-query-agent-sa` $\rightarrow$ `roles/cloudsql.viewer`
- `report-agent-sa` $\rightarrow$ `roles/datastore.user`
- `security-auditor-sa` $\rightarrow$ `roles/datastore.viewer`
- `notifier-agent-sa` $\rightarrow$ No ambient cloud permissions

This provides true network-level and OS-level process isolation, enforcing defense-in-depth across the entire fleet.

---

## 5. Real-Time Web Dashboard & Attack Studio

To make agent governance accessible, we built a real-time visual control plane:
- **Live SVG Topology Graph**: Visualizes live delegation traffic with animated green flow lines and crimson quarantine flashes.
- **Autonomous Planner (Gemini 2.5)**: Allows operators to submit open-ended enterprise goals, which Gemini decomposes into least-privilege subtasks.
- **Attack Simulation Studio**: One-click vulnerability testing for Privilege Escalation, Cross-Hop Scope Widening, Log Tampering, and SQL Injection.

---

## Summary & Next Steps

The **Fortified Enterprise Agent Fleet** proves that enterprise multi-agent systems do not have to sacrifice security for autonomy. By combining Gemini 2.5's reasoning capabilities with mathematical scope attenuation and cryptographic audit trails, we can safely govern autonomous agent networks at enterprise scale.

- **Explore the Code**: [GitHub Repository](https://github.com/sahil19891989/agent-fleet)
- **Watch the Demo**: [YouTube Demo Walkthrough](https://youtube.com/watch?v=...)
- **Built for**: Google's *All Things Agentic Hackathon* (#AllThingsAgenticHackathon)
