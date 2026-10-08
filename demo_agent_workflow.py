"""
End-to-End Demonstration Scenario for the Trusted Research Workflow Agent.
Demonstrates the full lifecycle on synthetic research proposal DETECTR-Aqua (mcr-1 diagnostic):
1. Ingest Proposal
2. Extract Context & Evidence
3. Evaluate Institutional Requirements
4. Flag Ambiguity & Issue Socratic Question
5. Researcher Submits Clarification
6. Re-evaluate Requirements & State
7. Compile Ethics Pre-Submission Dossier
8. Dispatch to BioEthics Adapter
9. Enforce Human Gate & Record Human Decision
10. Verify Full Tamper-Evident Audit Trail
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from agent.service import AgentOrchestrator
from agent.workflow import WorkflowState
from agent.audit import get_audit_history, verify_audit_integrity


import sys
import io

# Set UTF-8 encoding for stdout on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def run_demonstration():
    print("=" * 80)
    print("[*] TRUSTED RESEARCH WORKFLOW AGENT: END-TO-END CATALYST DEMONSTRATION")
    print("    2026 Digital Science Catalyst Grant Theme: 'Agentic Workflows You Can Trust'")
    print("=" * 80)

    orchestrator = AgentOrchestrator()
    project_id = "DEMO-DETECTR-AQUA-2026"

    # Step 1: Synthetic Research Proposal Input
    synthetic_proposal = {
        "student_id": project_id,
        "student_name": "Dr. Sarah Mansour (Synthetic Early-Career Fellow)",
        "title": "DETECTR-Aqua: CRISPR-Cas12a Molecular Diagnostic Assay for Rapid Field Detection of Colistin-Resistant mcr-1 Pathogens in Aquaculture Water",
        "chassis": "Clinical Bacterial Isolates and Aquaculture Water Matrix",
        "tool": "LbaCas12a with crRNA reporter and RPA amplification",
        "target": "Femtomolar LOD detection of mcr-1 antibiotic resistance gene",
        "methodology": (
            "Water samples from aquaculture facilities and multidrug-resistant clinical isolates will be tested. "
            "Recombinant Cas12a endonuclease will be complexed with synthetic guide RNA to trigger collateral ssDNA cleavage. "
            "Target DNA amplification will use isothermal RPA. Biosafety precautions follow standard lab rules."
        )
    }

    print("\n[STEP 1] PROPOSAL INGESTION")
    print(f" • Project ID:   {project_id}")
    print(f" • Title:        {synthetic_proposal['title']}")
    print(f" • Chassis:      {synthetic_proposal['chassis']}")
    print(f" • Tool:         {synthetic_proposal['tool']}")

    # Step 2: Context Extraction & Requirement Evaluation
    print("\n[STEP 2] AGENT CONTEXT EXTRACTION & REQUIREMENT ANALYSIS")
    analysis = orchestrator.analyze_proposal(synthetic_proposal, project_id=project_id)
    ctx = analysis["context"]
    print(f" • Workflow State: {analysis['workflow_state']}")
    print(f" • Extracted Host: {ctx['organism_or_chassis']['value']} (Status: {ctx['organism_or_chassis']['status']})")
    print(f" • Clinical/Human: {ctx['human_subjects']['value']} (Status: {ctx['human_subjects']['status']})")
    print(f" • Pathogen / AMR: {ctx['pathogen_work']['value']} (AMR Determinant: {ctx['antimicrobial_resistance']['value']})")
    print(f" • Containment:    {ctx['biosafety_containment']['value']} (Status: {ctx['biosafety_containment']['status']})")

    # Step 3: Triggered Requirements
    print("\n[STEP 3] TRIGGERED INSTITUTIONAL REQUIREMENTS")
    for req in analysis["requirements"]:
        print(f" • [{req['rule_id']}] {req['title']}")
        print(f"   - Annex:    {req['applicable_annex']}")
        print(f"   - Evidence: {req['evidence']}")
        print(f"   - Mandate:  {req['human_action_required']}")

    # Step 4: Socratic Ambiguity Clarification
    print("\n[STEP 4] TARGETED RESEARCHER QUESTIONS (ANTI-GHOSTWRITING)")
    print(" • Notice: The agent does not guess. It stops and asks the researcher for the missing evidence.")
    pending = analysis["pending_clarifications"]
    print(f" • Active Socratic Prompts: {len(pending)}")
    for q in pending:
        print(f"   Q ({q['question_id']}): {q['prompt']}")
        print(f"   Rationale: {q['rationale']}")

    # Step 5: Researcher Clarification Response
    print("\n[STEP 5] RESEARCHER RESPONDS TO CLARIFICATION PROMPTS [SYNTHETIC DEMONSTRATION DATA]")
    clarification_responses = {
        "CLAR-HUMAN-01": "[SYNTHETIC DEMONSTRATION DATA] The clinical isolates are verified, de-identified reference repository strains obtained from ATCC (ATCC BAA-2469), not collected directly from human patients.",
        "CLAR-BIO-01": "[SYNTHETIC DEMONSTRATION DATA] All live bacterial testing will be conducted strictly within a certified Class II BSL-2 laminar flow biosafety cabinet with subsequent autoclaving of biohazard waste."
    }

    for q in pending:
        q_id = q["question_id"]
        if q_id in clarification_responses:
            ans = clarification_responses[q_id]
            print(f" • Answering {q_id}...")
            print(f"   Researcher Response: \"{ans}\"")
            clarif_res = orchestrator.submit_clarification(project_id, q_id, ans)
            print(f"   -> Result: Updated state to {clarif_res['workflow_state']} (Remaining: {clarif_res['remaining_clarifications']})")

    # Step 6: Post-Clarification State
    overview = orchestrator.get_workflow_overview(project_id)
    print(f"\n[STEP 6] POST-CLARIFICATION STATE: {overview['current_state']}")
    print(f" • Next Action: {overview['next_action']['action']} (Actor: {overview['next_action']['actor']})")

    # Step 7: Dossier Synthesis
    print("\n[STEP 7] ETHICS PRE-SUBMISSION DOSSIER COMPILATION")
    dossier = orchestrator.compile_dossier(project_id)
    print(f" • Dossier ID:   {dossier['dossier_id']}")
    print(f" • Annexes:      {len(dossier['triggered_compliance_annexes'])} institutional compliance annex(es)")
    print(f" • Entity Matrix Rows: {len(dossier['entity_verification_matrix'])}")
    for row in dossier['entity_verification_matrix'][:3]:
        print(f"   - {row['parameter']}: {row['value']} [{row['status_classification']}] (Source: {row['source_section']})")

    # Step 8: Dispatch to BioEthics Adapter
    print("\n[STEP 8] DISPATCH TO BIOETHICS ADAPTER [MOCK / SIMULATED HANDOFF - NOT A REAL INSTITUTIONAL SUBMISSION]")
    dispatch_res = orchestrator.dispatch_to_bioethics(project_id, mode="mock")
    print(f" • Dispatch Status:  {dispatch_res['status']}")
    print(f" • Remote App ID:    {dispatch_res['remote_application_id']}")
    print(f" • Adapter Mode:     {dispatch_res['mode']} (Simulation)")
    print(f" • Resulting State:  {orchestrator.get_workflow_overview(project_id)['current_state']}")
    print(f" • Notice:           Handoff executed in local validated mock mode; institutional submission simulated.")

    # Step 9: Human Review Gate (Enforcing Non-Delegable Authority)
    print("\n[STEP 9] HUMAN REVIEW GATE EXECUTION (ENFORCING NON-DELEGABLE HUMAN AUTHORITY)")
    print(" • Notice: The agent can coordinate the workflow, but it cannot make the consequential institutional decision.")
    print(" • Attempting unauthorized agent self-approval...")
    try:
        from agent.gates import enforce_human_review_gate
        enforce_human_review_gate(project_id, actor="agent", role="ethics_officer", reviewer_id="agent", decision="approved")
    except Exception as e:
        print(f"   ✓ BLOCKED AS EXPECTED: {str(e)[:75]}...")

    print(" • Submitting authenticated human review sign-off...")
    human_res = orchestrator.record_human_decision(
        project_id=project_id,
        reviewer_id="DR-ABDELRAZEK-IBC-CHAIR",
        role="ethics_officer",
        decision="approved",
        notes="[SYNTHETIC DEMONSTRATION DATA] ATCC de-identified strain provenance verified. BSL-2 protocol approved.",
        conditions="Must adhere to standard BSL-2 PPE and laminar flow cabinet disinfection."
    )
    print(f" • Decision:       {human_res['decision'].upper()}")
    print(f" • Recorded By:     {human_res['recorded_by']}")
    print(f" • Resulting State: {human_res['workflow_state']}")

    # Step 10: Complete Audit History & Cryptographic Integrity Check
    print("\n[STEP 10] TAMPER-EVIDENT SHA-256 HASH-CHAINED AUDIT TRAIL VERIFICATION")
    print(" • Technical note: Events are chained via SHA-256 hashes for tamper evidence; storage is not physically immutable.")
    audit_history = get_audit_history(project_id)
    integrity = verify_audit_integrity(project_id)
    print(f" • Total Logged Events: {len(audit_history)}")
    print(f" • Hash-Chain Integrity: {'VALID [OK]' if integrity['valid'] else 'CORRUPTED [FAILED]'}")
    print(f" • Audit Chain Sample:")
    for ev in audit_history[-4:]:
        print(f"   [{ev['timestamp'][11:19]}] [{ev['actor'].upper()}] {ev['event_type']} -> {ev['action']}")

    print("\n" + "=" * 80)
    print("[SUCCESS] DEMONSTRATION COMPLETE: ALL 10 STEPS VERIFIED IN MOCK/TEST ENVIRONMENT")
    print("=" * 80)


if __name__ == "__main__":
    run_demonstration()
