"""
BioWriter Studio - Phase 4.1.6 Targeted Scientific Integrity & Citation Safety Test Suite
Author: Independent Remediation & Verification Team
Date: November 14, 2026

Scope:
- Repair A: Revalidate current references at submission time (15 adversarial tests).
- Repair B: Citation cache expiration, bounding, normalization & reliability.
- Repair C: Benchmark dictionary compatibility (_BenchmarkPriorArtDict).
- Repair D: Gootenberg/SHERLOCK scientific relationship classification correction.
- Repair E: Animal-model contextual analysis (compound negations, pronominal negation, 12 cases).

Data Isolation:
- Strictly executes within temporary directory (BIOWRITER_DATA_DIR).
- Zero live data modifications.
"""

import os
import sys
import time
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Step 0: Ensure testing environment and isolated BIOWRITER_DATA_DIR before importing app or storage
if "BIOWRITER_ENV" not in os.environ:
    os.environ["BIOWRITER_ENV"] = "testing"
if "SECRET_KEY" not in os.environ:
    os.environ["SECRET_KEY"] = "test-secret-key-32-chars-long-abc"

_TEMP_DATA_DIR = tempfile.mkdtemp(prefix="biowriter_test_phase4_1_6_")
os.environ["BIOWRITER_DATA_DIR"] = _TEMP_DATA_DIR

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from core.reference_service import (
    _CITATION_STATUS_CACHE,
    CitationStatusCache,
    DEFAULT_CACHE_TTL,
    normalize_doi,
    extract_dois,
    validate_citation_text,
    evaluate_submission_gate
)
from core.impact_novelty_engine import BENCHMARK_PRIOR_ART, audit_novelty_and_soundness
from core.paper_analyst_llm import analyze_animal_model_context, generate_inferred_limitations
from core.draft_store import save_student_draft, get_student_draft, toggle_draft_lock


