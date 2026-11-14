"""
BioWriter Studio - Phase 4.1.10 Scientific Integrity, Concurrency, and Cache Safety Test Suite
Target Project: upload/
Execution Mode: TARGETED IMPLEMENTATION VERIFICATION WITH STRICT DATA PROTECTION

Validates:
- Repair A: Faculty Feedback Concurrency, Versioning, and Atomic Write Protocol (dispatch_faculty_feedback)
- Repair B: CitationStatusCache Deep Copy and Internal Reference Isolation (cache.copy())
- Repair C: Animal Model Context Heuristics: Disambiguation of Descriptive Noun Phrases and Separated Verb-Preposition Syntax
"""

import os
import sys
import copy
import json
import time
import tempfile
import shutil
import unittest
import threading
from typing import Dict, Any

# Ensure test isolation: Set BIOWRITER_DATA_DIR to a temporary directory before importing app modules
_TEST_DATA_DIR = tempfile.mkdtemp(prefix="biowriter_test_phase4_1_10_")
os.environ["BIOWRITER_DATA_DIR"] = _TEST_DATA_DIR

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.draft_store import (
    save_student_draft,
    get_student_draft,
    toggle_draft_lock,
    dispatch_faculty_feedback,
    draft_store_lock,
    compute_draft_fingerprint,
    sanitize_student_id,
    get_drafts_dir
)
from core.reference_service import (
    CitationStatusCache,
    DEFAULT_CACHE_TTL,
    _CITATION_STATUS_CACHE,
    normalize_doi
)
from core.paper_analyst_llm import (
    analyze_animal_model_context,
    generate_inferred_limitations
)


def tearDownModule():
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)


