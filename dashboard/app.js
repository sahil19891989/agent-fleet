/**
 * FORTIFIED AGENT FLEET - REAL-TIME CONTROL PLANE & DASHBOARD LOGIC
 * Interacts with Orchestrator REST APIs and renders interactive SVG topology.
 */

// State Management
const state = {
  fleet: null,
  selectedAgent: null,
  activeTask: null,
  provenanceRecords: [],
};

// Node coordinates for SVG canvas (Width: 100%, Height: 380)
const NODE_COORDINATES = {
  orchestrator: { x: 260, y: 190, r: 34, color: '#3b82f6', label: 'Orchestrator' },
  db_query_agent: { x: 90, y: 80, r: 26, color: '#10b981', label: 'DbQueryAgent' },
  report_agent: { x: 430, y: 80, r: 26, color: '#60a5fa', label: 'ReportAgent' },
  notifier_agent: { x: 430, y: 300, r: 26, color: '#f59e0b', label: 'NotifierAgent' },
  security_auditor_agent: { x: 90, y: 300, r: 26, color: '#a855f7', label: 'SecurityAuditor' },
};

const AGENT_METADATA = {
  orchestrator: {
    name: 'Orchestrator Control Plane',
    iam: 'roles/pubsub.publisher + roles/datastore.user',
    scopes: '[Root Delegation Authority]',
    score: 'Root',
    status: 'ONLINE',
  },
  db_query_agent: {
    name: 'DbQueryAgent (Cloud SQL)',
    iam: 'roles/cloudsql.viewer',
    scopes: '[cloudsql:orders:read, cloudsql:analytics:read]',
    score: '2 (Low)',
    status: 'ONLINE',
  },
  report_agent: {
    name: 'ReportAgent (Firestore)',
    iam: 'roles/datastore.user',
    scopes: '[firestore:reports:read, firestore:reports:write]',
    score: '5 (Medium)',
    status: 'ONLINE',
  },
  notifier_agent: {
    name: 'NotifierAgent (Channels)',
    iam: 'No elevated cloud roles (Channel Tokens)',
    scopes: '[slack:general:send, email:outbound:send, pagerduty:alerts:send]',
    score: '6 (Medium)',
    status: 'ONLINE',
  },
  security_auditor_agent: {
    name: 'SecurityAuditorAgent (Governance)',
    iam: 'roles/datastore.viewer',
    scopes: '[provenance:chain:audit, compliance:policies:read]',
    score: '3 (Low)',
    status: 'ONLINE',
  },
};

const ACTION_WEIGHTS = { read: 1, audit: 2, write: 4, send: 6, admin: 10 };

// --- DOM Initializer ---
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupEventListeners();
  loadFleetStatus();
  loadProvenanceLog();
  renderTopology();
  selectAgent('orchestrator');
});

// --- Tab Switching ---
function setupTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
    });
  });
}

