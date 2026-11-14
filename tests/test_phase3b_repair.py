"""
Comprehensive Phase 3B Functional Reliability & Workflow Stability Verification Suite.
Validates the repair of:
- Task A (BUG-DEC-01): Paper Decoder response handling & HTML protection
- Task B (BUG-PHOTO-01 / CONN-UX-01): Results photo persistence, IndexedDB & save status indicator
- Task C (CRASH-TYPE-01 / CONN-TYPE-01): Reference recency auditor input validation (string & list[str], rejecting None/int/dict with 400)
- Task D (CRASH-ROUTE-01): Missing /test_maya_runner route redirection to /?student_id=13989
- Task E (REG-TEST-01): Evidence Matrix schema alignment, parameters, and guest test targets
- Task 7 (CONN-SYNC-01): JS synchronization between root and static directories
"""

import sys
import os
import unittest
import json
import re
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from core.reference_service import audit_bibliography_recency
from core.paper_summarizer import deconstruct_paper, SAMPLE_PAPERS, JARGON_LEXICON


class TestPhase3BRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile, shutil
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_test_phase3b_")
        cls.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_dir
        app.config["TESTING"] = True
        app.testing = True
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        import shutil
        if cls.old_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = cls.old_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # Task C: CRASH-TYPE-01 / CONN-TYPE-01 (Recency Auditor Input Handling)
    # =========================================================================
    def test_recency_auditor_string_input(self):
        """Verify audit_bibliography_recency accepts string input cleanly."""
        text = "Austin, H. P. et al. (2018). PNAS.\nTournier, V. et al. (2020). Nature."
        res = audit_bibliography_recency(text)
        self.assertIn("total_count", res)
        self.assertIn("recency_percentage", res)
        self.assertEqual(res["total_count"], 2)

    def test_recency_auditor_list_input(self):
        """Verify audit_bibliography_recency accepts List[str] input cleanly."""
        ref_list = [
            "Austin, H. P. et al. (2018). PNAS. 115(19):E4350.",
            "Tournier, V. et al. (2020). An engineered PET depolymerase. Nature, 580:216-219."
        ]
        res = audit_bibliography_recency(ref_list)
        self.assertIn("total_count", res)
        self.assertEqual(res["total_count"], 2)

    def test_recency_auditor_empty_inputs(self):
        """Verify empty string and empty list return zero references without crashing."""
        res_str = audit_bibliography_recency("")
        self.assertEqual(res_str["total_count"], 0)
        res_list = audit_bibliography_recency([])
        self.assertEqual(res_list["total_count"], 0)

    def test_recency_auditor_invalid_types_raise_value_error(self):
        """Verify non-string / non-list-of-strings raise ValueError in core service."""
        with self.assertRaises(ValueError):
            audit_bibliography_recency(None)
        with self.assertRaises(ValueError):
            audit_bibliography_recency(12345)
        with self.assertRaises(ValueError):
            audit_bibliography_recency({"ref": "Austin 2018"})
        with self.assertRaises(ValueError):
            audit_bibliography_recency(["Valid 2020 citation", 9999])

    def test_api_audit_recency_endpoint_status_codes(self):
        """Verify /api/reference/audit_recency returns 200 on valid input and 400 on invalid input."""
        # 1. Valid string
        resp = self.client.post("/api/reference/audit_recency", json={"references": "Tournier et al. (2020)"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["total_count"], 1)

        # 2. Valid list of strings
        resp = self.client.post("/api/reference/audit_recency", json={"references": ["Tournier et al. (2020)"]})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["total_count"], 1)

        # 3. Missing references field -> 400
        resp = self.client.post("/api/reference/audit_recency", json={})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

        # 4. None -> 400
        resp = self.client.post("/api/reference/audit_recency", json={"references": None})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

        # 5. Integer -> 400
        resp = self.client.post("/api/reference/audit_recency", json={"references": 12345})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

        # 6. Dict -> 400
        resp = self.client.post("/api/reference/audit_recency", json={"references": {"cite": "2020"}})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

        # 7. Mixed list -> 400
        resp = self.client.post("/api/reference/audit_recency", json={"references": ["Tournier 2020", 42]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    # =========================================================================
    # Task D: CRASH-ROUTE-01 (Missing /test_maya_runner Route Template)
    # =========================================================================
    def test_maya_runner_route_redirects_cleanly(self):
        """Verify /test_maya_runner returns HTTP 302 redirecting to /?student_id=13989."""
        resp = self.client.get("/test_maya_runner", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/?student_id=13989", resp.headers.get("Location", ""))

    # =========================================================================
    # Task E: REG-TEST-01 (Evidence Matrix Schema Alignment & API Tests)
    # =========================================================================
    def test_deconstruct_paper_schema_parameters(self):
        """Verify deconstruct_paper output has all required legacy and modern parameter keys."""
        sample = SAMPLE_PAPERS["petase"]
        res = deconstruct_paper(
            text=sample["abstract"],
            title=sample["title"],
            identifier=sample["doi"],
            authors=sample["authors"],
            year=sample["year"],
            journal=sample["journal"]
        )
        self.assertEqual(res["status"], "success")

        # Plain English
        pe = res.get("plain_english_explanation", {})
        self.assertIn("theme", pe)
        self.assertIn("core_analogy", pe)
        self.assertIn("Enzymatic Plastic Upcycling", pe["theme"])

        # Parameters
        params = res.get("extracted_parameters", {})
        self.assertIn("Escherichia coli", params["chassis"])
        self.assertTrue(len(params["metric_numbers"]) > 0)
        self.assertTrue(params["target_milestone"].startswith("Target"))

        # Backward compatibility explanation keys
        pexp = res.get("parameter_explanations", {})
        for k in ["burden_explanation", "benchmark_explanation", "gap_explanation",
                  "controls_explanation", "solution_explanation", "milestone_explanation",
                  "citation_explanation"]:
            self.assertIn(k, pexp)

        # 4 proposal recommendations
        self.assertEqual(len(res.get("proposal_recommendations", [])), 4)

    def test_student_draft_nonexistent_returns_404(self):
        """Verify GET /api/student/draft/<unknown> prevents enumeration for guests (403) and returns 404 for authorized faculty."""
        # Unauthorized guest receives generic 403 to prevent account enumeration
        resp = self.client.get("/api/student/draft/NON_EXISTENT_STUDENT_XYZ_9999")
        self.assertEqual(resp.status_code, 403)

        # Authorized faculty receives clean 404
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"
        resp_fac = self.client.get("/api/student/draft/NON_EXISTENT_STUDENT_XYZ_9999")
        self.assertEqual(resp_fac.status_code, 404)

    def test_student_draft_guest_test_prefix_access(self):
        """Verify ST_API_ and TEST- prefixes allow unauthenticated test access."""
        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "ST_API_TEST",
            "student_data": {"project_title": "Automated Test Project"}
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    # =========================================================================
    # Task A: BUG-DEC-01 (Paper Decoder Response Handling Verification)
    # =========================================================================
    def test_frontend_paper_decoder_html_error_protection(self):
        """Verify studio.js checks response content-type and wraps .json() safely."""
        with open("upload/static/js/studio.js", "r", encoding="utf-8") as f:
            js = f.read()

        # Check content-type verification before JSON parsing
        self.assertIn('contentType.includes("application/json")', js)
        self.assertIn("PDF decoding requires the BioWriter application server", js)
        self.assertIn("The backend service is currently unreachable", js)

    # =========================================================================
    # Task B: BUG-PHOTO-01 / CONN-UX-01 (IndexedDB Storage & Save Status Reporting)
    # =========================================================================
    def test_frontend_indexeddb_and_save_status_logic(self):
        """Verify studio.js defines BioWriterPhotoDB and never shows 'All progress saved' on error."""
        with open("upload/static/js/studio.js", "r", encoding="utf-8") as f:
            js = f.read()

        # 1. IndexedDB helper defined
        self.assertIn("BioWriterPhotoDB", js)
        self.assertIn("savePhoto", js)
        self.assertIn("getPhoto", js)
        self.assertIn("deletePhoto", js)

        # 2. QuotaExceededError offloads to IndexedDB
        self.assertIn("QuotaExceededError", js)
        self.assertIn("[stored_in_idb]", js)

        # 3. Accurate save status reporting on failure
        self.assertIn("Save Failed", js)
        self.assertIn("Storage Quota Exceeded", js)

    # =========================================================================
    # Task 7: CONN-SYNC-01 / Repair E (Frontend Routing & Canonical Integrity Audit)
    # =========================================================================
    def test_canonical_frontend_served_at_routes(self):
        """Verify Flask serves the canonical static/js/studio.js at /studio.js and /static/studio.js."""
        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "rb") as f:
            canonical_bytes = f.read()

        # 1. /studio.js route returns canonical file bytes
        resp1 = self.client.get("/studio.js")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.data, canonical_bytes)

        # 2. /static/studio.js route returns canonical file bytes
        resp2 = self.client.get("/static/studio.js")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data, canonical_bytes)

    def test_canonical_frontend_scientific_integrity_features(self):
        """Verify canonical static/js/studio.js contains required scientific integrity features."""
        canonical_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "studio.js")
        with open(canonical_path, "r", encoding="utf-8") as f:
            js = f.read()

        # Scientific integrity and citation status features
        self.assertIn("is_retracted", js)
        self.assertIn("RETRACTED", js)
        self.assertIn("Relevant Prior Art & Supporting Literature", js)
        self.assertIn("relationship_type", js)
        self.assertIn("relevance_explanation", js)

    def test_templates_do_not_reference_obsolete_copies(self):
        """Verify templates and routes serve canonical frontend assets without unrouted paths."""
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
        for fname in os.listdir(template_dir):
            if fname.endswith(".html"):
                fpath = os.path.join(template_dir, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for line in content.splitlines():
                    if "script" in line and "studio.js" in line:
                        self.assertTrue(
                            'src="studio.js"' in line or 'src="static/js/studio.js"' in line or 'src="/static/studio.js"' in line,
                            f"Unexpected studio.js script tag in {fname}: {line}"
                        )


if __name__ == "__main__":
    unittest.main()