class TestRepairACitationSubmissionRevalidation(unittest.TestCase):
    """Repair A: Revalidate current authoritative references at submission time."""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

    def setUp(self):
        _CITATION_STATUS_CACHE.clear()
        self.student_id = "TEST-416-A"
        # Seed a base draft
        save_student_draft(self.student_id, {
            "title": "AMR Surveillance Proposal",
            "references": "10.1038/s41586-clean-base",
            "is_locked_for_grading": False
        })
        _CITATION_STATUS_CACHE["10.1038/s41586-clean-base"] = {
            "success": True,
            "doi": "10.1038/s41586-clean-base",
            "title": "Clean Base Study",
            "year": 2023,
            "is_retracted": False,
            "is_expression_of_concern": False,
            "is_preprint": False,
            "is_corrected": False
        }

    def test_a01_save_clean_then_inject_retracted_before_submission(self):
        """1. Save clean list, inject retracted DOI into stored draft, then attempt lock -> BLOCKED."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.retracted-inject"] = {
            "success": True,
            "doi": "10.1016/j.cell.retracted-inject",
            "title": "Fraudulent Blot Study",
            "is_retracted": True,
            "retraction_notice": "Retracted for data fabrication."
        }
        # Inject retracted DOI into the authoritative stored draft
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.retracted-inject"
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "blocked_retraction")
        self.assertIn("retracted", data["error"].lower())

    def test_a02_submit_with_forged_citation_validation_metadata(self):
        """2. Submit with forged citation_validation metadata in request body -> BLOCKED."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.retracted-forge"] = {
            "success": True,
            "doi": "10.1016/j.cell.retracted-forge",
            "is_retracted": True
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.retracted-forge"
        save_student_draft(self.student_id, draft)

        # Client attempts to pass forged clean validation
        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True,
            "citation_validation": {
                "has_retracted": False,
                "has_unknown": False,
                "retracted_citations": []
            }
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], "blocked_retraction")

    def test_a03_submit_with_client_supplied_has_retracted_false(self):
        """3. Submit with has_retracted_citations=False supplied by client -> BLOCKED."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.retracted-flag"] = {
            "success": True,
            "doi": "10.1016/j.cell.retracted-flag",
            "is_retracted": True
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.retracted-flag"
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True,
            "has_retracted_citations": False
        })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_a04_submit_with_missing_validation_metadata(self):
        """4. Submit with draft that has no previous validation metadata -> evaluated live."""
        draft = get_student_draft(self.student_id)
        draft["citation_validation"] = None
        draft["references"] = "10.1038/s41586-clean-base"
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_a05_submit_with_stale_clean_metadata(self):
        """5. Submit with stale clean metadata when stored draft now references retracted paper -> BLOCKED."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.retracted-stale"] = {
            "success": True,
            "doi": "10.1016/j.cell.retracted-stale",
            "is_retracted": True
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.retracted-stale"
        # Stale clean metadata left on draft
        draft["citation_validation"] = {"has_retracted": False, "references": []}
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["status"], "blocked_retraction")

    def test_a06_submit_after_previous_crossref_outage(self):
        """6. Submit after draft was saved during an outage -> live revalidation completes."""
        _CITATION_STATUS_CACHE["10.1038/s41586-recovered"] = {
            "success": True,
            "doi": "10.1038/s41586-recovered",
            "is_retracted": False
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1038/s41586-recovered"
        # Outage metadata previously attached during save
        draft["citation_validation"] = {"has_retracted": False, "has_unknown": True}
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_a07_submit_with_cold_cache_and_retracted_doi(self):
        """7. Submit with cold cache and known retracted DOI -> BLOCKED (either retraction or pending verification)."""
        _CITATION_STATUS_CACHE.clear()
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.cold.retracted"
        save_student_draft(self.student_id, draft)

        with patch("core.reference_service.fetch_doi_metadata") as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "doi": "10.1016/j.cell.cold.retracted",
                "is_retracted": True,
                "status_type": "retracted"
            }
            resp = self.client.post("/api/student/lock", json={
                "student_id": self.student_id,
                "is_locked": True
            })
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.get_json()["status"], "blocked_retraction")

    def test_a08_submit_with_expired_cache_entry(self):
        """8. Submit with expired cache entry -> cache hit rejected, live revalidation triggered."""
        _CITATION_STATUS_CACHE.set("10.1038/s41586-expired", {
            "success": True,
            "doi": "10.1038/s41586-expired",
            "is_retracted": False
        }, ttl=0.01)
        time.sleep(0.02)  # Expire entry

        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1038/s41586-expired"
        save_student_draft(self.student_id, draft)

        # After expiration, paper was retracted by publisher!
        with patch("core.reference_service.fetch_doi_metadata") as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "doi": "10.1038/s41586-expired",
                "is_retracted": True,
                "status_type": "retracted"
            }
            resp = self.client.post("/api/student/lock", json={
                "student_id": self.student_id,
                "is_locked": True
            })
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.get_json()["status"], "blocked_retraction")

    def test_a09_submit_with_multiple_dois_including_one_retracted(self):
        """9. Submit with multiple DOIs, 1 of which is retracted -> BLOCKED."""
        _CITATION_STATUS_CACHE["10.1038/s41586-clean1"] = {"success": True, "is_retracted": False}
        _CITATION_STATUS_CACHE["10.1038/s41586-clean2"] = {"success": True, "is_retracted": False}
        _CITATION_STATUS_CACHE["10.1016/j.cell.bad"] = {"success": True, "is_retracted": True}

        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1038/s41586-clean1\n10.1016/j.cell.bad\n10.1038/s41586-clean2"
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["status"], "blocked_retraction")

    def test_a10_submit_with_crossref_unavailable_blocks_submission(self):
        """10. Submit with CrossRef unavailable and cold cache -> BLOCKED with verification_pending."""
        _CITATION_STATUS_CACHE.clear()
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1038/s41586-unverified-live"
        save_student_draft(self.student_id, draft)

        with patch("core.reference_service.fetch_doi_metadata") as mock_fetch:
            mock_fetch.return_value = {"success": False, "error": "Connection timeout (HTTP 504)"}
            resp = self.client.post("/api/student/lock", json={
                "student_id": self.student_id,
                "is_locked": True
            })
            self.assertEqual(resp.status_code, 400)
            data = resp.get_json()
            self.assertFalse(data["success"])
            self.assertEqual(data["status"], "verification_pending")
            self.assertTrue(data["verification_pending"])
            self.assertIn("verification could not be completed", data["error"].lower())

    def test_a11_save_draft_while_crossref_unavailable_remains_available(self):
        """11. Saving draft while CrossRef is unavailable succeeds with HTTP 200 without blocking student work."""
        with patch("core.reference_service.fetch_doi_metadata") as mock_fetch:
            mock_fetch.return_value = {"success": False, "error": "Connection timeout"}
            resp = self.client.post("/api/student/save_draft", json={
                "student_id": self.student_id,
                "student_data": {
                    "title": "Work in Progress",
                    "references": "10.1038/s41586-during-outage"
                }
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertTrue(data["success"])
            self.assertTrue(data["citation_validation"]["has_unknown"])

    def test_a12_failed_submission_does_not_change_lock_state(self):
        """12. Confirm that rejected submission leaves the proposal in an unlocked state."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.locked-check"] = {
            "success": True,
            "doi": "10.1016/j.cell.locked-check",
            "is_retracted": True
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.locked-check"
        draft["is_locked_for_grading"] = False
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 400)

        # Authoritative draft must still be unlocked
        reloaded = get_student_draft(self.student_id)
        self.assertFalse(reloaded.get("is_locked_for_grading", False))

    def test_a13_clean_verified_draft_can_be_submitted(self):
        """13. Confirm that a clean, successfully verified draft can be locked with HTTP 200."""
        _CITATION_STATUS_CACHE["10.1038/s41586-verified-ok"] = {
            "success": True,
            "doi": "10.1038/s41586-verified-ok",
            "is_retracted": False,
            "is_expression_of_concern": False
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1038/s41586-verified-ok"
        save_student_draft(self.student_id, draft)

        resp = self.client.post("/api/student/lock", json={
            "student_id": self.student_id,
            "is_locked": True
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])
        reloaded = get_student_draft(self.student_id)
        self.assertTrue(reloaded.get("is_locked_for_grading"))

    def test_a14_both_lock_endpoint_aliases_enforce_identical_rules(self):
        """14. Confirm /api/student/lock and /api/student/toggle_lock enforce identical gate logic."""
        _CITATION_STATUS_CACHE["10.1016/j.cell.alias-test"] = {
            "success": True,
            "doi": "10.1016/j.cell.alias-test",
            "is_retracted": True
        }
        draft = get_student_draft(self.student_id)
        draft["references"] = "10.1016/j.cell.alias-test"
        save_student_draft(self.student_id, draft)

        # Endpoint 1: /api/student/lock
        r1 = self.client.post("/api/student/lock", json={"student_id": self.student_id, "is_locked": True})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.get_json()["status"], "blocked_retraction")

        # Endpoint 2: /api/student/toggle_lock
        r2 = self.client.post("/api/student/toggle_lock", json={"student_id": self.student_id, "is_locked": True})
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(r2.get_json()["status"], "blocked_retraction")

    def test_a15_student_cannot_submit_another_students_draft(self):
        """15. Confirm that a student cannot submit or lock another student's draft."""
        save_student_draft("TEST-VICTIM", {"title": "Victim Draft", "references": ""})

        with self.client.session_transaction() as sess:
            sess["student_id"] = "TEST-ATTACKER"
            sess["role"] = "student"

        resp = self.client.post("/api/student/lock", json={
            "student_id": "TEST-VICTIM",
            "is_locked": True
        })
        # Student session binds student_id to attacker's ID, protecting victim
        self.assertIn(resp.status_code, [200, 403, 404])
        # Victim draft lock state must remain untouched
        victim_draft = get_student_draft("TEST-VICTIM")
        self.assertFalse(victim_draft.get("is_locked_for_grading", False))


class TestRepairBCitationCacheExpirationAndReliability(unittest.TestCase):
    """Repair B: Bounded, timestamped cache supporting expiration, normalization, and reliability."""

    def setUp(self):
        self.cache = CitationStatusCache(max_size=5, ttl=1.0)

    def test_b01_fresh_cache_hit(self):
        """Verify unexpired cache hit returns stored metadata with _cached_at."""
        self.cache["10.1038/nature1234"] = {"success": True, "title": "Paper 1"}
        self.assertIn("10.1038/nature1234", self.cache)
        entry = self.cache.get("10.1038/nature1234")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["title"], "Paper 1")
        self.assertTrue(entry.get("_from_cache"))
        self.assertIn("_cached_at", entry)

    def test_b02_expired_cache_entry(self):
        """Verify expired entry is evicted and returns None / False."""
        self.cache.set("10.1038/nature-expire", {"success": True, "title": "Old"}, ttl=0.01)
        time.sleep(0.02)
        self.assertNotIn("10.1038/nature-expire", self.cache)
        self.assertIsNone(self.cache.get("10.1038/nature-expire"))
        with self.assertRaises(KeyError):
            _ = self.cache["10.1038/nature-expire"]

    def test_b03_cold_cache(self):
        """Verify query against empty/cold cache returns default cleanly."""
        self.assertNotIn("10.1000/cold", self.cache)
        self.assertIsNone(self.cache.get("10.1000/cold"))
        self.assertEqual(self.cache.get("10.1000/cold", "default_val"), "default_val")

    def test_b04_cache_size_limit_and_eviction(self):
        """Verify hard capacity limit (max_size=5) evicts oldest entry upon overflow."""
        for i in range(5):
            self.cache[f"10.1000/p{i}"] = {"success": True, "idx": i}
        self.assertEqual(len(self.cache), 5)
        self.assertIn("10.1000/p0", self.cache)

        # Insert 6th entry -> should evict p0
        self.cache["10.1000/p5"] = {"success": True, "idx": 5}
        self.assertEqual(len(self.cache), 5)
        self.assertNotIn("10.1000/p0", self.cache)
        self.assertIn("10.1000/p5", self.cache)

    def test_b05_doi_normalization_across_formats(self):
        """Verify URL prefixes, uppercase characters, and spaces resolve to the same normalized key."""
        self.cache["10.1038/S41586-020-2012-7"] = {"success": True, "title": "Normalized"}
        self.assertIn("https://doi.org/10.1038/s41586-020-2012-7", self.cache)
        self.assertIn("doi:10.1038/s41586-020-2012-7.", self.cache)
        hit = self.cache.get("https://doi.org/10.1038/s41586-020-2012-7")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["title"], "Normalized")

    def test_b06_unknown_result_never_cached_as_clean(self):
        """Verify unsuccessful or unknown results are rejected by cache.set."""
        self.cache.set("10.1000/failed", {"success": False, "error": "HTTP 500"})
        self.assertNotIn("10.1000/failed", self.cache)
        self.assertIsNone(self.cache.get("10.1000/failed"))

    def test_b07_status_changes_from_clean_to_retracted_after_expiration(self):
        """Verify entry that expires can be updated to retracted upon revalidation."""
        self.cache.set("10.1038/retract-later", {"success": True, "is_retracted": False}, ttl=0.01)
        time.sleep(0.02)
        # Expired:
        self.assertIsNone(self.cache.get("10.1038/retract-later"))
        # Revalidated as retracted:
        self.cache.set("10.1038/retract-later", {"success": True, "is_retracted": True})
        hit = self.cache.get("10.1038/retract-later")
        self.assertTrue(hit["is_retracted"])