// --- Event Listeners ---
function setupEventListeners() {
  // Workflow task runner
  document.getElementById('btn-run-workflow')?.addEventListener('click', () => {
    const input = document.getElementById('workflow-input').value.trim();
    if (input) runTask('/api/run-task', { description: input });
  });

  // Autonomous goal runner
  document.getElementById('btn-run-autonomous')?.addEventListener('click', () => {
    const goal = document.getElementById('autonomous-input').value.trim();
    if (goal) runTask('/api/run-autonomous', { goal: goal });
  });

  // Preset pills
  document.querySelectorAll('.pill-btn').forEach(pill => {
    pill.addEventListener('click', () => {
      document.getElementById('workflow-input').value = pill.dataset.input;
    });
  });

  document.querySelectorAll('.pill-btn-auto').forEach(pill => {
    pill.addEventListener('click', () => {
      document.getElementById('autonomous-input').value = pill.dataset.goal;
    });
  });

  // Template selector for Register Agent tab
  document.querySelectorAll('.template-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.getElementById('reg-agent-name').value = pill.dataset.name;
      document.getElementById('reg-agent-scopes').value = pill.dataset.scopes;
      document.getElementById('reg-agent-desc').value = pill.dataset.desc;
      updateScopeRiskPreview(pill.dataset.scopes);
    });
  });

  // Live input update for scope risk preview
  document.getElementById('reg-agent-scopes')?.addEventListener('input', (e) => {
    updateScopeRiskPreview(e.target.value);
  });

  // Attack studio triggers
  document.getElementById('btn-attack-privilege')?.addEventListener('click', () => {
    runAttack('privilege_escalation', 'db_query_agent');
  });

  document.getElementById('btn-attack-widening')?.addEventListener('click', () => {
    runAttack('scope_widening', 'report_agent');
  });

  document.getElementById('btn-attack-tamper')?.addEventListener('click', () => {
    runTamperSimulation();
  });

  document.getElementById('btn-attack-injection')?.addEventListener('click', () => {
    runAttack('prompt_injection', 'db_query_agent');
  });

  // Scope Sandbox Evaluator
  document.getElementById('btn-eval-scopes')?.addEventListener('click', evaluateScopeSandbox);

  // Register New Agent Form
  document.getElementById('btn-register-agent')?.addEventListener('click', registerNewAgent);

  // Auditor trigger
  document.getElementById('btn-run-audit')?.addEventListener('click', () => {
    runTask('/api/run-task', { description: 'Audit fleet health and compliance' });
  });

  // Refresh and verify actions
  document.getElementById('btn-refresh-fleet')?.addEventListener('click', loadFleetStatus);
  document.getElementById('btn-refresh-log')?.addEventListener('click', loadProvenanceLog);
  document.getElementById('btn-verify-signatures')?.addEventListener('click', verifyAllSignatures);
}

function updateScopeRiskPreview(scopeStr) {
  const preview = document.getElementById('preview-blast-score');
  if (!preview) return;

  const scopes = (scopeStr || '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  let totalScore = 0;

  scopes.forEach(s => {
    const parts = s.split(':');
    const action = parts[parts.length - 1];
    totalScore += ACTION_WEIGHTS[action] || 2;
  });

  let riskTier = 'NONE';
  if (totalScore > 0 && totalScore <= 2) riskTier = 'LOW RISK';
  else if (totalScore <= 5) riskTier = 'MEDIUM RISK';
  else if (totalScore <= 9) riskTier = 'HIGH RISK';
  else if (totalScore > 9) riskTier = 'CRITICAL RISK';

  preview.textContent = `${totalScore} (${riskTier})`;
}

// --- API Calls ---

async function loadFleetStatus() {
  try {
    const res = await fetch('/api/fleet');
    const data = await res.json();
    state.fleet = data;
    document.getElementById('metric-agent-count').textContent = data.total_agents || 4;
    
    populateTargetDropdown(data.agents || []);
    renderTopology();
  } catch (err) {
    console.error('Error loading fleet status:', err);
  }
}

function populateTargetDropdown(agents) {
  const targetSelect = document.getElementById('eval-target');
  if (!targetSelect) return;
  targetSelect.innerHTML = '';

  agents.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.name;
    opt.textContent = `${a.name} (Max Blast: ${a.blast_radius_ceiling})`;
    targetSelect.appendChild(opt);

    if (!AGENT_METADATA[a.name]) {
      AGENT_METADATA[a.name] = {
        name: a.name,
        iam: 'Custom Cloud Run SA',
        scopes: `[${a.scope_ceiling.join(', ')}]`,
        score: `${a.blast_radius_ceiling} (${a.risk_level})`,
        status: 'ONLINE',
      };
    }
  });
}

async function loadProvenanceLog() {
  try {
    const res = await fetch('/api/provenance');
    const data = await res.json();
    state.provenanceRecords = data.records || [];
    
    const stats = data.stats || {};
    document.getElementById('metric-total-delegations').textContent = stats.total_records || 0;
    document.getElementById('metric-quarantines').textContent = stats.quarantined_count || 0;
    document.getElementById('metric-avg-blast').textContent = stats.average_blast_radius || '0.0';

    renderProvenanceTable(state.provenanceRecords);
  } catch (err) {
    console.error('Error loading provenance log:', err);
  }
}

