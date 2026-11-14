"""
BioWriter Studio - Phase 3C.5.6 Automated Test Suite
Targeted Stale-Session Endpoint Remediation Verification:
  1. /api/student/my_project
  2. /api/student/drafts
Verifies that unclaimed, deleted, and legacy cohort student sessions fail closed (HTTP 401 / cleared session),
while claimed students, faculty administrators, and legitimate guests retain their expected access.
All tests use 100% isolated temporary storage with zero live data touches.
"""

import unittest
import os
import sys
import json
import tempfile
import shutil

# Set environment variables for test isolation before app imports
os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-bytes-long-for-testing-p3c56"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
import core.auth_store as auth_store
import core.cohort_store as cohort_store
import core.draft_store as draft_store


class Phase3C56StaleSessionEndpointRepairsTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="biowriter_p3c56_test_")
        self.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir

        # Preserve and rebind module-level paths
        self.orig_users_file = auth_store.USERS_FILE
        self.orig_cohort_users_file = cohort_store.USERS_FILE
        self.orig_cohort_db = cohort_store.COHORT_DB_FILE
        self.orig_team_ws_dir = cohort_store.TEAM_WORKSPACES_DIR
        self.orig_drafts_dir = draft_store.DRAFTS_DIR

        self.test_users_file = os.path.join(self.temp_dir, "users.json")
        self.test_cohort_db_file = os.path.join(self.temp_dir, "cohort_db.json")
        self.test_team_ws_dir = os.path.join(self.temp_dir, "team_workspaces")
        self.test_drafts_dir = os.path.join(self.temp_dir, "drafts")

        auth_store.USERS_FILE = self.test_users_file
        cohort_store.USERS_FILE = self.test_users_file
        cohort_store.COHORT_DB_FILE = self.test_cohort_db_file
        cohort_store.TEAM_WORKSPACES_DIR = self.test_team_ws_dir
        draft_store.DRAFTS_DIR = self.test_drafts_dir

        os.makedirs(self.test_team_ws_dir, exist_ok=True)
        os.makedirs(self.test_drafts_dir, exist_ok=True)

        self.seed_test_data()
        self.client = app.test_client()

    def tearDown(self):
        auth_store.USERS_FILE = self.orig_users_file
        cohort_store.USERS_FILE = self.orig_cohort_users_file
        cohort_store.COHORT_DB_FILE = self.orig_cohort_db
        cohort_store.TEAM_WORKSPACES_DIR = self.orig_team_ws_dir
        draft_store.DRAFTS_DIR = self.orig_drafts_dir

        if self.old_data_dir is not None:
            os.environ["BIOWRITER_DATA_DIR"] = self.old_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def seed_test_data(self):
        # 1. Seed users.json
        users = {
            # Claimed student
            "STU-CLAIMED-01": {
                "student_id": "STU-CLAIMED-01",
                "student_name": "Alice Claimed",
                "password_hash": "dummy_pbkdf2_hash_for_testing",
                "created_at": "Nov 13, 2026 - 10:00",
                "last_login": "Nov 13, 2026 - 10:00",
                "role": "student",
                "account_claimed": True,
                "pre_enrolled_by_faculty": True,
                "lab_group": "L1",
                "team_id": "TEAM-ALPHA",
            },
            # Unclaimed pre-enrolled student
            "STU-UNCLAIMED-01": {
                "student_id": "STU-UNCLAIMED-01",
                "student_name": "Bob Unclaimed",
                "password_hash": "!UNCLAIMED!",
                "created_at": "Nov 13, 2026 - 10:00",
                "last_login": "Nov 13, 2026 - 10:00",
                "role": "student",
                "account_claimed": False,
                "pre_enrolled_by_faculty": True,
                "lab_group": "L1",
                "team_id": "TEAM-ALPHA",
            },
            # Legacy cohort student (null claim flag)
            "STU-LEGACY-01": {
                "student_id": "STU-LEGACY-01",
                "student_name": "Charlie Legacy",
                "password_hash": "legacy_hash",
                "created_at": "Nov 13, 2026 - 10:00",
                "last_login": "Nov 13, 2026 - 10:00",
                "role": "student",
                "account_claimed": None,
                "pre_enrolled_by_faculty": True,
                "lab_group": "L1",
                "team_id": "TEAM-ALPHA",
            },
        }
        with open(self.test_users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)

        # 2. Seed cohort_db.json
        cohort = {
            "semester": "Fall 2026",
            "course_id": "BT_301",
            "students": {
                "STU-CLAIMED-01": {
                    "student_id": "STU-CLAIMED-01",
                    "student_name": "Alice Claimed",
                    "email": "alice@student.edu.eg",
                    "lab_group": "L1",
                    "team_id": "TEAM-ALPHA",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
                "STU-UNCLAIMED-01": {
                    "student_id": "STU-UNCLAIMED-01",
                    "student_name": "Bob Unclaimed",
                    "email": "bob@student.edu.eg",
                    "lab_group": "L1",
                    "team_id": "TEAM-ALPHA",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
                "STU-LEGACY-01": {
                    "student_id": "STU-LEGACY-01",
                    "student_name": "Charlie Legacy",
                    "email": "charlie@student.edu.eg",
                    "lab_group": "L1",
                    "team_id": "TEAM-ALPHA",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
            },
            "lab_groups": {
                "Fall 2026::BT_301::L1": {"lab_group_id": "L1", "name": "Lab Group 1", "semester": "Fall 2026", "course_id": "BT_301"}
            },
            "teams": {
                "TEAM-ALPHA": {
                    "team_id": "TEAM-ALPHA",
                    "team_name": "Team Alpha",
                    "lab_group": "L1",
                    "student_ids": ["STU-CLAIMED-01", "STU-UNCLAIMED-01", "STU-LEGACY-01"],
                    "pi_id": "PI-01",
                    "pi_name": "Dr. Supervisor",
                    "topic_title": "CRISPR Biosensors",
                }
            },
            "audit_history": []
        }
        with open(self.test_cohort_db_file, "w", encoding="utf-8") as f:
            json.dump(cohort, f, indent=2)

        # 3. Seed drafts
        draft_claimed = {
            "student_id": "STU-CLAIMED-01",
            "title": "Alice's Private Research Proposal",
            "abstract": "Confidential claimed proposal text.",
        }
        with open(os.path.join(self.test_drafts_dir, "STU-CLAIMED-01.json"), "w", encoding="utf-8") as f:
            json.dump(draft_claimed, f)

        draft_unclaimed = {
            "student_id": "STU-UNCLAIMED-01",
            "title": "Bob's Unclaimed Research Draft",
            "abstract": "Private unclaimed proposal text.",
        }
        with open(os.path.join(self.test_drafts_dir, "STU-UNCLAIMED-01.json"), "w", encoding="utf-8") as f:
            json.dump(draft_unclaimed, f)

        draft_exemplar = {
            "student_id": "13989",
            "title": "Public Exemplar Proposal",
            "abstract": "Open demo reference material.",
        }
        with open(os.path.join(self.test_drafts_dir, "13989.json"), "w", encoding="utf-8") as f:
            json.dump(draft_exemplar, f)

    # --------------------------------------------------------------------------
    # 1. /api/student/my_project Tests
    # --------------------------------------------------------------------------

    def test_01_valid_claimed_student_can_access_my_project(self):
        """Legitimately claimed student session accesses /api/student/my_project successfully."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-CLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/my_project")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("my_project", data)
        self.assertEqual(data["my_project"]["team_id"], "TEAM-ALPHA")

        # Session must remain intact
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("student_id"), "STU-CLAIMED-01")

    def test_02_unclaimed_student_cannot_access_my_project(self):
        """Stale session for unclaimed student is rejected with 401 on /api/student/my_project."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-UNCLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/my_project")
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success", True))
        self.assertIn("Session invalidated", data.get("error", ""))

        # Stale session must be cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_03_deleted_student_cannot_access_my_project(self):
        """Stale session for non-existent/deleted student is rejected with 401 on /api/student/my_project."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-GHOST-99"
            sess["role"] = "student"

        resp = self.client.get("/api/student/my_project")
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success", True))

        # Stale session must be cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_04_legacy_unclaimed_cohort_student_cannot_access_my_project(self):
        """Legacy cohort student with null claim flag is rejected with 401 on /api/student/my_project."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-LEGACY-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/my_project")
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success", True))

        # Stale session must be cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_05_invalid_session_is_cleared_on_my_project(self):
        """Proves session.clear() wipes entire stale student state upon accessing /api/student/my_project."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-UNCLAIMED-01"
            sess["role"] = "student"
            sess["custom_field"] = "stale_payload"

        resp = self.client.get("/api/student/my_project")
        self.assertEqual(resp.status_code, 401)

        with self.client.session_transaction() as sess:
            self.assertNotIn("student_authenticated", sess)
            self.assertNotIn("student_id", sess)
            self.assertNotIn("custom_field", sess)

    # --------------------------------------------------------------------------
    # 2. /api/student/drafts Tests
    # --------------------------------------------------------------------------

    def test_06_valid_claimed_student_can_access_drafts(self):
        """Legitimately claimed student retrieves their own draft listing plus public exemplar."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-CLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        draft_list = data if isinstance(data, list) else data.get("drafts", [])
        draft_sids = [str(d.get("student_id", "")).upper() for d in draft_list]

        self.assertIn("STU-CLAIMED-01", draft_sids)
        self.assertIn("13989", draft_sids)
        self.assertNotIn("STU-UNCLAIMED-01", draft_sids)

    def test_07_unclaimed_student_cannot_retrieve_private_drafts(self):
        """Unclaimed student session cannot list their private draft; session is invalidated."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-UNCLAIMED-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        draft_list = data if isinstance(data, list) else data.get("drafts", [])
        draft_sids = [str(d.get("student_id", "")).upper() for d in draft_list]

        # Must NOT include the unclaimed student's private draft
        self.assertNotIn("STU-UNCLAIMED-01", draft_sids)
        # Only public exemplar is visible
        self.assertIn("13989", draft_sids)

        # Stale session must be cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_08_deleted_student_cannot_retrieve_private_drafts(self):
        """Non-existent student session cannot list drafts; session is cleared."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-GHOST-99"
            sess["role"] = "student"

        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        draft_list = data if isinstance(data, list) else data.get("drafts", [])
        draft_sids = [str(d.get("student_id", "")).upper() for d in draft_list]

        self.assertNotIn("STU-GHOST-99", draft_sids)
        self.assertIn("13989", draft_sids)

        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_09_legacy_unclaimed_cohort_student_cannot_retrieve_private_drafts(self):
        """Legacy cohort student with null claim flag cannot list private drafts; session cleared."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-LEGACY-01"
            sess["role"] = "student"

        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        draft_list = data if isinstance(data, list) else data.get("drafts", [])
        draft_sids = [str(d.get("student_id", "")).upper() for d in draft_list]

        self.assertNotIn("STU-LEGACY-01", draft_sids)
        self.assertIn("13989", draft_sids)

        with self.client.session_transaction() as sess:
            self.assertNotIn("student_id", sess)

    def test_10_guest_access_to_public_exemplar_drafts_preserved(self):
        """Unauthenticated visitor / guest can still retrieve public exemplar 13989."""
        resp = self.client.get("/api/student/drafts")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        draft_list = data if isinstance(data, list) else data.get("drafts", [])
        draft_sids = [str(d.get("student_id", "")).upper() for d in draft_list]

        self.assertEqual(draft_sids, ["13989"])

    def test_11_faculty_access_remains_unaffected(self):
        """Faculty session can view all drafts and inspect any student on /api/student/my_project."""
        with self.client.session_transaction() as sess:
            sess["faculty_authenticated"] = True
            sess["role"] = "faculty"
            sess["faculty_name"] = "Dr. Coordinator"

        # 1. Faculty on /api/student/drafts retrieves all drafts
        resp_drafts = self.client.get("/api/student/drafts")
        self.assertEqual(resp_drafts.status_code, 200)
        all_d = resp_drafts.get_json()
        all_list = all_d if isinstance(all_d, list) else all_d.get("drafts", [])
        all_sids = [str(d.get("student_id", "")).upper() for d in all_list]

        self.assertIn("STU-CLAIMED-01", all_sids)
        self.assertIn("STU-UNCLAIMED-01", all_sids)
        self.assertIn("13989", all_sids)

        # 2. Faculty on /api/student/my_project?student_id=STU-UNCLAIMED-01 succeeds
        resp_proj = self.client.get("/api/student/my_project?student_id=STU-UNCLAIMED-01")
        self.assertEqual(resp_proj.status_code, 200)
        proj_data = resp_proj.get_json()
        self.assertIn("my_project", proj_data)

        # Faculty session must not be touched or cleared
        with self.client.session_transaction() as sess:
            self.assertTrue(sess.get("faculty_authenticated"))
            self.assertEqual(sess.get("role"), "faculty")

    def test_12_existing_proposal_and_team_authorization_unaffected(self):
        """Claimed student can still read/write own draft and read team workspace."""
        with self.client.session_transaction() as sess:
            sess["student_authenticated"] = True
            sess["student_id"] = "STU-CLAIMED-01"
            sess["role"] = "student"

        # Read own draft
        resp_d = self.client.get("/api/student/draft/STU-CLAIMED-01")
        self.assertEqual(resp_d.status_code, 200)

        # Read team workspace
        resp_ws = self.client.get("/api/teams/TEAM-ALPHA/workspace")
        self.assertEqual(resp_ws.status_code, 200)


if __name__ == "__main__":
    unittest.main()