class TestRepairAFacultyFeedbackConcurrency(unittest.TestCase):
    """
    Repair A: Faculty feedback dispatch synchronization, atomic write, and versioning.
    Verifies that dispatch_faculty_feedback():
    1. Uses draft_store_lock to serialize concurrent access.
    2. Atomically updates the draft via _atomic_write_draft.
    3. Increments draft version and recomputes content_fingerprint.
    4. Preserves all student proposal contents, references, validation, and submission lock state.
    5. Returns formatted feedback with accurate timestamp and updated version.
    """

    def setUp(self):
        self.student_id = "STU_P4110_TEST"
        self.initial_data = {
            "title": "Engineering High-Fidelity Cas12a Orthologs",
            "abstract": "We develop novel engineered CRISPR nucleases with enhanced specificity.",
            "specific_aims": "Aim 1: Mutagenesis screen. Aim 2: Off-target profiling.",
            "references": "10.1038/nature12345\n10.1126/science.abc1234",
            "version": 1,
            "is_locked_for_grading": False,
            "citation_validation": {
                "has_retracted": False,
                "has_expression_of_concern": False,
                "verified_at": "2026-11-14 12:00:00"
            }
        }
        res = save_student_draft(self.student_id, self.initial_data)
        self.assertTrue(res.get("success"), f"Setup draft save failed: {res}")

    def test_a01_feedback_dispatch_preserves_content_and_increments_version(self):
        """Dispatched feedback must preserve proposal fields and increment version."""
        feedback = {
            "instructor": "Dr. Rosalind Franklin",
            "score": 96,
            "comments": "Rigorous experimental plan and excellent control design.",
            "standing": "Honors"
        }
        res = dispatch_faculty_feedback(self.student_id, feedback)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("version"), 2)
        self.assertEqual(res.get("student_id"), self.student_id)

        draft = get_student_draft(self.student_id)
        self.assertIsNotNone(draft)
        self.assertEqual(draft.get("version"), 2)
        self.assertEqual(draft.get("title"), self.initial_data["title"])
        self.assertEqual(draft.get("abstract"), self.initial_data["abstract"])
        self.assertEqual(draft.get("specific_aims"), self.initial_data["specific_aims"])
        self.assertEqual(draft.get("references"), self.initial_data["references"])
        self.assertEqual(draft.get("citation_validation"), self.initial_data["citation_validation"])

        # Check faculty review attached
        fr = draft.get("faculty_review")
        self.assertIsNotNone(fr)
        self.assertEqual(fr.get("instructor"), "Dr. Rosalind Franklin")
        self.assertEqual(fr.get("score"), 96)
        self.assertIn("dispatched_at", fr)

    def test_a02_feedback_dispatch_preserves_submission_lock_state(self):
        """Locked proposal must retain is_locked_for_grading and locked_at after feedback dispatch."""
        lock_res = toggle_draft_lock(self.student_id, True)
        self.assertTrue(lock_res.get("success"))
        v_locked = lock_res.get("version")

        locked_draft = get_student_draft(self.student_id)
        self.assertTrue(locked_draft.get("is_locked_for_grading"))
        self.assertIsNotNone(locked_draft.get("locked_at"))

        fb = {"instructor": "Prof. Smith", "grade": "A"}
        res = dispatch_faculty_feedback(self.student_id, fb)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("version"), v_locked + 1)

        updated_draft = get_student_draft(self.student_id)
        self.assertTrue(updated_draft.get("is_locked_for_grading"))
        self.assertEqual(updated_draft.get("locked_at"), locked_draft.get("locked_at"))
        self.assertEqual(updated_draft.get("faculty_review", {}).get("grade"), "A")

    def test_a03_feedback_dispatch_recomputes_fingerprint(self):
        """Content fingerprint should be updated or maintained consistently after dispatch."""
        draft_before = get_student_draft(self.student_id)
        fp_before = draft_before.get("content_fingerprint")

        fb = {"notes": "Approved with revisions."}
        dispatch_faculty_feedback(self.student_id, fb)

        draft_after = get_student_draft(self.student_id)
        fp_after = draft_after.get("content_fingerprint")
        self.assertIsNotNone(fp_after)
        self.assertEqual(fp_after, compute_draft_fingerprint(draft_after))

    def test_a04_nonexistent_student_returns_error(self):
        """Dispatching feedback for a non-existent student must cleanly return failure."""
        res = dispatch_faculty_feedback("NON_EXISTENT_STU_999", {"score": 50})
        self.assertFalse(res.get("success"))
        self.assertIn("not found", res.get("error", "").lower())

    def test_a05_invalid_student_id_rejected(self):
        """Empty or invalid student IDs must be safely rejected."""
        res_empty = dispatch_faculty_feedback("", {"score": 50})
        self.assertFalse(res_empty.get("success"))
        res_default = dispatch_faculty_feedback("student_draft", {"score": 50})
        self.assertFalse(res_default.get("success"))

    def test_a06_reentrant_lock_safety(self):
        """Calling dispatch_faculty_feedback while holding draft_store_lock must not deadlock."""
        clean_id = sanitize_student_id(self.student_id)
        with draft_store_lock(clean_id):
            res = dispatch_faculty_feedback(clean_id, {"grade": "Pass"})
            self.assertTrue(res.get("success"))

        draft = get_student_draft(clean_id)
        self.assertEqual(draft.get("faculty_review", {}).get("grade"), "Pass")

    def test_a07_concurrent_student_save_and_faculty_dispatch(self):
        """Concurrent saves and feedback dispatches for the same student must serialize safely."""
        num_threads = 8
        errors = []

        def worker_save(idx):
            try:
                save_student_draft(self.student_id, {"title": f"Title iteration {idx}"})
            except Exception as e:
                errors.append(f"Save error {idx}: {e}")

        def worker_dispatch(idx):
            try:
                dispatch_faculty_feedback(self.student_id, {"review_id": idx, "score": 90 + idx})
            except Exception as e:
                errors.append(f"Dispatch error {idx}: {e}")

        threads = []
        for i in range(num_threads):
            threads.append(threading.Thread(target=worker_save, args=(i,)))
            threads.append(threading.Thread(target=worker_dispatch, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent thread errors: {errors}")
        final_draft = get_student_draft(self.student_id)
        self.assertIsNotNone(final_draft)
        self.assertGreater(final_draft.get("version", 0), 1)

    def test_a08_atomic_write_file_integrity(self):
        """Draft JSON on disk must remain valid and parseable even under rapid feedback dispatch."""
        for i in range(5):
            res = dispatch_faculty_feedback(self.student_id, {"round": i, "score": 80 + i})
            self.assertTrue(res.get("success"))

        clean_id = sanitize_student_id(self.student_id)
        filepath = os.path.join(get_drafts_dir(), f"{clean_id}.json")
        self.assertTrue(os.path.exists(filepath))

        with open(filepath, "r", encoding="utf-8") as f:
            disk_data = json.load(f)

        self.assertEqual(disk_data.get("faculty_review", {}).get("round"), 4)
        self.assertEqual(disk_data.get("faculty_review", {}).get("score"), 84)


class TestRepairBCitationStatusCacheCopy(unittest.TestCase):
    """
    Repair B: CitationStatusCache deep copy and internal mutation isolation.
    Verifies:
    1. cache.copy() returns a CitationStatusCache instance.
    2. Deep copies entry dictionaries so mutating values in copy never leaks into source cache.
    3. Copying evicts expired entries cleanly.
    4. Timestamps dictionary is cloned independently.
    5. __copy__ and __deepcopy__ work identically.
    """

    def setUp(self):
        self.cache = CitationStatusCache(max_size=50, ttl=3600.0)
        self.cache["10.1000/nature_001"] = {
            "success": True,
            "title": "Crispr Cas12a Advances",
            "is_retracted": False,
            "metadata": {"authors": ["Doudna", "Charpentier"], "citations": 500}
        }
        self.cache["10.1000/science_002"] = {
            "success": True,
            "title": "Gene Editing Precision",
            "is_retracted": True,
            "metadata": {"authors": ["Zhang"], "citations": 320}
        }

    def test_b01_copy_returns_citation_status_cache_instance(self):
        """cache.copy() must return a valid CitationStatusCache instance with identical configuration."""
        copied = self.cache.copy()
        self.assertIsInstance(copied, CitationStatusCache)
        self.assertEqual(copied.max_size, self.cache.max_size)
        self.assertEqual(copied.ttl, self.cache.ttl)
        self.assertEqual(len(copied), 2)

    def test_b02_mutating_copied_entry_does_not_mutate_original(self):
        """Mutating values in the copied cache must NOT affect the original cache entries."""
        copied = self.cache.copy()

        # Modify top-level and nested fields in the copy
        copied["10.1000/nature_001"]["title"] = "COMPLETELY MUTATED TITLE"
        copied["10.1000/nature_001"]["is_retracted"] = True
        copied["10.1000/nature_001"]["metadata"]["citations"] = 999999

        # Verify original in-memory cache remains unchanged
        orig = self.cache.get("10.1000/nature_001")
        self.assertEqual(orig["title"], "Crispr Cas12a Advances")
        self.assertFalse(orig["is_retracted"])
        self.assertEqual(orig["metadata"]["citations"], 500)

        # Verify dict-access on original is also unchanged
        orig_dict_val = self.cache["10.1000/nature_001"]
        self.assertEqual(orig_dict_val["title"], "Crispr Cas12a Advances")

    def test_b03_modifying_original_does_not_affect_existing_copy(self):
        """Updating original cache after copy() must not mutate the previously created copy."""
        copied = self.cache.copy()
        self.cache["10.1000/nature_001"] = {
            "success": True,
            "title": "Fresh Title From Network",
            "is_retracted": False
        }

        self.assertEqual(copied["10.1000/nature_001"]["title"], "Crispr Cas12a Advances")

    def test_b04_copy_evicts_expired_entries(self):
        """cache.copy() must evict expired items prior to returning the deep copy."""
        short_cache = CitationStatusCache(max_size=10, ttl=0.1)
        short_cache["10.1000/live"] = {"success": True, "title": "Live Item"}
        short_cache["10.1000/expired"] = {"success": True, "title": "Expired Item"}

        # Artificially age the expired item
        short_cache._timestamps["10.1000/expired"] = time.time() - 100.0

        copied = short_cache.copy()
        self.assertIn("10.1000/live", copied)
        self.assertNotIn("10.1000/expired", copied)

    def test_b05_copy_clones_timestamps_independently(self):
        """Modifying timestamps on copied cache must not affect original timestamps."""
        copied = self.cache.copy()
        copied._timestamps["10.1000/nature_001"] = 0.0

        self.assertNotEqual(self.cache._timestamps["10.1000/nature_001"], 0.0)
        self.assertFalse(self.cache.is_expired("10.1000/nature_001"))

    def test_b06_standard_copy_and_deepcopy_compatibility(self):
        """copy.copy() and copy.deepcopy() should invoke cache.copy() safely."""
        c1 = copy.copy(self.cache)
        c2 = copy.deepcopy(self.cache)

        self.assertIsInstance(c1, CitationStatusCache)
        self.assertIsInstance(c2, CitationStatusCache)

        c1["10.1000/nature_001"]["title"] = "c1 mutation"
        c2["10.1000/nature_001"]["title"] = "c2 mutation"

        self.assertEqual(self.cache.get("10.1000/nature_001")["title"], "Crispr Cas12a Advances")


class TestRepairCAnimalModelContextNLP(unittest.TestCase):
    """
    Repair C: Animal Model Context Disambiguation & Complex Syntax.
    Verifies:
    1. Descriptive noun phrases ("Animal models are interesting.") return 'ambiguous' (NOT 'performed').
    2. Separated verb-preposition phrases ("Earlier studies evaluated cell culture, whereas we tested the formulation in mice.") return 'performed'.
    3. All 32 baseline/adversarial cases from Phase 4.1.8 remain 100% compliant.
    4. Additional adversarial cases with diverse sentence structures, negation, and non-rodent species.
    """

    def test_c01_target_f03_descriptive_noun_phrase_not_performed(self):
        """Descriptive noun phrases without execution verbs must return 'ambiguous' rather than 'performed'."""
        descriptive_cases = [
            "Animal models are interesting.",
            "Animal models provide valuable biological context.",
            "Animal models have both strengths and limitations.",
            "Rodent models are commonly discussed in immunological papers.",
            "Zebrafish assays represent an emerging model system."
        ]
        for text in descriptive_cases:
            res = analyze_animal_model_context(text)
            status = res.get("status")
            self.assertEqual(
                status, "ambiguous",
                f"Descriptive statement '{text}' must be 'ambiguous', got '{status}'."
            )

    def test_c02_target_f03_separated_verb_preposition_is_performed(self):
        """Separated action verb and preposition ('we tested the formulation in mice') must be classified as 'performed'."""
        executed_cases = [
            "Earlier studies evaluated cell culture, whereas we tested the formulation in mice.",
            "The authors tested the lipid nanoparticles in mice.",
            "Our laboratory evaluated systemic toxicity in rats.",
            "We investigated therapeutic efficacy in rodent models.",
            "The team administered the synthetic conjugate to rabbits."
        ]
        for text in executed_cases:
            res = analyze_animal_model_context(text)
            status = res.get("status")
            self.assertEqual(
                status, "performed",
                f"Separated verb phrase '{text}' must be 'performed', got '{status}'."
            )

    def test_c03_all_32_regression_cases_from_phase4_1_8(self):
        """All 32 test cases from Phase 4.1.8 must maintain 100% compliance."""
        cases = [
            # Required 12 baseline cases:
            ("Req-01", "The study used a non-animal model.", "excluded"),
            ("Req-02", "The study used a non-animal system for testing.", "excluded"),
            ("Req-03", "The paper discusses animal models, but does not use them.", "excluded"),
            ("Req-04", "Previous studies used mice, but we did not use them in this investigation.", "excluded"),
            ("Req-05", "Animal experiments were not performed in this study.", "excluded"),
            ("Req-06", "Future studies will investigate the formulation in mice.", "future_work"),
            ("Req-07", "The current study administered the compound to rats.", "performed"),
            ("Req-08", "Animal models were discussed in the introduction only.", "background_only"),
            ("Req-09", "The current study used in vitro assays, while cited studies used animal models.", "background_only"),
            ("Req-10", "The study used mice for pharmacokinetic analysis but excluded other animal experiments.", "mixed"),
            ("Req-11", "No animal models were used, although the introduction discusses previous animal studies.", "excluded"),
            ("Req-12", "The study used a mouse model.", "performed"),

            # Phase 4.1.7 Adversarial cases:
            ("Adv-13", "It cannot be denied that animal models were used.", "performed"),
            ("Adv-14", "We developed a non-animal assay for high-throughput screening.", "excluded"),
            ("Adv-15", "The formulation was administered to New Zealand white rabbits.", "performed"),
            ("Adv-16", "In vivo zebrafish assays were conducted.", "performed"),
            ("Adv-17", "Although early drafts planned in vivo studies, ultimately no animal experiments were performed.", "excluded"),
            ("Adv-18", "Reactions were performed with purified recombinant enzymes in 384-well plates.", "none"),
            ("Adv-19", "Efficacy in rodent models will be evaluated in future work.", "future_work"),
            ("Adv-20", "The study mentions in vivo validation, but did not perform it.", "excluded"),

            # Phase 4.1.8 Required Cases:
            ("New-21", "Zebrafish will be used in future experiments.", "future_work"),
            ("New-22", "Rabbit models are discussed in previous literature only.", "background_only"),
            ("New-23", "No animal experiments were performed.", "excluded"),
            ("New-24", "The study used mice, but rabbit experiments are planned for future work.", "mixed"),
            ("New-25", "Non-animal models were used.", "excluded"),
            ("New-26", "Danio rerio larvae were treated with varying inhibitor concentrations.", "performed"),
            ("New-27", "Danio rerio models will be investigated in subsequent trials.", "future_work"),
            ("New-28", "Previous literature cited rabbit models, while our laboratory employed Danio rerio.", "mixed"),
            ("New-29", "Experiments in rabbits were omitted due to ethical alternatives.", "excluded"),
            ("New-30", "We plan to test the compound in zebrafish embryos.", "future_work"),
            ("New-31", "A New Zealand white rabbit model was utilized for ocular pharmacokinetics.", "performed"),
            ("New-32", "Neither rats nor rabbits were employed in this investigation.", "excluded"),
        ]

        passed = 0
        failures = []
        for cid, text, expected in cases:
            res = analyze_animal_model_context(text)
            status = res.get("status")
            ok = (status == expected) or (expected in ["excluded", "background_only"] and status in ["excluded", "background_only"])
            if ok:
                passed += 1
            else:
                failures.append((cid, text, expected, status))

        self.assertEqual(len(failures), 0, f"Animal model regressions ({len(failures)}/{len(cases)}): {failures}")
        self.assertEqual(passed, len(cases))

    def test_c04_new_adversarial_syntactic_cases(self):
        """Additional 15 adversarial edge cases covering varied clause order and grammar."""
        adversarial_battery = [
            ("Adv4110-01", "Although earlier papers evaluated cell models, our group validated efficacy in mice.", "performed"),
            ("Adv4110-02", "Animal models were omitted in accordance with 3Rs replacement principles.", "excluded"),
            ("Adv4110-03", "Preclinical rodent assays will be conducted pending regulatory clearance.", "future_work"),
            ("Adv4110-04", "The authors reviewed prior rabbit models in Section 2.", "background_only"),
            ("Adv4110-05", "Danio rerio embryos were microinjected at the single-cell stage.", "performed"),
            ("Adv4110-06", "Animal models are useful tools in modern pharmacology.", "ambiguous"),
            ("Adv4110-07", "Neither murine nor zebrafish models were utilized.", "excluded"),
            ("Adv4110-08", "We tested the formulation in rabbits, but rat assays were excluded.", "mixed"),
            ("Adv4110-09", "In vivo mouse assays were performed to measure bioavailability.", "performed"),
            ("Adv4110-10", "Murine models were developed specifically for this gene knockout.", "performed"),
            ("Adv4110-11", "Animal studies are widely cited throughout the review.", "background_only"),
            ("Adv4110-12", "Prospective rodent trials are warranted.", "future_work"),
            ("Adv4110-13", "We established a C57BL/6 mouse colony for longevity studies.", "performed"),
            ("Adv4110-14", "All assays were conducted cell-free without animal models.", "excluded"),
            ("Adv4110-15", "The formulation was administered to rats via oral gavage.", "performed"),
        ]

        for cid, text, expected in adversarial_battery:
            res = analyze_animal_model_context(text)
            status = res.get("status")
            ok = (status == expected) or (expected in ["excluded", "background_only"] and status in ["excluded", "background_only"])
            self.assertTrue(
                ok,
                f"[{cid}] Expected '{expected}', got '{status}' for text: '{text}'"
            )

    def test_c05_downstream_inferred_limitations_integrity(self):
        """Inferred limitations must align with context classification (executed vs descriptive)."""
        # Executed case
        lims_perf = generate_inferred_limitations("Earlier studies evaluated cell culture, whereas we tested the formulation in mice.")
        combined_perf = " ".join(lims_perf).lower()
        self.assertIn("murine metabolic rates", combined_perf)

        # Descriptive case (ambiguous) -> falls through to cell culture or standard heuristics, NOT executed murine limitations
        lims_desc = generate_inferred_limitations("Animal models are interesting. The cell culture study showed promising data.")
        combined_desc = " ".join(lims_desc).lower()
        self.assertNotIn("murine metabolic rates", combined_desc)


if __name__ == "__main__":
    unittest.main()
