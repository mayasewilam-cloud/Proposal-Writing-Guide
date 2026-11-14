"""
BioWriter Studio — Phase 3C.5.2 Account Claiming & Activation Security Regression Test Suite.
Verifies all 23 security requirements for pre-enrolled student account claiming,
faculty-issued one-time activation tokens (OTAT), login protection for unclaimed accounts,
rate limiting, lockout behavior, proposal access restrictions, and persistence atomicity.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import threading
import datetime
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Set test environment flags before importing app
os.environ["FLASK_TESTING"] = "1"
os.environ["SECRET_KEY"] = "biowriter-test-secret-key-32chars-min-len!!"

from app import app
from core import auth_store, cohort_store


class Phase3C52AccountClaimingTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="biowriter_p3c52_test_")
        self.old_data_dir = os.environ.get("BIOWRITER_DATA_DIR")
        os.environ["BIOWRITER_DATA_DIR"] = self.temp_dir

        self.orig_users_file = auth_store.USERS_FILE
        self.orig_cohort_users_file = cohort_store.USERS_FILE
        self.orig_cohort_db = cohort_store.COHORT_DB_FILE
        self.orig_team_ws_dir = cohort_store.TEAM_WORKSPACES_DIR

        self.test_users_file = os.path.join(self.temp_dir, "users.json")
        self.test_cohort_db_file = os.path.join(self.temp_dir, "cohort_db.json")
        self.test_team_ws_dir = os.path.join(self.temp_dir, "team_workspaces")
        self.test_drafts_dir = os.path.join(self.temp_dir, "drafts")

        auth_store.USERS_FILE = self.test_users_file
        cohort_store.USERS_FILE = self.test_users_file
        cohort_store.COHORT_DB_FILE = self.test_cohort_db_file
        cohort_store.TEAM_WORKSPACES_DIR = self.test_team_ws_dir

        os.makedirs(self.test_team_ws_dir, exist_ok=True)
        os.makedirs(self.test_drafts_dir, exist_ok=True)

        # Copy faculty_security.json for faculty authentication
        fac_sec_src = os.path.join(BASE_DIR, "data", "faculty_security.json")
        if os.path.exists(fac_sec_src):
            shutil.copy2(fac_sec_src, os.path.join(self.temp_dir, "faculty_security.json"))

        # Initialize synthetic users and cohort data
        self.seed_test_data()

        app.config["TESTING"] = True
        app.testing = True
        self.client = app.test_client()

        # Reset in-memory rate limits between test runs
        with auth_store._activation_rate_lock:
            auth_store._failed_ip_activation_attempts.clear()

    def tearDown(self):
        if self.old_data_dir:
            os.environ["BIOWRITER_DATA_DIR"] = self.old_data_dir
        else:
            os.environ.pop("BIOWRITER_DATA_DIR", None)

        auth_store.USERS_FILE = self.orig_users_file
        cohort_store.USERS_FILE = self.orig_cohort_users_file
        cohort_store.COHORT_DB_FILE = self.orig_cohort_db
        cohort_store.TEAM_WORKSPACES_DIR = self.orig_team_ws_dir

        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def seed_test_data(self):
        """Sets up synthetic pre-enrolled, claimed, and active student test fixtures."""
        now_str = datetime.datetime.now().strftime("%b %d, %Y - %H:%M")
        
        # Load baseline default users with precomputed hashes to avoid expensive PBKDF2 re-seeding
        users = {}
        users_src = os.path.join(BASE_DIR, "data", "users.json")
        if os.path.exists(users_src):
            try:
                with open(users_src, "r", encoding="utf-8") as uf:
                    users = json.load(uf)
            except Exception:
                users = {}

        # Synthetic users for Phase 3C.5.2 testing
        users.update({
            "STU-PRE-01": {
                "student_id": "STU-PRE-01",
                "student_name": "Pre-Enrolled Student One",
                "email": "stu01@university.edu",
                "role": "student",
                "password_hash": "!UNCLAIMED!",
                "pre_enrolled_by_faculty": True,
                "account_claimed": False,
                "created_at": now_str,
                "last_login": now_str,
            },
            "STU-PRE-02": {
                "student_id": "STU-PRE-02",
                "student_name": "Pre-Enrolled Student Two",
                "email": "stu02@university.edu",
                "role": "student",
                "password_hash": "!UNCLAIMED!",
                "pre_enrolled_by_faculty": True,
                "account_claimed": False,
                "created_at": now_str,
                "last_login": now_str,
            },
            "STU-CLAIMED-01": {
                "student_id": "STU-CLAIMED-01",
                "student_name": "Claimed Student One",
                "email": "claimed01@university.edu",
                "role": "student",
                "password_hash": auth_store.generate_password_hash("activePassword123", method="pbkdf2:sha256", salt_length=16),
                "pre_enrolled_by_faculty": True,
                "account_claimed": True,
                "created_at": now_str,
                "last_login": now_str,
            }
        })
        with open(self.test_users_file, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)

        # Synthetic cohort db
        cdb = {
            "students": {
                "STU-PRE-01": {
                    "student_id": "STU-PRE-01",
                    "student_name": "Pre-Enrolled Student One",
                    "email": "stu01@university.edu",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                },
                "STU-PRE-02": {
                    "student_id": "STU-PRE-02",
                    "student_name": "Pre-Enrolled Student Two",
                    "email": "stu02@university.edu",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                },
                "STU-CLAIMED-01": {
                    "student_id": "STU-CLAIMED-01",
                    "student_name": "Claimed Student One",
                    "email": "claimed01@university.edu",
                    "lab_group": "L1",
                    "team_id": "L1-T1",
                }
            },
            "teams": {
                "L1-T1": {
                    "team_id": "L1-T1",
                    "team_name": "Team BioDetect",
                    "lab_group": "L1",
                    "topic_title": "CRISPR-Cas12a Molecular Diagnostic Biosensor",
                    "student_ids": ["STU-PRE-01", "STU-PRE-02", "STU-CLAIMED-01"]
                }
            }
        }
        with open(self.test_cohort_db_file, "w", encoding="utf-8") as f:
            json.dump(cdb, f, indent=2)

        # Team workspace draft
        ws_draft = {
            "team_id": "L1-T1",
            "title": "CRISPR-Cas12a Molecular Diagnostic Biosensor",
            "hypothesis": "Cas12a fluorescent assay enables single-copy pathogen detection.",
            "team_roster": ["STU-PRE-01", "STU-PRE-02", "STU-CLAIMED-01"]
        }
        with open(os.path.join(self.test_drafts_dir, "STU-CLAIMED-01.json"), "w", encoding="utf-8") as f:
            json.dump(ws_draft, f, indent=2)

    def _login_faculty(self):
        resp = self.client.post("/api/faculty/login", json={"passcode": "faculty2026"})
        self.assertEqual(resp.status_code, 200)

    # -------------------------------------------------------------------------
    # Scenario 1: Student ID alone cannot claim a pre-enrolled account
    # -------------------------------------------------------------------------
    def test_01_student_id_alone_cannot_claim_pre_enrolled_account(self):
        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "student_name": "Impostor",
            "password": "newSecurePassword123"
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Activation token is required", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 2: Missing activation token is rejected
    # -------------------------------------------------------------------------
    def test_02_missing_activation_token_is_rejected(self):
        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": None
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Activation token is required", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 3: Empty or whitespace token is rejected
    # -------------------------------------------------------------------------
    def test_03_empty_or_whitespace_token_is_rejected(self):
        for empty_token in ["", "   ", "\t\n"]:
            resp = self.client.post("/api/auth/register", json={
                "student_id": "STU-PRE-01",
                "password": "newSecurePassword123",
                "activation_token": empty_token
            })
            self.assertEqual(resp.status_code, 400)
            data = resp.get_json()
            self.assertFalse(data["success"])
            self.assertIn("Activation token is required", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 4: Incorrect token is rejected
    # -------------------------------------------------------------------------
    def test_04_incorrect_token_is_rejected(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.assertEqual(tok_resp.status_code, 200)
        self.client.post("/api/faculty/logout")

        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": "0000-1111-2222-3333-4444-5555-6666-7777"
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid or expired activation token", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 5: Correct token successfully claims the account
    # -------------------------------------------------------------------------
    def test_05_correct_token_successfully_claims_account(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.assertEqual(tok_resp.status_code, 200)
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": token
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data.get("claimed_pre_enrolled"))
        self.assertEqual(data["user"]["student_id"], "STU-PRE-01")

        # Verify account is now claimed in storage
        users = auth_store._load_users()
        self.assertTrue(users["STU-PRE-01"]["account_claimed"])
        self.assertNotIn("activation_token_hash", users["STU-PRE-01"])

    # -------------------------------------------------------------------------
    # Scenario 6: Consumed token cannot be reused
    # -------------------------------------------------------------------------
    def test_06_consumed_token_cannot_be_reused(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        # First claim succeeds
        resp1 = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": token
        })
        self.assertEqual(resp1.status_code, 200)

        # Second claim with same token must be rejected
        resp2 = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "secondPassword123",
            "activation_token": token
        })
        self.assertEqual(resp2.status_code, 400)
        data = resp2.get_json()
        self.assertIn("already registered", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 7: Expired token is rejected
    # -------------------------------------------------------------------------
    def test_07_expired_token_is_rejected(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        # Manually expire token in storage
        users = auth_store._load_users()
        past_date = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        users["STU-PRE-01"]["activation_token_expires_at"] = past_date
        auth_store._save_users(users)

        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": token
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("expired", data["error"].lower())

    # -------------------------------------------------------------------------
    # Scenario 8: Token issued to another student cannot be used
    # -------------------------------------------------------------------------
    def test_08_token_issued_to_another_student_cannot_be_used(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token_for_01 = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        # Attacker tries to use student 01's token to claim student 02's account
        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-02",
            "password": "newSecurePassword123",
            "activation_token": token_for_01
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid or expired activation token", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 9: Regenerated token invalidates previous token
    # -------------------------------------------------------------------------
    def test_09_regenerated_token_invalidates_previous_token(self):
        self._login_faculty()
        # First issuance
        tok1_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token1 = tok1_resp.get_json()["activation_token"]

        # Regeneration
        tok2_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token2 = tok2_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        self.assertNotEqual(token1, token2)

        # Attempt claim with token 1 (should fail)
        resp1 = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": token1
        })
        self.assertEqual(resp1.status_code, 400)

        # Attempt claim with token 2 (should succeed)
        resp2 = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "newSecurePassword123",
            "activation_token": token2
        })
        self.assertEqual(resp2.status_code, 200)

    # -------------------------------------------------------------------------
    # Scenario 10: Unauthorized faculty cannot issue or regenerate tokens
    # -------------------------------------------------------------------------
    def test_10_unauthorized_faculty_cannot_issue_or_regenerate_tokens(self):
        # Unauthenticated request
        resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.assertEqual(resp.status_code, 403)

        # Authenticated student trying to access faculty endpoint
        login_resp = self.client.post("/api/auth/login", json={
            "student_id": "STU-CLAIMED-01",
            "password": "activePassword123"
        })
        self.assertEqual(login_resp.status_code, 200)

        resp2 = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.assertEqual(resp2.status_code, 403)

    # -------------------------------------------------------------------------
    # Scenario 11: Authorized faculty can issue token for unclaimed account
    # -------------------------------------------------------------------------
    def test_11_authorized_faculty_can_issue_token_for_unclaimed_account(self):
        self._login_faculty()
        resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("activation_token", data)
        self.assertEqual(data["student_id"], "STU-PRE-01")
        # Token format: 8 groups of 4 separated by hyphens (32 hex characters)
        raw = data["activation_token"].replace("-", "")
        self.assertEqual(len(raw), 32)

    # -------------------------------------------------------------------------
    # Scenario 12: Claimed accounts cannot be claimed again
    # -------------------------------------------------------------------------
    def test_12_claimed_accounts_cannot_be_claimed_again(self):
        self._login_faculty()
        # Faculty cannot issue token for already claimed student
        resp_tok = self.client.post("/api/faculty/students/STU-CLAIMED-01/activation-token")
        self.assertEqual(resp_tok.status_code, 400)
        self.assertIn("already been claimed", resp_tok.get_json()["error"])
        self.client.post("/api/faculty/logout")

        # Claim attempt on already claimed student is rejected
        resp_reg = self.client.post("/api/auth/register", json={
            "student_id": "STU-CLAIMED-01",
            "password": "anotherPassword123",
            "activation_token": "some-token"
        })
        self.assertEqual(resp_reg.status_code, 400)
        self.assertIn("already registered", resp_reg.get_json()["error"])

    # -------------------------------------------------------------------------
    # Scenario 13: An unclaimed account cannot log in with bio123
    # -------------------------------------------------------------------------
    def test_13_unclaimed_account_cannot_log_in_with_bio123(self):
        for pwd in ["bio123", "password123", "!UNCLAIMED!"]:
            resp = self.client.post("/api/auth/login", json={
                "student_id": "STU-PRE-01",
                "password": pwd
            })
            self.assertEqual(resp.status_code, 401)
            data = resp.get_json()
            self.assertFalse(data["success"])
            self.assertIn("not been activated", data["error"])

    # -------------------------------------------------------------------------
    # Scenario 14: An unclaimed account cannot access proposal or team workspace data
    # -------------------------------------------------------------------------
    def test_14_unclaimed_account_cannot_access_proposal_data(self):
        # Direct proposal fetch for unclaimed student must be rejected
        resp = self.client.get("/api/student/draft/STU-PRE-01")
        self.assertEqual(resp.status_code, 403)

        # Team workspace fetch
        resp2 = self.client.get("/api/teams/L1-T1/workspace")
        self.assertEqual(resp2.status_code, 403)

    # -------------------------------------------------------------------------
    # Scenario 15: Successful claiming permits normal login and proposal access
    # -------------------------------------------------------------------------
    def test_15_successful_claiming_permits_normal_login_and_proposal_access(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        # Claim account
        claim_resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "myNewGraduationPassword99",
            "activation_token": token
        })
        self.assertEqual(claim_resp.status_code, 200)

        # Logout
        self.client.post("/api/auth/logout")

        # Login with newly established credentials
        login_resp = self.client.post("/api/auth/login", json={
            "student_id": "STU-PRE-01",
            "password": "myNewGraduationPassword99"
        })
        self.assertEqual(login_resp.status_code, 200)

        # Save proposal draft under authorized session
        save_resp = self.client.post("/api/student/save_draft", json={
            "draft": {
                "title": "CRISPR-Cas12a Molecular Diagnostic Biosensor",
                "hypothesis": "Fluorescent assay detects pathogens at single-copy resolution."
            }
        })
        self.assertEqual(save_resp.status_code, 200)

        # Access authorized proposal draft
        draft_resp = self.client.get("/api/student/draft/STU-PRE-01")
        self.assertEqual(draft_resp.status_code, 200)

    # -------------------------------------------------------------------------
    # Scenario 16: Invalid activation attempts trigger rate limits
    # -------------------------------------------------------------------------
    def test_16_invalid_activation_attempts_trigger_rate_limits(self):
        self._login_faculty()
        self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        self.client.post("/api/faculty/logout")

        # Submit 5 invalid activation attempts
        for i in range(5):
            resp = self.client.post("/api/auth/register", json={
                "student_id": "STU-PRE-01",
                "password": "validPassword123",
                "activation_token": f"wrong-token-{i}-00000000000000000000"
            })
            self.assertEqual(resp.status_code, 400)

        # 6th attempt triggers temporary lockout
        lock_resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "validPassword123",
            "activation_token": "wrong-token-6-00000000000000000000"
        })
        self.assertEqual(lock_resp.status_code, 400)
        self.assertIn("temporarily locked", lock_resp.get_json()["error"])

    # -------------------------------------------------------------------------
    # Scenario 17: Rate limits do not create permanent account lockout
    # -------------------------------------------------------------------------
    def test_17_rate_limits_do_not_create_permanent_lockout(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        # Lock account
        users = auth_store._load_users()
        users["STU-PRE-01"]["activation_locked_until"] = (datetime.datetime.now() - datetime.timedelta(minutes=1)).isoformat()
        auth_store._save_users(users)

        # After lockout window expires, valid claim succeeds
        resp = self.client.post("/api/auth/register", json={
            "student_id": "STU-PRE-01",
            "password": "validPassword123",
            "activation_token": token
        })
        self.assertEqual(resp.status_code, 200)

    # -------------------------------------------------------------------------
    # Scenario 18: Simultaneous claim attempts result in exactly one claim
    # -------------------------------------------------------------------------
    def test_18_simultaneous_claim_attempts_result_in_one_success(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        results = []
        def claim_worker(worker_id):
            client = app.test_client()
            resp = client.post("/api/auth/register", json={
                "student_id": "STU-PRE-01",
                "password": f"concurrentPassword{worker_id}!",
                "activation_token": token
            })
            results.append((resp.status_code, resp.get_json()))

        threads = [threading.Thread(target=claim_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r[0] == 200 and r[1].get("success")]
        self.assertEqual(len(successes), 1, "Exactly one concurrent claim attempt must succeed")

    # -------------------------------------------------------------------------
    # Scenario 19: Persistence failure does not create successful session
    # -------------------------------------------------------------------------
    def test_19_persistence_failure_does_not_create_session(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        token = tok_resp.get_json()["activation_token"]
        self.client.post("/api/faculty/logout")

        with patch("core.auth_store._save_users", side_effect=IOError("Simulated disk error")):
            with self.assertRaises(IOError):
                auth_store.register_student("STU-PRE-01", "Name", "validPassword123", activation_token=token)

        # Ensure account is still unclaimed
        users = auth_store._load_users()
        self.assertFalse(users["STU-PRE-01"]["account_claimed"])

    # -------------------------------------------------------------------------
    # Scenario 20: Public APIs never expose plaintext tokens or hashes
    # -------------------------------------------------------------------------
    def test_20_public_apis_never_expose_tokens_or_hashes(self):
        self._login_faculty()
        tok_resp = self.client.post("/api/faculty/students/STU-PRE-01/activation-token")
        raw_token = tok_resp.get_json()["activation_token"].replace("-", "").lower()
        self.client.post("/api/faculty/logout")

        # Test cohort overview
        resp = self.client.get("/api/faculty/cohort/overview")
        text = resp.get_data(as_text=True)
        self.assertNotIn(raw_token, text)
        self.assertNotIn("activation_token_hash", text)
        self.assertNotIn("activation_token_salt", text)

        # Test student directory
        resp2 = self.client.get("/api/faculty/students")
        text2 = resp2.get_data(as_text=True)
        self.assertNotIn(raw_token, text2)
        self.assertNotIn("activation_token_hash", text2)

    # -------------------------------------------------------------------------
    # Scenario 21: Non-pre-enrolled registration follows existing policy
    # -------------------------------------------------------------------------
    def test_21_non_pre_enrolled_open_registration(self):
        new_id = f"NEW-STU-{int(time.time())}"
        resp = self.client.post("/api/auth/register", json={
            "student_id": new_id,
            "student_name": "Open Enrolled Student",
            "password": "secureOpenPassword123"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["student_id"], new_id)

    # -------------------------------------------------------------------------
    # Scenario 22: Existing faculty login and cohort management functional
    # -------------------------------------------------------------------------
    def test_22_existing_faculty_login_and_cohort_management(self):
        # Login
        self._login_faculty()

        # Overview
        resp = self.client.get("/api/faculty/cohort/overview")
        self.assertEqual(resp.status_code, 200)

        # Add student
        add_resp = self.client.post("/api/faculty/students", json={
            "student_id": "NEW-FAC-ADD-01",
            "student_name": "Faculty Added Student",
            "lab_group": "L1",
            "email": "added@nu.edu.eg"
        })
        self.assertEqual(add_resp.status_code, 200)

    # -------------------------------------------------------------------------
    # Scenario 23: Existing claimed student login remains functional
    # -------------------------------------------------------------------------
    def test_23_existing_claimed_student_login_remains_functional(self):
        resp = self.client.post("/api/auth/login", json={
            "student_id": "STU-CLAIMED-01",
            "password": "activePassword123"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["student_id"], "STU-CLAIMED-01")


if __name__ == "__main__":
    unittest.main()
