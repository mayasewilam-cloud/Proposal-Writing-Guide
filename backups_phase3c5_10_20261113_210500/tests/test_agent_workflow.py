"""
Automated Test Suite for the Trusted Research Workflow Agent (Catalyst 2026).
Tests context extraction, requirement evaluation, state transitions,
clarification loops, human review gates, audit ledgers, and synthetic proposals A-G.
"""

import unittest
from unittest.mock import patch
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from agent.models import WorkflowState, FieldStatus
from agent.context_extractor import extract_research_context
from agent.llm_extractor import HybridLLMExtractor, get_llm_extractor
from agent.requirement_engine import evaluate_institutional_requirements
from agent.workflow import (
    load_workflow_state,
    save_workflow_state,
    transition_state,
    can_transition,
    WorkflowError
)
from agent.clarification import generate_clarification_questions, apply_researcher_clarification
from agent.dossier import compile_ethics_pre_submission_dossier
from agent.gates import enforce_human_review_gate, UnauthorizedActionError
from agent.audit import record_audit_event, get_audit_history, verify_audit_integrity
from agent.adapter import BioEthicsAdapter
from agent.service import AgentOrchestrator


class TestAgentSyntheticProposals(unittest.TestCase):
    """Tests 7 synthetic proposal models covering all regulatory archetypes."""

    def setUp(self):
        self.orchestrator = AgentOrchestrator()

        # Synthetic Proposal A: No obvious ethics trigger
        self.prop_a = {
            "student_id": "SYNTH-A",
            "student_name": "Synthetic Researcher A",
            "title": "Enzymatic PETase Depolymerization in Cell-Free Buffer to Achieve 95% Conversion",
            "chassis": "Cell-Free Buffer Reaction Matrix",
            "tool": "Engineered PETase",
            "target": "Polyethylene Terephthalate degradation",
            "methodology": "Lyophilized enzyme will be incubated with microplastic powder in 50 mM Tris-HCl at 40°C. Standard negative control uses heat-inactivated enzyme."
        }

        # Synthetic Proposal B: Human-derived samples
        self.prop_b = {
            "student_id": "SYNTH-B",
            "student_name": "Synthetic Researcher B",
            "title": "Lateral Flow Aptamer Assay for Detection of MicroRNA in Patient Blood",
            "chassis": "Paper Lateral Flow Matrix",
            "tool": "DNA Aptamer Probe",
            "target": "10 pM LOD in human serum",
            "methodology": "Patient blood and serum samples will be collected from hospital clinical volunteers following informed consent protocols."
        }

        # Synthetic Proposal C: Animal research
        self.prop_c = {
            "student_id": "SYNTH-C",
            "student_name": "Synthetic Researcher C",
            "title": "In Vivo Pharmacokinetics of Antimicrobial Peptide in Murine Infection Models",
            "chassis": "Mus musculus (Mice)",
            "tool": "Synthetic Antimicrobial Peptide",
            "target": "Bacterial clearance in vivo",
            "methodology": "Female BALB/c mice models will be inoculated intraperitoneally and monitored for 48 hours in vivo under standard animal care guidelines."
        }

        # Synthetic Proposal D: Genetic modification
        self.prop_d = {
            "student_id": "SYNTH-D",
            "student_name": "Synthetic Researcher D",
            "title": "Recombinant Secretory Expression of Cellulase in Pichia pastoris Expression Vector",
            "chassis": "Pichia pastoris",
            "tool": "Recombinant pPICZalpha Plasmid Vector",
            "target": "2.5 g/L secretory yield",
            "methodology": "Engineered plasmid vectors will be transformed into competent yeast host strains using electroporation."
        }

        # Synthetic Proposal E: Multiple triggers (Clinical + GMO + AMR Pathogen)
        self.prop_e = {
            "student_id": "SYNTH-E",
            "student_name": "Synthetic Researcher E",
            "title": "CRISPR-Cas12a Molecular Detection of Colistin-Resistant mcr-1 Pathogens in Clinical Isolates",
            "chassis": "Clinical E. coli Isolates",
            "tool": "CRISPR-Cas12a and gRNA Construct",
            "target": "Femtomolar detection of mcr-1 gene",
            "methodology": "Multidrug-resistant pathogenic clinical isolates will be tested using recombinant Cas12a. Containment will utilize certified BSL-2 biosafety cabinets."
        }

        # Synthetic Proposal F: Ambiguous proposal
        self.prop_f = {
            "student_id": "SYNTH-F",
            "student_name": "Synthetic Researcher F",
            "title": "Rapid Testing of Bacterial Strains",
            "chassis": "",
            "tool": "Fluorescent Probe",
            "target": "Detection",
            "methodology": "Clinical isolates will be tested for growth inhibition in liquid broth."
        }

        # Synthetic Proposal G: Missing information
        self.prop_g = {
            "student_id": "SYNTH-G",
            "student_name": "Synthetic Researcher G",
            "title": "Biotechnology Study",
            "chassis": "",
            "tool": "",
            "target": "",
            "methodology": ""
        }

    def test_proposal_a_no_ethics_trigger(self):
        """Proposal A should trigger zero human/animal ethics annexes."""
        ctx = extract_research_context(self.prop_a, "SYNTH-A")
        self.assertEqual(ctx.human_subjects.value, False)
        self.assertEqual(ctx.animal_subjects.value, False)
        reqs = evaluate_institutional_requirements(ctx)
        ethics_annexes = [r for r in reqs if r.category == "ethics"]
        self.assertEqual(len(ethics_annexes), 0)

    def test_proposal_b_human_samples_trigger(self):
        """Proposal B must trigger Human Ethics Annex A."""
        ctx = extract_research_context(self.prop_b, "SYNTH-B")
        self.assertEqual(ctx.human_subjects.value, True)
        self.assertIn("patient", ctx.human_subjects.evidence.lower())
        reqs = evaluate_institutional_requirements(ctx)
        annex_a = [r for r in reqs if "Annex A" in str(r.applicable_annex)]
        self.assertEqual(len(annex_a), 1)

    def test_proposal_c_animal_research_trigger(self):
        """Proposal C must trigger Animal Welfare Annex B."""
        ctx = extract_research_context(self.prop_c, "SYNTH-C")
        self.assertEqual(ctx.animal_subjects.value, True)
        reqs = evaluate_institutional_requirements(ctx)
        annex_b = [r for r in reqs if "Annex B" in str(r.applicable_annex)]
        self.assertEqual(len(annex_b), 1)

    def test_proposal_d_genetic_modification_trigger(self):
        """Proposal D must trigger Recombinant DNA & Biosafety Annex C."""
        ctx = extract_research_context(self.prop_d, "SYNTH-D")
        self.assertEqual(ctx.genetic_modification.value, True)
        self.assertEqual(ctx.recombinant_dna.value, True)
        reqs = evaluate_institutional_requirements(ctx)
        annex_c = [r for r in reqs if "Annex C" in str(r.applicable_annex)]
        self.assertGreaterEqual(len(annex_c), 1)

    def test_proposal_e_multiple_triggers(self):
        """Proposal E must trigger Human Ethics, Recombinant Biosafety, and AMR Oversight."""
        ctx = extract_research_context(self.prop_e, "SYNTH-E")
        self.assertTrue(ctx.human_subjects.value)
        self.assertTrue(ctx.pathogen_work.value)
        self.assertTrue(ctx.antimicrobial_resistance.value)
        self.assertEqual(ctx.biosafety_containment.value, "BSL-2")
        reqs = evaluate_institutional_requirements(ctx)
        self.assertGreaterEqual(len(reqs), 3)

    def test_proposal_f_ambiguity_detection(self):
        """Proposal F contains clinical isolates without origin -> generates uncertainties and questions."""
        ctx = extract_research_context(self.prop_f, "SYNTH-F")
        self.assertGreater(len(ctx.uncertainties), 0)
        qs = generate_clarification_questions(ctx)
        self.assertGreater(len(qs), 0)
        self.assertTrue(any(q.question_id == "CLAR-HUMAN-01" for q in qs))

    def test_proposal_g_missing_information(self):
        """Proposal G with missing fields flags missing chassis and empty parameters."""
        ctx = extract_research_context(self.prop_g, "SYNTH-G")
        self.assertEqual(ctx.organism_or_chassis.status, FieldStatus.MISSING)
        qs = generate_clarification_questions(ctx)
        self.assertTrue(any(q.question_id == "CLAR-CHASSIS-01" for q in qs))


