"""
BioWriter Studio — Phase 4.1 Scientific Integrity & Research Quality Test Suite.
Validates the targeted remediation of:
- Task 4.1.1: Removal of fabricated prior-art references (Smith, Wang, Johnson) & domain classification safeguards
- Task 4.1.2: Repair of document sectioning (elimination of arbitrary 20/25/30/25% word slicing)
- Task 4.1.3: Elimination of PETase plastic depolymerization fallback bias in paper analyst
- Task 4.1.4: Elimination of page-number regex collisions in bibliography recency auditor
- Task 4.1.5: Preprint (posted-content) and Crossmark retraction/correction status verification
- Task 4.1.6: Elimination of hardcoded regional regulatory assumptions (Egyptian Ministry of Health)
"""

import os
import sys
import unittest
import tempfile
import shutil
from typing import Dict, Any

# Ensure upload directory is on path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.impact_novelty_engine import audit_novelty_and_soundness
from core.retrieval_service import parse_raw_text_into_sections, retrieve_paper_data
from core.paper_analyst_llm import generate_inferred_limitations
from core.reference_service import audit_bibliography_recency, fetch_doi_metadata


class TestPhase41ScientificIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="biowriter_test_phase4_1_")
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
    # Task 4.1.1: Prior-Art Integrity & Domain Selection Safeguards
    # =========================================================================

    def test_non_crispr_non_petase_yeast_proposal_has_no_fabricated_references(self):
        """Verify yeast metabolic engineering does NOT generate fake Smith/Wang citations."""
        res = audit_novelty_and_soundness(
            title="Artemisinin Biosynthesis in Baker's Yeast",
            chassis="Saccharomyces cerevisiae",
            tool="Golden Gate Assembly",
            target="Artemisinic acid",
            hypothesis="Reconstructing the amorpha-4,11-diene pathway enables high titer because flux is diverted from squalene.",
            methodology="Multi-gene pathway integration. Negative control: untransformed yeast. Positive control: wild-type strain."
        )
        self.assertEqual(res["benchmark_status"], "no_benchmark")
        self.assertEqual(res["prior_approaches_total"], 0)
        self.assertEqual(res["prior_approaches"], [])
        self.assertIsNone(res["closest_approach"])
        self.assertIn("No verified pre-curated benchmark is currently available", res["benchmark_message"])
        self.assertIn("No verified pre-curated benchmark is currently available", res["differentiation_summary"])

        # Assert no fabricated authors/titles exist
        combined_text = str(res)
        for fake_author in ["Smith et al.", "Wang et al.", "Johnson et al.", "Patel et al."]:
            self.assertNotIn(fake_author, combined_text)

    def test_plant_prime_editing_not_misclassified_as_cas12a_diagnostic(self):
        """Verify plant prime editing proposal with Cas9 nickase is NOT classified as acellular Cas12a AMR diagnostic."""
        res = audit_novelty_and_soundness(
            title="Precision Prime Editing in Rice for Herbicide Resistance",
            chassis="Oryza sativa",
            tool="Prime Editor 2 (PE2)",
            target="OsALS gene",
            hypothesis="Engineered SpCas9 nickase fused to reverse transcriptase introduces targeted point mutations because pegRNA primes reverse transcription.",
            methodology="Deliver PE2 construct into rice protoplasts. Negative control: mock transfection. Positive control: standard Cas9 nuclease."
        )
        # Must NOT match acellular Cas12a AMR diagnostic benchmark
        self.assertEqual(res["benchmark_status"], "no_benchmark")
        self.assertEqual(res["prior_approaches"], [])
        self.assertNotIn("colistin", str(res).lower())
        self.assertNotIn("mcr-1", str(res).lower())
        self.assertNotIn("Acellular Point-of-Care", str(res))

    def test_lignin_valorization_not_misclassified_as_petase(self):
        """Verify lignin valorization proposal is NOT misclassified into PETase plastic benchmark."""
        res = audit_novelty_and_soundness(
            title="Engineered Laccase for Lignin Depolymerization",
            chassis="Pseudomonas putida",
            tool="Engineered Laccase",
            target="Lignin aromatic oligomers",
            hypothesis="Directed evolution of laccase active site enhances oxidative cleavage because redox potential is shifted.",
            methodology="Biochemical turnover assays. Negative control: buffer only. Positive control: commercial laccase."
        )
        self.assertEqual(res["benchmark_status"], "no_benchmark")
        self.assertEqual(res["prior_approaches"], [])
        self.assertNotIn("Tournier", str(res))
        self.assertNotIn("Austin", str(res))

    def test_legitimate_petase_curated_benchmark_verification(self):
        """Verify legitimate PETase proposal loads verified, curated benchmark with traceable DOIs."""
        res = audit_novelty_and_soundness(
            title="Engineered Ambient PETase for Plastic Bottle Upcycling",
            chassis="Escherichia coli",
            tool="PETase",
            target="PET plastic bottles",
            hypothesis="Engineered salt bridges stabilize the flexible beta-sheet because electrostatic bonds increase Tm.",
            methodology="Enzyme expression induced with IPTG. Negative control: empty vector. Positive control: wild-type enzyme."
        )
        self.assertEqual(res["benchmark_status"], "curated_benchmark")
        self.assertEqual(res["prior_approaches_total"], 7)
        self.assertEqual(len(res["prior_approaches"]), 7)

        # Check traceable source verification and DOIs
        pa1 = res["prior_approaches"][0]
        self.assertEqual(pa1["id"], "PA-01")
        self.assertEqual(pa1["authors"], "Austin et al. (PNAS 2018)")
        self.assertEqual(pa1["doi"], "10.1073/pnas.1718804115")
        self.assertEqual(pa1["benchmark_type"], "curated_benchmark")
        self.assertEqual(pa1["source_verification"], "Verified peer-reviewed publication")

        pa2 = res["prior_approaches"][1]
        self.assertEqual(pa2["authors"], "Tournier et al. (Nature 2020)")
        self.assertEqual(pa2["doi"], "10.1038/s41586-020-2149-4")

        # Regional neutrality check
        self.assertNotIn("Egyptian runoff matrix", pa1["differentiation"])

    def test_legitimate_cas12a_diagnostic_curated_benchmark_verification(self):
        """Verify legitimate acellular Cas12a AMR diagnostic proposal loads curated benchmark."""
        res = audit_novelty_and_soundness(
            title="Acellular Cas12a Field Biosensor for Colistin AMR Surveillance",
            chassis="Cell-free paper matrix",
            tool="Cas12a (DETECTR)",
            target="Colistin mcr-1 resistance gene",
            hypothesis="Trans-cleavage unleashes fluorophore signal upon target duplexing because of indiscriminate single-stranded DNase activity.",
            methodology="RPA coupled with Cas12a. Negative control: non-targeting crRNA. Positive control: purified synthetic target amplicon."
        )
        self.assertEqual(res["benchmark_status"], "curated_benchmark")
        self.assertEqual(res["prior_approaches_total"], 7)
        pa2 = res["prior_approaches"][1]
        self.assertEqual(pa2["authors"], "Chen et al. (Science 2018)")
        self.assertEqual(pa2["doi"], "10.1126/science.aar6245")

    def test_ambiguous_proposal_suspends_automated_benchmark(self):
        """Verify proposal with multiple conflicting tool domains triggers ambiguous_domain."""
        res = audit_novelty_and_soundness(
            title="Dual PETase Plastic Degradation and Cas12a AMR Diagnostic",
            chassis="Cell-free lysate",
            tool="PETase and Cas12a",
            target="PET plastic bottles and colistin mcr-1 gene",
            hypothesis="Dual functional platform accomplishes both tasks because enzymes are modular.",
            methodology="Standard assays with negative and positive controls."
        )
        self.assertEqual(res["benchmark_status"], "ambiguous_domain")
        self.assertEqual(res["prior_approaches"], [])
        self.assertIn("Ambiguous or multi-domain proposal detected", res["benchmark_message"])

    def test_novelty_caveat_truthfulness(self):
        """Verify caveat does not claim literature search when no external search took place."""
        res_no_bm = audit_novelty_and_soundness(
            title="Biofuel Production",
            chassis="Algae",
            tool="Overexpression",
            target="Lipids"
        )
        self.assertNotIn("This assessment is based on searched peer-reviewed literature", res_no_bm["caveat"])
        self.assertIn("Prior-art radar reflects only verified pre-curated benchmark sets", res_no_bm["caveat"])

    # =========================================================================
    # Task 4.1.2: Document Sectioning Integrity (Retrieval Service)
    # =========================================================================

    def test_unheaded_text_does_not_fabricate_percentage_sections(self):
        """Verify text lacking headings is NOT split into arbitrary 20/25/30/25% sections."""
        raw_text = " ".join([f"biowriter_word_{i}" for i in range(800)])
        secs = parse_raw_text_into_sections(raw_text)

        # Must NOT fabricate methods, results, or discussion
        self.assertNotIn("methods", secs)
        self.assertNotIn("results", secs)
        self.assertNotIn("discussion", secs)
        self.assertNotIn("introduction", secs)

        # Must store as unsegmented body
        self.assertIn("unsegmented_body", secs)
        self.assertEqual(secs["unsegmented_body"], raw_text)

    def test_headed_markdown_text_parses_sections_correctly(self):
        """Verify text with genuine headings correctly parses into structured sections."""
        headed_text = (
            "# Introduction\nBackground on agricultural traits.\n\n"
            "## Materials and Methods\nMarker-assisted backcrossing was performed.\n\n"
            "## Results\nSalt tolerance was increased significantly.\n\n"
            "## Discussion\nImplications for global food security."
        )
        secs = parse_raw_text_into_sections(headed_text)
        self.assertIn("introduction", secs)
        self.assertIn("methods", secs)
        self.assertIn("results", secs)
        self.assertIn("discussion", secs)

    def test_retrieval_service_unsegmented_mode_and_coverage(self):
        """Verify retrieve_paper_data correctly assigns unsegmented_text mode and missing flags."""
        raw_text = " ".join([f"paragraph_word_{i}" for i in range(500)])
        ret = retrieve_paper_data(pasted_text=raw_text)
        self.assertEqual(ret["coverage"]["mode"], "unsegmented_text")
        self.assertIn("Unsegmented Body Text", ret["coverage"]["sections_read"])
        self.assertIn("Structured Methods", ret["coverage"]["missing"])

    # =========================================================================
    # Task 4.1.3: Elimination of Inferred Limitations Domain Fallback Bias
    # =========================================================================

    def test_inferred_limitations_enzyme_paper_does_not_get_petase_limitations(self):
        """Verify enzyme engineering / lignin paper does NOT receive PETase crystallinity limitations."""
        lims = generate_inferred_limitations("Engineered laccase biocatalysis for lignin valorization")
        self.assertEqual(len(lims), 3)
        combined = " ".join(lims).lower()
        self.assertNotIn("crystallinity", combined)
        self.assertNotIn("depolymerization", combined)
        self.assertIn("enzyme", combined)

    def test_inferred_limitations_unknown_domain_returns_transparent_message(self):
        """Verify unclassified research model returns honest limitation message rather than PETase."""
        lims = generate_inferred_limitations("Quantum dot biosensing in marine sediments")
        self.assertEqual(len(lims), 2)
        combined = " ".join(lims).lower()
        self.assertNotIn("crystallinity", combined)
        self.assertNotIn("depolymerization", combined)
        self.assertIn("could not be automatically determined", combined)

    def test_inferred_limitations_petase_model_retains_plastic_limitations(self):
        """Verify PETase / plastic model still receives relevant depolymerization limitations."""
        lims = generate_inferred_limitations("Engineered PETase plastic bottle degradation")
        self.assertEqual(len(lims), 3)
        combined = " ".join(lims).lower()
        self.assertIn("crystallinity", combined)

    # =========================================================================
    # Task 4.1.4: Bibliography Recency Regex Collision Fix
    # =========================================================================

    def test_recency_auditor_rejects_page_number_year_collision(self):
        """Verify 1995 citation with page numbers 2021-2025 is correctly parsed as 1995 (non-recent)."""
        ref_text = "Doe, J. Historical perspectives on microbial fermentation. Journal of Biotechnology, 14(2), pp. 2021-2025 (1995)."
        res = audit_bibliography_recency(ref_text)
        self.assertEqual(res["total_count"], 1)
        self.assertEqual(res["recent_count"], 0)
        self.assertEqual(res["recency_percentage"], 0.0)
        parsed_ref = res["references"][0]
        self.assertEqual(parsed_ref["year"], 1995)
        self.assertFalse(parsed_ref["is_recent"])

    def test_recency_auditor_handles_standard_citations_and_author_date(self):
        """Verify recent and non-recent citations in various formats."""
        refs = [
            "Austin et al. (2018) PNAS 115(19):E4350.",
            "Tournier et al. (2020) Nature 580:216-219.",
            "Zhang et al. (2024) Targeted mutagenesis in maize. Nature Plants, 10, 112-120.",
            "Patel & Rao (2023) Metabolic engineering of yeast. Biotechnology Bioeng, 120, 45-56.",
            "Yoshida et al., 2022. Structural insights. ACS Catalysis, 12, 890-900."
        ]
        res = audit_bibliography_recency(refs)
        self.assertEqual(res["total_count"], 5)
        self.assertEqual(res["recent_count"], 3)  # 2024, 2023, 2022 are in 2021-2026
        self.assertEqual(res["recency_percentage"], 60.0)
        self.assertTrue(res["passed_rubric"])

    # =========================================================================
    # Task 4.1.5: Preprint and Retraction Integrity Verification
    # =========================================================================

    def test_doi_metadata_structure_has_preprint_and_retraction_fields(self):
        """Verify fetch_doi_metadata handles invalid DOIs gracefully without crashing."""
        res = fetch_doi_metadata("not-a-valid-doi")
        self.assertFalse(res["success"])
        self.assertIn("Invalid DOI format", res["error"])

    def test_doi_metadata_detects_preprint_status(self):
        """Verify fetch_doi_metadata detects posted-content as preprint and sets advisory notice."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["A novel bioRxiv study on CRISPR"],
                "author": [{"family": "Smith", "given": "John"}],
                "published-online": {"date-parts": [[2024, 5, 1]]},
                "type": "posted-content",
                "subtype": "preprint",
                "container-title": ["bioRxiv"]
            }
        }

        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1101/2024.05.01.123456")
            self.assertTrue(res["success"])
            self.assertTrue(res["is_preprint"])
            self.assertEqual(res["publication_type"], "preprint")
            self.assertFalse(res["is_retracted"])
            self.assertIn("unreviewed preprint", res["status_warning"])

    def test_doi_metadata_detects_retraction_status(self):
        """Verify fetch_doi_metadata detects Crossmark retraction and sets critical warning."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "title": ["Retracted Study on Polymer Hydrolases"],
                "author": [{"family": "Doe", "given": "Jane"}],
                "published-print": {"date-parts": [[2020, 1, 1]]},
                "type": "journal-article",
                "container-title": ["Journal of Biocatalysis"],
                "update-to": [
                    {"label": "Retraction", "type": "retraction", "doi": "10.1000/retraction.notice"}
                ]
            }
        }

        with patch("requests.get", return_value=mock_resp):
            res = fetch_doi_metadata("10.1000/retracted.study")
            self.assertTrue(res["success"])
            self.assertFalse(res["is_preprint"])
            self.assertTrue(res["is_retracted"])
            self.assertIn("RETRACTED", res["status_warning"])

    # =========================================================================
    # Task 4.1.6: Regional Regulatory Assumption Neutralization
    # =========================================================================

    def test_regulatory_neutrality_in_novelty_engine(self):
        """Verify no hardcoded Egyptian Ministry of Health assumption exists in novelty engine outputs."""
        for tool_name in ["PETase", "Cas12a", "Laccase"]:
            res = audit_novelty_and_soundness(title="Test", chassis="E. coli", tool=tool_name)
            self.assertNotIn("Egyptian Ministry of Health", str(res))
            self.assertNotIn("Egyptian runoff matrix", str(res))


if __name__ == "__main__":
    unittest.main()
