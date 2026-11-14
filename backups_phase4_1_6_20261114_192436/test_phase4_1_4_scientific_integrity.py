"""
Phase 4.1.4: Comprehensive Scientific Integrity & Test Isolation Regression Suite.
Validates the targeted repairs for Phase 4.1.3 findings:
- Repair A (Finding 4.1.3-F01): Server-side citation validation, manual DOI extraction, submission lock blocking for retracted papers.
- Repair B (Finding 4.1.3-F02): Scientific benchmark relationship classification, controlled vocabulary, and breakdown.
- Repair C (Finding 4.1.3-F03): Context-aware animal-model limitation handling (performed, excluded, future work, background, ambiguous, in-vitro).
- Repair D (Finding 4.1.3-F05): Complete test-data isolation for breakthroughs subsystem via BIOWRITER_DATA_DIR.
- Repair E (Finding 4.1.3-F04): Canonical frontend serving and routing integrity.
"""

import os
import sys
import unittest
import json
import hashlib
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Environment bootstrap
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

if "BIOWRITER_ENV" not in os.environ:
    os.environ["BIOWRITER_ENV"] = "testing"
if "SECRET_KEY" not in os.environ:
    os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

from app import app
from core.reference_service import (
    extract_dois,
    validate_citation_text,
    audit_bibliography_recency,
    _CITATION_STATUS_CACHE
)
from core.impact_novelty_engine import (
    VALID_RELATIONSHIP_TYPES,
    BENCHMARK_PRIOR_ART,
    audit_novelty_and_soundness
)
from core.paper_analyst_llm import (
    analyze_animal_model_context,
    generate_inferred_limitations
)
from core.breakthroughs_manager import (
    get_store_file,
    get_bookmarks_file,
    load_bookmarks,
    save_bookmarks,
    toggle_breakthrough_bookmark
)