class TestAgentWorkflowAndGovernance(unittest.TestCase):
    """Tests the state machine, human approval gate, and audit integrity."""

    def setUp(self):
        self.orchestrator = AgentOrchestrator()
        self.project_id = "TEST-PROJECT-GOV"
        # Reset state
        save_workflow_state(self.project_id, {
            "project_id": self.project_id,
            "current_state": WorkflowState.DRAFT,
            "previous_state": None,
            "pending_clarifications": [],
            "answered_clarifications": [],
            "requirements_summary": []
        })

    def test_state_machine_valid_transitions(self):
        """Verify legal state transitions advance predictably."""
        self.assertTrue(can_transition(WorkflowState.DRAFT, WorkflowState.CONTEXT_ANALYSIS))
        self.assertTrue(can_transition(WorkflowState.CONTEXT_ANALYSIS, WorkflowState.REQUIREMENT_CHECK))
        self.assertTrue(can_transition(WorkflowState.REQUIREMENT_CHECK, WorkflowState.READY_FOR_ETHICS_HANDOFF))
        self.assertTrue(can_transition(WorkflowState.READY_FOR_ETHICS_HANDOFF, WorkflowState.ETHICS_REVIEW_PENDING))
        self.assertTrue(can_transition(WorkflowState.ETHICS_REVIEW_PENDING, WorkflowState.HUMAN_REVIEW))
        self.assertTrue(can_transition(WorkflowState.HUMAN_REVIEW, WorkflowState.CLEARED_FOR_NEXT_STAGE))

    def test_illegal_state_jump_rejected(self):
        """Verify illegal jumps (e.g. DRAFT -> CLEARED_FOR_NEXT_STAGE) raise WorkflowError."""
        self.assertFalse(can_transition(WorkflowState.DRAFT, WorkflowState.CLEARED_FOR_NEXT_STAGE))
        with self.assertRaises(WorkflowError):
            transition_state(self.project_id, WorkflowState.CLEARED_FOR_NEXT_STAGE, actor="agent")

    def test_agent_forbidden_from_approving_consequential_gates(self):
        """Verify that actor='agent' is strictly blocked from approving CLEARED_FOR_NEXT_STAGE."""
        # Set state to HUMAN_REVIEW
        save_workflow_state(self.project_id, {
            "project_id": self.project_id,
            "current_state": WorkflowState.HUMAN_REVIEW
        })
        with self.assertRaises(WorkflowError):
            transition_state(self.project_id, WorkflowState.CLEARED_FOR_NEXT_STAGE, actor="agent")

        # Also verify through gate enforcement function
        with self.assertRaises(UnauthorizedActionError):
            enforce_human_review_gate(
                project_id=self.project_id,
                actor="agent",
                role="ethics_officer",
                reviewer_id="agent_bot",
                decision="approved"
            )

    def test_human_officer_approval_gate_succeeds(self):
        """Authenticated human officer can legally sign off on CLEARED_FOR_NEXT_STAGE."""
        gate_res = enforce_human_review_gate(
            project_id=self.project_id,
            actor="human",
            role="ethics_officer",
            reviewer_id="dr_ethics_chair",
            decision="approved",
            conditions="Subject to BSL-2 autoclaving SOP"
        )
        self.assertTrue(gate_res["success"])
        self.assertEqual(gate_res["target_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)
        self.assertTrue(gate_res["decision_record"]["is_human_signed"])

    def test_audit_log_append_and_integrity(self):
        """Audit log appends records and maintains valid SHA-256 cryptographic chain."""
        pid = "TEST-AUDIT-CHAIN"
        # Record 3 events
        ev1 = record_audit_event(pid, "STATE_TRANSITION", "agent", "orchestrator", "Start", WorkflowState.DRAFT)
        ev2 = record_audit_event(pid, "CONTEXT_EXTRACTED", "agent", "orchestrator", "Extracted", WorkflowState.CONTEXT_ANALYSIS)
        ev3 = record_audit_event(pid, "HUMAN_DECISION_RECORDED", "human", "dr_officer", "Approved", WorkflowState.CLEARED_FOR_NEXT_STAGE)

        history = get_audit_history(pid)
        self.assertGreaterEqual(len(history), 3)

        # Verify hash chain
        integ = verify_audit_integrity(pid)
        self.assertTrue(integ["valid"])
        self.assertEqual(integ["event_count"], len(history))

    def test_bioethics_adapter_validation(self):
        """Adapter validates required fields and dispatches mock payload without external network."""
        adapter = BioEthicsAdapter()
        # Invalid dossier rejected
        invalid_res = adapter.validate_dossier_payload({})
        self.assertFalse(invalid_res["valid"])

        # Valid minimal dossier
        valid_dossier = {
            "dossier_id": "DOSSIER-TEST",
            "metadata": {"project_id": "TEST-1", "proposal_title": "Test Title"},
            "entity_verification_matrix": [{"param": "Chassis"}]
        }
        val_ok = adapter.validate_dossier_payload(valid_dossier)
        self.assertTrue(val_ok["valid"])

        # Mock dispatch
        dispatch_res = adapter.dispatch_dossier(valid_dossier, mode="mock")
        self.assertTrue(dispatch_res["success"])
        self.assertEqual(dispatch_res["mode"], "mock_simulation")
        self.assertIn("ETH-MSA-", dispatch_res["remote_application_id"])

    def test_conflicting_information_detection(self):
        """Cross-field conflict: Acellular chassis vs clinical specimen methodology."""
        conflicting_prop = {
            "student_id": "TEST-CONFLICT-01",
            "title": "Acellular Enzyme Test with Patient Isolates",
            "chassis": "Cell-Free Buffer Reaction Matrix",
            "tool": "Enzyme Hydrolase",
            "methodology": "Clinical isolates collected from hospital intensive care patients will be incubated in the reaction."
        }
        ctx = extract_research_context(conflicting_prop, "TEST-CONFLICT-01")
        # Conflict should be detected on chassis and human subjects
        self.assertEqual(ctx.organism_or_chassis.status, FieldStatus.REQUIRES_HUMAN_REVIEW)
        self.assertIn("proposal.chassis", ctx.organism_or_chassis.evidence)
        self.assertIn("proposal.methodology", ctx.organism_or_chassis.evidence)
        self.assertTrue(any("Contradiction" in u.get("issue", "") for u in ctx.uncertainties))

        # Check REQ-GOV-01 is triggered
        reqs = evaluate_institutional_requirements(ctx)
        gov_reqs = [r for r in reqs if r.rule_id == "REQ-GOV-01"]
        self.assertEqual(len(gov_reqs), 1)

    def test_multistep_clarification_loop(self):
        """End-to-end multi-step Socratic clarification resolves ambiguities and advances state."""
        prop = {
            "student_id": "TEST-LOOP-01",
            "title": "Field Assay for Colistin Resistance",
            "chassis": "Bacterial Isolates",
            "tool": "CRISPR-Cas12a with crRNA",
            "methodology": "Clinical isolates will be tested for mcr-1 resistance. Standard BSL precautions apply.",
            "reset_clarifications": True
        }
        # Step 1: Initial analysis -> NEEDS_CLARIFICATION
        analysis = self.orchestrator.analyze_proposal(prop, project_id="TEST-LOOP-01")
        self.assertEqual(analysis["workflow_state"], WorkflowState.NEEDS_CLARIFICATION)
        pending = analysis["pending_clarifications"]
        self.assertGreaterEqual(len(pending), 1)

        # Step 2: Cannot jump directly to CLEARED_FOR_NEXT_STAGE
        with self.assertRaises(WorkflowError):
            transition_state("TEST-LOOP-01", WorkflowState.CLEARED_FOR_NEXT_STAGE, actor="agent")

        # Step 3: Answer first question
        q1_id = pending[0]["question_id"]
        res1 = self.orchestrator.submit_clarification(
            "TEST-LOOP-01",
            q1_id,
            "Reference strains obtained from ATCC repository (ATCC 25922), not human patients."
        )
        self.assertTrue(res1["success"])

        # If there is a second question (e.g. biosafety containment), answer it
        state = load_workflow_state("TEST-LOOP-01")
        rem_pending = state.get("pending_clarifications", [])
        if rem_pending:
            q2_id = rem_pending[0]["question_id"]
            res2 = self.orchestrator.submit_clarification(
                "TEST-LOOP-01",
                q2_id,
                "Testing conducted inside certified Class II BSL-2 biosafety cabinet."
            )
            self.assertTrue(res2["success"])
            self.assertEqual(res2["workflow_state"], WorkflowState.READY_FOR_ETHICS_HANDOFF)
        else:
            self.assertEqual(res1["workflow_state"], WorkflowState.READY_FOR_ETHICS_HANDOFF)

    def test_ambiguity_failure_mode_blocks_clearance(self):
        """Vague or missing proposal must be blocked from autonomous clearance."""
        empty_prop = {
            "student_id": "TEST-EMPTY-01",
            "title": "Vague Biotechnology Experiment",
            "chassis": "",
            "tool": "",
            "methodology": "",
            "reset_clarifications": True
        }
        analysis = self.orchestrator.analyze_proposal(empty_prop, project_id="TEST-EMPTY-01")
        self.assertEqual(analysis["workflow_state"], WorkflowState.NEEDS_CLARIFICATION)
        
        # Verify transition to clearance is prohibited
        self.assertFalse(can_transition(WorkflowState.NEEDS_CLARIFICATION, WorkflowState.CLEARED_FOR_NEXT_STAGE))
        with self.assertRaises(WorkflowError):
            transition_state("TEST-EMPTY-01", WorkflowState.CLEARED_FOR_NEXT_STAGE, actor="agent")

    def test_audit_hash_chain_tamper_detection(self):
        """Modifying any line in the append-only ledger is detected by SHA-256 integrity verification."""
        pid = "TEST-TAMPER-EVIDENCE"
        log_file = os.path.join(BASE_DIR, "data", "agent_audit", f"{pid}.jsonl")
        if os.path.exists(log_file):
            os.remove(log_file)

        # Record 4 legitimate chained events
        record_audit_event(pid, "STATE_TRANSITION", "agent", "orchestrator", "Action 1", WorkflowState.DRAFT)
        record_audit_event(pid, "CONTEXT_EXTRACTED", "agent", "orchestrator", "Action 2", WorkflowState.CONTEXT_ANALYSIS)
        record_audit_event(pid, "REQUIREMENT_FLAGGED", "agent", "orchestrator", "Action 3", WorkflowState.REQUIREMENT_CHECK)
        record_audit_event(pid, "HUMAN_DECISION_RECORDED", "human", "reviewer_01", "Action 4", WorkflowState.CLEARED_FOR_NEXT_STAGE)

        # Integrity should initially pass
        integ_before = verify_audit_integrity(pid)
        self.assertTrue(integ_before["valid"])
        self.assertEqual(integ_before["event_count"], 4)

        # Tamper with line 2 (index 1) by modifying its payload
        with open(log_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        tampered_event = json.loads(lines[1])
        tampered_event["action"] = "ILLEGALLY_ALTERED_ACTION_FOR_TAMPER_TEST"
        lines[1] = json.dumps(tampered_event)

        with open(log_file, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l + "\n")

        # Integrity verification must detect the hash-chain breach at index 2
        integ_after = verify_audit_integrity(pid)
        self.assertFalse(integ_after["valid"])
        self.assertEqual(integ_after.get("corrupted_index"), 2)
        self.assertIn("Tampering detected", integ_after["message"])

    def test_bioethics_mock_vs_live_states(self):
        """Mock handoff transitions to MOCK_HANDOFF_COMPLETED rather than implying live queue."""
        pid = "TEST-ADAPTER-MODES"
        prop = {
            "student_id": pid,
            "title": "Minimal Assay for Mode Test",
            "chassis": "Escherichia coli",
            "tool": "Cas12a",
            "methodology": "Standard laboratory testing without patient materials.",
            "reset_clarifications": True
        }
        self.orchestrator.analyze_proposal(prop, project_id=pid)
        save_workflow_state(pid, {
            "project_id": pid,
            "current_state": WorkflowState.READY_FOR_ETHICS_HANDOFF,
            "requirements_summary": []
        })

        # Mock dispatch
        res = self.orchestrator.dispatch_to_bioethics(pid, mode="mock")
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "mock_simulation")
        state = load_workflow_state(pid)
        self.assertEqual(state["current_state"], WorkflowState.MOCK_HANDOFF_COMPLETED)


class TestAgentHttpApi(unittest.TestCase):
    """Integration tests verifying HTTP REST endpoints and security gates via Flask test client."""

    def setUp(self):
        from app import app
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.project_id = "TEST-HTTP-API-PROJECT"

    def test_unauthorized_agent_approval_via_api_blocked(self):
        """POST /agent/api/human_decision with actor='agent' must return HTTP 403 and leave state unchanged."""
        # Ensure project exists in HUMAN_REVIEW
        save_workflow_state(self.project_id, {
            "project_id": self.project_id,
            "current_state": WorkflowState.HUMAN_REVIEW,
            "human_decision": None
        })

        resp = self.client.post(
            f"/agent/api/human_decision/{self.project_id}",
            json={
                "actor": "agent",
                "role": "ethics_officer",
                "reviewer_id": "automated_agent_bot",
                "decision": "approved"
            }
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Security Violation", data["error"])

        # State must remain HUMAN_REVIEW, not CLEARED_FOR_NEXT_STAGE
        state = load_workflow_state(self.project_id)
        self.assertEqual(state["current_state"], WorkflowState.HUMAN_REVIEW)

        # Audit log must record the unauthorized attempt
        audit_history = get_audit_history(self.project_id)
        unauth_events = [e for e in audit_history if e.get("event_type") == "UNAUTHORIZED_ACTION_ATTEMPTED"]
        self.assertGreaterEqual(len(unauth_events), 1)

    def test_authorized_human_approval_via_api_succeeds(self):
        """POST /agent/api/human_decision with actor='human' and authorized role/passcode returns HTTP 200."""
        save_workflow_state(self.project_id, {
            "project_id": self.project_id,
            "current_state": WorkflowState.HUMAN_REVIEW,
            "human_decision": None
        })

        resp = self.client.post(
            f"/agent/api/human_decision/{self.project_id}",
            json={
                "actor": "human",
                "role": "ethics_officer",
                "reviewer_id": "dr_human_reviewer",
                "decision": "approved",
                "conditions": "BSL-2 certified cabinet usage only",
                "reviewer_passcode": "faculty2026"
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["workflow_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)

        # Persisted state must reflect clearance
        state = load_workflow_state(self.project_id)
        self.assertEqual(state["current_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)
        self.assertTrue(state.get("is_locked", False))

    def test_full_rest_api_lifecycle(self):
        """End-to-end REST API pipeline: analyze -> clarify -> dossier -> dispatch -> human decision -> audit."""
        pid = "TEST-REST-E2E"
        proposal = {
            "student_id": pid,
            "title": "Aptamer MicroRNA Detection",
            "chassis": "Paper Lateral Flow Matrix",
            "tool": "DNA Aptamer Probe",
            "methodology": "Patient blood and serum samples will be collected following informed consent protocols.",
            "reset_clarifications": True
        }

        # 1. Analyze
        r1 = self.client.post(f"/agent/api/analyze/{pid}", json={"proposal_data": proposal})
        self.assertEqual(r1.status_code, 200)
        self.assertIn("workflow_state", r1.get_json())

        # 1b. Clarify any pending ambiguities via API
        for q in r1.get_json().get("pending_clarifications", []):
            rc = self.client.post(
                f"/agent/api/clarify/{pid}",
                json={
                    "question_id": q["question_id"],
                    "answer": "Verified clinical volunteer cohort following institutional informed consent protocols."
                }
            )
            self.assertEqual(rc.status_code, 200)

        # 2. Get status
        r2 = self.client.get(f"/agent/api/status/{pid}")
        self.assertEqual(r2.status_code, 200)

        # 3. Dossier HTML & JSON
        r3 = self.client.get(f"/agent/api/dossier/{pid}")
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(r3.get_json()["success"])

        r3_html = self.client.get(f"/agent/dossier/{pid}/view")
        self.assertEqual(r3_html.status_code, 200)
        self.assertIn("Institutional Governance & Compliance Dossier", r3_html.get_data(as_text=True))

        # 4. Dispatch (mock simulation)
        r4 = self.client.post(f"/agent/api/dispatch/{pid}", json={"mode": "mock"})
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.get_json()["mode"], "mock_simulation")

        # 5. Human Decision
        r5 = self.client.post(
            f"/agent/api/human_decision/{pid}",
            json={
                "actor": "human",
                "role": "ethics_officer",
                "reviewer_id": "dr_faculty_chair",
                "decision": "approved",
                "reviewer_passcode": "faculty2026"
            }
        )
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(r5.get_json()["workflow_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)

        # 6. Audit & Hash integrity
        r6 = self.client.get(f"/agent/api/audit/{pid}")
        self.assertEqual(r6.status_code, 200)
        audit_data = r6.get_json()
        self.assertTrue(audit_data["integrity"]["valid"])
        self.assertGreaterEqual(audit_data["event_count"], 4)


class TestHybridLLMExtractor(unittest.TestCase):
    """Tests neurosymbolic LLM extraction, grounding verification, and deterministic fallback."""

    def test_default_offline_fallback(self):
        """When no API key is provided, extractor must report unavailable and return None."""
        with patch.dict(os.environ, {}, clear=True):
            extractor = HybridLLMExtractor()
            self.assertFalse(extractor.is_available())
            info = extractor.get_provider_info()
            self.assertEqual(info["mode"], "deterministic_fallback")
            self.assertIsNone(extractor.extract({"title": "Test Title"}))

    def test_grounding_verification_guardrail(self):
        """Grounding guardrail must detect verbatim snippets vs hallucinated quotes."""
        extractor = HybridLLMExtractor()
        proposal_text = "Patient blood and serum samples will be collected from hospital clinical volunteers following informed consent."

        # Verbatim quote should pass
        self.assertTrue(extractor._verify_evidence_grounding("Patient blood and serum", proposal_text))
        self.assertTrue(extractor._verify_evidence_grounding("hospital clinical volunteers", proposal_text))

        # Hallucinated quote should fail
        self.assertFalse(extractor._verify_evidence_grounding("Mice were sacrificed using carbon dioxide", proposal_text))
        self.assertFalse(extractor._verify_evidence_grounding("CRISPR-Cas9 knockout in HeLa cell lines", proposal_text))

    def test_mock_llm_extraction_parsing(self):
        """Valid structured LLM JSON response must parse cleanly into ResearchContext."""
        extractor = HybridLLMExtractor()
        extractor.gemini_key = "test_mock_key"

        mock_response_json = json.dumps({
            "organism_or_chassis": {"value": "Escherichia coli", "evidence": "E. coli BL21(DE3)", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Explicitly stated in proposal"},
            "molecular_tools": [{"value": "CRISPR-Cas12a", "evidence": "Cas12a endonuclease", "status": "CONFIRMED", "confidence": 0.92, "rationale": "Targeted diagnostic tool"}],
            "sample_type": {"value": "Aquaculture Effluent", "evidence": "shrimp farm water samples", "status": "CONFIRMED", "confidence": 0.90, "rationale": "Sample matrix"},
            "human_subjects": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "No human subjects"},
            "animal_subjects": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.99, "rationale": "No vertebrate animal subjects"},
            "genetic_modification": {"value": True, "evidence": "plasmid transformation", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Recombinant plasmid"},
            "recombinant_dna": {"value": True, "evidence": "recombinant Cas12a expression", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Recombinant protein"},
            "pathogen_work": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.95, "rationale": "BSL-1 organism"},
            "antimicrobial_resistance": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.95, "rationale": "No AMR study"},
            "biosafety_containment": {"value": "BSL-1", "evidence": "E. coli BL21", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Standard BSL-1"},
            "uncertainties": []
        })

        proposal_data = {
            "student_id": "TEST-HYBRID-01",
            "student_name": "Test Student",
            "title": "Cas12a Diagnostic in E. coli",
            "chassis": "E. coli BL21(DE3)",
            "tool": "Cas12a endonuclease",
            "target": "Aquaculture pathogen detection",
            "methodology": "We perform plasmid transformation for recombinant Cas12a expression using shrimp farm water samples."
        }

        with patch.object(extractor, "_call_gemini_api", return_value=mock_response_json):
            ctx = extractor.extract(proposal_data, project_id="TEST-HYBRID-01")
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.organism_or_chassis.value, "Escherichia coli")
            self.assertEqual(ctx.genetic_modification.value, True)
            self.assertEqual(len(ctx.molecular_tools), 1)
            self.assertEqual(ctx.molecular_tools[0].value, "CRISPR-Cas12a")
            self.assertEqual(ctx.evidence_log[0]["extractor"], "gemini-1.5-flash")

    def test_mock_hallucinated_evidence_demotes_to_human_review(self):
        """If LLM hallucinates an evidence quote not in the text, status must be demoted to REQUIRES_HUMAN_REVIEW."""
        extractor = HybridLLMExtractor()
        extractor.gemini_key = "test_mock_key"

        mock_response_json = json.dumps({
            "organism_or_chassis": {"value": "HeLa Cells", "evidence": "hallucinated immortal human cell line", "status": "CONFIRMED", "confidence": 0.95, "rationale": "Extracted"},
            "molecular_tools": [],
            "sample_type": {"value": "Buffer", "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "human_subjects": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "animal_subjects": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "genetic_modification": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "recombinant_dna": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "pathogen_work": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "antimicrobial_resistance": {"value": False, "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "biosafety_containment": {"value": "BSL-1", "evidence": "", "status": "CONFIRMED", "confidence": 0.90, "rationale": ""},
            "uncertainties": []
        })

        proposal_data = {
            "title": "Simple Enzyme Kinetic Assay",
            "chassis": "Acellular Tris Buffer",
            "tool": "Spectrophotometer",
            "methodology": "Reactions carried out at room temperature in 96-well plates."
        }

        with patch.object(extractor, "_call_gemini_api", return_value=mock_response_json):
            ctx = extractor.extract(proposal_data, project_id="TEST-HALLUCINATE")
            self.assertIsNotNone(ctx)
            # Organism evidence quote was not in proposal text -> demoted to REQUIRES_HUMAN_REVIEW
            self.assertEqual(ctx.organism_or_chassis.status, FieldStatus.REQUIRES_HUMAN_REVIEW)
            self.assertIn("Grounding warning", ctx.organism_or_chassis.rationale)

    def test_extract_research_context_seamless_fallback_on_network_error(self):
        """When LLM raises a network exception, extract_research_context must smoothly fall back to deterministic extraction."""
        extractor = get_llm_extractor()
        proposal_data = {
            "student_id": "SYNTH-FALLBACK",
            "student_name": "Fallback Test Student",
            "title": "PETase Depolymerization in Cell-Free Buffer",
            "chassis": "Cell-Free Buffer Reaction Matrix",
            "tool": "PETase",
            "methodology": "Lyophilized enzyme incubated in 50 mM Tris-HCl."
        }
        with patch.object(extractor, "is_available", return_value=True):
            with patch.object(extractor, "extract", side_effect=Exception("Connection timed out")):
                ctx = extract_research_context(proposal_data, "SYNTH-FALLBACK")
                self.assertIsNotNone(ctx)
                self.assertEqual(ctx.organism_or_chassis.value, "Cell-Free Buffer Reaction Matrix")
                self.assertEqual(ctx.organism_or_chassis.source, "proposal.chassis")


if __name__ == "__main__":
    unittest.main()

