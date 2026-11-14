"""
Flask Blueprint & Agent Dashboard for the Trusted Research Workflow Agent.
Exposes REST endpoints for analysis, Socratic clarification, dossier generation,
adapter dispatch, human gates, audit trail inspection, and the web UI.
"""

from flask import Blueprint, request, jsonify, render_template_string, redirect, url_for, session
import os
import json
from .service import AgentOrchestrator
from .dossier import render_dossier_html
from .workflow import WorkflowError, load_workflow_state
from .audit import record_audit_event, get_audit_history, verify_audit_integrity
from core.auth_store import get_student_user, verify_faculty_passcode

agent_bp = Blueprint("agent_bp", __name__)
orchestrator = AgentOrchestrator()


def _check_project_access(project_id: str):
    """
    Verifies that a logged-in student cannot access or mutate another registered student's project.
    Faculty sessions have full access.
    """
    if session.get("faculty_authenticated"):
        return None
    logged_student = session.get("student_id")
    if session.get("role") == "student" and logged_student and logged_student != project_id:
        # Check if target project_id belongs to a registered student
        if get_student_user(project_id) is not None:
            return jsonify({
                "success": False,
                "error": f"Security Violation: Student '{logged_student}' is not authorized to access project '{project_id}'."
            }), 403
    return None


