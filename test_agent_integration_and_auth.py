"""
Authentication, Authorization & Index Integration Test Suite for Catalyst Agent.
Verifies:
1. Student sessions are strictly prohibited from executing human review gates (HTTP 403).
2. Agent self-approvals are strictly blocked (HTTP 403).
3. Faculty sessions are authorized to execute human review gates.
4. Proposal analysis and Socratic clarification flow using frontend projectState payloads.
5. Index.html exposes the compliance agent buttons, Phase 4 card, and agent_bridge.js.
"""

import unittest
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import app
from agent.models import WorkflowState


class TestAgentIntegrationAndAuth(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-catalyst-2026"
        self.client = self.app.test_client()

    def test_student_session_blocks_human_review_gate(self):
        """Logged-in students must be strictly prohibited from approving institutional gates."""
        pid = "AUTH-TEST-STU-01"
        
        # Ingest proposal first
        self.client.post(f"/agent/api/analyze/{pid}", json={
            "proposal_data": {
                "student_id": pid,
                "student_name": "Test Student",
                "title": "BioEthics Test Project",
                "methodology": "Incubation in buffer."
            }
        })

        # Set session as student
        with self.client.session_transaction() as sess:
            sess["student_id"] = pid
            sess["student_name"] = "Test Student"
            sess["role"] = "student"
            sess["faculty_authenticated"] = False

        # Attempt to approve
        resp = self.client.post(f"/agent/api/human_decision/{pid}", json={
            "actor": "human",
            "role": "ethics_officer",
            "reviewer_id": "dr_faculty_chair",
            "decision": "approved"
        })

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Logged-in students are strictly prohibited", data["error"])

    def test_agent_self_approval_always_blocked(self):
        """AI agent self-approval must always be rejected with HTTP 403."""
        pid = "AUTH-TEST-AGENT-01"
        
        resp = self.client.post(f"/agent/api/human_decision/{pid}", json={
            "actor": "agent",
            "role": "ethics_officer",
            "decision": "approved"
        })

        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Security Violation: Actor 'agent' is not authorized", data["error"])

    def test_faculty_session_allows_human_review_gate(self):
        """Authenticated faculty/ethics committee sessions can execute review gates."""
        pid = "AUTH-TEST-FAC-01"

        # Ingest proposal
        self.client.post(f"/agent/api/analyze/{pid}", json={
            "proposal_data": {
                "student_id": pid,
                "student_name": "Test Student",
                "title": "Faculty Approved Project",
                "methodology": "Cell-free enzyme assay."
            }
        })

        # Simulate authenticated faculty session
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["faculty_user"] = "DR-ABDELRAZEK-IBC-CHAIR"
            sess["faculty_role"] = "committee_chair"
            sess["role"] = "faculty"

        resp = self.client.post(f"/agent/api/human_decision/{pid}", json={
            "actor": "human",
            "decision": "approved",
            "notes": "Verified protocol safety."
        })

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["workflow_state"], WorkflowState.CLEARED_FOR_NEXT_STAGE)
        self.assertEqual(data["decision"], "approved")
        self.assertIn("DR-ABDELRAZEK-IBC-CHAIR", data["recorded_by"])

    def test_proposal_analysis_and_clarification_from_frontend_payload(self):
        """Simulates frontend index.html projectState submission to agent API."""
        pid = "13989"
        frontend_project_state = {
            "student_id": pid,
            "student_name": "Maya Abdelrazek",
            "title": "Aptamer-Based Lateral Flow Detection of Colistin Resistance",
            "chassis": "Clinical Bacterial Isolates",
            "tool": "DNA Aptamer Probe",
            "target": "mcr-1 Colistin Resistance in Clinical Isolates",
            "methodology": "Patient blood and serum isolates will be collected from hospital clinical volunteers.",
            "aims": {"aim1": "Synthesize aptamer probe", "aim2": "Validate LOD in clinical isolates"}
        }

        # 1. Analyze
        resp_analyze = self.client.post(f"/agent/api/analyze/{pid}", json={
            "proposal_data": frontend_project_state
        })
        self.assertEqual(resp_analyze.status_code, 200)
        data_analyze = resp_analyze.get_json()
        self.assertTrue(data_analyze["success"])
        self.assertEqual(data_analyze["workflow_state"], WorkflowState.NEEDS_CLARIFICATION)
        self.assertGreaterEqual(len(data_analyze["active_requirements"]), 1)
        self.assertGreaterEqual(len(data_analyze["pending_clarifications"]), 1)

        # 2. Clarify
        qid = data_analyze["pending_clarifications"][0]["question_id"]
        resp_clarify = self.client.post(f"/agent/api/clarify/{pid}", json={
            "question_id": qid,
            "answer": "All isolates are de-identified standard ATCC BAA-2469 reference strains."
        })
        self.assertEqual(resp_clarify.status_code, 200)
        data_clarify = resp_clarify.get_json()
        self.assertTrue(data_clarify["success"])

        # 3. Check Dossier
        resp_dossier = self.client.get(f"/agent/dossier/{pid}/view")
        self.assertEqual(resp_dossier.status_code, 200)
        self.assertIn("Institutional Governance & Compliance Dossier", resp_dossier.get_data(as_text=True))

    def test_index_html_contains_agent_elements(self):
        """Ensures index.html includes the Compliance Agent top nav button, Phase 4 card, and bridge script."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Top Navbar Button
        self.assertIn('id="btn-nav-agent-compliance"', html)
        self.assertIn("Compliance Agent", html)

        # Phase 4 Pre-Submission Card
        self.assertIn('id="agent-compliance-card"', html)
        self.assertIn('id="btn-agent-run-analysis"', html)
        self.assertIn('id="btn-agent-open-dashboard"', html)
        self.assertIn('id="agent-results-container"', html)

        # Script bridge
        self.assertIn("agent_bridge.js", html)

    def test_agent_bridge_js_file_serves(self):
        """Ensures static/agent_bridge.js is served with HTTP 200."""
        resp = self.client.get("/static/agent_bridge.js")
        self.assertEqual(resp.status_code, 200)
        content = resp.get_data(as_text=True)
        resp.close()
        self.assertIn("Agent Bridge", content)
        self.assertIn("runAgentAnalysis", content)

    def test_cors_headers_and_preflight_on_agent_api(self):
        """Ensures CORS headers are present to allow file:// and cross-origin access."""
        # 1. Test OPTIONS preflight
        resp_opt = self.client.options("/agent/api/analyze/13989")
        self.assertEqual(resp_opt.status_code, 200)
        self.assertEqual(resp_opt.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", resp_opt.headers.get("Access-Control-Allow-Methods", ""))

        # 2. Test GET with CORS header
        resp_get = self.client.get("/agent/api/status/13989")
        self.assertEqual(resp_get.status_code, 200)
        self.assertEqual(resp_get.headers.get("Access-Control-Allow-Origin"), "*")


if __name__ == "__main__":
    unittest.main()
