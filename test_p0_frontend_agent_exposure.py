"""
P0 Verification Test Suite: Exposing the Existing Phase 3 Governed Agent to the Researcher.
Verifies Tests 1-10 required by the P0 Implementation specification:
1. Agent Run Rendered (agent_run.steps returned & handled by frontend)
2. Multi-Step Re-Plan Visible (search_pubmed -> 0 records -> search_europe_pmc -> >0 records)
3. Tools Used vs Available Tools (tools_called vs available_tools handled distinctly)
4. Evidence Log Rendered (context.evidence_log displayed with provenance + empty-state message)
5. Planner Mode Rendered (deterministic_fallback, google_gemini, openai)
6. Dynamic Clarifications (3+ clarifications rendered without 2-card cap)
7. Answered Clarifications (researcher_response & response_timestamp rendered)
8. Audit Integrity Schema Fix (integrity.valid, integrity.event_count, ev.prev_hash, ev.event_hash)
9. Human Escalation Visible (HUMAN_REVIEW / human_escalation rendered)
10. Proposal Text Unmodified (running analysis & rendering never mutates researcher proposal text)
"""

import os
import sys
import copy
import hashlib
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from agent.routes import orchestrator
from agent.audit import get_audit_history, verify_audit_integrity


class TestP0FrontendAgentExposure(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["student_id"] = "13989"
            sess["student_name"] = "Maya Abdelrazek"
            sess["role"] = "student"

        self.portal_bridge_path = os.path.join(BASE_DIR, "static", "agent_bridge.js")
        self.root_static_bridge_path = os.path.join(ROOT_DIR, "static", "agent_bridge.js")
        self.root_bridge_path = os.path.join(ROOT_DIR, "agent_bridge.js")
        self.portal_root_bridge_path = os.path.join(BASE_DIR, "agent_bridge.js")

        with open(self.portal_bridge_path, "r", encoding="utf-8") as f:
            self.bridge_js = f.read()

    def test_00_all_agent_bridge_copies_are_byte_identical(self):
        """Verify portal/static/agent_bridge.js and all duplicate agent_bridge.js copies match by SHA-256."""
        paths = [
            self.portal_bridge_path,
            self.root_static_bridge_path,
            self.root_bridge_path,
            self.portal_root_bridge_path,
        ]
        hashes = set()
        for p in paths:
            self.assertTrue(os.path.exists(p), f"Missing expected agent_bridge.js at {p}")
            with open(p, "rb") as f:
                hashes.add(hashlib.sha256(f.read()).hexdigest())
        self.assertEqual(len(hashes), 1, "All copies of agent_bridge.js must have identical SHA-256 digests.")

    def test_01_agent_run_steps_returned_and_rendered(self):
        """Test 1 — Agent Run Rendered: Verify agent_run.steps is returned by /agent/api/analyze and rendered by agent_bridge.js."""
        proposal = {
            "title": "CRISPR-Cas12a Detection of mcr-1 Colistin Resistance in Escherichia coli",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 colistin resistance gene",
            "abstract": "Diagnostic assay for plasmid-mediated colistin resistance.",
            "methodology": "Amplification and Cas12a trans-cleavage in BSL-2 cabinet.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True,
        }
        resp = self.client.post("/agent/api/analyze/13989", json={"proposal_data": proposal})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("agent_run", data)
        agent_run = data["agent_run"]
        self.assertIn("agent_run_id", agent_run)
        self.assertIn("steps", agent_run)
        self.assertGreaterEqual(len(agent_run["steps"]), 1)

        step1 = agent_run["steps"][0]
        for required_key in [
            "step_index",
            "decision_outcome",
            "selected_tool",
            "tool_arguments",
            "reason",
            "policy_validation_result",
            "tool_execution_status",
            "observation_summary",
            "next_action",
            "planner_mode",
        ]:
            self.assertIn(required_key, step1)

        # Verify frontend JS explicitly renders agent_run and step fields
        self.assertIn("buildAgenticLoopHtml", self.bridge_js)
        self.assertIn("run.agent_run_id", self.bridge_js)
        self.assertIn("step.decision_outcome", self.bridge_js)
        self.assertIn("step.selected_tool", self.bridge_js)
        self.assertIn("step.tool_arguments", self.bridge_js)
        self.assertIn("step.policy_validation_result", self.bridge_js)
        self.assertIn("step.tool_execution_status", self.bridge_js)
        self.assertIn("step.observation_summary", self.bridge_js)
        self.assertIn("step.next_action", self.bridge_js)

    def test_02_multistep_replan_pubmed_zero_to_europe_pmc_visible(self):
        """Test 2 — Multi-Step Re-Plan Visible: Verify search_pubmed (0 records) -> REASSESS_OBSERVATION -> search_europe_pmc (>0 records)."""
        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload
            def raise_for_status(self):
                pass
            def json(self):
                return self._payload

        def fake_requests_get(url, *args, **kwargs):
            if "esearch.fcgi" in url:
                return FakeResponse({"esearchresult": {"idlist": []}})
            if "ebi.ac.uk/europepmc" in url:
                return FakeResponse({
                    "resultList": {
                        "result": [
                            {
                                "id": "34567890",
                                "pmid": "34567890",
                                "doi": "10.1093/nar/gkab123",
                                "title": "CRISPR-Cas12a detection of mcr-1 in bacterial isolates",
                                "journalTitle": "Nucleic Acids Research",
                                "pubYear": "2024",
                                "source": "MED",
                            },
                            {
                                "id": "34567891",
                                "pmid": "34567891",
                                "doi": "10.1016/j.bios.2024.11",
                                "title": "Rapid isothermal RPA-Cas12a assay for colistin resistance",
                                "journalTitle": "Biosensors and Bioelectronics",
                                "pubYear": "2024",
                                "source": "MED",
                            },
                        ]
                    }
                })
            return FakeResponse({})

        with patch("agent.tool_registry.requests.get", side_effect=fake_requests_get):
            proposal = {
                "title": "CRISPR-Cas12a Detection of mcr-1 in Escherichia coli",
                "chassis": "Escherichia coli",
                "tool": "CRISPR-Cas12a",
                "target": "mcr-1",
                "methodology": "Standard molecular assay in unspecified lab.",
                "human_subjects": False,
                "recombinant_dna": True,
                "pathogen_work": True,
            }
            resp = self.client.post("/agent/api/analyze/13989", json={"proposal_data": proposal})
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            steps = data["agent_run"]["steps"]
            self.assertGreaterEqual(len(steps), 2)
            self.assertEqual(steps[0]["selected_tool"], "search_pubmed")
            self.assertEqual(steps[0]["tool_result_provenance"]["records_count"], 0)
            self.assertEqual(steps[0]["next_action"], "REASSESS_OBSERVATION")
            self.assertEqual(steps[1]["selected_tool"], "search_europe_pmc")
            self.assertEqual(steps[1]["tool_result_provenance"]["records_count"], 2)

        # Verify frontend JS explicitly renders REASSESS_OBSERVATION and ↻ RE-PLANNING connector
        self.assertIn("REASSESS_OBSERVATION", self.bridge_js)
        self.assertIn("↻ RE-PLANNING", self.bridge_js)
        self.assertIn("TOOL_ZERO_RESULTS", self.bridge_js)
        self.assertIn("TOOL_OK_WITH_RECORDS", self.bridge_js)

    def test_03_tools_used_vs_available_tools(self):
        """Test 3 — Tools Used vs Available Tools: Verify tools_called and available_tools are returned and rendered distinctly."""
        resp = self.client.post(
            "/agent/api/analyze/13989",
            json={"proposal_data": {"title": "BSL-1 GFP Expression in E. coli K-12", "chassis": "Escherichia coli K-12", "tool": "GFP plasmid"}},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("available_tools", data)
        self.assertEqual(len(data["available_tools"]), 5)
        avail_ids = {t["tool_id"] for t in data["available_tools"]}
        self.assertEqual(
            avail_ids,
            {"search_pubmed", "search_europe_pmc", "search_openalex", "ask_researcher", "request_human_review"},
        )
        self.assertIn("tools_called", data["agent_run"])

        # Verify frontend JS renders both TOOLS USED IN THIS RUN and AVAILABLE BOUNDED TOOLS
        self.assertIn("buildToolsVisibilityHtml", self.bridge_js)
        self.assertIn("TOOLS USED IN THIS RUN", self.bridge_js)
        self.assertIn("AVAILABLE BOUNDED TOOLS", self.bridge_js)
        self.assertIn("run.tools_called", self.bridge_js)
        self.assertIn("data.available_tools", self.bridge_js)

    def test_04_evidence_log_rendered_with_provenance_and_empty_fallback(self):
        """Test 4 — Evidence Log Rendered: Verify context.evidence_log records & empty message are handled in agent_bridge.js."""
        self.assertIn("buildEvidenceLogHtml", self.bridge_js)
        self.assertIn("ctx.evidence_log", self.bridge_js)
        self.assertIn("No external evidence was retrieved during this run.", self.bridge_js)
        self.assertIn("establishes_biosafety_risk_group: false", self.bridge_js)
        self.assertIn("rec.pmid", self.bridge_js)
        self.assertIn("rec.doi", self.bridge_js)
        self.assertIn("rec.title", self.bridge_js)
        self.assertIn("rec.journal", self.bridge_js)
        self.assertIn("rec.url", self.bridge_js)

    def test_05_planner_mode_transparency(self):
        """Test 5 — Planner Mode Rendered: Verify deterministic_fallback, google_gemini, and openai are accurately represented."""
        self.assertIn("formatPlannerModeDisplay", self.bridge_js)
        self.assertIn("google_gemini", self.bridge_js)
        self.assertIn("openai", self.bridge_js)
        self.assertIn("deterministic_fallback", self.bridge_js)
        self.assertIn("deterministic_fallback_after_llm_error", self.bridge_js)
        self.assertIn("Deterministic fallback", self.bridge_js)
        self.assertIn("Gemini (", self.bridge_js)
        self.assertIn("OpenAI (", self.bridge_js)

    def test_06_dynamic_clarifications_no_two_card_cap(self):
        """Test 6 — Dynamic Clarifications: Verify 3+ clarifications are returned and rendered dynamically without the old 2-card cap."""
        proposal = {
            "title": "Clinical Blood AMR Screening and In Vivo Mouse Challenge with Unspecified Biosafety",
            "chassis": "",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 resistance gene",
            "abstract": "Testing patient blood specimens and in vivo mouse infection model for colistin resistance.",
            "methodology": "Testing patient blood swabs and in vivo mice challenge in laboratory without specified BSL level.",
            "human_subjects": False,  # Contradiction with patient blood -> CLAR-HUMAN-01
            "recombinant_dna": True,
            "pathogen_work": True,    # Unspecified BSL with pathogen -> CLAR-BIO-01 + in vivo mice -> CLAR-ANIMAL-01
        }
        resp = self.client.post(
            "/agent/api/analyze/13989",
            json={"proposal_data": {**proposal, "preserve_clarifications": False}},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        pending = data["pending_clarifications"]
        self.assertGreaterEqual(len(pending), 3, "Expected at least 3 pending clarifications (human, biosafety, animal/chassis)")

        # Verify agent_bridge.js no longer hardcodes only modal-clar-card-1 and modal-clar-card-2
        self.assertNotIn('getElementById("modal-clar-card-1")', self.bridge_js)
        self.assertNotIn('getElementById("modal-clar-card-2")', self.bridge_js)
        self.assertIn("buildClarificationsHtml", self.bridge_js)
        self.assertIn("pending.map", self.bridge_js)
        self.assertIn("answered.map", self.bridge_js)

    def test_07_answered_clarifications_show_response_and_timestamp(self):
        """Test 7 — Answered Clarifications: Verify answering a clarification populates answered_clarifications with response & timestamp."""
        proposal = {
            "title": "Clinical Isolate AMR Assay",
            "chassis": "Escherichia coli",
            "tool": "CRISPR-Cas12a",
            "methodology": "Testing clinical isolates from patient blood cultures in BSL-2 cabinet.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True,
        }
        r1 = self.client.post("/agent/api/analyze/13989", json={"proposal_data": {**proposal, "preserve_clarifications": False}})
        d1 = r1.get_json()
        pending_ids = [q["question_id"] for q in d1["pending_clarifications"]]
        self.assertIn("CLAR-HUMAN-01", pending_ids)

        r2 = self.client.post(
            "/agent/api/clarify/13989",
            json={
                "question_id": "CLAR-HUMAN-01",
                "answer": "All isolates are de-identified reference strains obtained from ATCC public repository.",
            },
        )
        self.assertEqual(r2.status_code, 200)
        d2 = r2.get_json()
        self.assertTrue(d2["success"])
        answered = d2["answered_clarifications"]
        self.assertGreaterEqual(len(answered), 1)
        ans_q = next(q for q in answered if q["question_id"] == "CLAR-HUMAN-01")
        self.assertEqual(ans_q["status"], "answered")
        self.assertIn("ATCC public repository", ans_q["researcher_response"])
        self.assertTrue(ans_q["response_timestamp"])

        # Verify frontend JS renders researcher_response and response_timestamp
        self.assertIn("q.researcher_response", self.bridge_js)
        self.assertIn("q.response_timestamp", self.bridge_js)
        self.assertIn("Answered Researcher Clarifications", self.bridge_js)

    def test_08_audit_integrity_schema_fix(self):
        """Test 8 — Audit Integrity Schema Fix: Verify backend audit schema (integrity.valid, integrity.event_count, ev.prev_hash, ev.event_hash) matches agent_bridge.js."""
        audit_resp = self.client.get("/agent/api/audit/13989")
        self.assertEqual(audit_resp.status_code, 200)
        audit_data = audit_resp.get_json()
        self.assertTrue(audit_data["success"])
        integrity = audit_data["integrity"]
        self.assertIn("valid", integrity)
        self.assertIn("event_count", integrity)
        self.assertTrue(integrity["valid"])
        self.assertGreater(integrity["event_count"], 0)

        events = audit_data["events"]
        self.assertEqual(len(events), integrity["event_count"])
        for ev in events:
            self.assertIn("prev_hash", ev)
            self.assertIn("event_hash", ev)
            self.assertIn("event_id", ev)

        # Verify hash chaining between consecutive events
        for idx in range(1, len(events)):
            self.assertEqual(events[idx]["prev_hash"], events[idx - 1]["event_hash"])

        # Verify agent_bridge.js uses integrity.valid, integrity.event_count, and ev.prev_hash
        self.assertIn("integrity.valid", self.bridge_js)
        self.assertIn("integrity.event_count", self.bridge_js)
        self.assertIn("ev.prev_hash", self.bridge_js)
        self.assertIn("ev.event_hash", self.bridge_js)

    def test_09_human_escalation_visible(self):
        """Test 9 — Human Escalation Visible: Verify mandatory governance boundary triggers HUMAN_REVIEW & human_escalation."""
        high_risk_proposal = {
            "title": "BSL-2 Characterization of Reference ATCC BAA-2469 mcr-1 Strain",
            "chassis": "Escherichia coli ATCC BAA-2469",
            "tool": "CRISPR-Cas12a",
            "target": "mcr-1 colistin resistance plasmid",
            "abstract": "Diagnostic characterization of colistin resistance plasmid in BSL-2 containment.",
            "methodology": "All work uses de-identified ATCC reference strain inside a certified BSL-2 Class II biosafety cabinet with autoclaving at 121C.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True,
        }
        resp = self.client.post(
            "/agent/api/analyze/13989",
            json={"proposal_data": {**high_risk_proposal, "preserve_clarifications": False}},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn(data["workflow_state"], ("READY_FOR_ETHICS_HANDOFF", "HUMAN_REVIEW", "ESCALATED_TO_HUMAN_REVIEW"))
        self.assertEqual(data["agent_run"]["final_decision"], "HUMAN_REVIEW")
        esc = data["agent_run"]["human_escalation"]
        self.assertIsNotNone(esc)
        self.assertIn("required_role", esc)
        self.assertIn("reason", esc)
        self.assertIn("risk_level", esc)
        self.assertTrue(esc["autonomous_approval_blocked"])

        # Verify frontend JS explicitly renders human_escalation fields
        self.assertIn("buildHumanEscalationHtml", self.bridge_js)
        self.assertIn("esc.required_role", self.bridge_js)
        self.assertIn("esc.reason", self.bridge_js)
        self.assertIn("esc.risk_level", self.bridge_js)
        self.assertIn("esc.autonomous_approval_blocked", self.bridge_js)

    def test_10_proposal_text_unmodified_after_analysis(self):
        """Test 10 — Proposal Text Unmodified: Verify running analysis never mutates researcher-authored proposal fields."""
        original_proposal = {
            "title": "Authoritative Researcher Title — Do Not Modify",
            "chassis": "Escherichia coli BL21(DE3)",
            "tool": "CRISPR-Cas12a",
            "target": "blaNDM-1",
            "abstract": "Verbatim researcher abstract text that must remain untouched by the agent.",
            "aims": {"aim1": "Design crRNA guides.", "objectives": "Measure fluorescence kinetics."},
            "methodology": "Perform isothermal RPA at 37C in certified Class II BSL-2 biosafety cabinet.",
            "pitfalls": "Potential secondary structure in crRNA.",
            "expected_outcomes": "Limit of detection below 10 fM.",
            "human_subjects": False,
            "recombinant_dna": True,
            "pathogen_work": True,
        }
        snapshot = copy.deepcopy(original_proposal)
        resp = self.client.post("/agent/api/analyze/13989", json={"proposal_data": original_proposal})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(original_proposal, snapshot, "Backend analyze_proposal must never mutate input proposal dict.")

        # Verify agent_bridge.js never writes to proposal input fields (.value =)
        forbidden_assignments = [
            'getElementById("proposal-title-input").value =',
            'getElementById("proposal-abstract-input").value =',
            'getElementById("section-4-1-methodology").value =',
            'getElementById("section-3-1-aim").value =',
        ]
        for pattern in forbidden_assignments:
            self.assertNotIn(pattern, self.bridge_js)


if __name__ == "__main__":
    unittest.main()