async function runTask(endpoint, payload) {
  setConsoleStatus('RUNNING', 'tag-running');
  setConsoleOutput('// Delegating task through Blast-Radius Firewall...\n');
  showSpinners(true);

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();

    if (result.quarantined) {
      setConsoleStatus('QUARANTINED', 'tag-danger');
      flashQuarantine('db_query_agent');
    } else {
      setConsoleStatus('SUCCESS', 'tag-success');
      flashFlow('all');
    }

    setConsoleOutput(JSON.stringify(result, null, 2));
    await loadProvenanceLog();
  } catch (err) {
    setConsoleStatus('ERROR', 'tag-danger');
    setConsoleOutput(`Execution Error: ${err.message}`);
  } finally {
    showSpinners(false);
  }
}

async function runAttack(attackType, targetAgent) {
  setConsoleStatus('ATTACKING', 'tag-running');
  setConsoleOutput(`// Simulating Attack: ${attackType} on ${targetAgent}...\n`);

  try {
    const res = await fetch('/api/run-attack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attack_type: attackType }),
    });
    const result = await res.json();

    if (result.quarantined || result.tamper_detected || result.status === 'MITIGATED_BY_AGENT') {
      setConsoleStatus('BLOCKED / QUARANTINED', 'tag-danger');
      flashQuarantine(targetAgent);
    } else {
      setConsoleStatus('ATTACK SUCCEEDED (UNEXPECTED)', 'tag-danger');
    }

    setConsoleOutput(JSON.stringify(result, null, 2));
    await loadProvenanceLog();
  } catch (err) {
    setConsoleStatus('ERROR', 'tag-danger');
    setConsoleOutput(`Simulation Error: ${err.message}`);
  }
}

async function evaluateScopeSandbox() {
  const caller = document.getElementById('eval-caller').value;
  const target = document.getElementById('eval-target').value;
  const scopesRaw = document.getElementById('eval-scopes').value;
  const scopes = scopesRaw.split(',').map(s => s.trim()).filter(Boolean);

  const resultBadge = document.getElementById('eval-result-badge');

  try {
    const res = await fetch('/api/evaluate-scope', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        caller_agent: caller,
        target_agent: target,
        requested_scopes: scopes,
      }),
    });
    const data = await res.json();

    resultBadge.classList.remove('hidden', 'eval-allowed', 'eval-quarantined');
    if (data.allowed) {
      resultBadge.classList.add('eval-allowed');
      resultBadge.innerHTML = `✅ <strong>APPROVED</strong>: Granted ${JSON.stringify(data.granted_scope)} | Risk Index: ${data.blast_radius_score} (${data.risk_level})<br><small>${data.reason}</small>`;
      flashFlow('all');
    } else {
      resultBadge.classList.add('eval-quarantined');
      resultBadge.innerHTML = `⛔ <strong>QUARANTINED</strong> (${data.violation_type}):<br><small>${data.reason}</small>`;
      flashQuarantine(target);
    }
  } catch (err) {
    alert('Scope evaluation error: ' + err.message);
  }
}