def _get_proposal_data_or_fallback(project_id: str):
    """Loads proposal draft from portal/data/drafts/ or returns synthetic fallback."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    draft_file = os.path.join(base_dir, "data", "drafts", f"{project_id}.json")
    if os.path.exists(draft_file):
        try:
            with open(draft_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "student_id": project_id,
        "student_name": f"Researcher {project_id}",
        "title": f"Biotechnology Proposal {project_id}",
        "methodology": "Standard laboratory procedures with model systems."
    }


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@agent_bp.route("/api/tools", methods=["GET"])
def api_tools():
    return jsonify({
        "success": True,
        "tool_count": len(orchestrator.get_tool_registry()),
        "tools": orchestrator.get_tool_registry(),
        "limits": orchestrator.agent_loop.limits.to_dict()
    })


@agent_bp.route("/api/status/<project_id>", methods=["GET"])
def api_status(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    overview = orchestrator.get_workflow_overview(project_id)
    return jsonify({"success": True, **overview})


@agent_bp.route("/api/analyze/<project_id>", methods=["POST"])
def api_analyze(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    req_data = request.get_json(silent=True) or {}
    proposal = req_data.get("proposal_data") or _get_proposal_data_or_fallback(project_id)
    try:
        res = orchestrator.analyze_proposal(proposal, project_id=project_id)
        res["active_requirements"] = res.get("requirements", [])
        res["extracted_context"] = res.get("context", {})
        return jsonify({"success": True, **res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@agent_bp.route("/api/clarify/<project_id>", methods=["POST"])
def api_clarify(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    q_id = data.get("question_id", "").strip()
    answer = data.get("answer", "").strip()
    if not q_id or not answer:
        return jsonify({"success": False, "error": "Both 'question_id' and 'answer' are required."}), 400

    res = orchestrator.submit_clarification(project_id, q_id, answer)
    status_code = 200 if res.get("success") else 400
    return jsonify(res), status_code


@agent_bp.route("/api/dossier/<project_id>", methods=["GET"])
def api_dossier(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    try:
        dossier = orchestrator.compile_dossier(project_id)
        return jsonify({"success": True, "dossier": dossier})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@agent_bp.route("/dossier/<project_id>/view", methods=["GET"])
def view_dossier_html(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    try:
        dossier = orchestrator.compile_dossier(project_id)
        html = render_dossier_html(dossier)
        return html
    except Exception as e:
        return f"<h3>Error compiling dossier: {str(e)}</h3>", 400


@agent_bp.route("/api/dispatch/<project_id>", methods=["POST"])
def api_dispatch(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "auto")
    try:
        res = orchestrator.dispatch_to_bioethics(project_id, mode=mode)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@agent_bp.route("/api/human_decision/<project_id>", methods=["POST"])
def api_human_decision(project_id):
    data = request.get_json(silent=True) or {}
    actor = data.get("actor", "human").strip()
    decision = data.get("decision", "").strip()
    notes = data.get("notes", "").strip()
    conditions = data.get("conditions", "").strip()
    passcode = (data.get("reviewer_passcode") or request.headers.get("X-Faculty-Passcode") or "").strip()

    if not decision:
        return jsonify({"success": False, "error": "Decision ('approved', 'revisions_requested', 'rejected') required."}), 400

    # If actor != "human" (e.g., actor="agent"), delegate directly to orchestrator so enforce_human_review_gate
    # raises UnauthorizedActionError and records UNAUTHORIZED_ACTION_ATTEMPTED in the hash-chained audit trail.
    if actor != "human":
        reviewer_id = data.get("reviewer_id", "").strip() or "autonomous_agent"
        role = data.get("role", "agent").strip()
        try:
            res = orchestrator.record_human_decision(
                project_id=project_id,
                reviewer_id=reviewer_id,
                role=role,
                decision=decision,
                notes=notes,
                conditions=conditions,
                actor=actor
            )
            return jsonify(res)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 403

    # For actor == "human": strictly require either an authenticated faculty session OR a verified reviewer passcode.
    # Logged-in students without faculty authentication / passcode are strictly blocked.
    is_faculty_session = bool(session.get("faculty_authenticated"))
    is_passcode_verified = bool(passcode and verify_faculty_passcode(passcode))

    if session.get("role") == "student" and not is_faculty_session and not is_passcode_verified:
        state = load_workflow_state(project_id)
        err_msg = "Security Violation: Logged-in students are strictly prohibited from executing institutional review gates."
        record_audit_event(
            project_id=project_id,
            event_type="UNAUTHORIZED_ACTION_ATTEMPTED",
            actor="student",
            actor_id=f"student:{session.get('student_id', 'unknown')}",
            action=f"Blocked student attempt to execute human decision gate: '{decision}'",
            workflow_state=state.get("current_state", "DRAFT"),
            evidence_reference=err_msg,
            details={"attempted_role": data.get("role"), "decision": decision}
        )
        return jsonify({"success": False, "error": err_msg}), 403

    if not is_faculty_session and not is_passcode_verified:
        state = load_workflow_state(project_id)
        err_msg = (
            "Security Violation: Institutional review gate requires an authenticated faculty/reviewer session "
            "or a valid reviewer authorization passcode."
        )
        record_audit_event(
            project_id=project_id,
            event_type="UNAUTHORIZED_ACTION_ATTEMPTED",
            actor="unauthenticated",
            actor_id=data.get("reviewer_id", "unauthenticated_caller"),
            action=f"Blocked unauthenticated human decision attempt: '{decision}'",
            workflow_state=state.get("current_state", "DRAFT"),
            evidence_reference=err_msg,
            details={"attempted_role": data.get("role"), "decision": decision}
        )
        return jsonify({"success": False, "error": err_msg}), 403

    if is_faculty_session:
        reviewer_id = data.get("reviewer_id", "").strip() or session.get("faculty_user", "faculty_chair")
        role = data.get("role", "").strip() or session.get("faculty_role", "faculty_instructor")
    else:
        reviewer_id = data.get("reviewer_id", "").strip() or "ethics_officer"
        role = data.get("role", "ethics_officer").strip()

    try:
        res = orchestrator.record_human_decision(
            project_id=project_id,
            reviewer_id=reviewer_id,
            role=role,
            decision=decision,
            notes=notes,
            conditions=conditions,
            actor="human"
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 403


@agent_bp.route("/api/audit/<project_id>", methods=["GET"])
def api_audit(project_id):
    denied = _check_project_access(project_id)
    if denied:
        return denied
    history = get_audit_history(project_id)
    integrity = verify_audit_integrity(project_id)
    return jsonify({"success": True, "project_id": project_id, "event_count": len(history), "integrity": integrity, "events": history})


# -------------------------------------------------------------
# Agent Web Dashboard UI (Phase 11)
# -------------------------------------------------------------

DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Trusted Research Workflow Agent • {{ project_id }}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #111827;
      --border: #1f2937;
      --indigo: #6366f1;
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --text: #f3f4f6;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; }
    body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; line-height: 1.5; }
    .navbar { background: #030712; border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; }
    .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.1rem; }
    .brand-badge { background: rgba(99, 102, 241, 0.2); color: var(--indigo); border: 1px solid rgba(99, 102, 241, 0.4); padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
    .container { max-width: 1200px; margin: 24px auto; padding: 0 20px; }
    .state-banner { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
    .state-badge { font-size: 0.85rem; font-weight: 800; text-transform: uppercase; padding: 6px 14px; border-radius: 8px; letter-spacing: 0.5px; }
    .badge-draft { background: rgba(156, 163, 175, 0.2); color: var(--muted); border: 1px solid var(--muted); }
    .badge-pending { background: rgba(245, 158, 11, 0.2); color: var(--amber); border: 1px solid var(--amber); }
    .badge-cleared { background: rgba(16, 185, 129, 0.2); color: var(--emerald); border: 1px solid var(--emerald); }
    .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 24px; }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    h2 { font-size: 1.1rem; margin: 0 0 16px 0; color: #fff; border-bottom: 1px solid var(--border); padding-bottom: 10px; display: flex; justify-content: space-between; }
    .btn { background: var(--indigo); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; transition: 0.15s; font-size: 0.88rem; }
    .btn:hover { background: #4f46e5; }
    .btn-emerald { background: var(--emerald); }
    .btn-emerald:hover { background: #059669; }
    .btn-amber { background: var(--amber); color: #000; }
    .btn-amber:hover { background: #d97706; }
    .btn-outline { background: transparent; border: 1px solid var(--border); color: var(--text); }
    .btn-outline:hover { background: rgba(255,255,255,0.05); }
    .entity-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .entity-table th { text-align: left; padding: 8px; color: var(--muted); border-bottom: 1px solid var(--border); }
    .entity-table td { padding: 10px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .log-item { font-size: 0.8rem; font-family: monospace; padding: 8px 12px; background: rgba(0,0,0,0.3); border-left: 3px solid var(--indigo); margin-bottom: 6px; border-radius: 0 6px 6px 0; }
    .clarif-box { background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 14px; margin-bottom: 12px; }
    textarea { width: 100%; background: #000; border: 1px solid var(--border); color: #fff; border-radius: 6px; padding: 8px; margin-top: 8px; font-family: inherit; font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="navbar">
    <div class="brand">
      <span>🛡️ Trusted Research Workflow Agent</span>
      <span class="brand-badge">Catalyst MVP • 2026</span>
    </div>
    <div>
      <a href="/" class="btn btn-outline" style="text-decoration:none; margin-right:8px;">← Proposal Studio</a>
      <a href="/faculty" class="btn btn-outline" style="text-decoration:none;">Faculty Studio</a>
    </div>
  </div>

  <div class="container">
    <div class="state-banner">
      <div>
        <div style="font-size:0.8rem; color:var(--muted); text-transform:uppercase;">Research Project Lifecycle State</div>
        <div style="font-size:1.3rem; font-weight:800; color:#fff; margin-top:2px;">{{ overview.context.title if overview.context else project_id }}</div>
        <div style="font-size:0.85rem; color:var(--muted); margin-top:4px;">
          Next Action: <strong>{{ overview.next_action.action }}</strong> • Actor: <span style="color:var(--indigo);">{{ overview.next_action.actor }}</span>
        </div>
      </div>
      <div>
        <span class="state-badge {% if overview.current_state == 'CLEARED_FOR_NEXT_STAGE' %}badge-cleared{% elif 'PENDING' in overview.current_state or 'CLARIFICATION' in overview.current_state %}badge-pending{% else %}badge-draft{% endif %}">
          {{ overview.current_state }}
        </span>
      </div>
    </div>

    <div class="grid">
      <!-- Left Column: Context, Requirements, Clarification -->
      <div>
        <!-- Socratic Clarifications Section -->
        {% if overview.pending_clarifications %}
        <div class="card" style="border-color:var(--amber);">
          <h2 style="color:var(--amber);">⚠️ Targeted Socratic Clarifications ({{ overview.pending_clarifications|length }})</h2>
          <p style="font-size:0.85rem; color:var(--muted);">The agent detected ambiguities in regulatory parameters. Please provide clarification to advance workflow:</p>
          {% for q in overview.pending_clarifications %}
          <div class="clarif-box">
            <div style="font-weight:700; font-size:0.9rem; color:#fff;">[{{ q.question_id }}] {{ q.prompt }}</div>
            <div style="font-size:0.8rem; color:var(--muted); margin-top:4px;"><em>Rationale: {{ q.rationale }}</em></div>
            <form onsubmit="submitClarification(event, '{{ q.question_id }}')">
              <textarea id="answer-{{ q.question_id }}" rows="2" placeholder="State strain repository (e.g. ATCC 25922) or exact containment protocol..." required></textarea>
              <div style="margin-top:8px; text-align:right;">
                <button type="submit" class="btn btn-amber">Submit Clarification</button>
              </div>
            </form>
          </div>
          {% endfor %}
        </div>
        {% endif %}

        <!-- Research Context Card -->
        <div class="card">
          <h2>
            <span>Extracted Research Context</span>
            <button onclick="runAnalysis()" class="btn btn-outline" style="font-size:0.75rem;">Re-Run Extraction</button>
          </h2>
          {% if overview.context %}
          <table class="entity-table">
            <thead>
              <tr><th>Entity / Parameter</th><th>Extracted Value</th><th>Status</th><th>Evidence Snippet</th></tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Host / Chassis</strong></td>
                <td>{{ overview.context.organism_or_chassis.value }}</td>
                <td><span style="color:var(--emerald);">{{ overview.context.organism_or_chassis.status }}</span></td>
                <td><em>"{{ overview.context.organism_or_chassis.evidence[:60] }}..."</em></td>
              </tr>
              <tr>
                <td><strong>Sample Type</strong></td>
                <td>{{ overview.context.sample_type.value }}</td>
                <td><span>{{ overview.context.sample_type.status }}</span></td>
                <td><em>"{{ overview.context.sample_type.evidence[:60] }}..."</em></td>
              </tr>
              <tr>
                <td><strong>Clinical / Human</strong></td>
                <td>{{ overview.context.human_subjects.value }}</td>
                <td><span>{{ overview.context.human_subjects.status }}</span></td>
                <td><em>"{{ overview.context.human_subjects.evidence[:60] }}..."</em></td>
              </tr>
              <tr>
                <td><strong>Pathogen / AMR</strong></td>
                <td>{{ overview.context.pathogen_work.value }} (AMR: {{ overview.context.antimicrobial_resistance.value }})</td>
                <td><span>{{ overview.context.pathogen_work.status }}</span></td>
                <td><em>"{{ overview.context.pathogen_work.evidence[:60] }}..."</em></td>
              </tr>
              <tr>
                <td><strong>Biosafety Containment</strong></td>
                <td>{{ overview.context.biosafety_containment.value }}</td>
                <td><span>{{ overview.context.biosafety_containment.status }}</span></td>
                <td><em>"{{ overview.context.biosafety_containment.evidence[:60] }}..."</em></td>
              </tr>
            </tbody>
          </table>
          {% else %}
          <p style="color:var(--muted);">No context extracted yet. Click 'Re-Run Extraction' to analyze proposal.</p>
          {% endif %}
        </div>

        <!-- Institutional Compliance Requirements -->
        <div class="card">
          <h2>Institutional Requirements & Gating Triggers ({{ overview.requirements|length }})</h2>
          {% if overview.requirements %}
            {% for req in overview.requirements %}
            <div style="background:rgba(255,255,255,0.03); border-left:3px solid var(--indigo); padding:10px 14px; margin-bottom:8px; border-radius:0 6px 6px 0;">
              <div style="font-weight:700; color:#fff;">{{ req.title }} <span style="font-size:0.75rem; color:var(--amber);">({{ req.status }})</span></div>
              <div style="font-size:0.8rem; color:var(--muted); margin-top:2px;">{{ req.applicable_annex }}</div>
              <div style="font-size:0.8rem; color:#cbd5e1; margin-top:4px;"><strong>Reviewer Mandate:</strong> {{ req.human_action_required }}</div>
            </div>
            {% endfor %}
          {% else %}
            <p style="color:var(--muted);">No requirements triggered.</p>
          {% endif %}
        </div>
      </div>

      <!-- Right Column: Actions, Dossier, Human Gate, Audit -->
      <div>
        <!-- Workflow Actions Card -->
        <div class="card">
          <h2>Workflow Operations</h2>
          <div style="display:flex; flex-direction:column; gap:8px;">
            <button onclick="runAnalysis()" class="btn">1. Analyze Proposal Context</button>
            <a href="/agent/dossier/{{ project_id }}/view" target="_blank" class="btn btn-outline" style="text-align:center; text-decoration:none;">
              2. View Pre-Submission Dossier (HTML)
            </a>
            <button onclick="dispatchBioEthics()" class="btn btn-emerald">3. Dispatch to BioEthics Adapter (Simulated Handoff)</button>
          </div>
        </div>

        <!-- Human Review Gate Card -->
        <div class="card" style="border-color:var(--indigo);">
          <h2 style="color:#fff;">🛡️ Human Decision Gate</h2>
          <p style="font-size:0.8rem; color:var(--muted);">
            Enforces non-delegable authority. Agent CANNOT approve clearance autonomously.
          </p>
          {% if overview.human_decision %}
          <div style="background:rgba(16,185,129,0.1); border:1px solid var(--emerald); padding:12px; border-radius:8px;">
            <div style="font-weight:700; color:var(--emerald);">Decision: {{ overview.human_decision.decision|upper }}</div>
            <div style="font-size:0.8rem; color:#fff; margin-top:4px;">Signed by: {{ overview.human_decision.role }} ({{ overview.human_decision.reviewer_id }})</div>
            <div style="font-size:0.8rem; color:var(--muted); margin-top:2px;">Conditions: {{ overview.human_decision.conditions or 'None' }}</div>
          </div>
          {% else %}
          <form onsubmit="submitHumanDecision(event)">
            <label style="font-size:0.8rem; color:var(--muted);">Reviewer Role:</label>
            <select id="human-role" style="width:100%; background:#000; border:1px solid var(--border); color:#fff; padding:6px; border-radius:6px; margin-bottom:8px;">
              <option value="ethics_officer">Ethics Committee Officer</option>
              <option value="biosafety_officer">Institutional Biosafety Officer</option>
              <option value="faculty_instructor">Course Faculty Chair</option>
            </select>
            <label style="font-size:0.8rem; color:var(--muted);">Decision:</label>
            <select id="human-decision" style="width:100%; background:#000; border:1px solid var(--border); color:#fff; padding:6px; border-radius:6px; margin-bottom:8px;">
              <option value="approved">Approve & Clear for Next Stage</option>
              <option value="revisions_requested">Request Proposal Revisions</option>
              <option value="rejected">Reject Submission</option>
            </select>
            <label style="font-size:0.8rem; color:var(--muted);">Reviewer Authorization Passcode (if not logged into Faculty Studio):</label>
            <input type="password" id="human-passcode" placeholder="Enter Faculty/Reviewer Passcode..." style="width:100%; background:#000; border:1px solid var(--border); color:#fff; padding:6px; border-radius:6px; margin-bottom:8px;" />
            <textarea id="human-conditions" rows="2" placeholder="Mandatory conditions (e.g. BSL-2 certified hood only)..."></textarea>
            <button type="submit" class="btn btn-emerald" style="width:100%; margin-top:8px;">Record Human Sign-Off</button>
          </form>
          {% endif %}
        </div>

        <!-- Audit Ledger Card -->
        <div class="card">
          <h2>
            <span>Audit History ({{ overview.audit_history|length }})</span>
            <span style="font-size:0.75rem; color:var(--emerald);">Hash Chain Valid ✓</span>
          </h2>
          <div style="max-height:300px; overflow-y:auto;">
            {% for ev in overview.audit_history|reverse %}
            <div class="log-item">
              <span style="color:var(--amber);">[{{ ev.timestamp[11:19] }}]</span>
              <strong style="color:#fff;">{{ ev.event_type }}</strong>
              <div style="color:var(--muted); font-size:0.75rem;">{{ ev.action }} ({{ ev.actor }})</div>
            </div>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const PROJECT_ID = "{{ project_id }}";

    async function runAnalysis() {
      const res = await fetch(`/agent/api/analyze/${PROJECT_ID}`, { method: 'POST', headers: {'Content-Type': 'application/json'} });
      const data = await res.json();
      if (data.success) {
        window.location.reload();
      } else {
        alert("Error running analysis: " + data.error);
      }
    }

    async function submitClarification(e, qId) {
      e.preventDefault();
      const ans = document.getElementById(`answer-${qId}`).value;
      const res = await fetch(`/agent/api/clarify/${PROJECT_ID}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ question_id: qId, answer: ans })
      });
      const data = await res.json();
      if (data.success) {
        window.location.reload();
      } else {
        alert("Error: " + data.error);
      }
    }

    async function dispatchBioEthics() {
      const res = await fetch(`/agent/api/dispatch/${PROJECT_ID}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mode: 'auto' })
      });
      const data = await res.json();
      if (data.success) {
        alert(`[SIMULATED HANDOFF — NOT A REAL INSTITUTIONAL SUBMISSION]\nDispatched to BioEthics Adapter (Mode: ${data.mode})\nRemote ID: ${data.remote_application_id}`);
        window.location.reload();
      } else {
        alert("Dispatch error: " + data.error);
      }
    }

    async function submitHumanDecision(e) {
      e.preventDefault();
      const role = document.getElementById('human-role').value;
      const dec = document.getElementById('human-decision').value;
      const cond = document.getElementById('human-conditions').value;
      const passcodeEl = document.getElementById('human-passcode');
      const passcode = passcodeEl ? passcodeEl.value : '';
      const res = await fetch(`/agent/api/human_decision/${PROJECT_ID}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ role: role, decision: dec, conditions: cond, reviewer_id: 'officer_101', reviewer_passcode: passcode })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message);
        window.location.reload();
      } else {
        alert("Decision error: " + data.error);
      }
    }
  </script>
</body>
</html>
"""


@agent_bp.route("/dashboard/<project_id>", methods=["GET"])
def agent_dashboard_view(project_id):
    overview = orchestrator.get_workflow_overview(project_id)
    # If project has never been analyzed, run initial analysis
    if overview.get("current_state") == "DRAFT" and not overview.get("context"):
        proposal = _get_proposal_data_or_fallback(project_id)
        orchestrator.analyze_proposal(proposal, project_id=project_id)
        overview = orchestrator.get_workflow_overview(project_id)

    return render_template_string(DASHBOARD_TEMPLATE, project_id=project_id, overview=overview)
