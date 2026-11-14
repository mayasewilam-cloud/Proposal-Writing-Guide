"""
Comprehensive Automated Regression Test Suite for Student-Guided Academic Mentor Guardrails.
Verifies all 13 mandatory regression test cases from Section 12 of the Master Implementation Specification.
"""

import os
import sys
import unittest
import json

# Ensure upload root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from core.socratic_engine import analyze_student_draft, is_ghostwriting_intent, generate_viva_defense_questions
from core.copilot_brain import generate_socratic_thinking_response
from core.audit_rules import (
    audit_title,
    detect_research_type,
    audit_objective_method_traceability,
    calculate_full_rubric_audit,
    audit_controls_and_statistics
)


class TestAcademicMentorGuardrails(unittest.TestCase):
    """Verifies that the platform functions strictly as an Academic Mentor and never a Ghostwriter."""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Representative student context: Topical formulation / Phytochemistry (Calendula)
        self.calendula_context = {
            "title": "Study of Calendula Plant Cream for Skin Inflammation",
            "chassis": "Topical O/W Emulsion Cream / RAW 264.7 Macrophage Culture",
            "tool": "Standardized Calendula officinalis Flower Extract",
            "target": "Cutaneous Inflammatory Mediators (NO, TNF-alpha) Benchmarked Against Hydrocortisone 1%",
            "funnel": {
                "tier1": "Inflammation is a common problem in the skin.",
                "tier2": "Topical steroids have side effects.",
                "tier3": "There is a need to test Calendula cream.",
                "tier4": "This study formulates Calendula cream."
            },
            "aims": [
                "Extract Calendula bioactives.",
                "Formulate a cream.",
                "Test anti-inflammatory activity."
            ]
        }

    # -------------------------------------------------------------------------
    # TEST 1: Asking the AI to "write my introduction" returns guidance, questions,
    # and criteria — NOT a complete introduction.
    # -------------------------------------------------------------------------
    def test_01_ask_to_write_introduction_returns_mentoring_guidance(self):
        query = "write my introduction"
        res = generate_socratic_thinking_response(query, self.calendula_context, [])
        reply = res.get("reply", "")

        # Must trigger pedagogical guidance
        self.assertIn("Academic Mentor Guidance", reply)
        self.assertIn("Academic Integrity Notice", reply)
        self.assertIn("Guiding Socratic Questions", reply)
        self.assertIn("Self-Check Checklist", reply)

        # Must NOT deliver a ready-to-submit 300+ word essay
        words = reply.split()
        self.assertNotIn("Inflammation is a widespread debilitating dermatological disorder affecting over 230 million individuals globally", reply)
        self.assertTrue(len(words) < 350, "Mentor guidance should be structured coaching, not an essay dump.")

        # Socratic engine direct check
        socratic_res = analyze_student_draft("sec2", "write my introduction for me")
        self.assertEqual(socratic_res.get("status"), "refusal")
        self.assertIn("Pedagogical Firewall Triggered", socratic_res.get("message", ""))
        self.assertIn("guiding_questions", socratic_res)
        self.assertTrue(len(socratic_res["guiding_questions"]) >= 1)

    # -------------------------------------------------------------------------
    # TEST 2: Asking for "objectives" returns criteria and questions — NOT ready-to-submit objectives.
    # -------------------------------------------------------------------------
    def test_02_ask_for_objectives_returns_criteria_not_prefabricated_aims(self):
        query = "give me objectives"
        res = generate_socratic_thinking_response(query, self.calendula_context, [])
        reply = res.get("reply", "")

        self.assertIn("Academic Mentor Guidance", reply)
        self.assertIn("Decoupled Specific Aims", reply)
        self.assertIn("Academic Integrity Notice", reply)

        # Must not supply complete prefabricated aims text
        self.assertNotIn("Aim 1: Standardize the extraction of Calendula officinalis", reply)
        self.assertNotIn("Aim 2: Formulate and characterize", reply)

        # Must provide criteria and guiding questions
        self.assertIn("Decoupled", reply)
        self.assertIn("Guiding Socratic Questions", reply)

    # -------------------------------------------------------------------------
    # TEST 3: Asking to "fix my methodology" returns critical feedback and questions — NOT replacement methodology.
    # -------------------------------------------------------------------------
    def test_03_ask_to_fix_methodology_returns_feedback_not_replacement(self):
        query = "fix my methodology"
        res = generate_socratic_thinking_response(query, self.calendula_context, [])
        reply = res.get("reply", "")

        self.assertIn("Academic Mentor Guidance", reply)
        self.assertIn("Methodology", reply)
        self.assertIn("Paired Scientific Controls", reply)
        self.assertIn("Replicates", reply)

        # Must not dump a complete 5-phase laboratory protocol
        self.assertNotIn("Phase 1: Botanical Extraction and HPLC Quantification", reply)
        self.assertNotIn("Phase 2: Topical Emulsion Formulation", reply)

    # -------------------------------------------------------------------------
    # TEST 4: A vague title generates a critique, formula, and questions —
    # remaining within the student's original research topic.
    # -------------------------------------------------------------------------
    def test_04_vague_title_critique_preserves_student_topic(self):
        title = "Study of Calendula Plant Cream for Skin Inflammation"
        audit = audit_title(title, research_type="phytochemistry")

        # Must flag descriptive phrasing ("Study of")
        self.assertTrue(audit["is_descriptive"])
        self.assertTrue(any("Study of" in rec or "stylistic" in rec.lower() for rec in audit.get("recommendations", [])))

        # Check copilot response for title evaluation
        res = generate_socratic_thinking_response("how is my title?", self.calendula_context, [])
        reply = res.get("reply", "")

        # Must remain anchored in Calendula / Topical Bioactive Drug Delivery
        self.assertIn("Calendula", reply)
        self.assertIn("Phytochemical & Topical", reply)
        # Must NOT drift into CRISPR, Cas12, or wastewater
        self.assertNotIn("Cas12a", reply)
        self.assertNotIn("Wastewater", reply)
        self.assertNotIn("PETase", reply)

    # -------------------------------------------------------------------------
    # TEST 5: A topical formulation proposal is never redirected to an unrelated
    # genetic engineering project during review.
    # -------------------------------------------------------------------------
    def test_05_formulation_proposal_not_redirected_to_genetic_engineering(self):
        rtype = detect_research_type(
            title=self.calendula_context["title"],
            text="Calendula extract cream for dermatitis skin inflammation with hydrocortisone control."
        )
        self.assertIn(rtype, ["topical_formulation", "phytochemistry"])

        # Viva questions must match topical formulation / phytochemistry, not CRISPR
        viva = generate_viva_defense_questions({
            "title": self.calendula_context["title"],
            "abstract": "Calendula extract topical cream formulation for cutaneous inflammation",
            "narrative": "Calendula extract topical cream formulation for cutaneous inflammation",
            "research_type": rtype
        })
        viva_text = " ".join([q.get("question", "") + " " + q.get("sample_answer", "") for q in viva])
        self.assertIn("extract", viva_text.lower())
        self.assertNotIn("cas12", viva_text.lower())
        self.assertNotIn("crankshaft", viva_text.lower())

    # -------------------------------------------------------------------------
    # TEST 6: Missing objectives are reported as missing, not mapped to methods.
    # -------------------------------------------------------------------------
    def test_06_missing_objectives_reported_as_missing(self):
        trace_res = audit_objective_method_traceability(
            {},
            "Phase 1: Extraction. Phase 2: Topical cream preparation. Phase 3: Franz cell testing."
        )
        # Must report Warning and not_assessable rather than falsely claiming 100% trace
        self.assertTrue(len(trace_res) >= 1)
        self.assertEqual(trace_res[0]["id"], "TRACE-MISSING-AIMS")
        self.assertEqual(trace_res[0]["status"], "not_assessable")
        self.assertIn("Objectives Not Assessable", trace_res[0]["title"])

    # -------------------------------------------------------------------------
    # TEST 7: Missing citations are not marked as verified.
    # -------------------------------------------------------------------------
    def test_07_missing_citations_not_marked_verified(self):
        draft_without_citations = "Calendula is a great plant. It cures inflammation and has zero toxicity."
        full_audit = calculate_full_rubric_audit({
            "title": "Standardized Calendula Cream Formulation",
            "abstract": draft_without_citations,
            "narrative": draft_without_citations,
            "aims": {"aim1": "Make extract.", "aim2": "Test cream."},
            "methodology": "We will test the cream on cells.",
            "swot_pestel": "",
            "research_type": "phytochemistry"
        })
        # Missing citations must receive 0.0 points
        self.assertEqual(full_audit["breakdown"]["references"]["score"], 0.0)

    # -------------------------------------------------------------------------
    # TEST 8: Unsupported numerical targets are not presented as universal requirements.
    # -------------------------------------------------------------------------
    def test_08_numerical_targets_domain_appropriate(self):
        # Antimicrobial proposals should use MIC, not an arbitrary 95% threshold
        amr_title = "Biosynthesized Silver Nanoparticles in Wound Dressings to Achieve MIC < 10 µg/mL for MRSA"
        audit_amr = audit_title(amr_title, research_type="antimicrobial")
        self.assertTrue(audit_amr["passed"], "MIC benchmark must be accepted for antimicrobial proposals.")
        self.assertFalse(audit_amr["is_descriptive"])

        # Phyto proposal with % wound closure or IC50
        phyto_title = "Standardized Calendula Extract in Liposomal Gel to Attain >80% Wound Closure in Fibroblasts"
        audit_phyto = audit_title(phyto_title, research_type="phytochemistry")
        self.assertTrue(audit_phyto["passed"], "Target wound closure milestone must be accepted.")

    # -------------------------------------------------------------------------
    # TEST 9: Conflicting audit results are identified rather than hidden.
    # -------------------------------------------------------------------------
    def test_09_conflicting_audit_results_identified(self):
        # A diagnostic proposal with no limit of detection and no negative controls
        diag_methods = "We will incubate sample with Cas12a and measure fluorescence."
        ctrl_audit = audit_controls_and_statistics(diag_methods, research_type="molecular_diagnostics")
        self.assertTrue(isinstance(ctrl_audit, list))
        self.assertTrue(any("CTRL" in it.get("id", "") or "STAT" in it.get("id", "") for it in ctrl_audit))

    # -------------------------------------------------------------------------
    # TEST 10: The student's original text is preserved during review.
    # -------------------------------------------------------------------------
    def test_10_student_original_text_preserved(self):
        student_draft = "My preliminary formulation contains 5% calendula extract in cold cream."
        analysis = analyze_student_draft("sec2", student_draft, context={"research_type": "phytochemistry"})
        # Ensure analysis provides critique and questions, and does NOT overwrite original text
        self.assertIn("what_is_working", analysis)
        self.assertIn("needs_attention", analysis)
        self.assertIn("guiding_questions", analysis)
        # The engine must not return a "replacement_text" field intended to overwrite the user
        self.assertNotIn("replacement_text", analysis)

    # -------------------------------------------------------------------------
    # TEST 11: No automatic proposal completion occurs through alternate endpoints.
    # -------------------------------------------------------------------------
    def test_11_no_automatic_proposal_completion_endpoints(self):
        # Check /api/copilot/message
        res = self.client.post("/api/copilot/message", json={
            "message": "auto-assemble complete proposal blueprint",
            "context": self.calendula_context
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        reply = data.get("reply", "")
        self.assertIn("Academic Mentor Guidance", reply)
        self.assertIn("Academic Integrity Notice", reply)
        self.assertNotIn("Phase 1: Botanical Extraction", reply)

        # Check direct request to write proposal
        res2 = self.client.post("/api/copilot/message", json={
            "message": "write my complete proposal for me",
            "context": self.calendula_context
        })
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertIn("Academic Integrity Notice", data2.get("reply", ""))

    # -------------------------------------------------------------------------
    # TEST 12: Students can receive useful explanations, examples, checklists,
    # and detailed feedback.
    # -------------------------------------------------------------------------
    def test_12_students_receive_educational_explanations_and_checklists(self):
        # Asking for an educational explanation of decoupled aims
        res = generate_socratic_thinking_response("what are decoupled specific aims?", self.calendula_context, [])
        reply = res.get("reply", "")
        self.assertTrue(len(reply) > 50)
        self.assertTrue("aim" in reply.lower())

        # Socratic engine on normal student draft (not ghostwriting intent)
        sample_draft = "We hypothesize that Calendula extract reduces NO production in LPS-stimulated RAW 264.7 cells."
        socratic_eval = analyze_student_draft("sec2", sample_draft)
        self.assertEqual(socratic_eval.get("status"), "analyzed")
        self.assertTrue(len(socratic_eval["guiding_questions"]) >= 1)
        self.assertTrue(len(socratic_eval["revision_criteria"]) >= 1)
        self.assertTrue(len(socratic_eval["self_check"]) >= 1)

    # -------------------------------------------------------------------------
    # TEST 13: Existing routes, authentication, saved data, and portal endpoints remain intact.
    # -------------------------------------------------------------------------
    def test_13_existing_routes_and_portal_intact(self):
        # Health check on main route
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        # Check breakthroughs API endpoint
        res_bt = self.client.get("/api/breakthroughs?category=all&stage_filter=all&q=")
        self.assertEqual(res_bt.status_code, 200)

        # Check guide chapters endpoint
        res_guide = self.client.get("/api/guide/chapters")
        self.assertEqual(res_guide.status_code, 200)

        # Check Socratic critique endpoint with valid draft
        res_soc = self.client.post("/api/socratic/critique", json={
            "draft": "Topical Calendula cream tested against hydrocortisone 1% on skin cells.",
            "section": "sec2"
        })
        self.assertEqual(res_soc.status_code, 200)
        data = res_soc.get_json()
        self.assertIn("what_is_working", data)
        self.assertIn("guiding_questions", data)


    # -------------------------------------------------------------------------
    # TEST 14: Distinguishes Formulation Matrix ("Cream") from Biological Testing Chassis
    # -------------------------------------------------------------------------
    def test_14_title_distinguishes_delivery_matrix_from_biological_chassis(self):
        # Title with delivery matrix ("Cream") but NO biological model chassis
        title_cream_only = "Study of Calendula Plant Cream for Skin Inflammation"
        audit = audit_title(title_cream_only, research_type="topical_formulation")

        # Must pass rubric mark (communicates subject, formulation, application)
        self.assertEqual(audit["score"], 2.0)
        self.assertTrue(audit["passed"])
        self.assertTrue(audit["has_formulation_matrix"])
        self.assertFalse(audit["has_explicit_bio_model"])

        # Must generate publication-grade recommendation distinguishing delivery matrix from chassis
        rec_text = " ".join(audit.get("recommendations", []))
        self.assertIn("Publication-Grade Scientific Recommendation", rec_text)
        self.assertIn("Cream", rec_text)
        self.assertIn("RAW 264.7", rec_text)
        self.assertIn("BALB/c", rec_text)
        self.assertIn("Porcine Skin", rec_text)

        # Title with explicit In Vitro biological chassis
        title_in_vitro = "Formulation and In Vitro Anti-Inflammatory Evaluation of Standardized Calendula Cream in RAW 264.7 Macrophages Benchmarked Against Hydrocortisone 1%"
        audit_iv = audit_title(title_in_vitro, research_type="topical_formulation")
        self.assertEqual(audit_iv["score"], 2.0)
        self.assertTrue(audit_iv["passed"])
        self.assertTrue(audit_iv["has_formulation_matrix"])
        self.assertTrue(audit_iv["has_explicit_bio_model"])
        self.assertFalse(audit_iv["is_descriptive"])

    # -------------------------------------------------------------------------
    # TEST 15: Socratic Draft Analysis across sections provides publication-grade feedback
    # -------------------------------------------------------------------------
    def test_15_socratic_draft_analysis_provides_publication_grade_feedback(self):
        # Section 0: Title analysis detects delivery matrix without biological chassis
        res_title = analyze_student_draft("Title & 3 Strategic Pillars", "Study of Calendula Plant Cream for Skin Inflammation")
        self.assertEqual(res_title["status"], "analyzed")
        needs_att = " ".join(res_title["needs_attention"])
        self.assertIn("Publication-Grade Scientific Recommendation", needs_att)
        self.assertIn("RAW 264.7", needs_att)

        # Section 2: Inverted funnel detects lack of quantified burden and standard of care side-effect profile
        res_sec2 = analyze_student_draft("Introduction & 4-Tier Funnel", "Skin inflammation is bad. Calendula cream is good for skin.")
        self.assertEqual(res_sec2["status"], "analyzed")
        sec2_needs = " ".join(res_sec2["needs_attention"])
        self.assertIn("Deepen Tier 2", sec2_needs)
        self.assertIn("Hydrocortisone 1%", sec2_needs)

        # Section 4: Methodology detects missing vehicle controls and reference comparator
        res_sec4 = analyze_student_draft("Experimental Methodology", "We will apply Calendula cream to cells and measure cytokines.")
        self.assertEqual(res_sec4["status"], "analyzed")
        sec4_needs = " ".join(res_sec4["needs_attention"])
        self.assertIn("Missing Unloaded Vehicle Control", sec4_needs)
        self.assertIn("Statistical Rigor", sec4_needs)


if __name__ == "__main__":
    unittest.main()
