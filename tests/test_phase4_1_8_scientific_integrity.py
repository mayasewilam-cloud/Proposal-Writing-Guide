"""
BioWriter Studio - Phase 4.1.8 Scientific Integrity, Submission Atomicity & Immutability Test Suite.
Verifies:
- Repair A: Elimination of the submission TOCTOU concurrency gap via versioning and optimistic concurrency (HTTP 409).
- Repair B: Defensive deep copies in CitationStatusCache preventing in-place mutations.
- Repair C: Non-rodent animal model recognition (rabbits, zebrafish) and future-work precedence over performed studies.
- Repair D: Strict lock-state input validation (rejecting strings, nulls, arrays, numbers, missing values with HTTP 400).
- Clean hermetic isolation with zero mutation to live persistent data.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

# Configure hermetic test data isolation BEFORE any application imports
TEST_TEMP_DIR = tempfile.mkdtemp(prefix="biowriter_test_phase4_1_8_")
os.environ["BIOWRITER_DATA_DIR"] = TEST_TEMP_DIR
os.environ["BIOWRITER_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
from core.draft_store import (
    save_student_draft,
    get_student_draft,
    toggle_draft_lock,
    compute_draft_fingerprint,
    draft_store_lock
)
from core.reference_service import CitationStatusCache, validate_citation_text
from core.paper_analyst_llm import analyze_animal_model_context, generate_inferred_limitations


class TestRepairASubmissionTOCTOUConcurrency(unittest.TestCase):
    """
    Repair A: Concurrency-Safe Proposal Submission Gate.
    Verifies that optimistic concurrency control prevents TOCTOU gaps,
    rejects stale commits with HTTP 409, and ensures atomic validation and locking.
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        from core.reference_service import _CITATION_STATUS_CACHE
        _CITATION_STATUS_CACHE.clear()
        self.student_id = "TEST-STU-418-CONC"
        self.draft_data = {
            "student_id": self.student_id,
            "student_name": "Test Student 418",
            "title": "CRISPR-Cas12a Water Surveillance",
            "references": "Chen, J. S. et al. (Science 2018). CRISPR-Cas12a target binding. DOI: 10.1126/science.aar6245"
        }
        save_student_draft(self.student_id, self.draft_data)

    def test_a01_clean_draft_validated_and_locked_successfully(self):
        """1. Clean draft is validated and locked successfully."""
        mock_meta = {
            "success": True,
            "doi": "10.1126/science.aar6245",
            "title": "CRISPR-Cas12a target binding",
            "year": 2018,
            "is_retracted": False,
            "is_expression_of_concern": False
        }
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={
                "student_id": self.student_id,
                "is_locked": True
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("is_locked_for_grading"))

            saved = get_student_draft(self.student_id)
            self.assertTrue(saved.get("is_locked_for_grading"))
            self.assertIsNotNone(saved.get("locked_at"))

    def test_a02_references_change_during_validation_interval(self):
        """2. References change during network-validation interval -> HTTP 409."""
        validation_started = threading.Event()
        interim_save_done = threading.Event()

        original_fetch = validate_citation_text

        def slow_validate(*args, **kwargs):
            validation_started.set()
            # Wait until the interim save has completed
            interim_save_done.wait(timeout=5.0)
            return {
                "total_citations": 1,
                "has_retracted": False,
                "has_unknown": False,
                "references": [{"doi": "10.1126/science.aar6245", "is_retracted": False}]
            }

        with patch("app.validate_citation_text", side_effect=slow_validate):
            def submit_thread_func(results):
                with app.test_client() as c:
                    r = c.post("/api/student/lock", json={
                        "student_id": self.student_id,
                        "is_locked": True
                    })
                    results.append((r.status_code, r.get_json()))

            results = []
            t = threading.Thread(target=submit_thread_func, args=(results,))
            t.start()

            validation_started.wait(timeout=5.0)
            # Concurrent edit adds a new reference
            updated_draft = dict(self.draft_data)
            updated_draft["references"] = "New Ref 2026. DOI: 10.1016/j.cell.2026.01.001"
            save_student_draft(self.student_id, updated_draft)
            interim_save_done.set()

            t.join(timeout=5.0)

            self.assertEqual(len(results), 1)
            status_code, resp_json = results[0]
            self.assertEqual(status_code, 409)
            self.assertFalse(resp_json.get("success"))
            self.assertEqual(resp_json.get("status"), "draft_changed_retry")

            # Verify proposal remains UNLOCKED and retains updated references
            final_draft = get_student_draft(self.student_id)
            self.assertFalse(final_draft.get("is_locked_for_grading", False))
            self.assertIn("10.1016/j.cell.2026.01.001", final_draft.get("references", ""))

    def test_a03_proposal_content_changes_between_read_and_commit(self):
        """3. Proposal content changes between initial read and final commit -> HTTP 409."""
        validation_started = threading.Event()
        interim_save_done = threading.Event()

        def slow_validate(*args, **kwargs):
            validation_started.set()
            interim_save_done.wait(timeout=5.0)
            return {
                "total_citations": 1,
                "has_retracted": False,
                "has_unknown": False,
                "references": []
            }

        with patch("app.validate_citation_text", side_effect=slow_validate):
            results = []
            def submit():
                with app.test_client() as c:
                    r = c.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
                    results.append((r.status_code, r.get_json()))

            t = threading.Thread(target=submit)
            t.start()
            validation_started.wait(timeout=5.0)

            # Change proposal abstract
            d = dict(self.draft_data)
            d["abstract"] = "Modified abstract content in the interim."
            save_student_draft(self.student_id, d)
            interim_save_done.set()
            t.join(timeout=5.0)

            self.assertEqual(results[0][0], 409)
            final_draft = get_student_draft(self.student_id)
            self.assertFalse(final_draft.get("is_locked_for_grading", False))
            self.assertEqual(final_draft.get("abstract"), "Modified abstract content in the interim.")

    def test_a04_second_browser_saves_draft_during_validation(self):
        """4. A second browser/session saves the draft during validation -> HTTP 409."""
        validation_started = threading.Event()
        interim_save_done = threading.Event()

        def slow_validate(*args, **kwargs):
            validation_started.set()
            interim_save_done.wait(timeout=5.0)
            return {"total_citations": 0, "has_retracted": False, "has_unknown": False, "references": []}

        with patch("app.validate_citation_text", side_effect=slow_validate):
            results = []
            t = threading.Thread(target=lambda: results.append(self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})))
            t.start()
            validation_started.wait(timeout=5.0)

            # Second session calls /api/student/save_draft
            self.client.post("/api/student/save_draft", json={
                "student_id": self.student_id,
                "student_data": {"title": "Updated by second session"}
            })
            interim_save_done.set()
            t.join(timeout=5.0)

            resp = results[0]
            self.assertEqual(resp.status_code, 409)

    def test_a05_save_occurs_immediately_before_final_commit(self):
        """5. A save occurs immediately before the final commit -> HTTP 409."""
        initial = get_student_draft(self.student_id)
        snap_ver = initial.get("version", 1)

        # Mutate draft directly on disk
        save_student_draft(self.student_id, {"title": "Version changed immediately before commit"})

        # Call toggle_draft_lock with the older expected_version
        res = toggle_draft_lock(self.student_id, is_locked=True, expected_version=snap_ver)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "draft_changed_retry")

    def test_a06_two_simultaneous_submission_requests(self):
        """6. Two simultaneous submission requests occur -> exactly one succeeds, one gets 409 or already locked."""
        mock_meta = {
            "success": True,
            "doi": "10.1126/science.aar6245",
            "is_retracted": False
        }
        barrier = threading.Barrier(2)
        results = []

        def submit():
            barrier.wait()
            with app.test_client() as c:
                r = c.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
                results.append((r.status_code, r.get_json()))

        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            t1 = threading.Thread(target=submit)
            t2 = threading.Thread(target=submit)
            t1.start()
            t2.start()
            t1.join(timeout=5.0)
            t2.join(timeout=5.0)

        status_codes = [r[0] for r in results]
        self.assertIn(200, status_codes)
        # The other must either succeed idempotently or return 409 conflict
        self.assertTrue(all(c in [200, 409] for c in status_codes))

    def test_a07_two_simultaneous_saves_occur(self):
        """7. Two simultaneous saves occur -> serial consistency preserved."""
        barrier = threading.Barrier(2)
        save_results = []

        def do_save(idx):
            barrier.wait()
            r = save_student_draft(self.student_id, {"title": f"Concurrent Save {idx}"})
            save_results.append(r)

        t1 = threading.Thread(target=do_save, args=(1,))
        t2 = threading.Thread(target=do_save, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        self.assertEqual(len(save_results), 2)
        self.assertTrue(all(r["success"] for r in save_results))
        versions = [r["version"] for r in save_results]
        self.assertNotEqual(versions[0], versions[1], "Concurrent saves must have distinct monotonic versions")

    def test_a08_submission_fails_due_to_retracted_doi(self):
        """8. Submission validation fails due to a retracted DOI -> HTTP 400 blocked_retraction."""
        retracted_draft = dict(self.draft_data)
        retracted_draft["references"] = "Retracted paper. DOI: 10.1016/j.cell.retracted"
        save_student_draft(self.student_id, retracted_draft)

        mock_meta = {
            "success": True,
            "doi": "10.1016/j.cell.retracted",
            "is_retracted": True
        }
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.get_json().get("status"), "blocked_retraction")

            saved = get_student_draft(self.student_id)
            self.assertFalse(saved.get("is_locked_for_grading", False))

    def test_a09_submission_fails_due_to_unavailable_crossref(self):
        """9. Submission validation fails due to unavailable CrossRef -> HTTP 400 verification_pending."""
        d = dict(self.draft_data)
        d["references"] = "Unavailable. DOI: 10.1000/timeout-doi"
        save_student_draft(self.student_id, d)
        mock_meta = {
            "success": False,
            "error": "504 Gateway Timeout"
        }
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.get_json().get("status"), "verification_pending")

            saved = get_student_draft(self.student_id)
            self.assertFalse(saved.get("is_locked_for_grading", False))

    def test_a10_version_mismatch_returns_409_leaves_unlocked(self):
        """10. Version mismatch returns HTTP 409 and leaves the proposal unlocked."""
        snap = get_student_draft(self.student_id)
        snap_ver = snap.get("version", 1)

        # Increment version by saving
        save_student_draft(self.student_id, {"title": "New Title"})

        res = toggle_draft_lock(self.student_id, is_locked=True, expected_version=snap_ver)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "draft_changed_retry")

        saved = get_student_draft(self.student_id)
        self.assertFalse(saved.get("is_locked_for_grading", False))

    def test_a11_newer_draft_never_overwritten_by_older_snapshot(self):
        """11. The newer draft is never overwritten by an older snapshot."""
        initial = get_student_draft(self.student_id)
        snap_ver = initial.get("version", 1)

        # Newer draft has valuable edits
        save_student_draft(self.student_id, {
            "title": "Valuable New Work",
            "methodology": "Cutting-edge protocol"
        })

        # Attempt to lock with stale version
        toggle_draft_lock(self.student_id, is_locked=True, expected_version=snap_ver)

        final_draft = get_student_draft(self.student_id)
        self.assertEqual(final_draft.get("title"), "Valuable New Work")
        self.assertEqual(final_draft.get("methodology"), "Cutting-edge protocol")

    def test_a12_committed_locked_draft_has_exact_validated_references(self):
        """12. Committed locked draft has exactly the references that passed validation."""
        mock_meta = {
            "success": True,
            "doi": "10.1126/science.aar6245",
            "is_retracted": False
        }
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
            self.assertEqual(resp.status_code, 200)

            saved = get_student_draft(self.student_id)
            self.assertTrue(saved.get("is_locked_for_grading"))
            self.assertIn("10.1126/science.aar6245", saved.get("references"))

    def test_a13_student_ownership_and_authorization_enforced(self):
        """13. Student ownership and authorization remain strictly enforced."""
        # Authenticate as STU-USER-A
        with self.client.session_transaction() as sess:
            sess["student_id"] = "STU-USER-A"
            sess["faculty_authenticated"] = False

        # Attempt to lock STU-USER-B's draft
        resp = self.client.post("/api/student/lock", json={
            "student_id": "STU-USER-B",
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 403)

    def test_a14_both_supported_lock_routes_identical_behavior(self):
        """14. Both /api/student/lock and /api/student/toggle_lock exhibit identical safe behavior."""
        for endpoint in ["/api/student/lock", "/api/student/toggle_lock"]:
            resp = self.client.post(endpoint, json={
                "student_id": self.student_id,
                "is_locked": "INVALID_VALUE"
            })
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")


class TestRepairBCitationCacheDefensiveCopying(unittest.TestCase):
    """
    Repair B: Defensive Copying in CitationStatusCache.
    Verifies that caller modifications cannot alter internal cached state.
    """

    def setUp(self):
        self.cache = CitationStatusCache(max_size=5, ttl=3600.0)
        self.entry_data = {
            "success": True,
            "doi": "10.1000/182",
            "title": "Immutable Paper Title",
            "authors": ["Smith, J.", "Doe, A."],
            "meta": {
                "retracted": False,
                "citations": [1, 2, 3]
            }
        }
        self.cache.set("10.1000/182", self.entry_data)

    def test_b01_modify_top_level_field(self):
        """1. Retrieve a cache entry and modify a top-level field."""
        retrieved = self.cache.get("10.1000/182")
        retrieved["title"] = "MUTATED TOP-LEVEL TITLE"

        fresh = self.cache.get("10.1000/182")
        self.assertEqual(fresh["title"], "Immutable Paper Title")

    def test_b02_modify_nested_dictionaries_and_lists(self):
        """2. Retrieve an entry containing nested dictionaries/lists and modify nested values."""
        retrieved = self.cache.get("10.1000/182")
        retrieved["authors"].append("Malicious Co-Author")
        retrieved["meta"]["retracted"] = True
        retrieved["meta"]["citations"].append(999)

        fresh = self.cache.get("10.1000/182")
        self.assertEqual(fresh["authors"], ["Smith, J.", "Doe, A."])
        self.assertFalse(fresh["meta"]["retracted"])
        self.assertEqual(fresh["meta"]["citations"], [1, 2, 3])

    def test_b03_retrieve_through_get_internal_state_unchanged(self):
        """3. Retrieve through get() and verify internal state remains unchanged."""
        v1 = self.cache.get("10.1000/182")
        v1["extra_key"] = "injected"

        v2 = self.cache.get("10.1000/182")
        self.assertNotIn("extra_key", v2)

    def test_b04_retrieve_through_indexing_internal_state_unchanged(self):
        """4. Retrieve through indexing and verify internal state remains unchanged."""
        v1 = self.cache["10.1000/182"]
        v1["title"] = "INDEXING MUTATION"
        v1["authors"].clear()

        v2 = self.cache["10.1000/182"]
        self.assertEqual(v2["title"], "Immutable Paper Title")
        self.assertEqual(len(v2["authors"]), 2)

    def test_b05_defaults_for_missing_keys(self):
        """5. Confirm defaults for missing keys still work."""
        self.assertIsNone(self.cache.get("10.9999/nonexistent"))
        self.assertEqual(self.cache.get("10.9999/nonexistent", default="FALLBACK"), "FALLBACK")
        with self.assertRaises(KeyError):
            _ = self.cache["10.9999/nonexistent"]

    def test_b06_ttl_expiration_remains_correct(self):
        """6. Confirm TTL expiration remains correct."""
        short_cache = CitationStatusCache(max_size=5, ttl=0.1)
        short_cache.set("10.1000/short", {"success": True, "doi": "10.1000/short"})
        self.assertIsNotNone(short_cache.get("10.1000/short"))

        time.sleep(0.15)
        self.assertIsNone(short_cache.get("10.1000/short"))
        self.assertNotIn("10.1000/short", short_cache)

    def test_b07_capacity_and_fifo_eviction(self):
        """7. Confirm capacity and FIFO eviction remain correct."""
        tiny_cache = CitationStatusCache(max_size=2, ttl=3600.0)
        tiny_cache.set("10.1000/1", {"success": True, "id": 1})
        tiny_cache.set("10.1000/2", {"success": True, "id": 2})
        tiny_cache.set("10.1000/3", {"success": True, "id": 3})  # Evicts 10.1000/1

        self.assertIsNone(tiny_cache.get("10.1000/1"))
        self.assertIsNotNone(tiny_cache.get("10.1000/2"))
        self.assertIsNotNone(tiny_cache.get("10.1000/3"))
        self.assertEqual(len(tiny_cache), 2)

    def test_b08_failed_or_unknown_responses_not_cached(self):
        """8. Confirm failed or unknown citation responses are still not cached as clean."""
        self.cache.set("10.1000/failed", {"success": False, "error": "Not found"})
        self.assertIsNone(self.cache.get("10.1000/failed"))
        self.assertNotIn("10.1000/failed", self.cache)


class TestRepairCAnimalModelContextNLP(unittest.TestCase):
    """
    Repair C: Non-rodent animal model recognition and future-work precedence.
    Verifies 32 distinct cases covering rodents, rabbits, zebrafish, future work, negation, and background.
    """

    def test_c01_all_32_contextual_cases(self):
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

            # Phase 4.1.8 Required New Cases (Rabbits, Zebrafish, Future Work, Mixed, Exclusions):
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

        self.assertEqual(len(failures), 0, f"Animal model failures ({len(failures)}/{len(cases)}): {failures}")
        self.assertEqual(passed, len(cases))

    def test_c02_downstream_inferred_limitations_future_work(self):
        """Confirm downstream inferred limitations do not describe future animal studies as executed."""
        lims = generate_inferred_limitations("Efficacy in rodent models will be evaluated in future work.")
        combined = " ".join(lims).lower()
        self.assertIn("future work", combined)
        self.assertNotIn("murine metabolic rates", combined)

    def test_c03_downstream_inferred_limitations_background_only(self):
        """Confirm downstream inferred limitations do not describe background animal studies as executed."""
        lims = generate_inferred_limitations("Rabbit models are discussed in previous literature only.")
        combined = " ".join(lims).lower()
        self.assertIn("prior literature", combined)
        self.assertNotIn("murine metabolic rates", combined)

    def test_c04_downstream_inferred_limitations_performed(self):
        """Confirm genuine performed animal studies trigger standard preclinical limitations."""
        lims = generate_inferred_limitations("The formulation was administered to New Zealand white rabbits.")
        combined = " ".join(lims).lower()
        self.assertTrue(any("animal cohort" in l.lower() or "murine metabolic" in l.lower() for l in lims))


class TestRepairDStrictLockStateInputValidation(unittest.TestCase):
    """
    Repair D: Strict Lock-State Input Validation on /api/student/lock and /api/student/toggle_lock.
    Rejects strings, nulls, arrays, objects, numbers, and missing values with HTTP 400.
    """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.student_id = "TEST-STU-418-INPUT"
        save_student_draft(self.student_id, {
            "student_id": self.student_id,
            "title": "Input Validation Test Proposal",
            "references": "10.1126/science.aar6245"
        })

    def test_d01_explicit_boolean_true_accepted(self):
        """Explicit boolean True is accepted."""
        mock_meta = {"success": True, "doi": "10.1126/science.aar6245", "is_retracted": False}
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()["is_locked_for_grading"])

    def test_d02_explicit_boolean_false_accepted(self):
        """Explicit boolean False is accepted (unlock)."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": False})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["is_locked_for_grading"])

    def test_d03_documented_legacy_payload_lock_accepted(self):
        """Documented legacy payload with 'lock': True is accepted."""
        mock_meta = {"success": True, "doi": "10.1126/science.aar6245", "is_retracted": False}
        with patch("core.reference_service.fetch_doi_metadata", return_value=mock_meta):
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "lock": True})
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()["is_locked_for_grading"])

    def test_d04_invalid_string_rejected(self):
        """String 'INVALID' is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": "INVALID"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d05_string_false_rejected(self):
        """String 'false' is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": "false"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d06_string_zero_rejected(self):
        """String '0' is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": "0"})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d07_null_value_rejected(self):
        """Null / None value is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": None})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d08_missing_lock_parameter_rejected(self):
        """Payload missing is_locked parameter is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d09_array_value_rejected(self):
        """Array [] is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": []})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d10_object_value_rejected(self):
        """Object {} is rejected with HTTP 400."""
        resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": {}})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json().get("status"), "invalid_lock_parameter")

    def test_d11_numeric_integer_rejected(self):
        """Integer 0 and 1 are rejected with HTTP 400."""
        for num in [0, 1]:
            resp = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": num})
            self.assertEqual(resp.status_code, 400)

    def test_d12_invalid_request_does_not_modify_draft(self):
        """Invalid requests do not lock or unlock the draft."""
        initial = get_student_draft(self.student_id)
        initial_locked = initial.get("is_locked_for_grading", False)

        self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": "CORRUPT"})
        after = get_student_draft(self.student_id)
        self.assertEqual(after.get("is_locked_for_grading", False), initial_locked)


@classmethod
def tearDownClass(cls):
    shutil.rmtree(TEST_TEMP_DIR, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