async function registerNewAgent() {
  const name = document.getElementById('reg-agent-name').value.trim();
  const desc = document.getElementById('reg-agent-desc').value.trim();
  const scopesRaw = document.getElementById('reg-agent-scopes').value.trim();
  const scopes = scopesRaw.split(',').map(s => s.trim()).filter(Boolean);

  if (!name || scopes.length === 0) {
    alert('Please enter an agent name and at least one scope (e.g. stripe:invoices:read).');
    return;
  }

  showSpinners(true);
  try {
    const res = await fetch('/api/register-agent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, scopes: scopes, description: desc }),
    });
    const result = await res.json();

    setConsoleStatus('AGENT REGISTERED', 'tag-success');
    setConsoleOutput(`// Newly Registered Agent: ${name}\nDeclared Scope Ceilings: ${JSON.stringify(result.scope_ceiling, null, 2)}\nBlast-Radius Ceiling: ${result.blast_radius_ceiling}\nStatus: ONLINE`);

    // Dynamically calculate coordinate for new agent on SVG canvas
    const count = Object.keys(NODE_COORDINATES).length;
    NODE_COORDINATES[name] = {
      x: 260 + Math.cos(count * 1.25) * 170,
      y: 190 + Math.sin(count * 1.25) * 110,
      r: 26,
      color: '#ec4899',
      label: name,
    };

    AGENT_METADATA[name] = {
      name: `${name} (Dynamic Agent)`,
      iam: 'Custom IAM Service Account',
      scopes: `[${result.scope_ceiling.join(', ')}]`,
      score: `${result.blast_radius_ceiling}`,
      status: 'ONLINE',
    };

    document.getElementById('reg-agent-name').value = '';
    document.getElementById('reg-agent-scopes').value = '';
    document.getElementById('reg-agent-desc').value = '';

    await loadFleetStatus();
    selectAgent(name);
    alert(`🎉 Agent '${name}' successfully onboarded into Fleet!`);
  } catch (err) {
    alert('Failed to register agent: ' + err.message);
  } finally {
    showSpinners(false);
  }
}

async function runTamperSimulation() {
  setConsoleStatus('TAMPERING', 'tag-running');
  setConsoleOutput('// Adversary injected unauthorized mutation into stored provenance log...\n');

  try {
    const res = await fetch('/api/simulate-tamper', { method: 'POST' });
    const result = await res.json();
    
    setConsoleStatus('TAMPER DETECTED', 'tag-danger');
    setConsoleOutput(JSON.stringify(result, null, 2));
    
    const badge = document.getElementById('chain-health-badge');
    badge.className = 'badge badge-danger';
    badge.innerHTML = '<span class="dot dot-red"></span> HMAC Chain: Compromised';

    await loadProvenanceLog();
  } catch (err) {
    setConsoleOutput(`Tamper error: ${err.message}`);
  }
}

async function verifyAllSignatures() {
  try {
    const res = await fetch('/api/verify-chain');
    const result = await res.json();

    const badge = document.getElementById('chain-health-badge');
    if (result.is_integral) {
      badge.className = 'badge badge-success';
      badge.innerHTML = '<span class="dot dot-green"></span> HMAC Chain: 100% Integral';
      alert(`✅ Provenance Integrity Certified:\nAll ${result.total} records verified against HMAC-SHA256 signatures.`);
    } else {
      badge.className = 'badge badge-danger';
      badge.innerHTML = `<span class="dot dot-red"></span> Tampering Detected (${result.tampered_count} records)`;
      alert(`⚠️ Audit Warning: Detected ${result.tampered_count} corrupted record(s) with invalid signatures.`);
    }
  } catch (err) {
    alert('Verification failed: ' + err.message);
  }
}

// --- SVG Topology Visualizer ---

function renderTopology() {
  const svg = document.getElementById('topology-svg');
  if (!svg) return;
  svg.innerHTML = '';

  const center = NODE_COORDINATES.orchestrator || { x: 260, y: 190, r: 34 };

  // Render Links
  Object.keys(NODE_COORDINATES).forEach(key => {
    if (key === 'orchestrator') return;
    const node = NODE_COORDINATES[key];

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', center.x);
    line.setAttribute('y1', center.y);
    line.setAttribute('x2', node.x);
    line.setAttribute('y2', node.y);
    line.setAttribute('class', 'topo-link');
    line.setAttribute('id', `link-${key}`);
    svg.appendChild(line);
  });

  // Render Nodes
  Object.keys(NODE_COORDINATES).forEach(key => {
    const node = NODE_COORDINATES[key];

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    group.setAttribute('class', 'node-group');
    group.setAttribute('id', `node-${key}`);
    group.addEventListener('click', () => selectAgent(key));

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', node.x);
    circle.setAttribute('cy', node.y);
    circle.setAttribute('r', node.r);
    circle.setAttribute('class', 'node-circle');
    circle.setAttribute('stroke', node.color);

    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', node.x);
    label.setAttribute('y', node.y + (key === 'orchestrator' ? 4 : 3));
    label.setAttribute('class', 'node-label');
    label.textContent = node.label;

    group.appendChild(circle);
    group.appendChild(label);
    svg.appendChild(group);
  });
}

