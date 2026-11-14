"""
BioWriter Studio - Phase 3C.5.8 Test Suite:
- Verification of Protected Exemplar 13989 Synchronization Immunity:
  Ensures that when team members update a shared team workspace, protected exemplar
  student drafts (e.g. 13989) are NEVER overwritten via team workspace mirroring.
- Verification of Test Suite Isolation:
  Ensures test fixtures strictly isolate cohort_db.json and never fall back to live persistent storage.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"

import app as portal_app
from core import auth_store, cohort_store, draft_store


class Phase3C58ExemplarSyncAndIsolationTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="biowriter_p3c58_test_")
        self.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir

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

        # Copy faculty_security.json for faculty authentication
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fac_sec_src = os.path.join(base_dir, "data", "faculty_security.json")
        if os.path.exists(fac_sec_src):
            shutil.copy2(fac_sec_src, os.path.join(self.temp_dir, "faculty_security.json"))

        # Seed synthetic isolated data
        self._seed_test_environment()

        portal_app.app.config["TESTING"] = True
        portal_app.app.testing = True
        self.client = portal_app.app.test_client()

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

    def _seed_test_environment(self):
        # 1. Seed users.json
        pwd_hash = generate_password_hash("Password123!", method="pbkdf2:sha256", salt_length=16)
        users_data = {
            "13989": {
                "student_id": "13989",
                "student_name": "Maya Abdelrazek",
                "email": "m.abdelrazek@nu.edu.eg",
                "password_hash": pwd_hash,
                "account_claimed": True,
                "role": "student",
                "lab_group": "L1",
                "team_id": "L1-T1",
            },
            "20230001": {
                "student_id": "20230001",
                "student_name": "Ahmed Ali",
                "email": "ahmed.ali@student.edu.eg",
                "password_hash": pwd_hash,
                "account_claimed": True,
                "role": "student",
                "lab_group": "L1",
                "team_id": "L1-T1",
            },
            "20230002": {
                "student_id": "20230002",
                "student_name": "Sara Mohamed",
                "email": "sara.mohamed@student.edu.eg",
                "password_hash": pwd_hash,
                "account_claimed": True,
                "role": "student",
                "lab_group": "L1",
                "team_id": "L1-T1",
            },
        }
        with open(self.test_users_file, "w", encoding="utf-8") as f:
            json.dump(users_data, f)

        # 2. Seed cohort_db.json
        cohort_data = {
            "active_semester": "Fall 2026",
            "active_course_id": "BT_301",
            "semesters": ["Fall 2026"],
            "students": {
                "13989": {
                    "student_id": "13989",
                    "student_name": "Maya Abdelrazek",
                    "email": "m.abdelrazek@nu.edu.eg",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
                "20230001": {
                    "student_id": "20230001",
                    "student_name": "Ahmed Ali",
                    "email": "ahmed.ali@student.edu.eg",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
                "20230002": {
                    "student_id": "20230002",
                    "student_name": "Sara Mohamed",
                    "email": "sara.mohamed@student.edu.eg",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                },
            },
            "lab_groups": {
                "Fall 2026::BT_301::L1": {
                    "lab_group_id": "L1",
                    "name": "Lab Group 1 (L1)",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                }
            },
            "teams": {
                "L1-T1": {
                    "team_id": "L1-T1",
                    "team_name": "Team 1 — DETECTR-Aqua",
                    "lab_group": "L1",
                    "semester": "Fall 2026",
                    "course_id": "BT_301",
                    "student_ids": ["13989", "20230001", "20230002"],
                    "pi_id": "PI-RANIA",
                    "pi_name": "Dr. Rania Hassan",
                    "topic_title": "DETECTR-Aqua: A CRISPR-Cas12a-Assisted Isothermal Assay",
                    "status": "active",
                }
            },
            "pis": {
                "PI-RANIA": {
                    "pi_id": "PI-RANIA",
                    "name": "Dr. Rania Hassan",
                    "role": "pi",
                }
            },
            "audit_history": [],
        }
        with open(self.test_cohort_db_file, "w", encoding="utf-8") as f:
            json.dump(cohort_data, f)

        # 3. Seed individual drafts
        self.original_exemplar_title = "Original Exemplar DETECTR-Aqua Title"
        self.original_exemplar_abstract = "This is the pristine, immutable exemplar abstract."
        exemplar_draft = {
            "student_id": "13989",
            "student_name": "Maya Abdelrazek",
            "title": self.original_exemplar_title,
            "abstract": self.original_exemplar_abstract,
            "chassis": "Cell-free",
        }
        with open(os.path.join(self.test_drafts_dir, "13989.json"), "w", encoding="utf-8") as f:
            json.dump(exemplar_draft, f)

        teammate_draft = {
            "student_id": "20230001",
            "student_name": "Ahmed Ali",
            "title": "Ahmed's Initial Draft",
            "abstract": "Initial draft text.",
        }
        with open(os.path.join(self.test_drafts_dir, "20230001.json"), "w", encoding="utf-8") as f:
            json.dump(teammate_draft, f)

    def _login_student(self, student_id: str = "20230001", password: str = "Password123!"):
        resp = self.client.post(
            "/api/auth/login",
            json={"identifier": student_id, "password": password},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()

    def _login_faculty(self, passcode: str = "faculty2026"):
        resp = self.client.post("/api/faculty/login", json={"passcode": passcode})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()

    # =========================================================================
    # REPAIR 1: PROTECTED EXEMPLAR SYNCHRONIZATION IMMUNITY
    # =========================================================================

    def test_01_update_team_workspace_skips_protected_exemplar(self):
        """Calling update_team_workspace mirrors drafts to ordinary teammates but skips exemplar 13989."""
        payload = {
            "proposal_draft": {
                "title": "Modified By Teammate",
                "abstract": "Teammate changed the abstract entirely.",
            }
        }
        res = cohort_store.update_team_workspace(
            team_id="L1-T1",
            payload=payload,
            actor_id="20230001",
            actor_name="Ahmed Ali",
            actor_role="student",
        )
        self.assertTrue(res["success"])

        # Teammate 20230001 draft MUST be updated
        draft_20230001 = draft_store.get_student_draft("20230001")
        self.assertIsNotNone(draft_20230001)
        self.assertEqual(draft_20230001.get("title"), "Modified By Teammate")

        # Protected exemplar 13989 draft MUST REMAIN COMPLETELY UNTOUCHED!
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertIsNotNone(draft_13989)
        self.assertEqual(draft_13989.get("title"), self.original_exemplar_title)
        self.assertEqual(draft_13989.get("abstract"), self.original_exemplar_abstract)

    def test_02_student_save_draft_does_not_overwrite_exemplar_via_sync(self):
        """When an authenticated teammate saves draft via /api/student/save_draft,
        the team workspace sync mirrors to teammates but leaves 13989 untouched."""
        self._login_student("20230001")
        resp = self.client.post(
            "/api/student/save_draft",
            json={
                "student_data": {
                    "title": "Ahmed's New Title via API",
                    "abstract": "Ahmed's new abstract submitted through save_draft endpoint.",
                }
            },
        )
        self.assertEqual(resp.status_code, 200)

        # Verify teammate 20230001 draft was updated
        draft_20230001 = draft_store.get_student_draft("20230001")
        self.assertEqual(draft_20230001.get("title"), "Ahmed's New Title via API")

        # Verify exemplar 13989 was NOT overwritten
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertEqual(draft_13989.get("title"), self.original_exemplar_title)
        self.assertEqual(draft_13989.get("abstract"), self.original_exemplar_abstract)

    def test_03_team_workspace_put_does_not_overwrite_exemplar(self):
        """When a teammate updates workspace via PUT /api/teams/<team_id>/workspace,
        exemplar 13989 is protected from being overwritten."""
        self._login_student("20230001")
        resp = self.client.put(
            "/api/teams/L1-T1/workspace",
            json={
                "proposal_draft": {
                    "title": "Shared Workspace PUT Title",
                    "abstract": "Shared workspace PUT abstract.",
                }
            },
        )
        self.assertEqual(resp.status_code, 200)

        # Verify teammate draft updated
        draft_20230001 = draft_store.get_student_draft("20230001")
        self.assertEqual(draft_20230001.get("title"), "Shared Workspace PUT Title")

        # Verify exemplar 13989 preserved intact
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertEqual(draft_13989.get("title"), self.original_exemplar_title)

    def test_04_direct_student_write_to_exemplar_denied(self):
        """Direct attempt by a student session to write to 13989 is blocked or coerced to own ID."""
        self._login_student("20230001")
        # Direct save_draft for 13989 is coerced to 20230001
        resp = self.client.post(
            "/api/student/save_draft",
            json={
                "student_id": "13989",
                "student_data": {
                    "title": "Malicious Tamper Title",
                },
            },
        )
        self.assertEqual(resp.status_code, 200)
        # Verify 13989 was NOT altered
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertEqual(draft_13989.get("title"), self.original_exemplar_title)

    def test_05_guest_direct_write_to_exemplar_forbidden(self):
        """Unauthenticated guest cannot write to protected exemplar 13989."""
        self.client.get("/api/auth/logout")
        resp = self.client.post(
            "/api/student/save_draft",
            json={
                "student_id": "13989",
                "student_data": {"title": "Guest Tampering"},
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("error", resp.get_json())
        # Verify 13989 untouched
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertEqual(draft_13989.get("title"), self.original_exemplar_title)

    def test_06_faculty_direct_write_to_exemplar_permitted(self):
        """Faculty administrators maintain explicit write permissions for exemplars."""
        self._login_faculty()
        resp = self.client.post(
            "/api/student/save_draft",
            json={
                "student_id": "13989",
                "student_data": {
                    "title": "Faculty Updated Exemplar Title",
                    "abstract": "Faculty updated exemplar abstract.",
                },
            },
        )
        self.assertEqual(resp.status_code, 200)
        draft_13989 = draft_store.get_student_draft("13989")
        self.assertEqual(draft_13989.get("title"), "Faculty Updated Exemplar Title")

    def test_07_all_canonical_exemplar_ids_protected(self):
        """All IDs in PROTECTED_EXEMPLAR_IDS are immune to team sync overwriting."""
        protected_ids = cohort_store.get_protected_exemplar_ids()
        self.assertIn("13989", protected_ids)
        self.assertIn("CUSTOM-TOPIC-01", protected_ids)
        self.assertIn("BT301-NANOMED", protected_ids)
        self.assertIn("BT301-BIOCAT", protected_ids)

    # =========================================================================
    # REPAIR 2: TEST FIXTURE ISOLATION VERIFICATION
    # =========================================================================

    def test_08_test_fixture_creates_cohort_db_on_disk(self):
        """Verifies that the setUp() pattern creates cohort_db.json on disk so _load_db()
        never falls back to bundled live data."""
        isolated_dir = tempfile.mkdtemp(prefix="biowriter_fixture_check_")
        try:
            temp_cohort_file = os.path.join(isolated_dir, "cohort_db.json")
            with open(temp_cohort_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

            orig_cohort_db = cohort_store.COHORT_DB_FILE
            orig_env = os.environ.get("BIOWRITER_DATA_DIR")
            try:
                cohort_store.COHORT_DB_FILE = temp_cohort_file
                os.environ["BIOWRITER_DATA_DIR"] = isolated_dir

                # Calling _load_db() MUST load the isolated file and not the live bundled file
                loaded = cohort_store._load_db()
                self.assertIsInstance(loaded, dict)
                # The file on disk in isolated_dir MUST have been populated with default seeds
                self.assertTrue(os.path.exists(temp_cohort_file))
                self.assertGreater(os.path.getsize(temp_cohort_file), 50)
            finally:
                cohort_store.COHORT_DB_FILE = orig_cohort_db
                if orig_env is not None:
                    os.environ["BIOWRITER_DATA_DIR"] = orig_env
                else:
                    os.environ.pop("BIOWRITER_DATA_DIR", None)
        finally:
            shutil.rmtree(isolated_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
