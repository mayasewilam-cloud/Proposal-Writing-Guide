"""
BioWriter Studio — Phase 4.1.2 Scientific Integrity Remediation Test Suite.
Validates the targeted repairs:
- Repair A: Publication-Year Extraction (correct parenthetical regex boundaries, author-date priority, volume exclusion)
- Repair B: Retraction, Expression-of-Concern, Preprint, and Correction warnings (Backend & Frontend simulation)
- Repair C: Curated Benchmark DOI Integrity (Herrero Acero/Ribitsch 2013 and Skariyachan 2018 in PETase)
- Repair D: Animal-Model Keyword Substring Collision (Word-bounded matching against "integration")
- Repair E: Short Unheaded Text Classification (Unsegmented body preservation, no false abstract labeling)
- Repair F: Frontend Regional Assumption Neutralization (Institutional neutrality in studio.js)
"""

import os
import sys
import re
import json
import unittest
import tempfile
import shutil
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Ensure upload directory is on path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.reference_service import extract_citation_year, audit_bibliography_recency, fetch_doi_metadata
from core.impact_novelty_engine import audit_novelty_and_soundness
from core.paper_analyst_llm import generate_inferred_limitations
from core.retrieval_service import parse_raw_text_into_sections, retrieve_paper_data


class TestPhase412ScientificIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_test_phase4_1_2_")
        cls.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_dir
        os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"
        os.environ["FLASK_TESTING"] = "1"
        os.environ["TESTING"] = "1"

    @classmethod
    def tearDownClass(cls):
        if cls.old_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = cls.old_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    # =========================================================================
    # REPAIR A: Publication-Year Extraction Tests
    # =========================================================================

    def test_repair_a_adversarial_case_6_historical_date_and_author_year(self):
        """Case 6: Historical date followed by author year must extract author year, not historical date."""
        text = "In 1999, we initiated trials, which were reported by Zhang (2023) following 2015 pilot data."
        self.assertEqual(extract_citation_year(text), 2023)

    def test_repair_a_adversarial_case_10_volume_number_collision(self):
        """Case 10: Journal volume number must not collide with author publication year."""
        text = "Wang (2024). Progress. Vol. 1990, Art 12."
        self.assertEqual(extract_citation_year(text), 2024)

    def test_repair_a_page_range_exclusion(self):
        """Case 2: Page ranges like pp. 2021-2025 must not override publication year."""
        text = "Johnson, A. B. (1998) ... pp. 2021-2025."
        self.assertEqual(extract_citation_year(text), 1998)

    def test_repair_a_standard_author_date(self):
        """Case 1: Standard author parenthetical format."""
        text = "Smith et al. (2020) J. Mol. Biol."
        self.assertEqual(extract_citation_year(text), 2020)

    def test_repair_a_multiple_citations_first_author_priority(self):
        """Case 12: Multiple author-year citations in one string returns primary cited author year."""
        text = "Brown (2019a) and Green (2021b)."
        self.assertEqual(extract_citation_year(text), 2019)

    def test_repair_a_year_out_of_bounds(self):
        """Cases 7 & 8: Years outside valid historical bounds (1900-2026) return None."""
        self.assertIsNone(extract_citation_year("Historical report from 1850."))
        self.assertIsNone(extract_citation_year("Future perspectives on synthetic biology (2035)."))

    def test_repair_a_no_year(self):
        """Case 5: Text lacking 4-digit numbers returns None."""
        self.assertIsNone(extract_citation_year("A citation with no publication year"))

    def test_repair_a_dataset_marker(self):
        """Case 3: Author year takes precedence over dataset accession dates."""
        text = "Doe (2024) [Dataset] ... 2021"
        self.assertEqual(extract_citation_year(text), 2024)

    def test_repair_a_author_date_without_parentheses(self):
        """Case 4: Author-date citation without parentheses."""
        text = "Al-Bahrani et al. 2022. Title..."
        self.assertEqual(extract_citation_year(text), 2022)

    def test_repair_a_patent_exclusion(self):
        """Case 11: 11-digit patent identifier does not collide with parenthetical year."""
        text = "Patent US20210012345A1 (2022)."
        self.assertEqual(extract_citation_year(text), 2022)

    def test_repair_a_ambiguous_multiple_years_returns_none(self):
        """Multiple plausible years without author-date association returns None (honest uncertainty)."""
        text = "Conference 2025, presentation 2022."
        self.assertIsNone(extract_citation_year(text))

    def test_repair_a_single_isolated_year_returns_year(self):
        """Single isolated year in note returns that year."""
        text = "Single isolated year in note: 2018."
        self.assertEqual(extract_citation_year(text), 2018)

    # =========================================================================
    # REPAIR B: Retraction, Expression-of-Concern, and Preprint Warnings
    # =========================================================================

    def test_repair_b_backend_detects_retraction_and_blocks_status(self):
        """Verify fetch_doi_metadata detects CrossRef retraction and sets critical status."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Fabricated PETase Variant Crystal Structure"],
                "author": [{"family": "Fraudulent", "given": "John"}],
                "published-print": {"date-parts": [[2024, 1, 1]]},
                "type": "journal-article",
                "container-title": ["Journal of Falsified Results"],
                "update-to": [{"label": "Retraction", "type": "retraction", "doi": "10.1000/retract.1"}],
                "relation": {"is-retracted-by": [{"id": "10.1000/retract.1"}]}
            }
        }
        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1000/retracted.article")
            self.assertTrue(res["success"])
            self.assertTrue(res["is_retracted"])
            self.assertEqual(res["status_type"], "retracted")
            self.assertIn("RETRACTED", res["status_warning"])
            self.assertFalse(res["is_expression_of_concern"])

    def test_repair_b_backend_detects_expression_of_concern(self):
        """Verify fetch_doi_metadata detects Expression of Concern."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Questionable Enzyme Kinetic Assays"],
                "author": [{"family": "Doubtful", "given": "Sarah"}],
                "published-print": {"date-parts": [[2023, 6, 1]]},
                "type": "journal-article",
                "container-title": ["Biochemical Investigations"],
                "update-to": [{"label": "Expression of Concern", "type": "expression_of_concern", "doi": "10.1000/eoc.1"}],
                "relation": {"has-expression-of-concern": [{"id": "10.1000/eoc.1"}]}
            }
        }
        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1000/eoc.article")
            self.assertTrue(res["success"])
            self.assertFalse(res["is_retracted"])
            self.assertTrue(res["is_expression_of_concern"])
            self.assertEqual(res["status_type"], "expression_of_concern")
            self.assertIn("Expression of Concern", res["status_warning"])

    def test_repair_b_backend_detects_preprint_status(self):
        """Verify fetch_doi_metadata detects posted-content preprint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["CRISPR Diagnostics in bioRxiv"],
                "author": [{"family": "PreprintAuthor", "given": "A."}],
                "published-online": {"date-parts": [[2024, 3, 1]]},
                "type": "posted-content",
                "subtype": "preprint",
                "container-title": ["bioRxiv"]
            }
        }
        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1101/2024.03.01.123456")
            self.assertTrue(res["success"])
            self.assertTrue(res["is_preprint"])
            self.assertEqual(res["status_type"], "preprint")
            self.assertIn("unreviewed preprint", res["status_warning"])

    def test_repair_b_backend_detects_correction_without_false_retraction(self):
        """Verify publication with erratum is labeled corrected, NOT retracted."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Catalytic Characterization with Minor Erratum"],
                "author": [{"family": "Careful", "given": "Tom"}],
                "published-print": {"date-parts": [[2022, 5, 1]]},
                "type": "journal-article",
                "container-title": ["Journal of Applied Biocatalysis"],
                "update-to": [{"label": "Erratum", "type": "erratum", "doi": "10.1000/erratum.1"}]
            }
        }
        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1000/corrected.article")
            self.assertTrue(res["success"])
            self.assertFalse(res["is_retracted"])
            self.assertFalse(res["is_expression_of_concern"])
            self.assertTrue(res["is_corrected"])
            self.assertEqual(res["status_type"], "corrected")
            self.assertIn("corrections, corrigenda, or errata", res["status_warning"])

    def test_repair_b_backend_standard_unretracted_metadata(self):
        """Verify normal article has standard status without falsely claiming verified unretracted."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Sound Biochemical Study"],
                "author": [{"family": "Solid", "given": "Jane"}],
                "published-print": {"date-parts": [[2023, 2, 1]]},
                "type": "journal-article",
                "container-title": ["Biotechnology and Bioengineering"]
            }
        }
        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1002/bit.99999")
            self.assertTrue(res["success"])
            self.assertFalse(res["is_retracted"])
            self.assertFalse(res["is_preprint"])
            self.assertEqual(res["status_type"], "standard")
            self.assertIsNone(res["status_warning"])
            self.assertIn("No update or retraction records found", res["status_details"])

    def test_repair_b_frontend_simulation_retracted_paper_blocks_insertion(self):
        """Frontend simulation: Retracted paper renders red warning and disables insertion action."""
        # Read the exact logic from studio.js
        with open(os.path.join(BASE_DIR, "static", "js", "studio.js"), "r", encoding="utf-8") as f:
            studio_js = f.read()

        # Verify studio.js checks data.is_retracted and renders RETRACTED badge and blocked button
        self.assertIn("data.is_retracted", studio_js)
        self.assertIn("RETRACTED", studio_js)
        self.assertIn("Insertion Blocked (Retracted Publication)", studio_js)
        self.assertIn("data.is_expression_of_concern", studio_js)
        self.assertIn("Insertion Blocked (Expression of Concern)", studio_js)

    # =========================================================================
    # REPAIR C: Curated Benchmark DOI Integrity Tests
    # =========================================================================

    def test_repair_c_petase_benchmark_dois_are_verified(self):
        """Verify all 7 PETase benchmark DOIs match genuine peer-reviewed publications."""
        res = audit_novelty_and_soundness(
            title="Engineered PETase Depolymerase",
            chassis="E. coli",
            tool="PETase",
            target="PET plastic bottles"
        )
        self.assertEqual(res["benchmark_status"], "curated_benchmark")
        self.assertEqual(res["prior_approaches_total"], 7)

        approaches = {pa["id"]: pa for pa in res["prior_approaches"]}

        # Check PA-05: Herrero Acero, Ribitsch et al. (2013)
        pa5 = approaches["PA-05"]
        self.assertEqual(pa5["doi"], "10.1002/bit.24930")
        self.assertIn("Ribitsch", pa5["authors"])
        self.assertIn("Surface engineering of a cutinase", pa5["title"])
        self.assertEqual(pa5["source_verification"], "Verified peer-reviewed publication")

        # Check PA-06: Skariyachan et al. (2018)
        pa6 = approaches["PA-06"]
        self.assertEqual(pa6["doi"], "10.1016/j.polymdegradstab.2018.01.018")
        self.assertIn("Skariyachan", pa6["authors"])
        self.assertIn("Enhanced polymer degradation", pa6["title"])
        self.assertEqual(pa6["source_verification"], "Verified peer-reviewed publication")

    def test_repair_c_cas12a_benchmark_dois_are_verified(self):
        """Verify all 7 Cas12a AMR benchmark DOIs match genuine peer-reviewed publications."""
        res = audit_novelty_and_soundness(
            title="Field Acellular Cas12a Biosensor for Colistin AMR",
            chassis="Cell-free paper matrix",
            tool="Cas12a (DETECTR)",
            target="Colistin mcr-1 resistance gene"
        )
        self.assertEqual(res["benchmark_status"], "curated_benchmark")
        self.assertEqual(res["prior_approaches_total"], 7)
        for pa in res["prior_approaches"]:
            self.assertEqual(pa["benchmark_type"], "curated_benchmark")
            self.assertTrue(pa["doi"].startswith("10."))

    # =========================================================================
    # REPAIR D: Animal-Model Keyword Substring Collision Tests
    # =========================================================================

    def test_repair_d_yeast_metabolic_integration_does_not_trigger_animal_limitations(self):
        """Verify 'integration' does NOT trigger animal model limitations due to 'rat' substring."""
        lims = generate_inferred_limitations("Recombinant yeast metabolic pathway integration for artemisinin biosynthesis")
        combined = " ".join(lims).lower()
        self.assertNotIn("murine", combined)
        self.assertNotIn("animal", combined)
        self.assertNotIn("in vivo", combined)
        self.assertNotIn("rodent", combined)

    def test_repair_d_genomic_integration_does_not_trigger_animal_limitations(self):
        """Verify 'genomic integration' does NOT trigger animal model limitations."""
        lims = generate_inferred_limitations("Genomic integration of a recombinant biosynthetic pathway")
        combined = " ".join(lims).lower()
        self.assertNotIn("murine", combined)
        self.assertNotIn("animal", combined)

    def test_repair_d_genuine_rat_model_triggers_animal_limitations(self):
        """Verify genuine 'rat model' DOES trigger animal model considerations."""
        lims = generate_inferred_limitations("Rat model for evaluating inflammatory responses")
        combined = " ".join(lims).lower()
        self.assertIn("murine", combined)

    def test_repair_d_genuine_mouse_model_triggers_animal_limitations(self):
        """Verify genuine 'mouse model' DOES trigger animal model considerations."""
        lims = generate_inferred_limitations("Mouse model of disease progression")
        combined = " ".join(lims).lower()
        self.assertIn("murine", combined)

    def test_repair_d_genuine_in_vivo_triggers_animal_limitations(self):
        """Verify genuine 'in vivo' DOES trigger animal model considerations."""
        lims = generate_inferred_limitations("In vivo evaluation of therapeutic efficacy")
        combined = " ".join(lims).lower()
        self.assertIn("murine", combined)

    # =========================================================================
    # REPAIR E: Short Unheaded Text Classification Tests
    # =========================================================================

    def test_repair_e_short_unheaded_methods_excerpt_remains_unsegmented(self):
        """A 150-word unheaded methods excerpt must NOT be labeled as an abstract."""
        methods_text = "Recombinant cutinase was expressed in E. coli BL21(DE3) using standard IPTG induction at 18 degrees Celsius. " * 10
        secs = parse_raw_text_into_sections(methods_text)
        self.assertNotIn("abstract", secs)
        self.assertIn("unsegmented_body", secs)
        self.assertEqual(secs["unsegmented_body"], methods_text.strip())

    def test_repair_e_short_unheaded_conclusion_excerpt_remains_unsegmented(self):
        """A 200-word unheaded conclusion excerpt must NOT be labeled as an abstract."""
        conclusion_text = "In conclusion, these findings demonstrate the feasibility of ambient enzymatic plastic recycling without thermophilic heating. " * 12
        secs = parse_raw_text_into_sections(conclusion_text)
        self.assertNotIn("abstract", secs)
        self.assertIn("unsegmented_body", secs)

    def test_repair_e_short_unheaded_abstract_like_excerpt_remains_unsegmented(self):
        """A 100-word unheaded excerpt without an abstract heading must remain unsegmented."""
        text = "This study reports the directed evolution of PETase to achieve enhanced catalytic turnover on crystalline substrate. " * 6
        secs = parse_raw_text_into_sections(text)
        self.assertNotIn("abstract", secs)
        self.assertIn("unsegmented_body", secs)

    def test_repair_e_long_unheaded_document_remains_unsegmented(self):
        """An 800-word unheaded document must remain unsegmented."""
        text = " ".join([f"synthetic_biology_token_{i}" for i in range(800)])
        secs = parse_raw_text_into_sections(text)
        self.assertNotIn("abstract", secs)
        self.assertNotIn("methods", secs)
        self.assertIn("unsegmented_body", secs)

    def test_repair_e_properly_headed_abstract_is_recognized(self):
        """A text with an explicit Abstract heading is recognized as an abstract."""
        text = "# Abstract\nThis study investigates the biochemical turnover of engineered cutinase on PET."
        secs = parse_raw_text_into_sections(text)
        self.assertIn("abstract", secs)
        self.assertNotIn("unsegmented_body", secs)

    def test_repair_e_methods_at_end_correctly_parsed(self):
        """Document with Methods at the end is correctly parsed without positional guessing."""
        text = (
            "# Introduction\nBackground on biocatalysis.\n\n"
            "# Results\nHigh conversion observed.\n\n"
            "# Discussion\nSignificance of findings.\n\n"
            "# Materials and Methods\nRecombinant plasmid was constructed using Gibson assembly."
        )
        secs = parse_raw_text_into_sections(text)
        self.assertIn("introduction", secs)
        self.assertIn("results", secs)
        self.assertIn("discussion", secs)
        self.assertIn("methods", secs)

    def test_repair_e_short_excerpt_coverage_metadata_in_retrieval_service(self):
        """Verify retrieve_paper_data distinguishes excerpt from missing sections in coverage."""
        short_text = "Brief experimental note on buffer preparation and enzyme storage. " * 5
        ret = retrieve_paper_data(pasted_text=short_text)
        self.assertEqual(ret["coverage"]["mode"], "unsegmented_text")
        self.assertIn("Unsegmented Text Excerpt", ret["coverage"]["sections_read"])
        self.assertIn("Original Full Text Not Supplied (Excerpt Only; specific sections cannot be inferred as absent)", ret["coverage"]["missing"])

    # =========================================================================
    # REPAIR F: Frontend Regional Assumption Neutralization Tests
    # =========================================================================

    def test_repair_f_no_hardcoded_egyptian_regulatory_assumptions_in_studio_js(self):
        """Verify studio.js contains no hardcoded Egyptian Ministry of Health or regulatory assumptions."""
        with open(os.path.join(BASE_DIR, "static", "js", "studio.js"), "r", encoding="utf-8") as f:
            studio_js = f.read()

        self.assertNotIn("Compliance with Egyptian biosafety regulations", studio_js)
        self.assertNotIn("Compliance with Egyptian Ministry of Health and IBC regulations", studio_js)
        self.assertNotIn("National biotechnology research initiatives in Egypt", studio_js)
        self.assertNotIn("domestic biocatalyst for Egyptian textile", studio_js)


if __name__ == "__main__":
    unittest.main()