class TestRepairCBenchmarkDictionaryCompatibility(unittest.TestCase):
    """Repair C: Standard dict compatibility on _BenchmarkPriorArtDict."""

    def test_c01_get_and_indexing_equivalence(self):
        """Verify BENCHMARK_PRIOR_ART.get() returns the exact same list as bracket indexing."""
        by_index = BENCHMARK_PRIOR_ART["cas12a_detection"]
        by_get = BENCHMARK_PRIOR_ART.get("cas12a_detection")
        self.assertEqual(by_index, by_get)
        self.assertEqual(len(by_get), 7)

    def test_c02_unknown_topic_returns_default(self):
        """Verify unknown topic returns supplied default or None."""
        self.assertIsNone(BENCHMARK_PRIOR_ART.get("unknown_topic"))
        self.assertEqual(BENCHMARK_PRIOR_ART.get("unknown_topic", []), [])
        self.assertEqual(BENCHMARK_PRIOR_ART.get("unknown_topic", "fallback"), "fallback")

    def test_c03_membership_checks(self):
        """Verify 'in' membership operators behave correctly."""
        self.assertIn("cas12a_detection", BENCHMARK_PRIOR_ART)
        self.assertIn("petase_engineering", BENCHMARK_PRIOR_ART)
        self.assertNotIn("unknown_topic", BENCHMARK_PRIOR_ART)

    def test_c04_dict_iteration_and_collection_methods(self):
        """Verify keys(), values(), items(), and __iter__."""
        keys = list(BENCHMARK_PRIOR_ART.keys())
        self.assertIn("cas12a_detection", keys)
        self.assertIn("petase_engineering", keys)

        items = list(BENCHMARK_PRIOR_ART.items())
        self.assertEqual(len(items), 2)
        for k, v in items:
            self.assertIsInstance(v, list)
            self.assertEqual(len(v), 7)