class TestCitationValidationServerSide(unittest.TestCase):
    """Repair A (Finding 4.1.3-F01): Citation-status validation & manual DOI bypass defense."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir.name
        app.config["TESTING"] = True
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        if self.orig_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = self.orig_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        self.temp_dir.cleanup()

    def test_extract_dois_formats_and_punctuation(self):
        """Verify robust regex extraction of DOIs across prefixes, URLs, and punctuation."""
        sample_text = (
            "References:\n"
            "1. Smith et al. Nature https://doi.org/10.1038/s41586-020-2012-7.\n"
            "2. Jones et al. Science doi:10.1126/science.1234567;\n"
            "3. Bare DOI: 10.1016/j.cell.2020.12.001 (retracted).\n"
            "4. Bracketed: [10.1073/pnas.2000000117],\n"
            "5. Duplicate: https://doi.org/10.1038/s41586-020-2012-7\n"
        )
        dois = extract_dois(sample_text)
        self.assertEqual(len(dois), 4)  # deduplicated
        self.assertIn("10.1038/s41586-020-2012-7", dois)
        self.assertIn("10.1126/science.1234567", dois)
        self.assertIn("10.1016/j.cell.2020.12.001", dois)
        self.assertIn("10.1073/pnas.2000000117", dois)

    def test_extract_dois_empty_and_no_doi(self):
        """Verify empty and non-DOI text returns an empty list cleanly."""
        self.assertEqual(extract_dois(""), [])
        self.assertEqual(extract_dois("Just some text with no digital object identifiers."), [])

    def test_validate_citation_text_clean_reference(self):
        """Verify validation on clean reference with valid DOI."""
        _CITATION_STATUS_CACHE["10.1038/s41586-clean-01"] = {
            "success": True,
            "doi": "10.1038/s41586-clean-01",
            "title": "Valid Nature Paper",
            "year": 2022,
            "is_retracted": False,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False
        }
        val = validate_citation_text("10.1038/s41586-clean-01", use_network=False)
        self.assertEqual(val["total_citations"], 1)
        self.assertFalse(val["has_retracted"])
        self.assertFalse(val["has_expression_of_concern"])
        self.assertEqual(val["references"][0]["status_type"], "standard")
        self.assertFalse(val["references"][0]["is_retracted"])

    def test_validate_citation_text_retracted_reference(self):
        """Verify validation identifies retracted reference."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.2020.12.001"] = {
            "success": True,
            "doi": "10.1016/j.cell.2020.12.001",
            "title": "Fabricated CRISPR Screening Data",
            "year": 2020,
            "is_retracted": True,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False,
            "retraction_notice": "Formal Retraction (Cell 2021)."
        }
        val = validate_citation_text("Ref: 10.1016/j.cell.2020.12.001", use_network=False)
        self.assertEqual(val["total_citations"], 1)
        self.assertTrue(val["has_retracted"])
        self.assertEqual(len(val["retracted_citations"]), 1)
        self.assertEqual(val["references"][0]["status_type"], "retracted")
        self.assertTrue(val["references"][0]["is_retracted"])

    def test_validate_citation_text_expression_of_concern(self):
        """Verify validation identifies expression of concern."""
        _CITATION_STATUS_CACHE["10.1126/science.concern01"] = {
            "success": True,
            "doi": "10.1126/science.concern01",
            "title": "Questionable Protocol",
            "year": 2023,
            "is_retracted": False,
            "is_expression_of_concern": True,
            "is_preprint": False,
            "is_corrected": False,
            "status_warning": "Formal investigation active."
        }
        val = validate_citation_text("10.1126/science.concern01", use_network=False)
        self.assertTrue(val["has_expression_of_concern"])
        self.assertEqual(len(val["expression_of_concern_citations"]), 1)
        self.assertEqual(val["references"][0]["status_type"], "expression_of_concern")

    def test_validate_citation_text_network_failure_graceful(self):
        """Verify network errors gracefully degrade to status_type=unknown without throwing."""
        with patch("requests.get", side_effect=Exception("Connection timeout")):
            val = validate_citation_text("https://doi.org/10.1038/s41586-unreachable-test", use_network=True)
            self.assertEqual(val["total_citations"], 1)
            self.assertFalse(val["has_retracted"])
            self.assertTrue(val["has_unknown"])
            self.assertEqual(val["references"][0]["status_type"], "unknown")
            self.assertTrue(val["references"][0]["is_unknown"])

    def test_audit_bibliography_recency_includes_citation_validation(self):
        """Verify audit_bibliography_recency attaches citation_validation report."""
        text = "Tournier et al. (2020). Nature. https://doi.org/10.1038/s41586-020-2149-4"
        res = audit_bibliography_recency(text)
        self.assertIn("citation_validation", res)
        self.assertIn("total_citations", res["citation_validation"])
        self.assertIn("has_retracted", res["citation_validation"])

    def test_api_save_draft_with_retracted_doi_attaches_validation(self):
        """Verify draft saving with retracted DOI attaches validation metadata without blocking save."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.2020.retracted"] = {
            "success": True,
            "doi": "10.1016/j.cell.2020.retracted",
            "title": "Retracted Study",
            "year": 2020,
            "is_retracted": True,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False,
            "retraction_notice": "Retracted paper."
        }

        payload = {
            "student_id": "TEST-RETRACTED-STUDENT",
            "student_data": {
                "title": "Novel Biosensor",
                "references": "Smith et al. Cell. https://doi.org/10.1016/j.cell.2020.retracted"
            }
        }
        resp = self.client.post("/api/student/save_draft", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["has_retracted_citations"])
        self.assertIn("citation_validation", data)
        self.assertTrue(data["citation_validation"]["has_retracted"])

    def test_api_save_draft_manual_string_paste_detected(self):
        """Verify manual string pasting containing retracted DOI is detected by server-side validator."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.2020.pasted"] = {
            "success": True,
            "doi": "10.1016/j.cell.2020.pasted",
            "title": "Pasted Retracted DOI",
            "year": 2019,
            "is_retracted": True,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False
        }

        payload = {
            "student_id": "TEST-MANUAL-PASTE",
            "student_data": {
                "title": "Manual Paste Project",
                "references": "Unverified manual reference list:\nAuthor A. (2019). Cell. doi:10.1016/j.cell.2020.pasted"
            }
        }
        resp = self.client.post("/api/student/save_draft", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["has_retracted_citations"])

    def test_api_toggle_lock_blocks_retracted_citations(self):
        """Verify locking/submission for grading is blocked (HTTP 400) when retracted citations exist."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.2020.blocked"] = {
            "success": True,
            "doi": "10.1016/j.cell.2020.blocked",
            "title": "Blocked Study",
            "year": 2020,
            "is_retracted": True,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False,
            "retraction_notice": "Retracted for falsified blots."
        }

        # 1. Save draft with retracted citation
        save_resp = self.client.post("/api/student/save_draft", json={
            "student_id": "TEST-LOCK-BLOCK",
            "student_data": {
                "title": "Draft with Retraction",
                "references": "10.1016/j.cell.2020.blocked"
            }
        })
        self.assertEqual(save_resp.status_code, 200)

        # 2. Attempt to lock for grading -> HTTP 400
        lock_resp = self.client.post("/api/student/lock", json={
            "student_id": "TEST-LOCK-BLOCK",
            "is_locked": True
        })
        self.assertEqual(lock_resp.status_code, 400)
        lock_data = lock_resp.get_json()
        self.assertFalse(lock_data["success"])
        self.assertIn("Submission blocked", lock_data["error"])
        self.assertIn("retracted", lock_data["error"].lower())
        self.assertEqual(len(lock_data["retracted_citations"]), 1)

    def test_api_toggle_lock_succeeds_clean_draft(self):
        """Verify locking/submission succeeds (HTTP 200) when draft has no retracted citations."""
        _CITATION_STATUS_CACHE["10.1038/s41586-clean"] = {
            "success": True,
            "doi": "10.1038/s41586-clean",
            "title": "Clean Nature Study",
            "year": 2023,
            "is_retracted": False,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False
        }

        save_resp = self.client.post("/api/student/save_draft", json={
            "student_id": "TEST-LOCK-SUCCESS",
            "student_data": {
                "title": "Clean Draft",
                "references": "10.1038/s41586-clean"
            }
        })
        self.assertEqual(save_resp.status_code, 200)

        lock_resp = self.client.post("/api/student/lock", json={
            "student_id": "TEST-LOCK-SUCCESS",
            "is_locked": True
        })
        self.assertEqual(lock_resp.status_code, 200)
        self.assertTrue(lock_resp.get_json()["is_locked_for_grading"])


class TestScientificBenchmarkRelationships(unittest.TestCase):
    """Repair B (Finding 4.1.3-F02): Benchmark prior-art relationship classification."""

    def test_controlled_vocabulary_and_schema(self):
        """Verify VALID_RELATIONSHIP_TYPES contains exactly the 4 required categories."""
        expected = {"direct_prior_art", "enabling_technology", "target_biology", "adjacent_background"}
        self.assertEqual(VALID_RELATIONSHIP_TYPES, expected)

    def test_all_curated_records_valid(self):
        """Verify all curated benchmark prior art records have valid types and informative explanations."""
        total_records = 0
        for topic_key, records in BENCHMARK_PRIOR_ART.items():
            self.assertGreater(len(records), 0, f"Benchmark {topic_key} has no records")
            for record in records:
                total_records += 1
                self.assertIn("relationship_type", record, f"Record missing relationship_type: {record.get('title')}")
                self.assertIn(record["relationship_type"], VALID_RELATIONSHIP_TYPES, f"Invalid type in {record.get('title')}")
                self.assertIn("relevance_explanation", record, f"Record missing relevance_explanation: {record.get('title')}")
                self.assertIsInstance(record["relevance_explanation"], str)
                self.assertGreaterEqual(len(record["relevance_explanation"].strip()), 15, "Relevance explanation must be descriptive")
        self.assertEqual(total_records, 14, "Expected exactly 14 benchmark prior-art records across Cas12a and PETase")

    def test_curated_benchmark_relationship_breakdown(self):
        """Verify exact breakdown per benchmark topic."""
        cas12a_records = BENCHMARK_PRIOR_ART["cas12a_detection"]
        petase_records = BENCHMARK_PRIOR_ART["petase_engineering"]

        cas12a_types = [r["relationship_type"] for r in cas12a_records]
        petase_types = [r["relationship_type"] for r in petase_records]

        # Cas12a: 3 direct_prior_art, 2 enabling_technology, 1 target_biology, 1 adjacent_background
        self.assertEqual(cas12a_types.count("direct_prior_art"), 3)
        self.assertEqual(cas12a_types.count("enabling_technology"), 2)
        self.assertEqual(cas12a_types.count("target_biology"), 1)
        self.assertEqual(cas12a_types.count("adjacent_background"), 1)

        # PETase: 4 direct_prior_art, 2 enabling_technology, 0 target_biology, 1 adjacent_background
        self.assertEqual(petase_types.count("direct_prior_art"), 4)
        self.assertEqual(petase_types.count("enabling_technology"), 2)
        self.assertEqual(petase_types.count("target_biology"), 0)
        self.assertEqual(petase_types.count("adjacent_background"), 1)

    def test_audit_novelty_and_soundness_relationship_breakdown(self):
        """Verify audit_novelty_and_soundness includes relationship_breakdown in its response."""
        res = audit_novelty_and_soundness(
            title="CRISPR-Cas12a Biosensor for Pathogen Detection",
            chassis="Cell-free detection",
            tool="CRISPR-Cas12a",
            target="Klebsiella pneumoniae NDM-1 gene",
            hypothesis="Cas12a provides isothermal limit of detection under 10 copies",
            methodology="RPA coupled with Cas12a fluorophore probe cleavage"
        )
        self.assertIn("relationship_breakdown", res)
        breakdown = res["relationship_breakdown"]
        self.assertEqual(breakdown["direct_prior_art"], 3)
        self.assertEqual(breakdown["enabling_technology"], 2)
        self.assertEqual(breakdown["target_biology"], 1)
        self.assertEqual(breakdown["adjacent_background"], 1)
        self.assertEqual(breakdown["total_records"], 7)


class TestContextAwareAnimalModelLimitations(unittest.TestCase):
    """Repair C (Finding 4.1.3-F03): Context-aware animal-model limitation handling."""

    def test_scenario1_performed_animal_study(self):
        """Scenario 1: Performed animal studies -> limitation generated with evidence."""
        text = "Mice were treated with 5 mg/kg compound once daily for 14 days to assess in vivo toxicity."
        ctx = analyze_animal_model_context(text)
        self.assertEqual(ctx["status"], "performed")

        limits = generate_inferred_limitations(model_type=text)
        self.assertTrue(any("murine" in l.lower() or "animal cohort" in l.lower() for l in limits))

    def test_scenario2_explicitly_excluded_animal_study(self):
        """Scenario 2: Explicitly excluded animal studies -> limitation recognizes exclusion."""
        text = (
            "Because this study focuses on cell-free enzymatic characterization, "
            "animal experiments were explicitly omitted and excluded from the experimental design."
        )
        ctx = analyze_animal_model_context(text)
        self.assertEqual(ctx["status"], "excluded")

        limits = generate_inferred_limitations(model_type=text)
        self.assertTrue(any("explicitly excluded" in l.lower() for l in limits))

    def test_scenario3_future_work_mention(self):
        """Scenario 3: Animal mentions in future work -> categorized as future work, not current gap."""
        text = "Future work will include validating pharmacokinetic parameters in rodent animal models."
        ctx = analyze_animal_model_context(text)
        self.assertEqual(ctx["status"], "future_work")

        limits = generate_inferred_limitations(model_type=text)
        self.assertTrue(any("future work" in l.lower() for l in limits))

    def test_scenario4_background_literature_mention(self):
        """Scenario 4: Animal mentions in background citation -> attributed to background."""
        text = "Previous studies by Jones et al. demonstrated in vivo neurotoxicity in rat models."
        ctx = analyze_animal_model_context(text)
        self.assertEqual(ctx["status"], "background_only")

        limits = generate_inferred_limitations(model_type=text)
        self.assertTrue(any("prior literature" in l.lower() or "background" in l.lower() for l in limits))

    def test_scenario5_ambiguous_mentions(self):
        """Scenario 5: Ambiguous animal mentions -> flagged cautious or not asserted as performed."""
        text = "Animal-free protocols require careful consideration when evaluating physiological boundaries."
        ctx = analyze_animal_model_context(text)
        self.assertNotEqual(ctx["status"], "performed")

    def test_scenario6_pure_in_vitro(self):
        """Scenario 6: In vitro study with zero animal mentions -> in vitro limitation only, zero animal model mention."""
        text = "Purified Cas12a enzyme was mixed with guide RNA and fluorophore quencher ssDNA probe at 37 C."
        ctx = analyze_animal_model_context(text)
        self.assertEqual(ctx["status"], "none")

        limits = generate_inferred_limitations(model_type=text)
        self.assertFalse(any("animal cohort" in l.lower() or "murine" in l.lower() for l in limits))

    def test_finding_4_1_3_f03_reproduction(self):
        """Reproduction of exact text from Finding 4.1.3-F03 produces no spurious executed animal limitation."""
        f03_text = (
            "We designed a purely computational deep learning algorithm for enzyme design. "
            "All experiments were conducted in silico using AlphaFold structures and Rosetta energy functions. "
            "No animal models or live organism experiments were performed, and in vivo testing was explicitly "
            "excluded from this computational discovery phase."
        )
        ctx = analyze_animal_model_context(f03_text)
        self.assertEqual(ctx["status"], "excluded")
        limits = generate_inferred_limitations(model_type=f03_text)
        self.assertTrue(any("explicitly excluded" in l.lower() for l in limits))
        self.assertFalse(any("murine metabolic" in l.lower() for l in limits))


class TestBreakthroughsDataIsolation(unittest.TestCase):
    """Repair D (Finding 4.1.3-F05): Test data isolation for breakthroughs subsystem."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir.name

    def tearDown(self):
        if self.orig_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = self.orig_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        self.temp_dir.cleanup()

    def test_breakthroughs_store_file_in_isolated_dir(self):
        """Verify get_store_file and get_bookmarks_file use BIOWRITER_DATA_DIR."""
        store_file = get_store_file()
        bookmarks_file = get_bookmarks_file()
        self.assertTrue(store_file.startswith(self.temp_dir.name))
        self.assertTrue(bookmarks_file.startswith(self.temp_dir.name))

    def test_bookmark_operations_isolated(self):
        """Verify bookmarking saves to the isolated directory."""
        self.assertEqual(load_bookmarks(), [])
        toggle_breakthrough_bookmark("test_id_alphafold")
        self.assertEqual(load_bookmarks(), ["test_id_alphafold"])
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir.name, "breakthroughs_bookmarks.json")))

    def test_canonical_data_file_untouched(self):
        """Verify canonical project data file is not modified during operations."""
        canonical_bookmarks = os.path.join(BASE_DIR, "data", "breakthroughs_bookmarks.json")
        with open(canonical_bookmarks, "rb") as f:
            h1 = hashlib.sha256(f.read()).hexdigest()

        # Perform operations in isolated temp dir
        toggle_breakthrough_bookmark("test_item_isolated")
        toggle_breakthrough_bookmark("test_item_isolated")

        with open(canonical_bookmarks, "rb") as f:
            h2 = hashlib.sha256(f.read()).hexdigest()

        self.assertEqual(h1, h2, "Canonical breakthroughs_bookmarks.json must remain completely untouched")


