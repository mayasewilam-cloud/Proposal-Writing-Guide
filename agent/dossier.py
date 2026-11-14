"""
Ethics Pre-Submission Dossier Compiler for the Trusted Research Workflow Agent.
Generates an audit-ready, structured compliance dossier from verified proposal context.
Every attribute is classified as CONFIRMED, INFERRED, UNCERTAIN, or MISSING.
Supports JSON export and clean HTML rendering.
"""

from typing import Dict, Any, List
import datetime
from .models import ResearchContext, RequirementAssessment, FieldStatus


def compile_ethics_pre_submission_dossier(
    context: ResearchContext,
    requirements: List[RequirementAssessment],
    clarification_history: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synthesizes a structured Ethics Pre-Submission Dossier.
    Strictly distinguishes between confirmed data, inferred triggers, and missing fields.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    clarification_history = clarification_history or []

    # Map entities to explicit certainty buckets
    entity_matrix = []
    
    def _add_entity_row(label: str, field_ev):
        status_label = {
            FieldStatus.CONFIRMED: "CONFIRMED FROM PROPOSAL / RESEARCHER",
            FieldStatus.INFERRED: "INFERRED / FLAGGED BY AGENT",
            FieldStatus.REQUIRES_HUMAN_REVIEW: "REQUIRES HUMAN REVIEW / CONTRADICTION FLAGGED",
            FieldStatus.UNCERTAIN: "UNCERTAIN / AMBIGUOUS",
            FieldStatus.MISSING: "MISSING FROM PROPOSAL"
        }.get(field_ev.status, "UNVERIFIED")

        entity_matrix.append({
            "parameter": label,
            "value": str(field_ev.value),
            "status_classification": status_label,
            "source_section": field_ev.source,
            "confidence": f"{int(field_ev.confidence * 100)}%",
            "verbatim_evidence": field_ev.evidence or "None specified",
            "regulatory_rationale": field_ev.rationale
        })

    _add_entity_row("Host Organism / Chassis", context.organism_or_chassis)
    _add_entity_row("Sample Type / Origin", context.sample_type)
    _add_entity_row("Human Subjects / Clinical Samples", context.human_subjects)
    _add_entity_row("Vertebrate / In Vivo Animal Models", context.animal_subjects)
    _add_entity_row("Genetic Modification / Recombinant Vectors", context.genetic_modification)
    _add_entity_row("Antimicrobial Resistance Determinants", context.antimicrobial_resistance)
    _add_entity_row("Pathogen / Infectious Agents", context.pathogen_work)
    _add_entity_row("Biosafety Containment Level", context.biosafety_containment)

    # Format tools
    tools_summary = ", ".join([f"{t.value} ({t.status})" for t in context.molecular_tools]) or "None extracted"

    # Compile triggered annexes
    applicable_annexes = []
    for req in requirements:
        if req.status == "potentially_relevant" and req.applicable_annex:
            applicable_annexes.append({
                "rule_id": req.rule_id,
                "annex_name": req.applicable_annex,
                "category": req.category,
                "title": req.title,
                "action_required": req.human_action_required,
                "cited_evidence": req.evidence
            })

    dossier = {
        "dossier_id": f"DOSSIER-{context.project_id}",
        "generated_at": now_iso,
        "governing_standard": "BioEthics & Institutional Biosafety Committee (IBC) Pre-Submission Protocol",
        "metadata": {
            "project_id": context.project_id,
            "proposal_title": context.title,
            "researcher_name": context.researcher_name,
            "institution": "Faculty of Biotechnology, MSA University",
            "course_context": "BT_301: Introduction to Biotechnology"
        },
        "molecular_tools_summary": tools_summary,
        "entity_verification_matrix": entity_matrix,
        "triggered_compliance_annexes": applicable_annexes,
        "clarification_log": clarification_history,
        "human_review_mandates": [
            {
                "gate": "Biosafety Officer Sign-Off",
                "condition": "Verify BSL-2 barrier containment and biohazard autoclaving SOPs.",
                "status": "AWAITING_HUMAN_INSPECTION"
            },
            {
                "gate": "BioEthics Committee Determination",
                "condition": "Inspect strain provenance (ATCC repository vs patient consent requirement).",
                "status": "AWAITING_HUMAN_INSPECTION"
            }
        ],
        "agent_certification": {
            "orchestrator_version": "TrustedResearchAgent-v1.0",
            "agent_role": "Advisory Context Extractor & Routing Coordinator",
            "statement": "The automated agent has compiled this dossier strictly from verifiable proposal evidence and researcher responses. The agent holds NO authority to approve, clear, or waive compliance requirements."
        }
    }

    return dossier


def render_dossier_html(dossier: Dict[str, Any]) -> str:
    """Renders a clean, institutional HTML document representation of the dossier."""
    meta = dossier.get("metadata", {})
    matrix = dossier.get("entity_verification_matrix", [])
    annexes = dossier.get("triggered_compliance_annexes", [])
    clarifications = dossier.get("clarification_log", [])

    rows_html = ""
    for row in matrix:
        badge_color = "#10b981" if "CONFIRMED" in row["status_classification"] else ("#f59e0b" if "INFERRED" in row["status_classification"] else "#ef4444")
        rows_html += f"""
        <tr>
          <td style="padding:10px; border-bottom:1px solid #e2e8f0; font-weight:600;">{row['parameter']}</td>
          <td style="padding:10px; border-bottom:1px solid #e2e8f0;">{row['value']}</td>
          <td style="padding:10px; border-bottom:1px solid #e2e8f0;">
            <span style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}55; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:700;">
              {row['status_classification']}
            </span>
          </td>
          <td style="padding:10px; border-bottom:1px solid #e2e8f0; font-size:0.85rem; color:#475569;">
            <em>"{row['verbatim_evidence'][:140]}"</em>
          </td>
        </tr>
        """

    annexes_html = ""
    if annexes:
        for a in annexes:
            annexes_html += f"""
            <div style="background:#f8fafc; border-left:4px solid #4f46e5; padding:12px; margin-bottom:10px; border-radius:0 6px 6px 0;">
              <div style="font-weight:700; color:#1e1b4b; font-size:0.95rem;">{a['annex_name']} ({a['rule_id']})</div>
              <div style="font-size:0.85rem; color:#334155; margin-top:4px;"><strong>Requirement:</strong> {a['title']}</div>
              <div style="font-size:0.85rem; color:#475569; margin-top:2px;"><strong>Action Required:</strong> {a['action_required']}</div>
            </div>
            """
    else:
        annexes_html = "<p style='color:#64748b;'>No institutional annexes triggered by this proposal context.</p>"

    clarif_html = ""
    if clarifications:
        for c in clarifications:
            clarif_html += f"""
            <div style="background:#f1f5f9; padding:8px 12px; margin-bottom:6px; border-radius:6px; font-size:0.85rem;">
              <strong>Q ({c.get('question_id', '')}):</strong> {c.get('prompt', '')}<br>
              <strong>A (Researcher):</strong> <span style="color:#0f766e;">{c.get('researcher_response', '')}</span>
            </div>
            """
    else:
        clarif_html = "<p style='color:#64748b; font-size:0.85rem;'>No clarification rounds required.</p>"

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Ethics Pre-Submission Dossier • {meta.get('project_id', '')}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.5; color: #0f172a; padding: 40px; background: #f8fafc; }}
    .dossier-card {{ max-width: 900px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
    .header {{ border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; margin-bottom: 24px; }}
    h1 {{ font-size: 1.4rem; color: #1e293b; margin: 0 0 6px 0; }}
    .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.88rem; color: #475569; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.88rem; }}
    th {{ background: #f1f5f9; padding: 10px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; }}
    .cert-box {{ background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 16px; margin-top: 28px; font-size: 0.8rem; color: #64748b; }}
  </style>
</head>
<body>
  <div class="dossier-card">
    <div class="header">
      <div style="font-size:0.75rem; font-weight:800; color:#4f46e5; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">
        Institutional Governance & Compliance Dossier
      </div>
      <h1>{dossier.get('dossier_id', '')}</h1>
      <div class="meta-grid">
        <div><strong>Project Title:</strong> {meta.get('proposal_title', '')}</div>
        <div><strong>Researcher / Student:</strong> {meta.get('researcher_name', '')} ({meta.get('project_id', '')})</div>
        <div><strong>Institution / Course:</strong> {meta.get('institution', '')} • {meta.get('course_context', '')}</div>
        <div><strong>Compiled At:</strong> {dossier.get('generated_at', '')}</div>
      </div>
    </div>

    <h2 style="font-size:1.05rem; color:#1e293b; margin-top:24px;">1. Extracted Entity & Regulatory Matrix</h2>
    <table>
      <thead>
        <tr>
          <th>Research Parameter</th>
          <th>Extracted Value</th>
          <th>Classification Status</th>
          <th>Verbatim Evidence Trace</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>

    <h2 style="font-size:1.05rem; color:#1e293b; margin-top:28px;">2. Triggered Institutional Compliance Annexes</h2>
    {annexes_html}

    <h2 style="font-size:1.05rem; color:#1e293b; margin-top:28px;">3. Researcher Socratic Clarifications</h2>
    {clarif_html}

    <div class="cert-box">
      <strong>Agent Trust & Non-Delegable Authority Certification:</strong><br>
      {dossier.get('agent_certification', {}).get('statement', '')}
    </div>
  </div>
</body>
</html>"""
    return html
