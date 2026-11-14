"""
Phase 3B.2 Targeted Security & Persistence Remediation Verification Suite.
Validates:
1. Production-mode test-ID authorization bypass removal (TEST-*, ST_API_* require current_app.testing).
2. Draft account enumeration oracle fix (7 scenarios: guest, student, faculty vs existing/nonexistent).
3. Exemplar proposal 13989 immutability and deletion block.
4. Teammate delegation preservation (teammates can collaborate, non-teammates blocked with 403).
5. Data directory test isolation.
"""

import os
import sys
import unittest
import json
import tempfile
import shutil
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from core import auth_store, cohort_store, draft_store


class TestPhase3B2SecurityAndPersistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create isolated temporary data directory for this test suite
        cls.test_data_dir = tempfile.mkdtemp(prefix="biowriter_test_phase3b2_")
        cls.old_data_dir_env = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = cls.test_data_dir

        # Copy authentic seeds into isolated test directory so tests can use real seeded accounts
        live_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(os.path.join(cls.test_data_dir, "drafts"), exist_ok=True)
        for fname in ["users.json", "cohort_db.json", "faculty_security.json"]:
            src = os.path.join(live_data, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(cls.test_data_dir, fname))

        for df in ["13989.json", "20230001.json", "20230002.json", "20230004.json"]:
            src = os.path.join(live_data, "drafts", df)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(cls.test_data_dir, "drafts", df))

    @classmethod
    def tearDownClass(cls):
        if cls.old_data_dir_env is not None:
            os.environ["BIOWRITER_DATA_DIR"] = cls.old_data_dir_env
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)
        shutil.rmtree(cls.test_data_dir, ignore_errors=True)

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    # --------------------------------------------------------------------------
    # 1. PRODUCTION-MODE TEST-ID AUTHORIZATION BYPASS
    # --------------------------------------------------------------------------
    def test_production_guest_cannot_write_or_lock_test_ids(self):
        """In production mode (app.testing = False), unauthenticated users must NOT be able
        to write, modify, or lock drafts using TEST-* or ST_API_* prefixes."""
        self.app.testing = False

        # Attempt to save draft with TEST- prefix
        resp_test = self.client.post("/api/student/save_draft", json={
            "student_id": "TEST-ATTACKER-01",
            "student_data": {"title": "Exploit Attempt"}
        })
        self.assertEqual(resp_test.status_code, 403, "Production guest write to TEST-* must be 403")

        # Attempt to save draft with ST_API_ prefix
        resp_st = self.client.post("/api/student/save_draft", json={
            "student_id": "ST_API_EXPLOIT",
            "student_data": {"title": "Exploit Attempt"}
        })
        self.assertEqual(resp_st.status_code, 403, "Production guest write to ST_API_* must be 403")

        # Attempt to toggle lock on TEST- draft
        resp_lock_test = self.client.post("/api/student/toggle_lock", json={
            "student_id": "TEST-ATTACKER-01",
            "is_locked": True
        })
        self.assertEqual(resp_lock_test.status_code, 403, "Production guest lock on TEST-* must be 403")

        # Attempt to toggle lock on ST_API_ draft
        resp_lock_st = self.client.post("/api/student/toggle_lock", json={
            "student_id": "ST_API_EXPLOIT",
            "is_locked": True
        })
        self.assertEqual(resp_lock_st.status_code, 403, "Production guest lock on ST_API_* must be 403")

    def test_testing_mode_guest_can_write_test_ids(self):
        """In testing mode (app.testing = True), test runners can write and lock synthetic IDs."""
        self.app.testing = True

        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "TEST-SYNTHETIC-OK",
            "student_data": {"title": "Test Mode Synthetic Draft"}
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json().get("success"))

        resp_lock = self.client.post("/api/student/toggle_lock", json={
            "student_id": "TEST-SYNTHETIC-OK",
            "is_locked": True
        })
        self.assertEqual(resp_lock.status_code, 200)
        self.assertTrue(resp_lock.get_json().get("is_locked_for_grading"))

    # --------------------------------------------------------------------------
    # 2. AUTHENTICATED STUDENT, TEAMMATE, & FACULTY ACCESS
    # --------------------------------------------------------------------------
    def test_authenticated_student_can_write_own_draft(self):
        """Authenticated student 20230001 can save their own draft."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "20230001"
            sess["role"] = "student"

        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "20230001",
            "student_data": {"title": "Legitimate Student Update"}
        })
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_student_cannot_write_other_student_draft(self):
        """Authenticated student 20230001 cannot overwrite student 20230004 draft."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "20230001"
            sess["role"] = "student"

        # Even if payload specifies 20230004, app locks student_id to session identity (20230001)
        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "20230004",
            "student_data": {"title": "Tampering Attempt"}
        })
        data = resp.get_json()
        self.assertEqual(data.get("student_id"), "20230001")

    def test_teammate_collaboration_preserved(self):
        """Teammates in same group (20230001 and 20230002 in L1-T1) can read each other's drafts."""
        with self.client.session_transaction() as sess:
            sess["student_id"] = "20230001"
            sess["role"] = "student"

        resp = self.client.get("/api/student/draft/20230002")
        self.assertEqual(resp.status_code, 200, "Teammates must be able to read each other's drafts")

    def test_faculty_full_access(self):
        """Faculty account can write to any draft."""
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"

        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "20230001",
            "student_data": {"title": "Faculty Feedback Update"}
        })
        self.assertEqual(resp.status_code, 200)

    # --------------------------------------------------------------------------
    # 3. EXEMPLAR PROTECTION & DELETION BLOCK
    # --------------------------------------------------------------------------
    def test_exemplar_write_and_deletion_protection(self):
        """Exemplar 13989 cannot be modified by students/guests and cannot be deleted by anyone."""
        # Student cannot modify exemplar
        with self.client.session_transaction() as sess:
            sess["student_id"] = "20230001"
            sess["role"] = "student"

        resp = self.client.post("/api/student/save_draft", json={
            "student_id": "13989",
            "student_data": {"title": "Corrupt Exemplar"}
        })
        # Student is locked to their own ID 20230001
        self.assertEqual(resp.get_json().get("student_id"), "20230001")

        # Guest cannot modify exemplar
        fresh_client = self.app.test_client()
        resp_guest = fresh_client.post("/api/student/save_draft", json={
            "student_id": "13989",
            "student_data": {"title": "Corrupt Exemplar"}
        })
        self.assertEqual(resp_guest.status_code, 403)

        # Faculty cannot delete exemplar
        faculty_client = self.app.test_client()
        with faculty_client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"

        del_resp = faculty_client.delete("/api/faculty/submission/13989")
        self.assertEqual(del_resp.status_code, 403)
        self.assertIn("cannot be deleted", del_resp.get_json().get("error", "").lower())

    # --------------------------------------------------------------------------
    # 4. ACCOUNT ENUMERATION ORACLE (7 SCENARIOS)
    # --------------------------------------------------------------------------
    def test_account_enumeration_all_seven_scenarios(self):
        """Tests all 7 account enumeration cases required by Phase 3B.2."""
        self.app.testing = True  # Testing harness mode

        # Scenario 1: Guest requests existing student draft (20230001)
        guest_client = self.app.test_client()
        resp1 = guest_client.get("/api/student/draft/20230001")

        # Scenario 2: Guest requests nonexistent student draft (NONEXISTENT_9999)
        resp2 = guest_client.get("/api/student/draft/NONEXISTENT_9999")

        self.assertEqual(resp1.status_code, 403, "Guest request to existing draft must be 403")
        self.assertEqual(resp2.status_code, 403, "Guest request to nonexistent draft must be 403")
        self.assertEqual(resp1.get_json(), resp2.get_json(), "Guest responses for existing vs nonexistent must be identical")
        self.assertNotIn("20230001", resp1.get_json().get("error", ""), "Requested ID must not appear in error message")

        # Scenario 3: Student requests a non-teammate student's existing draft (20230004 in L1-T2)
        student_client = self.app.test_client()
        with student_client.session_transaction() as sess:
            sess["student_id"] = "20230001"
            sess["role"] = "student"
        resp3 = student_client.get("/api/student/draft/20230004")

        # Scenario 4: Student requests another student's nonexistent draft (NONEXISTENT_9999)
        resp4 = student_client.get("/api/student/draft/NONEXISTENT_9999")

        self.assertEqual(resp3.status_code, 403, "Student request to non-teammate existing draft must be 403")
        self.assertEqual(resp4.status_code, 403, "Student request to other nonexistent draft must be 403")
        self.assertEqual(resp3.get_json(), resp4.get_json(), "Student responses for other existing vs nonexistent must be identical")
        self.assertNotIn("20230004", resp3.get_json().get("error", ""), "Requested ID must not appear in error message")

        # Scenario 5: Student requests their own existing draft (20230001)
        resp5 = student_client.get("/api/student/draft/20230001")
        self.assertEqual(resp5.status_code, 200, "Student requesting own existing draft must be 200")
        self.assertTrue(resp5.get_json().get("success"))

        # Scenario 6: Student requests their own nonexistent draft (ST-NEW-USER)
        new_stu_client = self.app.test_client()
        with new_stu_client.session_transaction() as sess:
            sess["student_id"] = "ST-NEW-USER"
            sess["role"] = "student"
        resp6 = new_stu_client.get("/api/student/draft/ST-NEW-USER")
        self.assertEqual(resp6.status_code, 404, "Student requesting own nonexistent draft must be 404")
        self.assertIn("not found", resp6.get_json().get("error", "").lower())

        # Scenario 7: Faculty requests existing and nonexistent drafts
        fac_client = self.app.test_client()
        with fac_client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"
        resp7_exist = fac_client.get("/api/student/draft/20230001")
        resp7_nonexist = fac_client.get("/api/student/draft/NONEXISTENT_9999")

        self.assertEqual(resp7_exist.status_code, 200, "Faculty requesting existing draft must be 200")
        self.assertEqual(resp7_nonexist.status_code, 404, "Faculty requesting nonexistent draft must be 404")


if __name__ == "__main__":
    unittest.main()