class TestFrontendConsistencyAndRouting(unittest.TestCase):
    """Repair E (Finding 4.1.3-F04): Canonical frontend serving and routing integrity."""

    def setUp(self):
        self.client = app.test_client()

    def test_canonical_studio_js_served_by_routes(self):
        """Verify /studio.js and /static/studio.js serve exact bytes of upload/static/js/studio.js."""
        canonical_path = os.path.join(BASE_DIR, "static", "js", "studio.js")
        with open(canonical_path, "rb") as f:
            expected_bytes = f.read()

        r1 = self.client.get("/studio.js")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data, expected_bytes)
        r1.close()

        r2 = self.client.get("/static/studio.js")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data, expected_bytes)
        r2.close()

    def test_canonical_js_contains_scientific_integrity_features(self):
        """Verify canonical studio.js contains required Phase 4.1.4 features."""
        canonical_path = os.path.join(BASE_DIR, "static", "js", "studio.js")
        with open(canonical_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("is_retracted", js)
        self.assertIn("RETRACTED", js)
        self.assertIn("Relevant Prior Art & Supporting Literature", js)
        self.assertIn("relationship_type", js)
        self.assertIn("relevance_explanation", js)

    def test_templates_do_not_reference_unrouted_paths(self):
        """Verify templates reference only properly routed studio.js endpoints."""
        template_dir = os.path.join(BASE_DIR, "templates")
        for fname in os.listdir(template_dir):
            if fname.endswith(".html"):
                with open(os.path.join(template_dir, fname), "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                for line in content.splitlines():
                    if "script" in line and "studio.js" in line:
                        self.assertTrue(
                            'src="studio.js"' in line or 'src="static/js/studio.js"' in line or 'src="/static/studio.js"' in line,
                            f"Disallowed studio.js script tag in {fname}: {line}"
                        )


if __name__ == "__main__":
    unittest.main()