class TestRepairDGootenbergCas12aClassification(unittest.TestCase):
    """Repair D: Correct Gootenberg et al. (2017) SHERLOCK relationship classification."""

    def test_d01_gootenberg_is_not_direct_prior_art(self):
        """Assert Gootenberg is reclassified from direct_prior_art to enabling_technology."""
        records = BENCHMARK_PRIOR_ART["cas12a_detection"]
        goot = next((r for r in records if "Gootenberg" in r.get("authors", "")), None)
        self.assertIsNotNone(goot, "Gootenberg et al. record must exist")
        self.assertNotEqual(goot["relationship_type"], "direct_prior_art")
        self.assertEqual(goot["relationship_type"], "enabling_technology")

    def test_d02_relevance_explanation_identifies_cas13a_and_paradigm(self):
        """Assert explanation accurately distinguishes Cas13 RNA cleavage from Cas12a ssDNA cleavage."""
        records = BENCHMARK_PRIOR_ART["cas12a_detection"]
        goot = next(r for r in records if "Gootenberg" in r.get("authors", ""))
        expl = goot["relevance_explanation"]
        self.assertIn("Cas13", expl)
        self.assertIn("collateral", expl.lower())
        self.assertNotIn("direct Cas12a implementation", expl)

    def test_d03_chen_2018_remains_direct_prior_art(self):
        """Assert Chen et al. (2018) DETECTR remains the foundational direct prior art."""
        records = BENCHMARK_PRIOR_ART["cas12a_detection"]
        chen = next(r for r in records if "Chen" in r.get("authors", ""))
        self.assertEqual(chen["relationship_type"], "direct_prior_art")
        self.assertIn("Cas12a", chen["title"])

    def test_d04_cas12a_relationship_breakdown(self):
        """Assert revised relationship breakdown matches exact catalog composition."""
        records = BENCHMARK_PRIOR_ART["cas12a_detection"]
        types = [r["relationship_type"] for r in records]
        self.assertEqual(types.count("direct_prior_art"), 2)
        self.assertEqual(types.count("enabling_technology"), 3)
        self.assertEqual(types.count("target_biology"), 1)
        self.assertEqual(types.count("adjacent_background"), 1)
        self.assertEqual(len(records), 7)