function selectAgent(agentKey) {
  const meta = AGENT_METADATA[agentKey] || {
    name: agentKey,
    iam: 'Custom IAM Service Account',
    scopes: '[]',
    score: '0',
    status: 'ONLINE',
  };

  document.getElementById('inspector-name').textContent = meta.name;
  document.getElementById('inspector-iam').textContent = meta.iam;
  document.getElementById('inspector-scopes').textContent = meta.scopes;
  document.getElementById('inspector-score').textContent = meta.score;
  document.getElementById('inspector-status').textContent = meta.status;

  document.querySelectorAll('.node-circle').forEach(c => c.classList.remove('active-node'));
  const circle = document.querySelector(`#node-${agentKey} .node-circle`);
  if (circle) circle.classList.add('active-node');
}

function flashFlow(target) {
  document.querySelectorAll('.topo-link').forEach(l => {
    l.classList.add('active-flow');
    setTimeout(() => l.classList.remove('active-flow'), 2000);
  });
}

function flashQuarantine(agentKey) {
  const link = document.getElementById(`link-${agentKey}`);
  const circle = document.querySelector(`#node-${agentKey} .node-circle`);
  
  if (link) {
    link.classList.add('quarantine-flow');
    setTimeout(() => link.classList.remove('quarantine-flow'), 3000);
  }
  if (circle) {
    circle.classList.add('quarantined-node');
    setTimeout(() => circle.classList.remove('quarantined-node'), 3000);
  }
}

// --- Table Rendering ---

function renderProvenanceTable(records) {
  const tbody = document.getElementById('provenance-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!records || records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No audit records found. Run a task to generate logs.</td></tr>';
    return;
  }

  records.forEach(r => {
    const tr = document.createElement('tr');
    
    const statusHtml = r.allowed
      ? '<span class="status-badge badge-allowed">ALLOWED</span>'
      : '<span class="status-badge badge-quarantined">QUARANTINED</span>';

    const timeStr = new Date(r.timestamp * 1000).toLocaleTimeString();
    const sigTruncated = r.signature ? `${r.signature.substring(0, 12)}...` : 'NONE';
    const sigHtml = `<span class="sig-badge sig-valid" title="${r.signature}">HMAC-SHA256: ${sigTruncated}</span>`;

    tr.innerHTML = `
      <td>${statusHtml}</td>
      <td>${timeStr}</td>
      <td><strong>${escapeHtml(r.parent_agent)}</strong> &rarr; <strong>${escapeHtml(r.child_agent)}</strong></td>
      <td><code>${escapeHtml(r.requested_scope)}</code></td>
      <td><code>${escapeHtml(r.granted_scope || '{}')}</code></td>
      <td><span class="badge-score">${r.blast_radius_score}</span></td>
      <td>${sigHtml}</td>
      <td title="${escapeHtml(r.reason)}">${escapeHtml(r.reason.substring(0, 75))}${r.reason.length > 75 ? '...' : ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

// --- Helpers ---

function setConsoleStatus(text, className) {
  const el = document.getElementById('console-status');
  if (el) {
    el.className = `status-tag ${className}`;
    el.textContent = text;
  }
}

function setConsoleOutput(text) {
  const el = document.getElementById('console-body') || document.getElementById('console-output');
  if (el) el.textContent = text;
}

function showSpinners(show) {
  document.querySelectorAll('.spinner').forEach(s => {
    s.classList.toggle('hidden', !show);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