class TestRepairEAnimalModelContextualAnalysis(unittest.TestCase):
    """Repair E: Context-aware animal model analysis with compound negation and pronominal negation."""

    def test_e01_compound_negation_non_animal_model(self):
        """Case 1: 'The study used a non-animal model.' -> excluded."""
        res = analyze_animal_model_context("The study used a non-animal model.")
        self.assertEqual(res["status"], "excluded")
        lims = generate_inferred_limitations("The study used a non-animal model.")
        self.assertFalse(any("murine" in l.lower() for l in lims))

    def test_e02_compound_negation_non_animal_system(self):
        """Case 2: 'The study used a non-animal system for testing.' -> excluded."""
        res = analyze_animal_model_context("The study used a non-animal system for testing.")
        self.assertEqual(res["status"], "excluded")

    def test_e03_pronominal_negation_discusses_but_does_not_use_them(self):
        """Case 3: 'The paper discusses animal models, but does not use them.' -> excluded."""
        res = analyze_animal_model_context("The paper discusses animal models, but does not use them.")
        self.assertEqual(res["status"], "excluded")
        lims = generate_inferred_limitations("The paper discusses animal models, but does not use them.")
        self.assertFalse(any("murine" in l.lower() for l in lims))

    def test_e04_pronominal_negation_previous_studies_used_mice_we_did_not(self):
        """Case 4: 'Previous studies used mice, but we did not use them in this investigation.' -> excluded."""
        res = analyze_animal_model_context("Previous studies used mice, but we did not use them in this investigation.")
        self.assertIn(res["status"], ["excluded", "background_only"])

    def test_e05_explicit_exclusion(self):
        """Case 5: 'Animal experiments were not performed in this study.' -> excluded."""
        res = analyze_animal_model_context("Animal experiments were not performed in this study.")
        self.assertEqual(res["status"], "excluded")

    def test_e06_future_work(self):
        """Case 6: 'Future studies will investigate the formulation in mice.' -> future_work."""
        res = analyze_animal_model_context("Future studies will investigate the formulation in mice.")
        self.assertEqual(res["status"], "future_work")

    def test_e07_executed_rats(self):
        """Case 7: 'The current study administered the compound to rats.' -> performed."""
        res = analyze_animal_model_context("The current study administered the compound to rats.")
        self.assertEqual(res["status"], "performed")

    def test_e08_background_introduction_only(self):
        """Case 8: 'Animal models were discussed in the introduction only.' -> background_only."""
        res = analyze_animal_model_context("Animal models were discussed in the introduction only.")
        self.assertEqual(res["status"], "background_only")

    def test_e09_in_vitro_vs_cited_animal(self):
        """Case 9: 'The current study used in vitro assays, while cited studies used animal models.' -> background_only/excluded."""
        res = analyze_animal_model_context("The current study used in vitro assays, while cited studies used animal models.")
        self.assertIn(res["status"], ["excluded", "background_only"])

    def test_e10_mixed_performed_and_excluded(self):
        """Case 10: 'The study used mice for pharmacokinetic analysis but excluded other animal experiments.' -> mixed."""
        res = analyze_animal_model_context("The study used mice for pharmacokinetic analysis but excluded other animal experiments.")
        self.assertEqual(res["status"], "mixed")

    def test_e11_no_animals_although_introduction_discusses(self):
        """Case 11: 'No animal models were used, although the introduction discusses previous animal studies.' -> excluded."""
        res = analyze_animal_model_context("No animal models were used, although the introduction discusses previous animal studies.")
        self.assertEqual(res["status"], "excluded")

    def test_e12_standard_mouse_model(self):
        """Case 12: 'The study used a mouse model.' -> performed."""
        res = analyze_animal_model_context("The study used a mouse model.")
        self.assertEqual(res["status"], "performed")


if __name__ == "__main__":
    unittest.main()
